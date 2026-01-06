"""
User Context Helper Module

Provides helper functions for extracting and validating user context from requests.
Supports role-based access control.
"""
import logging
from typing import Dict, Any, Optional
from fastapi import HTTPException, Header
from nexus.modules.user_manager import user_manager

logger = logging.getLogger("nexus.user_context")


async def get_user_id_from_header(user_id: Optional[str] = Header(None, alias="X-User-ID")) -> Optional[str]:
    """
    Extract user_id from request header.
    
    Args:
        user_id: User ID from X-User-ID header
    
    Returns:
        User ID string or None
    """
    return user_id


async def get_user_context(
    user_id: Optional[str] = Header(None, alias="X-User-ID"),
    session_id: Optional[str] = Header(None, alias="X-Session-ID")
) -> Dict[str, Any]:
    """
    Extract user context from request headers.
    
    Args:
        user_id: User ID from X-User-ID header
        session_id: Session ID from X-Session-ID header (optional)
    
    Returns:
        Dictionary with user_id and session_id
    """
    return {
        "user_id": user_id or "system",
        "session_id": session_id
    }


async def require_user_context(
    user_id: Optional[str] = Header(None, alias="X-User-ID")
) -> str:
    """
    Require user_id in request, raise exception if missing.
    
    Args:
        user_id: User ID from X-User-ID header
    
    Returns:
        User ID string
    
    Raises:
        HTTPException: If user_id is missing
    """
    if not user_id:
        raise HTTPException(status_code=401, detail="User ID required")
    return user_id


async def require_admin_role(
    user_id: Optional[str] = Header(None, alias="X-User-ID")
) -> str:
    """
    Require admin role, raise exception if user is not admin.
    
    Args:
        user_id: User ID from X-User-ID header (as auth_id string)
    
    Returns:
        User ID string
    
    Raises:
        HTTPException: If user is not admin
    """
    if not user_id:
        raise HTTPException(status_code=401, detail="User ID required")
    
    # For now, user_id from header is auth_id string, not users.id
    # TODO: Resolve auth_id to users.id and check role
    # This is a placeholder - proper implementation should:
    # 1. Get user by auth_id
    # 2. Check if role is 'admin'
    # 3. Raise 403 if not admin
    
    # For backward compatibility, we'll allow this check to pass for now
    # but log a warning
    logger.warning(f"[user_context.require_admin_role] Admin check not fully implemented - user_id={user_id}")
    return user_id


async def check_permission(
    user_id: str,
    permission: str
) -> bool:
    """
    Check if user has permission.
    
    Args:
        user_id: User ID (auth_id string)
        permission: Permission to check
    
    Returns:
        True if user has permission
    """
    # TODO: Resolve auth_id to users.id and check permission
    # This is a placeholder implementation
    logger.debug(f"[user_context.check_permission] Permission check - user_id={user_id}, permission={permission}")
    return True


def build_user_context_dict(user_id: str, session_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Build user context dictionary for passing to managers.
    
    Args:
        user_id: User ID
        session_id: Session ID (optional)
    
    Returns:
        User context dictionary
    """
    return {
        "user_id": user_id,
        "session_id": session_id
    }



