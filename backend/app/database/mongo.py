import certifi
import datetime
from typing import List, Optional
from motor.motor_asyncio import AsyncIOMotorClient
from app.config import settings, logger
from app.models.chat import ChatMessage, ChatSession

class MongoDBManager:
    """
    Handles connection lifecycle and properties for the MongoDB Atlas database.
    Reuses a single client instance across the application lifetime.
    """
    def __init__(self):
        self.client: Optional[AsyncIOMotorClient] = None
        self.db = None

    def connect(self) -> None:
        """
        Establishes connection to MongoDB Atlas.
        Reuses the existing client if already initialized.
        """
        if self.client is not None:
            logger.info("MongoDB client already initialized. Reusing active connection.")
            return
            
        if not settings.MONGODB_URI:
            logger.error("MONGODB_URI is not set in environment or config.")
            raise ValueError("MONGODB_URI environment variable is missing or empty.")
        
        try:
            logger.info("Initializing single AsyncIOMotorClient instance...")
            # Initialize without tlsCAFile to use the default system trust store matching pymongo
            self.client = AsyncIOMotorClient(settings.MONGODB_URI)
            self.db = self.client[settings.MONGODB_DB_NAME]
            logger.info(f"MongoDB single client instance created for database: {settings.MONGODB_DB_NAME}")
        except Exception as e:
            logger.error(f"MongoDB connection failed: {str(e)}")
            raise e

    def disconnect(self) -> None:
        """
        Closes active connections.
        """
        if self.client:
            self.client.close()
            self.client = None
            self.db = None
            logger.info("MongoDB connection closed.")

db_manager = MongoDBManager()

# In-memory session and history fallbacks for testing and local development if database is unreachable
IN_MEMORY_SESSIONS = {}
IN_MEMORY_HISTORIES = {}

async def init_db() -> None:
    """
    Initializes database indexes and verifies connectivity with a ping.
    """
    try:
        db_manager.connect()
        # Verify connectivity
        await db_manager.client.admin.command('ping')
        logger.info("MongoDB connectivity verified via ping.")
        
        # Ensure collections exist and build indexes
        sessions_col = db_manager.db["chat_sessions"]
        await sessions_col.create_index("session_id", unique=True)
        logger.info("Ensured unique index on chat_sessions:session_id")
        
        histories_col = db_manager.db["chat_histories"]
        await histories_col.create_index("session_id", unique=True)
        logger.info("Ensured unique index on chat_histories:session_id")
    except Exception as e:
        logger.error(f"Database initialization error: {str(e)}")
        db_manager.disconnect()
        logger.warning("MongoDB Atlas initialization failed. Fallback to In-Memory mode is active.")

async def create_session(session_id: str) -> ChatSession:
    """
    Creates a new chat session state in MongoDB. If it exists, returns it.
    Falls back to local memory if MongoDB is disconnected.
    """
    if db_manager.db is None:
        logger.warning(f"MongoDB offline. Creating in-memory session mock for ID: {session_id}")
        if session_id in IN_MEMORY_SESSIONS:
            return IN_MEMORY_SESSIONS[session_id]
        session = ChatSession(session_id=session_id)
        IN_MEMORY_SESSIONS[session_id] = session
        IN_MEMORY_HISTORIES[session_id] = []
        return session

    try:
        sessions_col = db_manager.db["chat_sessions"]
        existing = await sessions_col.find_one({"session_id": session_id})
        
        if existing:
            logger.info(f"Session {session_id} already exists. Returning existing session.")
            return ChatSession(**existing)
            
        session = ChatSession(session_id=session_id)
        await sessions_col.insert_one(session.model_dump())
        
        # Initialize an empty chat history array for this session
        histories_col = db_manager.db["chat_histories"]
        await histories_col.insert_one({
            "session_id": session_id,
            "messages": []
        })
        
        logger.info(f"Created session logs and chat history database rows for: {session_id}")
        return session
    except Exception as e:
        logger.error(f"Failed to create session {session_id}: {str(e)}")
        raise e

