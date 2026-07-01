# Visiting Card Digitization and Voice Notes Orchestrator - Implementation Plan

This plan details the design decisions, schemas, and workflows, updated to include contact UUIDs, Pydantic validation, and MongoDB session tracking.

---

# Step 1: Complete Architecture Explanation (Updated)

- **Frontend**: Single-page React application with a dynamic glassmorphic chat interface, session sidebar, and media uploader.
- **Backend API**: FastAPI serving routes for chat/upload and sessions.
- **Agent Orchestrator**: LangGraph agent executing tools for Vision, Sheets, Speech, and WhatsApp.
- **Primary Database**: Google Sheets (stores contact info including a unique UUID, name, email, phone, company, voice transcripts, and timestamps).
- **Session Database**: MongoDB Atlas (stores session history, conversation states, checkpoints, and maps the active session to the current contact UUID).
- **Validation**: Pydantic models validate extracted JSON data from the Vision model.

---

# Step 2: System Workflow

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant FE as React Frontend
    participant BE as FastAPI Backend
    participant Agent as LangGraph Agent
    participant Vision as Vision API (Gemini/OpenAI)
    participant Sheets as Google Sheets API
    participant Mongo as MongoDB Atlas
    participant WA as WhatsApp Cloud API

    %% Phase 1: Card Upload
    Note over User, WA: Phase 1: Card Digitization
    User->>FE: Upload Visiting Card Image
    FE->>BE: POST /api/chat/upload (Image + Session ID)
    BE->>Agent: Invoke Agent StateGraph (Session ID, image_bytes)
    Agent->>Vision: Call Vision Tool (Process Image)
    Vision-->>Agent: Raw Contact Data (Name, Phone, Email, Company)
    Agent->>Agent: Validate with Pydantic & Generate Contact UUID
    Agent->>Sheets: Call Sheet Tool (Check duplicates: Email/Phone)
    alt Is Duplicate
        Sheets-->>Agent: Duplicate Found (Row details)
        Agent->>Mongo: Log Duplicate Session Event
        Agent-->>BE: Return "Duplicate Contact found. Not inserted."
    else Is Unique
        Agent->>Sheets: Call Sheet Tool (Insert Row: UUID + Data)
        Sheets-->>Agent: Insertion Success
        Agent->>Mongo: Save Session Checkpoint & last_contact_uuid
        Agent->>WA: Call WhatsApp Tool (Notify Predefined Manager with UUID & details)
        WA-->>Agent: Notification Sent
        Agent-->>BE: Return "Card Digitized! Contact added with UUID."
    end
    BE-->>FE: Stream/Return Chat Message Response
    FE-->>User: Display Success/Duplicate Status & Contact JSON

    %% Phase 2: Voice Note Upload
    Note over User, WA: Phase 2: Voice Note Orchestration
    User->>FE: Upload Voice Note (Audio)
    FE->>BE: POST /api/chat/upload (Audio + Session ID)
    BE->>Agent: Invoke Agent StateGraph (Session ID, audio_bytes)
    Agent->>Mongo: Retrieve current last_contact_uuid for session
    Agent->>Vision: Call Speech Tool (Transcribe Audio)
    Vision-->>Agent: Text Transcript
    Agent->>Sheets: Call Sheet Tool (Find row by UUID & Append Transcript)
    Sheets-->>Agent: Row Updated Success
    Agent->>Mongo: Log Update Session Event
    Agent-->>BE: Return "Speech transcribed. Appended to current contact."
    BE-->>FE: Return Chat Message Response
    FE-->>User: Display Transcript & Confirmation
