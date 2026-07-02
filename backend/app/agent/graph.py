from langchain_core.messages import BaseMessage, AIMessage, HumanMessage
from langgraph.graph import StateGraph, END
from app.config import settings, logger
from app.agent.state import AgentState
from app.services.vision import vision_service
from app.services.speech import speech_service
from app.services.sheets import sheets_service
from app.services.whatsapp import whatsapp_service
from app.services.ai_provider import get_ai_service
from app.models.contact import ContactCard
import asyncio

def process_input_node(state: AgentState) -> dict:
    logger.info(f"Agent processing input for session ID: {state['session_id']}")
    return {"session_id": state["session_id"]}

# Node 2: Vision Card OCR Extractor
async def extract_card_node(state: AgentState) -> dict:
    logger.info("Executing extract_card_node...")
    if not state.get("file_bytes"):
        return {"status": "failed", "error_message": "Missing image file payload."}
    try:
        card = await vision_service.extract_contact_card(
            state["file_bytes"],
            state.get("file_mime", "image/jpeg")
        )
        return {
            "extracted_contact": card.model_dump(),
            "status": "extracted"
        }
    except Exception as e:
        logger.error(f"Vision extraction failed in graph node: {str(e)}")
        return {
            "status": "failed",
            "error_message": str(e)
        }

# Node 3: Audio Notes Speech Transcriber
async def transcribe_audio_node(state: AgentState) -> dict:
    logger.info("Executing transcribe_audio_node...")
    if not state.get("file_bytes"):
        return {"status": "failed", "error_message": "Missing audio file payload."}
    try:
        transcript = await speech_service.transcribe_audio(
            state["file_bytes"],
            state.get("file_mime", "audio/mp3")
        )
        return {
            "transcription": transcript,
            "status": "transcribed"
        }
    except Exception as e:
        logger.error(f"Audio transcription failed in graph node: {str(e)}")
        return {
            "status": "failed",
            "error_message": str(e)
        }

# Node 4: Database Integrator Node (Google Sheets and MongoDB Session State)
async def manage_sheet_node(state: AgentState) -> dict:
    logger.info("Executing manage_sheet_node...")
    status = state.get("status")
    if status == "failed":
        return {"session_id": state["session_id"]}
        
    extracted = state.get("extracted_contact")
    transcription = state.get("transcription")
    session_id = state.get("session_id")

    # Flow A: Save Digitized Card Info
    if extracted:
        try:
            contact = ContactCard(**extracted)
            result = await sheets_service.insert_contact(contact)
            
            if result["status"] == "duplicate":
                dup = result["contact"]
                existing_uuid = dup.get("uuid")
                
                # Link active session to duplicate contact UUID and name in MongoDB
                from app.database.mongo import update_last_contact_uuid
                await update_last_contact_uuid(session_id, existing_uuid, dup.get("name"))
                
                msg = (
                    f"⚠️ **Duplicate contact detected!**\n\n"
                    f"A contact with email *{contact.email}* or phone *{contact.phone}* already exists. "
                    f"This session is now linked to the existing contact."
                )
                return {
                    "status": "duplicate",
                    "last_contact_uuid": existing_uuid,
                    "extracted_contact": {
                        "name": dup.get("name"),
                        "company": dup.get("company"),
                        "phone": dup.get("phone"),
                        "email": dup.get("email"),
                        "uuid": existing_uuid
                    },
                    "messages": [AIMessage(content=msg)]
                }
            
            # Successful write
            msg = (
                f"✅ **Visiting Card Digitized & Saved!**\n\n"
                f"The contact has been successfully added to Google Sheets and is linked to this session."
            )
            
            # Track UUID and Name in MongoDB session
            from app.database.mongo import update_last_contact_uuid
            await update_last_contact_uuid(session_id, contact.uuid, contact.name)
            
            return {
                "status": "inserted",
                "last_contact_uuid": contact.uuid,
                "messages": [AIMessage(content=msg)]
            }
        except Exception as e:
            logger.error(f"Google Sheets contact save failed: {str(e)}")
            err_msg = str(e)
            if "EOF occurred" in err_msg or "violation of protocol" in err_msg or "SSL" in err_msg or "handshake" in err_msg.lower():
                err_msg += " (Tip: This SSL handshake disruption is usually caused by an active corporate VPN, network proxy filters, or local antivirus security software intercepting HTTPS traffic. Please temporarily disable your VPN/proxy/antivirus and try again.)"
            return {
                "status": "failed",
                "error_message": f"Google Sheets write failure: {err_msg}"
            }

    # Flow B: Append Voice Notes Transcript
    elif transcription is not None:
        if not transcription.strip():
            msg = (
                f"⚠️ **Speech Transcription Warning**\n\n"
                f"I processed the audio file, but it appears to be silent or contains no recognizable speech. "
                f"No notes were appended to the contact."
            )
            return {
                "status": "failed",
                "messages": [AIMessage(content=msg)]
            }

        last_uuid = state.get("last_contact_uuid")
        if not last_uuid:
            msg = (
                f"❌ **Failed to update contact notes.**\n\n"
                f"I transcribed your voice note: \n"
                f"_\"{transcription}\"_\n\n"
                f"However, there is no active contact associated with this session. "
                f"Please upload a business card first."
            )
            return {
                "status": "failed",
                "messages": [AIMessage(content=msg)]
            }
            
        try:
            logger.info(f"Updating voice notes for contact UUID: {last_uuid}")
            success = await sheets_service.update_voice_note(last_uuid, transcription)
            if success:
                msg = (
                    f"🎙️ **Voice Note Added to Current Contact!**\n\n"
                    f"📝 *Transcript:* \"{transcription}\"\n"
                    f"🆔 *Associated Contact UUID:* {last_uuid}"
                )
                return {
                    "status": "updated",
                    "messages": [AIMessage(content=msg)]
                }
            else:
                msg = f"❌ Failed to locate contact UUID {last_uuid} in Google Sheets to append transcript."
                return {
                    "status": "failed",
                    "messages": [AIMessage(content=msg)]
                }
        except Exception as e:
            logger.error(f"Google Sheets voice note update failed: {str(e)}")
            err_msg = str(e)
            if "EOF occurred" in err_msg or "violation of protocol" in err_msg or "SSL" in err_msg or "handshake" in err_msg.lower():
                err_msg += " (Tip: This SSL handshake disruption is usually caused by an active corporate VPN, network proxy filters, or local antivirus security software intercepting HTTPS traffic. Please temporarily disable your VPN/proxy/antivirus and try again.)"
            return {
                "status": "failed",
                "error_message": f"Google Sheets update failure: {err_msg}"
            }

    return {"session_id": state["session_id"]}

