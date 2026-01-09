"""
Permission and RBAC Utilities

Role-based access control helpers.
"""
import logging
from typing import Optional
from fastapi import HTTPException, Depends
from nexus.modules.users.domain.user import User
from nexus.modules.users.services.user_service import UserService
from nexus.modules.users.auth.middleware import get_current_user

logger = logging.getLogger("nexus.users.permissions")

_user_service = UserService()


async def check_permission(
    user: User,
    permission: str
) -> bool:
    """
    Check if user has a specific permission.
    
    Args:
        user: User object
        permission: Permission to check (e.g., 'view', 'edit', 'admin')
    
    Returns:
        True if user has permission, False otherwise
    """
    return await _user_service.has_permission(user.id, permission)


async def require_permission(
    permission: str,
    current_user: User = Depends(get_current_user)
) -> User:
    """
    FastAPI dependency to require a specific permission.
    
    Raises HTTPException if user doesn't have the required permission.
    
    Args:
        permission: Required permission (e.g., 'view', 'edit', 'admin')
        current_user: Current authenticated user (from get_current_user)
    
    Returns:
        User object if permission granted
    
    Raises:
        HTTPException: If user doesn't have permission
    """
    has_permission = await check_permission(current_user, permission)
    if not has_permission:
        raise HTTPException(
            status_code=403,
            detail=f"Permission '{permission}' required"
        )
    return current_user



