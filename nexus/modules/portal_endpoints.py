from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, List
import time
from nexus.modules.database import database

router = APIRouter()

# --- Data Models (Portal Specific) ---
class Message(BaseModel):
    role: str
    content: str
    timestamp: Optional[float] = None

class PortalChatRequest(BaseModel):
    user_id: str
    messages: List[Message]
    active_patient_id: Optional[str] = None # Portal specific context
    stream: bool = False

# --- Helper ---
async def log_portal_interaction(user_id: str, role: str, content: str):
    query = "INSERT INTO interactions (user_id, role, content) VALUES (:user_id, :role, :content)"
    # Prefix role with 'portal_' to distinguish in DB
    db_role = f"portal_{role}" if role in ["user", "assistant"] else role
    await database.execute(query=query, values={"user_id": user_id, "role": db_role, "content": content})

# --- Endpoints ---

@router.post("/chat")
async def portal_chat(request: PortalChatRequest, background_tasks: BackgroundTasks):
    """
    Dedicated chat endpoint for the Web Portal.
    """
    last_msg = request.messages[-1]
    
    # Log
    background_tasks.add_task(log_portal_interaction, request.user_id, "user", last_msg.content)
    
    # Logic
    response_content = f"Portal: Validating request for patient {request.active_patient_id or 'None'}. Logic path: Dashboard."
    
    response_msg = Message(
        role="assistant",
        content=response_content,
        timestamp=time.time()
    )
    
    # Log
    background_tasks.add_task(log_portal_interaction, request.user_id, "assistant", response_content)
    
    return response_msg