async def get_session(session_id: str) -> Optional[ChatSession]:
    """
    Queries chat session state from the database.
    Falls back to local memory if MongoDB is disconnected.
    """
    if db_manager.db is None:
        return IN_MEMORY_SESSIONS.get(session_id)

    try:
        sessions_col = db_manager.db["chat_sessions"]
        data = await sessions_col.find_one({"session_id": session_id})
        if data:
            return ChatSession(**data)
        return None
    except Exception as e:
        logger.error(f"Error fetching session {session_id}: {str(e)}")
        return None

async def update_last_contact_uuid(session_id: str, last_contact_uuid: str, contact_name: Optional[str] = None) -> bool:
    """
    Updates the session state tracking the latest parsed contact UUID.
    Falls back to local memory if MongoDB is disconnected.
    """
    if db_manager.db is None:
        if session_id in IN_MEMORY_SESSIONS:
            IN_MEMORY_SESSIONS[session_id].last_contact_uuid = last_contact_uuid
            if contact_name:
                IN_MEMORY_SESSIONS[session_id].contact_name = contact_name
            IN_MEMORY_SESSIONS[session_id].updated_at = datetime.datetime.now(datetime.timezone.utc)
            logger.info(f"[In-Memory] Linked session {session_id} to last_contact_uuid {last_contact_uuid}")
            return True
        return False

    try:
        sessions_col = db_manager.db["chat_sessions"]
        update_fields = {
            "last_contact_uuid": last_contact_uuid,
            "updated_at": datetime.datetime.now(datetime.timezone.utc)
        }
        if contact_name:
            update_fields["contact_name"] = contact_name

        result = await sessions_col.update_one(
            {"session_id": session_id},
            {
                "$set": update_fields
            }
        )
        if result.modified_count > 0:
            logger.info(f"Linked session {session_id} to last_contact_uuid {last_contact_uuid} (Name: {contact_name})")
            return True
        logger.warning(f"No changes made while updating session {session_id} with last_contact_uuid")
        return False
    except Exception as e:
        logger.error(f"Failed to update last_contact_uuid for session {session_id}: {str(e)}")
        return False

async def save_chat_message(session_id: str, message: ChatMessage) -> bool:
    """
    Appends a new message block into a session's chat history array.
    Falls back to local memory if MongoDB is disconnected.
    """
    if db_manager.db is None:
        if session_id not in IN_MEMORY_HISTORIES:
            IN_MEMORY_HISTORIES[session_id] = []
        IN_MEMORY_HISTORIES[session_id].append(message)
        logger.debug(f"[In-Memory] Saved message from {message.sender} in session {session_id}")
        return True

    try:
        histories_col = db_manager.db["chat_histories"]
        result = await histories_col.update_one(
            {"session_id": session_id},
            {"$push": {"messages": message.model_dump()}}
        )
        
        if result.matched_count == 0:
            # If historical document did not exist, initialize it with the message
            logger.info(f"Chat history document not found for {session_id}. Initializing with message.")
            await histories_col.insert_one({
                "session_id": session_id,
                "messages": [message.model_dump()]
            })
        
        logger.debug(f"Saved message from {message.sender} in session {session_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to save chat message in session {session_id}: {str(e)}")
        return False

async def get_chat_history(session_id: str) -> List[ChatMessage]:
    """
    Retrieves message history items associated with a session.
    Falls back to local memory if MongoDB is disconnected.
    """
    if db_manager.db is None:
        return IN_MEMORY_HISTORIES.get(session_id, [])

    try:
        histories_col = db_manager.db["chat_histories"]
        data = await histories_col.find_one({"session_id": session_id})
        if data and "messages" in data:
            return [ChatMessage(**msg) for msg in data["messages"]]
        return []
    except Exception as e:
        logger.error(f"Error retrieving chat history for session {session_id}: {str(e)}")
        return []
