import json
import asyncio
from typing import Optional
from google import genai
from google.genai import types
from google.genai.errors import APIError
from app.config import settings, logger
from app.models.contact import ContactCard, ExtractedContact

class VisionService:
    """
    Independent service for business card OCR and structured information extraction using Gemini API.
    """
    def __init__(self):
        self._client = None

    def _get_client(self) -> genai.Client:
        if self._client:
            return self._client
        
        if not settings.GEMINI_API_KEY:
            logger.error("GEMINI_API_KEY is not set or empty.")
            raise ValueError("Gemini API key is not configured in settings.")
            
        # Initialize Google GenAI client
        self._client = genai.Client(api_key=settings.GEMINI_API_KEY)
        return self._client

    async def extract_contact_card(self, image_content: bytes, mime_type: str = "image/jpeg") -> ContactCard:
        """
        Asynchronously routes image payloads to thread-pool runners for vision extraction.
        Returns a validated ContactCard Pydantic object.
        """
        return await asyncio.to_thread(self._extract_contact_card_sync, image_content, mime_type)

    def _extract_contact_card_sync(self, image_content: bytes, mime_type: str) -> ContactCard:
        if not image_content:
            logger.error("Empty image bytes provided.")
            raise ValueError("Invalid image: File payload is empty.")

        client = self._get_client()
        
        prompt = (
            "Analyze the business card image. Extract Name, Phone, Email, and Company. "
            "Follow these strict rules:\n"
            "1. If a field is not present, is unreadable, blurry, or missing, set it to null. Do not invent values.\n"
            "2. If there are multiple cards in the image, extract details only from the primary/most prominent card.\n"
            "3. If the image is invalid, blurry, or not a business card, set all fields to null or return an empty structure.\n"
            "Clean phone numbers to contain only digits, spaces, and '+'."
        )

        try:
            logger.info("Sending business card to Gemini Vision (gemini-2.5-flash)...")
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[
                    types.Part.from_bytes(data=image_content, mime_type=mime_type),
                    prompt
                ],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=ExtractedContact,
                    temperature=0.1
                )
            )
            
            logger.info("Gemini Vision response received.")
            if not response.text:
                logger.error("Gemini model returned empty response text.")
                raise ValueError("Unreadable business card: Gemini returned an empty response.")
                
            raw_text = response.text.strip()
            logger.debug(f"Raw Gemini Vision JSON: {raw_text}")
            
            try:
                data = json.loads(raw_text)
            except json.JSONDecodeError as je:
                logger.error(f"Malformed JSON returned by Gemini: {raw_text}. Error: {str(je)}")
                raise ValueError("Malformed JSON error: Unable to parse structured card data.")
            
            name_val = data.get("name")
            if not name_val or not str(name_val).strip() or name_val == "Unknown":
                logger.warning("Gemini was unable to extract a valid contact name. Rejecting card.")
                raise ValueError("The uploaded image doesn't appear to be a valid business card. Please upload a clear business card image.")

            # Load extracted values and instantiate validated ContactCard schema
            contact = ContactCard(
                name=name_val,
                phone=data.get("phone"),
                email=data.get("email"),
                company=data.get("company")
            )

            return contact
            
        except APIError as ae:
            logger.error(f"Gemini API Error (code={ae.code}): {ae.message}")
            if ae.code == 429:
                raise ValueError("Rate limit exceeded: Gemini API rate limit hit. Please try again in a few moments.")
            raise ValueError(f"Gemini API failure: {ae.message}")
        except Exception as e:
            if isinstance(e, ValueError):
                raise e
            logger.error(f"Unexpected error during vision extraction: {str(e)}")
            raise ValueError(f"Vision service extraction failure: {str(e)}")

vision_service = VisionService()
