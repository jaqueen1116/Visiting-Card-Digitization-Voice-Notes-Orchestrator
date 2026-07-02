import os
import logging
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # API Server Configuration
    PORT: int = Field(default=8000)
    ENVIRONMENT: str = Field(default="development")
    LOG_LEVEL: str = Field(default="INFO")

    # Database Configuration
    MONGODB_URI: str = Field(default="")
    MONGODB_DB_NAME: str = Field(default="krid_db")

    # Google Sheets Configuration
    GOOGLE_SHEETS_ID: str = Field(default="")
    GOOGLE_SHEETS_JSON_CREDS_BASE64: str = Field(default="")
    GOOGLE_APPLICATION_CREDENTIALS: str = Field(default="")

    # WhatsApp API Configuration
    WHATSAPP_PHONE_NUMBER_ID: str = Field(default="")
    WHATSAPP_ACCESS_TOKEN: str = Field(default="")
    WHATSAPP_MANAGER_PHONE: str = Field(default="")

    # Gemini API Configuration
    GEMINI_API_KEY: str = Field(default="")

    # AI Pipeline Provider Configuration (gemini, groq)
    AI_PROVIDER: str = Field(default="gemini")
    GROQ_API_KEY: str = Field(default="")
    GROQ_MODEL: str = Field(default="llama-3.3-70b-versatile")

    # Load from .env file if it exists, prioritizing system environment variables
    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()

# Setup logging configuration
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("krid_backend")
logger.info(f"Configuration loaded for environment: {settings.ENVIRONMENT}")
