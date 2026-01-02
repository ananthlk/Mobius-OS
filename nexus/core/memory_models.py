from pydantic import BaseModel, Field
from typing import Literal, Dict, Any, Optional
from datetime import datetime

class MemoryEvent(BaseModel):
    """
    Base model for all 4 memory event types.
    Aligns with the 'memory_events' DB table.
    """
    session_id: int
    bucket: Literal["THINKING", "ARTIFACTS", "PERSISTENCE", "OUTPUT"]
    created_at: datetime = Field(default_factory=datetime.now)
    payload: Dict[str, Any] # Flexible payload for JSON persistence

class ThinkingEvent(MemoryEvent):
    """Layer 2: Logic/Reasoning (The Brain Bubble)"""
    bucket: Literal["THINKING"] = "THINKING"
    payload: Dict[str, Any] = Field(..., description="{'message': 'Analyzing manual...', 'confidence': 0.9}")

class ArtifactEvent(MemoryEvent):
    """Layer 3: Structured Data (Left Rail / RAG)"""
    bucket: Literal["ARTIFACTS"] = "ARTIFACTS"
    payload: Dict[str, Any] = Field(..., description="{'type': 'DRAFT_PLAN', 'data': {...}}")

class PersistenceEvent(MemoryEvent):
    """Layer 1: Audit Logs (Invisible to User)"""
    bucket: Literal["PERSISTENCE"] = "PERSISTENCE"
    payload: Dict[str, Any] = Field(..., description="{'query': 'INSERT INTO...', 'rows': 1}")

class OutputEvent(MemoryEvent):
    """Layer 4: Conversational Reply (Chat)"""
    bucket: Literal["OUTPUT"] = "OUTPUT"
    payload: Dict[str, Any] = Field(..., description="{'role': 'system', 'content': 'Hello world'}")
