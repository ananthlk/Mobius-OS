"""
Helper functions for easy integration of profile tracking into chat endpoints.
"""
import logging
from typing import Optional, Dict, Any
from fastapi import BackgroundTasks
from nexus.modules.user_profile_manager import ProfileEvent, user_profile_manager
from nexus.modules.user_manager import user_manager

logger = logging.getLogger("nexus.user_profile_events")


async def track_chat_interaction(
    auth_id: str,
    user_message: str,
    assistant_response: str,
    background_tasks: BackgroundTasks,
    session_id: Optional[int] = None,
    interaction_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
):
    """
    Track a chat interaction and update user profiles.
    Call this after serving a user query.
    
    Args:
        auth_id: User's authentication ID (from session)
        user_message: The user's message/query
        assistant_response: The assistant's response
        background_tasks: FastAPI BackgroundTasks instance
        session_id: Optional session ID if from workflow
        interaction_id: Optional interaction ID
        metadata: Additional metadata (workflow_name, module, strategy, etc.)
    """
    try:
        user = await user_manager.get_user_by_auth_id(auth_id)
        if not user:
            logger.warning(f"User not found for auth_id: {auth_id}")
            return
        
        event = ProfileEvent(
            user_id=user["id"],
            event_type=metadata.get("module", "chat") if metadata else "chat",
            user_message=user_message,
            assistant_response=assistant_response,
            session_id=session_id,
            interaction_id=interaction_id,
            workflow_name=metadata.get("workflow_name") if metadata else None,
            strategy=metadata.get("strategy") if metadata else None,
            metadata=metadata or {}
        )
        
        background_tasks.add_task(user_profile_manager.process_event, event)
        
    except Exception as e:
        logger.error(f"Failed to track chat interaction: {e}", exc_info=True)


async def track_workflow_interaction(
    auth_id: str,
    user_message: str,
    assistant_response: str,
    session_id: int,
    workflow_name: Optional[str],
    strategy: Optional[str],
    background_tasks: BackgroundTasks,
    interaction_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
):
    """
    Track a workflow interaction and update user profiles.
    
    Args:
        auth_id: User's authentication ID
        user_message: The user's message/query
        assistant_response: The assistant's response
        session_id: Workflow session ID
        workflow_name: Name of the workflow
        strategy: Consultant strategy used (TABULA_RASA, EVIDENCE_BASED, CREATIVE)
        background_tasks: FastAPI BackgroundTasks instance
        interaction_id: Optional interaction ID
        metadata: Additional metadata
    """
    workflow_metadata = metadata or {}
    workflow_metadata["workflow_name"] = workflow_name
    workflow_metadata["module"] = "workflow"
    workflow_metadata["strategy"] = strategy
    
    await track_chat_interaction(
        auth_id=auth_id,
        user_message=user_message,
        assistant_response=assistant_response,
        background_tasks=background_tasks,
        session_id=session_id,
        interaction_id=interaction_id,
        metadata=workflow_metadata
    )