```

---

# Step 3: LangGraph Workflow

```mermaid
graph TD
    Start([Start]) --> ProcessInput[process_input_node]
    
    ProcessInput -->|Is Image| ExtractCard[extract_card_node]
    ProcessInput -->|Is Audio| TranscribeAudio[transcribe_audio_node]
    ProcessInput -->|Is Text| GenerateResponse[generate_response_node]
    
    ExtractCard --> ValidateData{Pydantic Validation}
    ValidateData -->|Valid| ManageSheet[manage_sheet_node]
    ValidateData -->|Invalid| GenerateResponse
    
    TranscribeAudio --> ManageSheet
    
    ManageSheet --> CheckAction{Action Type}
    CheckAction -->|Insert New Card & Unique| WhatsAppNotify[whatsapp_notify_node]
    CheckAction -->|Duplicate or Audio Update| GenerateResponse
    
    WhatsAppNotify --> GenerateResponse
    GenerateResponse --> End([End])
```

### Graph State Definition
```python
from typing import TypedDict, List, Optional
from langchain_core.messages import BaseMessage

class AgentState(TypedDict):
    messages: List[BaseMessage]
    session_id: str
    last_contact_uuid: Optional[str]
    extracted_contact: Optional[dict]  # Temp holder for pydantic data
    transcription: Optional[str]        # Temp holder for transcript
    status: Optional[str]               # e.g., 'extracted', 'duplicate', 'inserted', 'updated', 'failed'
    error_message: Optional[str]
