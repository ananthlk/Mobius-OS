"""
External Conversation Logging
Allows external tools (like Cursor IDE) to log conversations to the interactions table.
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional
from nexus.modules.database import database
import logging

logger = logging.getLogger("nexus.external_logging")

router = APIRouter(prefix="/api/external", tags=["external"])

class ConversationMessage(BaseModel):
    role: str  # "user" | "assistant" | "system"
    content: str
    timestamp: Optional[str] = None

class LogConversationRequest(BaseModel):
    user_id: str
    source: str  # "cursor", "vscode", "manual", etc.
    messages: List[ConversationMessage]
    metadata: Optional[dict] = None

async def log_external_interaction(user_id: str, source: str, role: str, content: str):
    """
    Logs an interaction from an external source to the interactions table.
    """
    try:
        query = "INSERT INTO interactions (user_id, role, content) VALUES (:user_id, :role, :content)"
        # Prefix role with source to distinguish in DB
        db_role = f"{source}_{role}" if role in ["user", "assistant", "system"] else role
        await database.execute(query=query, values={
            "user_id": user_id,
            "role": db_role,
            "content": content
        })
        logger.info(f"Logged {source} interaction: {role} ({len(content)} chars)")
    except Exception as e:
        logger.error(f"Failed to log external interaction: {e}")
        raise

@router.post("/log-conversation")
async def log_conversation(request: LogConversationRequest, background_tasks: BackgroundTasks):
    """
    Logs a full conversation from an external source (e.g., Cursor IDE).
    
    Example:
    ```json
    {
        "user_id": "ananth@example.com",
        "source": "cursor",
        "messages": [
            {"role": "user", "content": "How do I...", "timestamp": "2025-12-31T12:00:00Z"},
            {"role": "assistant", "content": "You can...", "timestamp": "2025-12-31T12:00:05Z"}
        ],
        "metadata": {"workspace": "Mobius OS"}
    }
    ```
    """
    try:
        # Log all messages in background
        for msg in request.messages:
            background_tasks.add_task(
                log_external_interaction,
                request.user_id,
                request.source,
                msg.role,
                msg.content
            )
        
        return {
            "status": "logged",
            "message_count": len(request.messages),
            "source": request.source
        }
    except Exception as e:
        logger.error(f"Failed to log conversation: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/log-message")
async def log_single_message(
    user_id: str,
    source: str,
    role: str,
    content: str,
    background_tasks: BackgroundTasks
):
    """
    Logs a single message from an external source.
    Quick endpoint for real-time logging.
    """
    try:
        background_tasks.add_task(
            log_external_interaction,
            user_id,
            source,
            role,
            content
        )
        return {"status": "logged", "source": source}
    except Exception as e:
        logger.error(f"Failed to log message: {e}")
        raise HTTPException(status_code=500, detail=str(e))








