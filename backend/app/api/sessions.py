import uuid
from typing import List
from fastapi import APIRouter, HTTPException, Path
from app.database import mongo
from app.models.chat import ChatSession, ChatMessage

router = APIRouter(prefix="/api/sessions", tags=["sessions"])

@router.post("", response_model=ChatSession, status_code=201)
async def create_new_session():
    """
    Creates a new chat session with a unique UUID.
    """
    session_id = str(uuid.uuid4())
    try:
        session = await mongo.create_session(session_id)
        return session
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create chat session: {str(e)}")

@router.get("", response_model=List[ChatSession])
async def list_active_sessions():
    """
    Retrieves all active chat sessions from MongoDB or local storage fallback.
    """
    try:
        if mongo.db_manager.db is None:
            return list(mongo.IN_MEMORY_SESSIONS.values())

        sessions_col = mongo.db_manager.db["chat_sessions"]
        cursor = sessions_col.find()
        sessions = []
        async for doc in cursor:
            sessions.append(ChatSession(**doc))
        return sessions
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve sessions: {str(e)}")

@router.delete("/{session_id}", status_code=200)
async def delete_chat_session(session_id: str = Path(..., description="The ID of the session to delete")):
    """
    Removes a chat session and its corresponding message logs from MongoDB or local storage.
    """
    try:
        # Check existence
        existing = await mongo.get_session(session_id)
        if not existing:
            raise HTTPException(status_code=404, detail="Session not found.")
            
        if mongo.db_manager.db is None:
            if session_id in mongo.IN_MEMORY_SESSIONS:
                del mongo.IN_MEMORY_SESSIONS[session_id]
            if session_id in mongo.IN_MEMORY_HISTORIES:
                del mongo.IN_MEMORY_HISTORIES[session_id]
            return {"message": f"Successfully deleted session: {session_id}"}

        sessions_col = mongo.db_manager.db["chat_sessions"]
        histories_col = mongo.db_manager.db["chat_histories"]
        await sessions_col.delete_one({"session_id": session_id})
        await histories_col.delete_one({"session_id": session_id})
        return {"message": f"Successfully deleted session: {session_id}"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete session: {str(e)}")

@router.get("/{session_id}/messages", response_model=List[ChatMessage])
async def get_session_message_history(session_id: str = Path(..., description="The session ID")):
    """
    Retrieves the message logs associated with a session.
    """
    try:
        # Check existence
        existing = await mongo.get_session(session_id)
        if not existing:
            raise HTTPException(status_code=404, detail="Session not found.")
            
        history = await mongo.get_chat_history(session_id)
        return history
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve message history: {str(e)}")
