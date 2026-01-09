from fastapi import APIRouter, HTTPException, BackgroundTasks, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import time
import httpx
import logging
import json
import asyncio
from datetime import datetime, timezone
from nexus.modules.database import database

router = APIRouter()
logger = logging.getLogger("nexus.spectacles")

# --- Data Models ---
class ContextPayload(BaseModel):
    url: str
    title: str
    selection: Optional[str] = None
    dom_snippet: Optional[str] = None

class ActionCommand(BaseModel):
    user_id: str
    command: str # "draft_reply", "summarize", "scrape"
    context: ContextPayload

class Message(BaseModel):
    role: str
    content: str
    timestamp: Optional[float] = None

class ExtensionChatRequest(BaseModel):
    user_id: str
    messages: List[Message]
    context_id: Optional[str] = None # Link to previously sent context

class EmailContext(BaseModel):
    subject: str
    from_: str  # Use from_ in Python (from is reserved keyword)
    body: str
    client: str

class EmailDraftRequest(BaseModel):
    user_id: str
    email_context: EmailContext

# --- Helper Services ---
async def log_spectacles_event(user_id: str, event_type: str, details: str):
    query = "INSERT INTO interactions (user_id, role, content) VALUES (:user_id, :role, :content)"
    await database.execute(query=query, values={"user_id": user_id, "role": f"spectacles_event:{event_type}", "content": details})

# --- Endpoints ---

@router.post("/chat")
async def spectacles_chat(request: ExtensionChatRequest, background_tasks: BackgroundTasks):
    """
    Dedicated chat endpoint for the Chrome Extension.
    """
    last_msg = request.messages[-1]
    
    # Log user message
    background_tasks.add_task(log_spectacles_event, request.user_id, "chat_user", last_msg.content)
    
    # Mock logic - eventually this uses the Context ID to pull RAG data
    response_content = f"Spectacles: Received your message. Logic path: Extension."
    
    response_msg = Message(
        role="assistant",
        content=response_content,
        timestamp=time.time()
    )
    
    # Log assistant response
    background_tasks.add_task(log_spectacles_event, request.user_id, "chat_assistant", response_content)
    
    return response_msg

@router.post("/command")
async def execute_command(command: ActionCommand, background_tasks: BackgroundTasks):
    """
    Handle specific button clicks (e.g. 'Draft Reply').
    """
    background_tasks.add_task(log_spectacles_event, command.user_id, "command", f"Executed {command.command} on {command.context.url}")
    
    # Mock result
    result_text = f"Executed {command.command} successfully."
    
    return {
        "status": "success",
        "result": result_text,
        "action_taken": command.command
    }

@router.post("/email/draft")
async def draft_email_reply(request: EmailDraftRequest, background_tasks: BackgroundTasks):
    """
    Generate a draft reply for an email.
    Currently returns a stub reply.
    """
    email_ctx = request.email_context
    
    # Log the email draft request
    log_details = f"Draft request for email from {email_ctx.from_}, subject: {email_ctx.subject[:100]}"
    background_tasks.add_task(log_spectacles_event, request.user_id, "email_draft_request", log_details)
    
    # Stub reply - in the future this will use LLM to generate actual draft
    stub_reply = "Thank you for your email. I will review this and get back to you soon."
    
    # Log the draft response
    background_tasks.add_task(log_spectacles_event, request.user_id, "email_draft_response", f"Draft generated: {stub_reply}")
    
    return {
        "status": "success",
        "draft": stub_reply,
        "user_id": request.user_id
    }

class ScrapeRequest(BaseModel):
    user_id: str
    scrape_type: str  # 'page' or 'tree'
    data: Dict[str, Any]

class EligibilityCheckRequest(BaseModel):
    user_id: str
    mrn: str

