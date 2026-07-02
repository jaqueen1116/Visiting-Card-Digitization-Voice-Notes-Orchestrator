import os
import base64
import json
import asyncio
import time
import socket
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Tuple
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from app.config import settings, logger
from app.models.contact import ContactCard

def is_transient_error(e: Exception) -> bool:
    """
    Determine if an exception is transient and warrants a retry.
    Transient errors include HTTP 429, 5xx server errors, socket timeouts, and connection resets.
    Permanent errors (authentication 401/403, 400 bad request, 404 not found) are NOT retried.
    """
    if isinstance(e, HttpError):
        try:
            status = e.resp.status
            # Retry on rate limit (429) or transient server errors (5xx)
            if status == 429 or (status >= 500 and status < 600):
                return True
        except AttributeError:
            pass
        return False
        
    # Retry on standard socket, timeout, or reset errors
    if isinstance(e, (socket.timeout, TimeoutError, ConnectionResetError, ConnectionAbortedError)):
        return True
        
    # Check for text indications of timeout / socket reset
    err_str = str(e).lower()
    transient_keywords = ["timeout", "timed out", "connection reset", "eof occurred", "handshake disruption"]
    if any(kw in err_str for kw in transient_keywords):
        return True
        
    return False

class GoogleSheetsService:
    """
    Synchronous implementation of Google Sheets API client calls.
    All public calls should be routed through AsyncGoogleSheetsService to avoid blocking.
    """
    def __init__(self):
        self.scopes = ["https://www.googleapis.com/auth/spreadsheets"]
        self.spreadsheet_id = settings.GOOGLE_SHEETS_ID
        self._creds = None
        self._service = None

    def _get_creds(self) -> Credentials:
        if self._creds:
            return self._creds
        
        # 1. Try loading from GOOGLE_SHEETS_JSON_CREDS_BASE64 if provided
        if settings.GOOGLE_SHEETS_JSON_CREDS_BASE64:
            try:
                logger.info("Loading Google Sheets credentials from Base64 env variable.")
                creds_json = base64.b64decode(settings.GOOGLE_SHEETS_JSON_CREDS_BASE64).decode("utf-8")
                creds_info = json.loads(creds_json)
                self._creds = Credentials.from_service_account_info(creds_info, scopes=self.scopes)
                return self._creds
            except Exception as e:
                logger.error(f"Failed to load credentials from Base64: {str(e)}")
                raise e

        # 2. Fall back to loading from file path specified by GOOGLE_APPLICATION_CREDENTIALS
        credentials_file = settings.GOOGLE_APPLICATION_CREDENTIALS or os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        if credentials_file:
            try:
                logger.info(f"Loading Google Sheets credentials from service account file: {credentials_file}")
                # Resolve relative paths against backend root
                if not os.path.isabs(credentials_file):
                    backend_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                    resolved_path = os.path.join(backend_root, credentials_file)
                else:
                    resolved_path = credentials_file
                
                if os.path.exists(resolved_path):
                    self._creds = Credentials.from_service_account_file(resolved_path, scopes=self.scopes)
                    return self._creds
                else:
                    logger.error(f"Credentials file not found at: {resolved_path}")
            except Exception as e:
                logger.error(f"Failed to load credentials from service account file {credentials_file}: {str(e)}")
                raise e

        logger.error("No Google Sheets credentials found. Set GOOGLE_SHEETS_JSON_CREDS_BASE64 or GOOGLE_APPLICATION_CREDENTIALS.")
        raise ValueError("Google Sheets credentials are not configured.")

    def _get_service(self):
        if self._service:
            return self._service
        
        try:
            creds = self._get_creds()
            import httplib2
            # Configure Http client transport with unified 30s timeout
            http_client = httplib2.Http(timeout=30.0)
            authorized_http = creds.authorize(http_client)
            self._service = build("sheets", "v4", http=authorized_http, cache_discovery=False)
            return self._service
        except Exception as e:
            logger.error(f"Failed to build Google Sheets service client: {str(e)}")
            raise e

    def _get_all_rows(self) -> List[List[Any]]:
        try:
            service = self._get_service()
            sheet = service.spreadsheets()
            result = sheet.values().get(
                spreadsheetId=self.spreadsheet_id,
                range="Sheet1!A:H"
            ).execute()
            return result.get("values", [])
        except Exception as e:
            logger.error(f"Failed to fetch rows from Google Sheets: {str(e)}")
            raise e

    def _initialize_headers(self) -> None:
        try:
            rows = self._get_all_rows()
            if not rows:
                headers = [["UUID", "Name", "Phone", "Email", "Company", "Voice Notes", "Created At", "Updated At"]]
                service = self._get_service()
                sheet = service.spreadsheets()
                sheet.values().update(
                    spreadsheetId=self.spreadsheet_id,
                    range="Sheet1!A1",
                    valueInputOption="RAW",
                    body={"values": headers}
                ).execute()
                logger.info("Initialized Google Sheet headers.")
        except Exception as e:
            logger.error(f"Failed to check/initialize sheet headers: {str(e)}")
            raise e

    def _row_to_dict(self, headers: List[str], row: List[Any]) -> Dict[str, Any]:
        contact = {}
        for i, header in enumerate(headers):
            val = row[i] if i < len(row) else ""
            contact[header.lower().replace(" ", "_")] = val
        return contact

    def _find_duplicate(self, email: Optional[str], phone: Optional[str]) -> Optional[Dict[str, Any]]:
        rows = self._get_all_rows()
        if not rows or len(rows) <= 1:
            return None
        
        headers = [h.strip() for h in rows[0]]
        try:
            email_idx = headers.index("Email")
            phone_idx = headers.index("Phone")
        except ValueError as e:
            logger.error(f"Required Email or Phone headers missing in Google Sheet: {str(e)}")
            return None

        email_norm = email.strip().lower() if email else None
        phone_norm = "".join(filter(str.isdigit, phone)) if phone else None

        for row in rows[1:]:
            row_email = row[email_idx].strip().lower() if len(row) > email_idx and row[email_idx] else None
            row_phone = "".join(filter(str.isdigit, row[phone_idx])) if len(row) > phone_idx and row[phone_idx] else None
            
            if email_norm and row_email == email_norm:
                logger.info(f"Duplicate found matching email: {email}")
                return self._row_to_dict(headers, row)
            if phone_norm and row_phone == phone_norm:
                logger.info(f"Duplicate found matching phone number: {phone}")
                return self._row_to_dict(headers, row)
                
        return None

    def _verify_row_written(self, uuid: str) -> bool:
        """
        Verify that a row with the given UUID exists in the spreadsheet.
        """
        try:
            rows = self._get_all_rows()
            if not rows or len(rows) <= 1:
                return False
            headers = [h.strip() for h in rows[0]]
            uuid_idx = headers.index("UUID")
            for row in rows[1:]:
                if len(row) > uuid_idx and row[uuid_idx] == uuid:
                    return True
            return False
        except Exception as e:
            logger.warning(f"Row verification failed during check: {str(e)}")
            return False

    def _verify_voice_note_updated(self, uuid: str, expected_notes: str) -> bool:
        """
        Verify that the voice notes cell for the given UUID contains the expected notes.
        """
        try:
            rows = self._get_all_rows()
            if not rows or len(rows) <= 1:
                return False
            headers = [h.strip() for h in rows[0]]
            uuid_idx = headers.index("UUID")
            vn_idx = headers.index("Voice Notes")
            for row in rows[1:]:
                if len(row) > uuid_idx and row[uuid_idx] == uuid:
                    val = row[vn_idx] if len(row) > vn_idx else ""
                    return val.strip() == expected_notes.strip()
            return False
        except Exception as e:
            logger.warning(f"Voice note cell verification failed: {str(e)}")
            return False

    def _insert_contact(self, contact: ContactCard) -> Dict[str, Any]:
        self._initialize_headers()
        
        # Guard against duplicate phone or email
        dup = self._find_duplicate(contact.email, contact.phone)
        if dup:
            logger.info("Skipping contact insertion. Duplicate match found.")
            return {"status": "duplicate", "contact": dup}
        
        now_str = datetime.now(timezone.utc).isoformat()
        row_data = [
            contact.uuid,
            contact.name or "",
            contact.phone or "",
            contact.email or "",
            contact.company or "",
            contact.voice_notes or "",
            now_str,
            now_str
        ]
        
        logger.info(f"Starting Google Sheets contact write for UUID: {contact.uuid}")
        start_time = datetime.now(timezone.utc)
        
        MAX_RETRIES = 3
        BACKOFF_FACTOR = 2.0
        
        for attempt in range(1, MAX_RETRIES + 1):
            attempt_start = datetime.now(timezone.utc)
            try:
                service = self._get_service()
                sheet = service.spreadsheets()
                
                logger.info(f"Google Sheets append attempt {attempt}/{MAX_RETRIES} for UUID: {contact.uuid}")
                sheet.values().append(
                    spreadsheetId=self.spreadsheet_id,
                    range="Sheet1!A:H",
                    valueInputOption="RAW",
                    body={"values": [row_data]}
                ).execute()
                
                # Strict verification check
                logger.info(f"Verifying Google Sheets write for UUID: {contact.uuid}...")
                verified = self._verify_row_written(contact.uuid)
                if not verified:
                    raise ValueError(f"Google Sheets row verification failed. Row with UUID {contact.uuid} was not found after execution.")
                
                total_duration = (datetime.now(timezone.utc) - start_time).total_seconds()
                logger.info(f"Google Sheets contact write successful and verified. Total duration: {total_duration:.2f}s")
                return {"status": "inserted", "uuid": contact.uuid}
                
            except Exception as e:
                attempt_duration = (datetime.now(timezone.utc) - attempt_start).total_seconds()
                total_duration = (datetime.now(timezone.utc) - start_time).total_seconds()
                
                is_transient = is_transient_error(e)
                err_msg = str(e)
                
                if is_transient and attempt < MAX_RETRIES:
                    backoff_delay = BACKOFF_FACTOR ** attempt
                    logger.warning(
                        f"Transient failure on Sheets append attempt {attempt} (attempt duration: {attempt_duration:.2f}s, "
                        f"total duration: {total_duration:.2f}s): {err_msg}. Retrying in {backoff_delay}s..."
                    )
                    time.sleep(backoff_delay)
                else:
                    logger.error(
                        f"Permanent error or exhausted retries on Sheets append (attempt: {attempt}/{MAX_RETRIES}, "
                        f"total duration: {total_duration:.2f}s): {err_msg}"
                    )
                    raise e

    def _update_voice_note(self, uuid: str, transcript: str) -> bool:
        logger.info(f"Starting Google Sheets voice note update transaction for UUID: {uuid}")
        start_time = datetime.now(timezone.utc)
        
        MAX_RETRIES = 3
        BACKOFF_FACTOR = 2.0
        
        for attempt in range(1, MAX_RETRIES + 1):
            attempt_start = datetime.now(timezone.utc)
            try:
                # Place read, formatting, and update inside loop to resolve transient read errors
                rows = self._get_all_rows()
                if not rows or len(rows) <= 1:
                    logger.error("No contacts available to update voice notes.")
                    return False
                
                headers = [h.strip() for h in rows[0]]
                try:
                    uuid_idx = headers.index("UUID")
                    vn_idx = headers.index("Voice Notes")
                except ValueError as e:
                    logger.error(f"Missing required UUID or Voice Notes columns in sheet for updates: {str(e)}")
                    return False

                updated_idx = None
                for candidate in ["Updated At", "Updated_At"]:
                    try:
                        updated_idx = headers.index(candidate)
                        break
                    except ValueError:
                        continue

                row_num = -1
                existing_voice_notes = ""
                for idx, row in enumerate(rows[1:], start=2):
                    if len(row) > uuid_idx and row[uuid_idx] == uuid:
                        row_num = idx
                        existing_voice_notes = row[vn_idx] if len(row) > vn_idx else ""
                        break
                        
                if row_num == -1:
                    logger.error(f"Contact with UUID {uuid} not found in Google Sheets.")
                    return False
                    
                # Append transcription notes with formatted timestamps
                timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
                formatted_note = f"[{timestamp}]: {transcript}"
                new_voice_notes = f"{existing_voice_notes}\n{formatted_note}".strip()
                
                now_str = datetime.now(timezone.utc).isoformat()
                
                service = self._get_service()
                sheet = service.spreadsheets()
                
                logger.info(f"Google Sheets update attempt {attempt}/{MAX_RETRIES} for voice note UUID: {uuid}")
                # Update Voice Notes cell
                sheet.values().update(
                    spreadsheetId=self.spreadsheet_id,
                    range=f"Sheet1!{self._col_letter(vn_idx + 1)}{row_num}",
                    valueInputOption="RAW",
                    body={"values": [[new_voice_notes]]}
                ).execute()
                
                # Update Updated At timestamp cell if present
                if updated_idx is not None:
                    sheet.values().update(
                        spreadsheetId=self.spreadsheet_id,
                        range=f"Sheet1!{self._col_letter(updated_idx + 1)}{row_num}",
                        valueInputOption="RAW",
                        body={"values": [[now_str]]}
                    ).execute()
                
                # Strict cell write verification check
                logger.info(f"Verifying Google Sheets voice note update for UUID: {uuid}...")
                verified = self._verify_voice_note_updated(uuid, new_voice_notes)
                if not verified:
                    raise ValueError(f"Google Sheets cell verification failed. Voice notes cell for UUID {uuid} was not updated.")
                
                total_duration = (datetime.now(timezone.utc) - start_time).total_seconds()
                logger.info(f"Updated Google Sheets contact UUID: {uuid} successfully and verified. Total duration: {total_duration:.2f}s")
                return True
                
            except Exception as e:
                attempt_duration = (datetime.now(timezone.utc) - attempt_start).total_seconds()
                total_duration = (datetime.now(timezone.utc) - start_time).total_seconds()
                
                is_transient = is_transient_error(e)
                err_msg = str(e)
                
                if is_transient and attempt < MAX_RETRIES:
                    backoff_delay = BACKOFF_FACTOR ** attempt
                    logger.warning(
                        f"Transient failure on Sheets update attempt {attempt} (attempt duration: {attempt_duration:.2f}s, "
                        f"total duration: {total_duration:.2f}s): {err_msg}. Retrying in {backoff_delay}s..."
                    )
                    time.sleep(backoff_delay)
                else:
                    logger.error(
                        f"Permanent error or exhausted retries on Sheets update (attempt: {attempt}/{MAX_RETRIES}, "
                        f"total duration: {total_duration:.2f}s): {err_msg}"
                    )
                    raise e

    def _col_letter(self, col_idx: int) -> str:
        letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        return letters[col_idx - 1]

    def _verify_connection(self) -> bool:
        try:
            self._get_all_rows()
            return True
        except Exception as e:
            logger.error(f"Connection verification failed: {str(e)}")
            return False


class AsyncGoogleSheetsService:
    """
    Asynchronous wrapper exposing non-blocking calls to the event loop.
    """
    def __init__(self):
        self._service = GoogleSheetsService()

    async def insert_contact(self, contact: ContactCard) -> Dict[str, Any]:
        """
        Inserts contact to sheets if it is unique. Otherwise returns duplicate details.
        """
        return await asyncio.to_thread(self._service._insert_contact, contact)

    async def update_voice_note(self, uuid: str, transcript: str) -> bool:
        """
        Finds row by UUID and appends the transcript text to the voice notes cell.
        """
        return await asyncio.to_thread(self._service._update_voice_note, uuid, transcript)

    async def verify_connection(self) -> bool:
        """
        Verifies API connection by reading spreadsheet contents.
        """
        return await asyncio.to_thread(self._service._verify_connection)

sheets_service = AsyncGoogleSheetsService()
