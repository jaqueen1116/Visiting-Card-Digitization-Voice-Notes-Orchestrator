from datetime import datetime, timezone
from typing import Optional, Any
from pydantic import BaseModel, Field

class ChatMessage(BaseModel):
    """
    Pydantic schema representing a single message within a chat session.
    """
    sender: str = Field(..., description="The sender of the message: 'user' or 'assistant'")
    text: str = Field(..., description="Message text content")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Timestamp of when the message was sent")
    type: str = Field(default="text", description="Type of content: 'text', 'image', or 'audio'")
    media_url: Optional[str] = Field(default=None, description="Optional URL to media uploaded")
    metadata: Optional[dict] = Field(default=None, description="Metadata dictionary for storing extraction status, UUIDs, or duplicate warnings")

class ChatSession(BaseModel):
    """
    Pydantic schema representing a chat session state.
    """
    session_id: str = Field(..., description="Unique ID for the conversation session")
    last_contact_uuid: Optional[str] = Field(default=None, description="The UUID of the most recently processed contact in this session")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Creation timestamp")
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Last updated timestamp")
