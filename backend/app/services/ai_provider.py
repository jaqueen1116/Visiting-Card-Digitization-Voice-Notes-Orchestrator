import json
import asyncio
import base64
from abc import ABC, abstractmethod
from typing import List, Any, Optional

from google import genai
from google.genai import types
from google.genai.errors import APIError
from groq import Groq
from openai import OpenAI

from app.config import settings, logger
from app.models.contact import ContactCard, ExtractedContact

class AIPublicService(ABC):
    @abstractmethod
    async def extract_contact_card(self, image_content: bytes, mime_type: str = "image/jpeg") -> ContactCard:
        """
        Extract business card metadata and return a validated ContactCard.
        """
        pass

    @abstractmethod
    async def generate_chat_response(self, prompt: str, history: List[Any]) -> str:
        """
        Generate conversational responses.
        """
        pass

# Cached singletons for clients and models
_gemini_client = None
_groq_client = None
_openai_client = None

def get_gemini_client() -> genai.Client:
    global _gemini_client
    if _gemini_client is None:
        if not settings.GEMINI_API_KEY:
            logger.error("GEMINI_API_KEY is not set or empty.")
            raise ValueError("Gemini API key is not configured in settings.")
        _gemini_client = genai.Client(api_key=settings.GEMINI_API_KEY)
    return _gemini_client

def get_groq_client() -> Groq:
    global _groq_client
    if _groq_client is None:
        if not settings.GROQ_API_KEY:
            logger.error("GROQ_API_KEY is not set or empty.")
            raise ValueError("Groq API key is not configured in settings.")
        _groq_client = Groq(api_key=settings.GROQ_API_KEY)
    return _groq_client

def get_openai_client() -> OpenAI:
    global _openai_client
    if _openai_client is None:
        if not settings.OPENAI_API_KEY:
            logger.error("OPENAI_API_KEY is not set or empty.")
            raise ValueError("OpenAI API key is not configured in settings.")
        _openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)
    return _openai_client


class GeminiProvider(AIPublicService):
    async def extract_contact_card(self, image_content: bytes, mime_type: str = "image/jpeg") -> ContactCard:
        return await asyncio.to_thread(self._extract_sync, image_content, mime_type)

    def _extract_sync(self, image_content: bytes, mime_type: str) -> ContactCard:
        if not image_content:
            logger.error("Empty image bytes provided.")
            raise ValueError("Invalid image: File payload is empty.")

        client = get_gemini_client()
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
                raise ValueError("Unreadable business card: Gemini returned an empty response.")
                
            raw_text = response.text.strip()
            data = json.loads(raw_text)
            
            name_val = data.get("name")
            if not name_val or not str(name_val).strip() or name_val == "Unknown":
                raise ValueError("The uploaded image doesn't appear to be a valid business card. Please upload a clear business card image.")

            return ContactCard(
                name=name_val,
                phone=data.get("phone"),
                email=data.get("email"),
                company=data.get("company")
            )
        except APIError as ae:
            logger.error(f"Gemini API Error: {ae.message}")
            if ae.code == 429:
                raise ValueError("Rate limit exceeded: Gemini API rate limit hit. Please try again in a few moments.")
            raise ValueError(f"Gemini API failure: {ae.message}")
        except Exception as e:
            if isinstance(e, ValueError):
                raise e
            logger.error(f"Unexpected error in GeminiProvider: {str(e)}")
            raise ValueError(f"Vision service extraction failure: {str(e)}")

    async def generate_chat_response(self, prompt: str, history: List[Any]) -> str:
        return await asyncio.to_thread(self._chat_sync, prompt, history)

    def _chat_sync(self, prompt: str, history: List[Any]) -> str:
        client = get_gemini_client()
        context = ""
        for msg in history[-6:]:
            role = "User" if msg.type == "human" else "Assistant"
            context += f"{role}: {msg.content}\n"

        instruction = (
            "You are a helpful AI Visiting Card Digitizer and Voice Note Orchestration Assistant. "
            "You help users manage their contact databases by digitizing business card images and appending voice note transcripts. "
            "Respond politely, helpfully, and concisely to the user's queries.\n\n"
        )
        full_prompt = f"{instruction}{context}User: {prompt}\nAssistant:"
        
        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=full_prompt
            )
            return response.text.strip() if response.text else "I couldn't generate a reply."
        except Exception as e:
            logger.error(f"Gemini chat response failed: {str(e)}")
            raise e


