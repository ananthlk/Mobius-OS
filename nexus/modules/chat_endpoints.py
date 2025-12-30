from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, List
import time
from modules.database import database

router = APIRouter()

# --- Data Models ---
class Message(BaseModel):
    role: str  # "user" or "assistant"
    content: str
    timestamp: Optional[float] = None

class ChatRequest(BaseModel):
    user_id: str 
    messages: List[Message]
    stream: bool = False

# --- Helper Services ---
async def log_interaction(user_id: str, role: str, content: str):
    """
    Background task to log interaction to Postgres.
    """
    query = "INSERT INTO interactions (user_id, role, content) VALUES (:user_id, :role, :content)"
    await database.execute(query=query, values={"user_id": user_id, "role": role, "content": content})

# --- Endpoints ---

@router.post("/completions")
async def chat_completions(request: ChatRequest, background_tasks: BackgroundTasks):
    """
    Standard chat completion endpoint.
    New: Uses BackgroundTasks to log to DB without adding latency.
    """
    # 1. Queue User Message Log
    last_user_msg = request.messages[-1]
    background_tasks.add_task(log_interaction, request.user_id, "user", last_user_msg.content)
    
    # TODO: Connect to LLM Service (OpenAI/Gemini/Local)
    
    response_content = f"Received {len(request.messages)} messages. This is a mock response from the Nexus."
    
    response_msg = Message(
        role="assistant", 
        content=response_content,
        timestamp=time.time()
    )
    
    # 2. Queue Assistant Response Log
    background_tasks.add_task(log_interaction, request.user_id, "assistant", response_content)
    
    return response_msg

@router.get("/history")
async def get_chat_history(user_id: str):
    """
    Retrieve chat history for a user from Postgres.
    """
    query = "SELECT role, content, created_at FROM interactions WHERE user_id = :user_id ORDER BY created_at ASC"
    rows = await database.fetch_all(query=query, values={"user_id": user_id})
    return {"history": rows}
