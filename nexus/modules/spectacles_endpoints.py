from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import time
from modules.database import database

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
