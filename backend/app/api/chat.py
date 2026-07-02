from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from pydantic import BaseModel
from typing import Optional
from app.models.chat import ChatMessage
from app.database import mongo
from app.agent.graph import agent_app
from app.config import logger
from langchain_core.messages import HumanMessage, AIMessage
import logging

router = APIRouter(prefix="/api/chat", tags=["chat"])

class TextMessageRequest(BaseModel):
    session_id: str
    text: str

async def run_agent(
    session_id: str, 
    file_bytes: Optional[bytes] = None, 
    file_type: Optional[str] = None, 
    file_mime: Optional[str] = None, 
    text_input: Optional[str] = None
) -> ChatMessage:
    """
    Loads conversation context from MongoDB, prepares graph states, runs the
    LangGraph agent, commits messages to MongoDB, and returns the agent reply.
    """
    # 1. Fetch current session parameters
    session = await mongo.get_session(session_id)
    if not session:
        raise ValueError(f"Session {session_id} not found in database.")

    # 2. Map stored MongoDB message histories to LangChain format
    db_history = await mongo.get_chat_history(session_id)
    langchain_history = []
    for msg in db_history:
        if msg.sender == "user":
            langchain_history.append(HumanMessage(content=msg.text))
        else:
            langchain_history.append(AIMessage(content=msg.text))

    # Append the current user query turn to the graph message stream context
    current_user_text = text_input
    if file_type == "image":
        current_user_text = "Uploaded business card image."
    elif file_type == "audio":
        current_user_text = "Uploaded voice note audio."
        
    if current_user_text:
        langchain_history.append(HumanMessage(content=current_user_text))

    # 3. Handle Human-in-the-Loop Confirmation State Restoration
    restored_contact = None
    if text_input in ["CONFIRM_SAVE_CARD", "CANCEL_SAVE_CARD"]:
        for msg in reversed(db_history):
            if msg.sender == "assistant" and msg.metadata and msg.metadata.get("status") == "needs_confirmation":
                restored_contact = msg.metadata.get("extracted_contact")
                break
                
    # 4. Assemble inputs dict matching AgentState schema
    inputs = {
        "messages": langchain_history,
        "session_id": session_id,
        "last_contact_uuid": session.last_contact_uuid,
        "file_bytes": file_bytes,
        "file_type": file_type,
        "file_mime": file_mime,
        "text_input": text_input,
        "extracted_contact": restored_contact,
        "transcription": None,
        "status": None,
        "error_message": None
    }

    # 5. Invoke LangGraph agent pipeline
    try:
        final_state = await agent_app.ainvoke(inputs)
    except Exception as e:
        logger.error(f"LangGraph execution exception: {str(e)}")
        # Construct fallback failure reply
        final_state = {
            "messages": langchain_history + [AIMessage(content=f"❌ Agent execution error: {str(e)}")],
            "last_contact_uuid": session.last_contact_uuid,
            "status": "failed",
            "error_message": str(e)
        }

    # 5. Retrieve last AI Message
    new_messages = final_state.get("messages", [])
    if not new_messages:
        agent_reply = AIMessage(content="I'm sorry, I encountered an internal execution failure.")
    else:
        agent_reply = new_messages[-1]

    # 6. Commit user query event to MongoDB
    user_text = text_input
    if file_type == "image":
        user_text = "Uploaded business card image."
    elif file_type == "audio":
        user_text = "Uploaded voice note audio."
        
    if text_input == "CONFIRM_SAVE_CARD":
        user_text = "Confirmed save to Google Sheets."
    elif text_input == "CANCEL_SAVE_CARD":
        user_text = "Cancelled save operation."
        
    user_msg = ChatMessage(
        sender="user",
        text=user_text or "Sent attachment file",
        type=file_type or "text",
        metadata={"mime": file_mime} if file_mime else None
    )
    await mongo.save_chat_message(session_id, user_msg)

    status = final_state.get("status")
    agent_msg = ChatMessage(
        sender="assistant",
        text=agent_reply.content,
        type="text",
        metadata={
            "status": status,
            "last_contact_uuid": final_state.get("last_contact_uuid") if status != "failed" else None,
            "extracted_contact": final_state.get("extracted_contact") if status not in ["failed", "cancelled"] else None
        }
    )
    await mongo.save_chat_message(session_id, agent_msg)

    # 8. Sync state tracker variables back to MongoDB
    new_uuid = final_state.get("last_contact_uuid")
    if new_uuid and new_uuid != session.last_contact_uuid:
        await mongo.update_last_contact_uuid(session_id, new_uuid)

    return agent_msg

@router.post("/message", response_model=ChatMessage)
async def send_text_message(payload: TextMessageRequest):
    """
    Processes plain text messaging inside the session.
    """
    session = await mongo.get_session(payload.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")
        
    try:
        agent_msg = await run_agent(
            session_id=payload.session_id,
            text_input=payload.text
        )
        return agent_msg
    except Exception as e:
        logger.error(f"Failed to process text message: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/upload", response_model=ChatMessage)
async def upload_file(
    file: UploadFile = File(...),
    session_id: str = Form(...)
):
    """
    Accepts business cards (images) or voice notes (audio), identifies file class,
    and runs them through the LangGraph agent orchestrator.
    """
    session = await mongo.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")
        
    # Read file payload
    try:
        file_bytes = await file.read()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read upload: {str(e)}")
        
    # Classify file extension and MIME types
    content_type = file.content_type or ""
    filename_lower = file.filename.lower()
    
    if content_type.startswith("image/"):
        file_type = "image"
    elif content_type.startswith("audio/") or filename_lower.endswith((".wav", ".mp3", ".m4a", ".ogg", ".webm")):
        file_type = "audio"
        if not content_type.startswith("audio/"):
            content_type = "audio/mp3"
    else:
        raise HTTPException(
            status_code=400,
            detail="Unsupported format. Please upload a business card image or audio voice note."
        )
        
    try:
        agent_msg = await run_agent(
            session_id=session_id,
            file_bytes=file_bytes,
            file_type=file_type,
            file_mime=content_type
        )
        return agent_msg
    except Exception as e:
        logger.error(f"Failed to run file processor: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
