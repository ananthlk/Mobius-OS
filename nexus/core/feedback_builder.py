"""
Feedback Builder - Helper for emitting feedback UI via ARTIFACTS.

Allows any brain/agent to emit feedback UI that will be rendered
dynamically in the frontend chat interface, similar to action buttons.
"""
from typing import Optional, Dict, Any
from nexus.core.base_agent import BaseAgent

async def emit_feedback_ui(
    agent: BaseAgent,
    memory_event_id: int,
    metadata: Optional[Dict[str, Any]] = None
) -> None:
    """
    Helper function to emit feedback UI via ARTIFACTS.
    
    Args:
        agent: BaseAgent instance
        memory_event_id: The ID of the memory_event (OUTPUT) this feedback is for
        metadata: Optional metadata for additional context
    
    Example:
        await emit_feedback_ui(
            agent,
            memory_event_id=123,
            metadata={"session_id": 456}
        )
    """
    payload = {
        "type": "FEEDBACK_UI",
        "memory_event_id": memory_event_id,
    }
    
    # Add metadata if provided
    if metadata:
        payload["metadata"] = metadata
    
    await agent.emit("ARTIFACTS", payload)

