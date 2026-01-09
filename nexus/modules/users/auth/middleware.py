"""
Authentication Middleware

FastAPI dependencies for authentication and user context.
"""
import logging
from typing import Optional
from fastapi import HTTPException, Header, Depends
from nexus.modules.users.domain.user import User
from nexus.modules.users.services.user_service import UserService
from nexus.modules.users.services.provisioning import UserProvisioningService

logger = logging.getLogger("nexus.users.auth")


# Singleton instances
_user_service = UserService()
_provisioning_service = UserProvisioningService()


async def get_auth_id_from_header(
    x_user_id: Optional[str] = Header(None, alias="X-User-ID")
) -> Optional[str]:
    """
    Extract auth_id from X-User-ID header.
    
    Note: In the current implementation, X-User-ID contains the auth_id (Google OAuth subject ID).
    In a full implementation, this would extract from JWT token.
    """
    return x_user_id


async def get_current_user(
    auth_id: Optional[str] = Depends(get_auth_id_from_header)
) -> User:
    """
    FastAPI dependency to get current authenticated user.
    
    Raises HTTPException if user not found or not authenticated.
    For now, this requires X-User-ID header. In production, this should
    extract from JWT token and validate it.
    """
    if not auth_id:
        raise HTTPException(
            status_code=401,
            detail="Authentication required. Missing X-User-ID header."
        )
    
    user = await _user_service.get_user_by_auth_id(auth_id)
    if not user:
        raise HTTPException(
            status_code=404,
            detail=f"User not found for auth_id: {auth_id}"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=403,
            detail="User account is inactive"
        )
    
    return user


async def get_optional_user(
    auth_id: Optional[str] = Depends(get_auth_id_from_header)
) -> Optional[User]:
    """
    FastAPI dependency to get current user if authenticated, None otherwise.
    
    Does not raise exception if not authenticated - returns None instead.
    """
    if not auth_id:
        return None
    
    try:
        user = await _user_service.get_user_by_auth_id(auth_id)
        if user and user.is_active:
            return user
    except Exception as e:
        logger.warning(f"Failed to get optional user: {e}")
    
    return None


async def get_or_create_user(
    auth_id: str,
    email: str,
    name: Optional[str] = None
) -> User:
    """
    Get existing user or create new one automatically.
    
    This is used by authentication middleware to provision users
    on first OAuth signin.
    """
    return await _provisioning_service.get_or_create_user(
        auth_id=auth_id,
        email=email,
        name=name,
        role="user"
    )


async def require_admin(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    FastAPI dependency to require admin role.
    
    Raises HTTPException if user is not admin.
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=403,
            detail="Admin access required"
        )
    return current_user



