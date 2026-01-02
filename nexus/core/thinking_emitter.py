"""
Utility module for emitting thinking messages from any module.
Any module can use this without inheriting from BaseOrchestrator.
"""
from typing import Dict, Any, Optional
from nexus.core.base_agent import BaseAgent
import logging

logger = logging.getLogger("nexus.thinking_emitter")


async def emit_thinking(session_id: Optional[int], payload: Dict[str, Any]) -> None:
    """
    Emit a thinking message from any module.
    
    Args:
        session_id: Session ID (None to skip emission)
        payload: Thinking payload dict (must include 'message' field)
    """
    if session_id is None:
        logger.debug(f"Skipping thinking emission - no session_id. Payload: {payload.get('message', 'N/A')}")
        return
    
    try:
        agent = BaseAgent(session_id=session_id)
        await agent.emit_thinking(payload)
    except Exception as e:
        logger.error(f"Failed to emit thinking message: {e}")


async def emit_prompt_usage(
    session_id: Optional[int],
    prompt_key: str,
    prompt_length: int,
    strategy: Optional[str] = None,
    module_name: str = "unknown"
) -> None:
    """
    Emit a thinking message about prompt usage.
    This is called automatically by prompt_manager when a prompt is retrieved.
    
    Args:
        session_id: Session ID (None to skip)
        prompt_key: Prompt key (e.g., "workflow:tabula_rasa:None")
        prompt_length: Length of the prompt in characters
        strategy: Strategy used (e.g., "TABULA_RASA", "EVIDENCE_BASED")
        module_name: Module name (e.g., "workflow", "chat")
    """
    if session_id is None:
        return
    
    # Build message with strategy and prompt info
    message = f"📝 Prompt: {prompt_key}"
    if strategy:
        message += f" | Strategy: {strategy}"
    message += f" | Length: {prompt_length} chars"
    
    payload = {
        "message": message,
        "prompt_key": prompt_key,
        "prompt_length": prompt_length,
        "strategy": strategy,
        "module": module_name
    }
    
    await emit_thinking(session_id, payload)

