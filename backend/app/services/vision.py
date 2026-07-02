from app.services.ai_provider import get_ai_service
from app.models.contact import ContactCard

class VisionService:
    """
    Proxy wrapper service for business card OCR routing requests 
    to the configured active AIPublicService provider (Gemini or Groq + PaddleOCR).
    """
    async def extract_contact_card(self, image_content: bytes, mime_type: str = "image/jpeg") -> ContactCard:
        ai_service = get_ai_service()
        return await ai_service.extract_contact_card(image_content, mime_type)

vision_service = VisionService()
