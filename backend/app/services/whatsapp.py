import httpx
import asyncio
from app.config import settings, logger
from app.models.contact import ContactCard

class WhatsAppService:
    """
    Service integrating with Meta WhatsApp Cloud API to send digitized contact notifications.
    Supports asynchronous non-blocking HTTP requests via httpx.
    """
    def __init__(self):
        self.access_token = settings.WHATSAPP_ACCESS_TOKEN
        self.phone_number_id = settings.WHATSAPP_PHONE_NUMBER_ID
        self.manager_phone = settings.WHATSAPP_MANAGER_PHONE
        self.api_version = "v20.0"

    @property
    def is_configured(self) -> bool:
        """
        Returns True if all required credentials are set in environment settings.
        """
        return bool(self.access_token and self.phone_number_id and self.manager_phone)

    async def send_contact_notification(self, contact: ContactCard) -> bool:
        """
        Sends a stylized contact digitization alert message to the manager's phone.
        If credentials are not configured, details are printed to the server logs as a fallback.
        """
        message_body = (
            f"🔔 *New Business Card Digitized!*\n\n"
            f"👤 *Name:* {contact.name or 'N/A'}\n"
            f"🏢 *Company:* {contact.company or 'N/A'}\n"
            f"📞 *Phone:* {contact.phone or 'N/A'}\n"
            f"📧 *Email:* {contact.email or 'N/A'}\n"
            f"🆔 *UUID:* {contact.uuid}"
        )

        if not self.is_configured:
            logger.info("=== [MOCK WHATSAPP NOTIFICATION DISPATCH] ===")
            logger.info(f"To Manager Phone: {settings.WHATSAPP_MANAGER_PHONE or 'NOT_CONFIGURED'}")
            safe_body = message_body.encode('ascii', 'replace').decode('ascii')
            logger.info(f"Message Body:\n{safe_body}")
            logger.info("=============================================")
            return True

        url = f"https://graph.facebook.com/{self.api_version}/{self.phone_number_id}/messages"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": self.manager_phone,
            "type": "text",
            "text": {
                "body": message_body
            }
        }

        max_retries = 3
        backoff_sec = 1.0

        async with httpx.AsyncClient() as client:
            for attempt in range(1, max_retries + 1):
                try:
                    logger.info(f"Sending WhatsApp message (attempt {attempt}/{max_retries})...")
                    response = await client.post(url, headers=headers, json=payload, timeout=10.0)
                    
                    if response.status_code == 200:
                        logger.info(f"WhatsApp notification sent successfully to {self.manager_phone}")
                        return True
                    
                    # Handle API-level error responses
                    try:
                        resp_json = response.json()
                        error_msg = resp_json.get("error", {}).get("message", "Unknown API error")
                    except Exception:
                        error_msg = response.text or "Unknown raw error"
                        
                    logger.error(f"WhatsApp API error response (Status {response.status_code}): {error_msg}")
                    
                    # Fail immediately on client errors (400, 401, 403) unless rate limited (429)
                    if response.status_code < 500 and response.status_code != 429:
                        logger.error("Non-retryable client error. Aborting retries.")
                        break
                        
                except httpx.RequestError as exc:
                    logger.warning(f"Network transport failure on attempt {attempt}: {str(exc)}")
                    if attempt == max_retries:
                        logger.error(f"Failed to complete WhatsApp send after {max_retries} retries.")
                        raise exc
                
                # Backoff delay before retry attempt
                await asyncio.sleep(backoff_sec * attempt)
                
        return False

    async def verify_connection(self) -> bool:
        """
        Verifies WhatsApp configuration by checking credentials against Meta's profile endpoint.
        """
        if not self.is_configured:
            return False
            
        url = f"https://graph.facebook.com/{self.api_version}/{self.phone_number_id}/whatsapp_business_profile"
        headers = {
            "Authorization": f"Bearer {self.access_token}"
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=headers, timeout=5.0)
                if response.status_code == 200:
                    logger.info("WhatsApp configuration verified and healthy.")
                    return True
                else:
                    logger.error(f"WhatsApp credential verification failed (Status {response.status_code}): {response.text}")
                    return False
        except Exception as e:
            logger.error(f"WhatsApp health connection query failed: {str(e)}")
            return False

whatsapp_service = WhatsAppService()