class OpenAIVisionProvider(AIPublicService):
    def __init__(self, gemini_fallback: GeminiProvider):
        self.gemini_fallback = gemini_fallback

    async def extract_contact_card(self, image_content: bytes, mime_type: str = "image/jpeg") -> ContactCard:
        try:
            return await asyncio.to_thread(self._extract_sync, image_content, mime_type)
        except ValueError as ve:
            # Propagate validation errors (e.g. card invalid, name missing) directly without falling back
            raise ve
        except Exception as e:
            logger.warning(f"OpenAI Vision extraction failed: {str(e)}. Automatically falling back to GeminiProvider...")
            try:
                return await self.gemini_fallback.extract_contact_card(image_content, mime_type)
            except Exception as fe:
                logger.error(f"Gemini fallback vision extraction also failed: {str(fe)}")
                raise fe

    def _extract_sync(self, image_content: bytes, mime_type: str) -> ContactCard:
        if not image_content:
            logger.error("Empty image bytes provided.")
            raise ValueError("Invalid image: File payload is empty.")

        client = get_openai_client()
        
        # Convert image to base64
        base64_image = base64.b64encode(image_content).decode("utf-8")
        
        system_prompt = (
            "You are an expert AI business card parser. Extract contact details from the provided image "
            "and return a JSON object matching this schema exactly:\n"
            "{\n"
            "  \"name\": \"Full Name (or null if not found)\",\n"
            "  \"phone\": \"Phone number (or null if not found)\",\n"
            "  \"email\": \"Email address (or null if not found)\",\n"
            "  \"company\": \"Company name (or null if not found)\"\n"
            "}\n"
            "Rules:\n"
            "1. If a field is not present, blurry, or missing, set it to null. Do not invent values.\n"
            "2. If name is missing or is 'Unknown', set name to null.\n"
            "3. Clean phone numbers to contain only digits, spaces, and '+'.\n"
            "4. Respond with ONLY the raw JSON object. Do not explain or wrap in markdown blocks."
        )

        logger.info("Sending image to OpenAI GPT-4.1 API...")
        completion = client.chat.completions.create(
            model="gpt-4.1",
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Extract contact information from this business card."},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
            response_format={"type": "json_object"},
            temperature=0.1
        )

        raw_json = completion.choices[0].message.content.strip()
        logger.info(f"Raw OpenAI Vision JSON response: {raw_json}")
        
        data = json.loads(raw_json)
        name_val = data.get("name")
        if not name_val or not str(name_val).strip() or name_val == "Unknown":
            raise ValueError("The uploaded image doesn't appear to be a valid business card. Please upload a clear business card image.")

        return ContactCard(
            name=name_val,
            phone=data.get("phone"),
            email=data.get("email"),
            company=data.get("company")
        )

    async def generate_chat_response(self, prompt: str, history: List[Any]) -> str:
        try:
            return await asyncio.to_thread(self._chat_sync, prompt, history)
        except Exception as e:
            logger.warning(f"Groq chat reply generation failed: {str(e)}. Automatically falling back to GeminiProvider...")
            try:
                return await self.gemini_fallback.generate_chat_response(prompt, history)
            except Exception as fe:
                logger.error(f"Gemini fallback chat response also failed: {str(fe)}")
                raise fe

    def _chat_sync(self, prompt: str, history: List[Any]) -> str:
        # Keep Groq Llama 3.3 for chat
        client = get_groq_client()
        model_name = settings.GROQ_MODEL or "llama-3.3-70b-versatile"
        
        context = ""
        for msg in history[-6:]:
            role = "User" if msg.type == "human" else "Assistant"
            context += f"{role}: {msg.content}\n"

        instruction = (
            "You are a helpful AI Visiting Card Digitizer and Voice Note Orchestration Assistant. "
            "You help users manage their contact databases by digitizing business card images and appending voice note transcripts. "
            "Respond politely, helpfully, and concisely to the user's queries.\n\n"
        )
        
        logger.info(f"Sending chat query to Groq model {model_name}...")
        completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": instruction},
                {"role": "user", "content": f"{context}User: {prompt}\nAssistant:"}
            ],
            model=model_name,
            temperature=0.7
        )
        return completion.choices[0].message.content.strip()


# Cached Provider instances
_gemini_provider = None
_openai_provider = None

def get_ai_service() -> AIPublicService:
    global _gemini_provider, _openai_provider
    
    if _gemini_provider is None:
        _gemini_provider = GeminiProvider()
        
    provider_type = settings.AI_PROVIDER.lower().strip()
    if provider_type == "openai":
        if _openai_provider is None:
            _openai_provider = OpenAIVisionProvider(gemini_fallback=_gemini_provider)
        return _openai_provider
        
    return _gemini_provider