# Node 5: WhatsApp Notification dispatcher
async def whatsapp_notify_node(state: AgentState) -> dict:
    logger.info("Executing whatsapp_notify_node...")
    extracted = state.get("extracted_contact")
    if not extracted:
        return {"session_id": state["session_id"]}
    try:
        contact = ContactCard(**extracted)
        await whatsapp_service.send_contact_notification(contact)
    except Exception as e:
        logger.error(f"WhatsApp dispatch failure inside graph node: {str(e)}")
    return {"session_id": state["session_id"]}

# Node 6: Conversational Chat Replier Node
async def chat_response_node(state: AgentState) -> dict:
    logger.info("Executing chat_response_node...")
    status = state.get("status")
    error_msg = state.get("error_message")
    
    # Check for graph failures
    if status == "failed" or error_msg:
        err_message = f"❌ *Error Encountered:* {error_msg or 'Processing failed.'}"
        return {
            "messages": [AIMessage(content=err_message)]
        }
        
    # If a message has already been generated by manage_sheet_node on this turn, do nothing
    if status in ["inserted", "duplicate", "updated"]:
        return {"session_id": state["session_id"]}
        
    # General text prompt conversational response
    text_input = state.get("text_input")
    if text_input:
        reply = await get_ai_service().generate_chat_response(text_input, state["messages"])
        return {
            "messages": [AIMessage(content=reply)]
        }
        
    return {"session_id": state["session_id"]}

# Define Graph Workflow
workflow = StateGraph(AgentState)

# Add Nodes
workflow.add_node("process_input", process_input_node)
workflow.add_node("extract_card", extract_card_node)
workflow.add_node("transcribe_audio", transcribe_audio_node)
workflow.add_node("manage_sheet", manage_sheet_node)
workflow.add_node("whatsapp_notify", whatsapp_notify_node)
workflow.add_node("chat_response", chat_response_node)

# Set Entry Edge
workflow.set_entry_point("process_input")

# Conditional Router: Image vs Audio vs Text
def route_input(state: AgentState) -> str:
    file_type = state.get("file_type")
    if file_type == "image":
        return "extract_card"
    elif file_type == "audio":
        return "transcribe_audio"
    else:
        return "chat_response"

workflow.add_conditional_edges(
    "process_input",
    route_input,
    {
        "extract_card": "extract_card",
        "transcribe_audio": "transcribe_audio",
        "chat_response": "chat_response"
    }
)

# Connect processing nodes to Sheets Manager
workflow.add_edge("extract_card", "manage_sheet")
workflow.add_edge("transcribe_audio", "manage_sheet")

# Conditional Router: Alert dispatcher on new insertions
def route_after_sheet(state: AgentState) -> str:
    if state.get("status") == "inserted":
        return "whatsapp_notify"
    return "chat_response"

workflow.add_conditional_edges(
    "manage_sheet",
    route_after_sheet,
    {
        "whatsapp_notify": "whatsapp_notify",
        "chat_response": "chat_response"
    }
)

# Connect WhatsApp dispatcher to final Chat response node
workflow.add_edge("whatsapp_notify", "chat_response")
workflow.add_edge("chat_response", END)

# Compile Graph Application
agent_app = workflow.compile()
