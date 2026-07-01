import uuid
from typing import Optional
from pydantic import BaseModel, Field

class ContactCard(BaseModel):
    """
    Pydantic schema to validate and structure extracted business card data.
    """
    uuid: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique ID for the contact")
    name: str = Field(default="Unknown", description="Full Name of the contact")
    phone: Optional[str] = Field(default=None, description="Phone number of the contact")
    email: Optional[str] = Field(default=None, description="Email address of the contact")
    company: Optional[str] = Field(default=None, description="Company name of the contact")
    voice_notes: Optional[str] = Field(default="", description="Speech transcript voice note logs")


class ExtractedContact(BaseModel):
    """
    Pydantic schema used exclusively for Gemini Vision API responses.
    Does not contain defaults, as Gemini schema generation does not support them.
    """
    name: Optional[str] = Field(description="Full Name of the contact")
    phone: Optional[str] = Field(description="Phone number of the contact")
    email: Optional[str] = Field(description="Email address of the contact")
    company: Optional[str] = Field(description="Company name of the contact")
