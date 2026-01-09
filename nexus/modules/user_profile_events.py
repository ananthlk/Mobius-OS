"""
User Profile Events

Helper functions for tracking user interactions with different modules.
"""
import logging
from typing import Optional, Dict, Any
from nexus.modules.database import database

logger = logging.getLogger("nexus.user_profile_events")


async def track_chat_interaction(
    auth_id: str,
    user_message: str,
    assistant_response: str,
    background_tasks: Optional[Any] = None,
    metadata: Optional[Dict[str, Any]] = None
):
    """
    Track chat interaction for user profile.
    This is a no-op placeholder - can be extended to log to user_profiles table.
    """
    try:
        # Placeholder implementation - can be extended to actually track interactions
        logger.debug(f"Tracking chat interaction for user {auth_id}")
        # Future: Insert into user_profiles.interaction_history or similar
    except Exception as e:
        logger.warning(f"Failed to track chat interaction: {e}")


async def track_workflow_interaction(
    auth_id: str,
    user_message: str,
    assistant_response: str,
    session_id: Optional[int] = None,
    workflow_name: Optional[str] = None
):
    """
    Track workflow interaction for user profile.
    This is a no-op placeholder - can be extended to log to user_profiles table.
    """
    try:
        # Placeholder implementation - can be extended to actually track interactions
        logger.debug(f"Tracking workflow interaction for user {auth_id}, workflow: {workflow_name}")
        # Future: Insert into user_profiles.interaction_history or similar
    except Exception as e:
        logger.warning(f"Failed to track workflow interaction: {e}")
