import asyncio
from google import genai
from google.genai import types
from google.genai.errors import APIError
from app.config import settings, logger

class SpeechService:
    """
    Speech service using Google Gemini 2.5 Flash's multimodal audio parsing capabilities
    to transcribe speech to text.
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

    async def transcribe_audio(self, audio_content: bytes, mime_type: str = "audio/mp3") -> str:
        """
        Asynchronously routes audio payloads to thread-pool runners for transcription.
        Returns only the transcript text.
        """
        return await asyncio.to_thread(self._transcribe_audio_sync, audio_content, mime_type)

    def _transcribe_audio_sync(self, audio_content: bytes, mime_type: str) -> str:
        if not audio_content:
            logger.error("Empty audio bytes provided.")
            raise ValueError("Invalid audio: File payload is empty.")

        client = self._get_client()
        
        prompt = (
            "Transcribe the spoken language in this audio file exactly. "
            "Return only the transcription text. If the audio contains only silence, noise, "
            "or is completely unreadable, return an empty string. Do not add any conversational preamble."
        )

        try:
            logger.info(f"Sending audio content ({mime_type}) to Gemini (gemini-2.5-flash)...")
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[
                    types.Part.from_bytes(data=audio_content, mime_type=mime_type),
                    prompt
                ]
            )
            
            logger.info("Gemini Speech transcription response received.")
            if not response.text:
                logger.warning("Gemini model returned empty response text for audio file.")
                return ""
                
            transcript = response.text.strip()
            logger.debug(f"Transcribed Text: {transcript}")
            return transcript
            
        except APIError as ae:
            logger.error(f"Gemini API Error during speech transcription (code={ae.code}): {ae.message}")
            if ae.code == 429:
                raise ValueError("Rate limit exceeded: Gemini API rate limit hit. Please try again in a few moments.")
            raise ValueError(f"Gemini Speech API failure: {ae.message}")
        except Exception as e:
            if isinstance(e, ValueError):
                raise e
            logger.error(f"Unexpected error during speech transcription: {str(e)}")
            raise ValueError(f"Speech service transcription failure: {str(e)}")

speech_service = SpeechService()
