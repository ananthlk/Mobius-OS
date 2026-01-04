from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import time
from nexus.modules.database import database

router = APIRouter()

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
