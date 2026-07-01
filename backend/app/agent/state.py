from typing import TypedDict, List, Optional
from langchain_core.messages import BaseMessage

class AgentState(TypedDict):
    """
    State definition for the single LangGraph orchestrator agent.
    Maintains active conversation memory, media payloads, and execution variables.
    """
    messages: List[BaseMessage]
    session_id: str
    last_contact_uuid: Optional[str]
    
    # Input files and metadata (passed in via API router)
    file_bytes: Optional[bytes]
    file_type: Optional[str]        # "image" | "audio" | "text"
    file_mime: Optional[str]        # e.g., "image/jpeg", "audio/wav"
    text_input: Optional[str]       # Raw text input if no file upload is present
    
    # Process variables
    extracted_contact: Optional[dict]
    transcription: Optional[str]
    status: Optional[str]           # 'extracted', 'duplicate', 'inserted', 'updated', 'failed'
    error_message: Optional[str]