@router.post("/scrape")
async def save_scraped_data(request: ScrapeRequest, background_tasks: BackgroundTasks):
    """
    Save scraped page data or DOM tree.
    """
    scrape_type = request.scrape_type
    data = request.data
    
    # Log the scrape request
    url = data.get('url', 'unknown')
    log_details = f"Scrape {scrape_type} from {url}"
    background_tasks.add_task(log_spectacles_event, request.user_id, f"scrape_{scrape_type}", log_details)
    
    # Store scraped data (in production, this would go to a database or storage)
    # For now, just log it
    if scrape_type == 'page':
        text_length = data.get('textLength', 0)
        links_count = len(data.get('links', []))
        images_count = len(data.get('images', []))
        log_details = f"Page scraped: {text_length} chars, {links_count} links, {images_count} images"
    elif scrape_type == 'tree':
        log_details = f"DOM tree scraped: {url}"
    
    background_tasks.add_task(log_spectacles_event, request.user_id, f"scrape_{scrape_type}_saved", log_details)
    
    return {
        "status": "success",
        "scrape_type": scrape_type,
        "url": url,
        "saved_at": time.time()
    }

@router.post("/eligibility/check")
async def check_eligibility(request: EligibilityCheckRequest, background_tasks: BackgroundTasks):
    """
    Check patient eligibility using eligibility v2.
    Accepts MRN, starts session, creates case, and processes initial turn.
    """
    try:
        mrn = request.mrn.strip().upper()
        user_id = request.user_id
        
        # Validate MRN format (MRN followed by alphanumeric)
        import re
        if not re.match(r'^MRN\w+$', mrn):
            raise HTTPException(status_code=400, detail=f"Invalid MRN format. Expected format: MRN followed by alphanumeric characters (e.g., MRN056)")
        
        # Log the eligibility check request
        log_details = f"Eligibility check requested for MRN: {mrn}"
        background_tasks.add_task(log_spectacles_event, user_id, "eligibility_check_request", log_details)
        
        base_url = "http://localhost:8000"  # TODO: Get from config
        
        # Step 1: Start eligibility v2 session
        async with httpx.AsyncClient(timeout=30.0) as client:
            session_response = await client.post(
                f"{base_url}/api/eligibility-v2/session/start",
                json={"user_id": user_id},
                headers={"Content-Type": "application/json"}
            )
            session_response.raise_for_status()
            session_data = session_response.json()
            session_id = session_data.get("session_id")
            
            if not session_id:
                raise HTTPException(status_code=500, detail="Failed to create eligibility session")
            
            logger.info(f"Created eligibility session {session_id} for MRN {mrn}")
            
            # Step 2: Generate case_id (use MRN as case_id for simplicity)
            case_id = f"spectacles_{mrn}_{int(time.time())}"
            
            # Step 3: Create/get case with patient_id header
            case_response = await client.get(
                f"{base_url}/api/eligibility-v2/cases/{case_id}/view",
                headers={
                    "X-Session-ID": str(session_id),
                    "X-Patient-ID": mrn
                }
            )
            case_response.raise_for_status()
            case_data = case_response.json()
            
            logger.info(f"Created/retrieved case {case_id} for session {session_id}")
            
            # Step 4: Process initial turn with MRN message
            ui_event_data = {
                "event_type": "user_message",
                "data": {"message": f"Check eligibility for {mrn}"},
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            turn_response = await client.post(
                f"{base_url}/api/eligibility-v2/cases/{case_id}/turn",
                json=ui_event_data,
                headers={
                    "X-Session-ID": str(session_id),
                    "X-Patient-ID": mrn,
                    "X-User-ID": user_id,
                    "Content-Type": "application/json"
                }
            )
            turn_response.raise_for_status()
            turn_data = turn_response.json()
            
            logger.info(f"Processed initial turn for case {case_id}")
            
            # Log success
            background_tasks.add_task(log_spectacles_event, user_id, "eligibility_check_started", 
                                    f"Eligibility check started for {mrn}, session_id={session_id}, case_id={case_id}")
            
            return {
                "status": "success",
                "session_id": session_id,
                "case_id": case_id,
                "mrn": mrn,
                "message": "Eligibility check initiated. Status updates will stream via SSE."
            }
            
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error in eligibility check: {e.response.status_code} - {e.response.text}")
        raise HTTPException(status_code=e.response.status_code, detail=f"Eligibility service error: {e.response.text}")
    except httpx.RequestError as e:
        logger.error(f"Request error in eligibility check: {str(e)}")
        raise HTTPException(status_code=503, detail=f"Failed to connect to eligibility service: {str(e)}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error checking eligibility: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

@router.get("/eligibility/stream")
async def stream_eligibility_events(
    session_id: int = Query(..., description="Session ID to stream events for"),
    last_event_time: Optional[str] = Query(None, description="ISO timestamp of last received event")
):
    """
    Stream eligibility events via Server-Sent Events (SSE).
    Streams ELIGIBILITY_PROCESS, THINKING, and OUTPUT events from memory_events table.
    """
    from nexus.modules.database import parse_jsonb
    
    async def event_generator():
        try:
            last_timestamp = None
            if last_event_time:
                try:
                    last_timestamp = datetime.fromisoformat(last_event_time.replace('Z', '+00:00'))
                except:
                    pass
            
            # Initial connection message
            yield f"data: {json.dumps({'type': 'connected', 'session_id': session_id, 'timestamp': datetime.now(timezone.utc).isoformat()})}\n\n"
            
            while True:
                try:
                    # Query for new events
                    query = """
                        SELECT id, bucket_type, payload, created_at
                        FROM memory_events
                        WHERE session_id = :session_id
                        AND bucket_type IN ('ELIGIBILITY_PROCESS', 'THINKING', 'OUTPUT')
                    """
                    params = {"session_id": session_id}
                    
                    if last_timestamp:
                        query += " AND created_at > :last_timestamp"
                        params["last_timestamp"] = last_timestamp
                    
                    query += " ORDER BY created_at ASC LIMIT 100"
                    
                    rows = await database.fetch_all(query=query, values=params)
                    
                    if rows:
                        for row in rows:
                            event_type = None
                            # Parse JSONB payload properly
                            payload_data = parse_jsonb(row["payload"])
                            
                            # Map bucket_type to event type
                            if row["bucket_type"] == "ELIGIBILITY_PROCESS":
                                event_type = "status"
                            elif row["bucket_type"] == "THINKING":
                                event_type = "thinking"
                            elif row["bucket_type"] == "OUTPUT":
                                event_type = "chat"
                            
                            if event_type:
                                # Format timestamp
                                timestamp = row["created_at"]
                                if hasattr(timestamp, "isoformat"):
                                    timestamp_str = timestamp.isoformat()
                                else:
                                    timestamp_str = str(timestamp)
                                
                                # For OUTPUT events, include memory_event_id for feedback
                                memory_event_id = row["id"] if event_type == "chat" else None
                                
                                event_data = {
                                    "type": event_type,
                                    "payload": payload_data,
                                    "timestamp": timestamp_str,
                                    "event_id": row["id"]
                                }
                                if memory_event_id:
                                    event_data["memory_event_id"] = memory_event_id
                                
                                yield f"data: {json.dumps(event_data)}\n\n"
                                last_timestamp = row["created_at"]
                    
                    # Poll every 500ms
                    await asyncio.sleep(0.5)
                    yield f": keepalive\n\n"
                    
                except asyncio.CancelledError:
                    logger.info(f"SSE stream cancelled for session {session_id}")
                    break
                except Exception as e:
                    logger.error(f"Error in SSE stream for session {session_id}: {e}", exc_info=True)
                    error_data = {
                        "type": "error",
                        "message": str(e),
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                    yield f"data: {json.dumps(error_data)}\n\n"
                    await asyncio.sleep(1)
                    
        except Exception as e:
            logger.error(f"Fatal error in SSE stream for session {session_id}: {e}", exc_info=True)
            error_data = {
                "type": "error",
                "message": f"Stream error: {str(e)}",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            yield f"data: {json.dumps(error_data)}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable nginx buffering
        }
    )