```

---

# Step 4: MongoDB Schema Design

We will maintain two main collections:
1. `chat_sessions`:
   ```json
   {
     "_id": "session_id_uuid_or_string",
     "last_contact_uuid": "contact-uuid-string-or-null",
     "created_at": "ISODate",
     "updated_at": "ISODate"
   }
   ```
2. `chat_histories` (For rendering messages in the React frontend):
   ```json
   {
     "_id": "history_id_uuid",
     "session_id": "session_id_uuid_or_string",
     "messages": [
       {
         "sender": "user" | "assistant",
         "text": "Message content",
         "timestamp": "ISODate",
         "type": "text" | "image" | "audio",
         "media_url": "optional_local_or_cloud_storage_path",
         "metadata": {
           "extracted_contact": {},
           "uuid": "contact_uuid_if_any",
           "status": "duplicate" | "inserted" | "updated"
         }
       }
     ]
   }
   ```
3. `checkpoints` (Used internally by LangGraph's MongoDBSaver to maintain checkpoint states).

---

# Step 5: Google Sheet Format Design

The Sheets database will use a fixed column schema. The backend will parse/write values by matching column headers.

| Column Letter | Column Header | Data Type | Description |
|---|---|---|---|
| **A** | `UUID` | String | Unique UUID for the contact |
| **B** | `Name` | String | Extracted Full Name |
| **C** | `Phone` | String | Cleaned Phone Number (with country code) |
| **D** | `Email` | String | Validated Email Address |
| **E** | `Company` | String | Extracted Company Name |
| **F** | `Voice Notes` | String | Appended speech transcripts |
| **G** | `Created At` | Timestamp | Date and time contact was added |
| **H** | `Updated At` | Timestamp | Date and time of last modification |

---

# Step 6: Folder Structure Design

```
krid/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── chat.py
│   │   │   └── sessions.py
│   │   ├── database/
│   │   │   ├── __init__.py
│   │   │   └── mongo.py
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   └── contact.py
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── sheets.py
│   │   │   ├── whatsapp.py
│   │   │   ├── vision.py
│   │   │   └── speech.py
│   │   ├── agent/
│   │   │   ├── __init__.py
│   │   │   ├── graph.py
│   │   │   ├── state.py
│   │   │   └── tools.py
│   │   └── utils/
│   │       ├── __init__.py
│   │       └── helpers.py
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
├── frontend/
│   ├── public/
│   ├── src/
│   │   ├── assets/
│   │   ├── components/
│   │   │   ├── ChatWindow.jsx
│   │   │   ├── SessionSidebar.jsx
│   │   │   ├── Uploader.jsx
│   │   │   └── MessageItem.jsx
│   │   ├── App.jsx
│   │   ├── index.css
│   │   ├── main.jsx
│   │   └── config.js
│   ├── package.json
│   ├── vite.config.js
│   └── .env.example
└── README.md
```

---

# Step 7: List of API Endpoints

### 1. Chat & Session Operations
- **`GET /api/sessions`**: Retrieve all active chat sessions.
- **`POST /api/sessions`**: Create a new chat session. Returns `session_id`.
- **`DELETE /api/sessions/{session_id}`**: Delete a chat session and its corresponding messages.
- **`GET /api/sessions/{session_id}/messages`**: Retrieve historical messages for a session.

### 2. Message & Media Handlers
- **`POST /api/chat/message`**: Handle text messages within a session.
- **`POST /api/chat/upload`**: Multipart form endpoint accepting an `image` or `audio` file, plus `session_id`. Initiates the LangGraph Agent execution loop.

---

# Step 8: Explain Every Tool in LangGraph

1. **`extract_business_card_tool`**:
   - **Input**: Image file bytes.
   - **Action**: Sends image to Vision Model, parses response, fits it to the `ContactCard` Pydantic model.
   - **Output**: Pydantic model representation or validation error message.
2. **`transcribe_audio_tool`**:
   - **Input**: Audio file bytes.
   - **Action**: Sends audio to Speech-to-Text Model, transcribes it.
   - **Output**: Clean transcript text.
3. **`check_duplicate_contact_tool`**:
   - **Input**: Email and Phone.
   - **Action**: Queries the Google Sheet, searching for matching values in columns `Email` and `Phone`.
   - **Output**: Boolean (True if found, False otherwise) and details of matching contact.
4. **`insert_contact_tool`**:
   - **Input**: `ContactCard` details and generated UUID.
   - **Action**: Appends a new row to Google Sheets.
   - **Output**: Dictionary confirming write success.
5. **`update_voice_note_tool`**:
   - **Input**: `UUID` and `transcript`.
   - **Action**: Finds row in Sheets with the matching `UUID` and appends the transcript to the `Voice Notes` column, appending timestamp.
   - **Output**: Success status.
6. **`whatsapp_notification_tool`**:
   - **Input**: Contact name, company, UUID, and manager phone number.
   - **Action**: Invokes Meta Graph API to send template or custom message.
   - **Output**: API response payload status.

---

# Step 9: Development Roadmap

```mermaid
gantt
    title Development Roadmap
    dateFormat  YYYY-MM-DD
    section Phase 1: Setup
    Directory & Dependencies Setup        :active, 2026-06-30, 1d
    Database and Config Initialization    : 2026-07-01, 1d
    section Phase 2: Services
    Vision & Speech Services              : 2026-07-02, 1d
    Sheets & WhatsApp Services            : 2026-07-03, 1d
    section Phase 3: LangGraph Agent
    Graph Nodes & Edges Setup             : 2026-07-04, 2d
    Session Memory Checkpointing          : 2026-07-06, 1d
    section Phase 4: API & Frontend
    FastAPI Router Endpoints              : 2026-07-07, 1d
    React Frontend Development            : 2026-07-08, 2d
    section Phase 5: Testing & Cloud
    End-to-End Integration Testing        : 2026-07-10, 1d
    Dockerization & Render/GCP Deployment : 2026-07-11, 1d
```

---

## Verification Plan

### Automated Tests
- Run backend unit tests using `pytest` for each helper service (Sheets duplicate check, Pydantic validation, WhatsApp mock).
- Test FastAPI routes with `TestClient`.

### Manual Verification
- Upload test business card image -> Verify Google Sheets insertion & WhatsApp alert.
- Upload duplicate business card image -> Verify message warns user and stops duplicate write.
- Upload audio note -> Verify audio transcript is appended to the correct row via its UUID.
- Toggle between multiple chat sessions -> Verify conversation memory persists.
