"""
User Management API Endpoints

REST API endpoints for user CRUD operations.
Uses new service layer and authentication middleware.
"""
import logging
from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel, EmailStr
from typing import List, Optional, Dict, Any
from nexus.modules.users.domain.user import User
from nexus.modules.users.services.user_service import UserService
from nexus.modules.users.auth.middleware import get_current_user, require_admin, get_auth_id_from_header
from nexus.modules.users.auth.permissions import require_permission

logger = logging.getLogger("nexus.users.api")

router = APIRouter(prefix="/api/users", tags=["users"])

# Request/Response Models
class CreateUserRequest(BaseModel):
    auth_id: str
    email: EmailStr
    name: Optional[str] = None
    role: str = "user"


class UpdateUserRequest(BaseModel):
    email: Optional[EmailStr] = None
    name: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None


# Service instance
_user_service = UserService()


def build_user_context(user: User, session_id: Optional[str] = None) -> Dict[str, Any]:
    """Build user context dictionary for audit logs."""
    return {
        "user_id": str(user.id),
        "session_id": session_id
    }


@router.get("")
async def list_users(
    role: Optional[str] = Query(None, description="Filter by role"),
    active_only: bool = Query(True, description="Only return active users"),
    current_user: User = Depends(get_current_user)  # Temporarily allowing all authenticated users
):
    """
    List users (temporarily allowing all authenticated users).
    
    Returns list of users with optional filtering.
    """
    logger.debug(f"[user_endpoints.list_users] role={role}, active_only={active_only}")
    
    try:
        users = await _user_service.list_users(
            role_filter=role,
            active_only=active_only
        )
        return {
            "users": [user.to_dict() for user in users],
            "count": len(users)
        }
    except Exception as e:
        logger.error(f"[user_endpoints.list_users] ERROR: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{user_id}")
async def get_user(
    user_id: int,
    current_user: User = Depends(get_current_user)
):
    """
    Get user details by ID.
    
    Users can view their own profile, admins can view any profile.
    """
    logger.debug(f"[user_endpoints.get_user] user_id={user_id}")
    
    try:
        # Temporarily allowing all authenticated users to view any user
        # Check permission: user can view self, admin can view anyone
        # if current_user.id != user_id and current_user.role != "admin":
        #     raise HTTPException(status_code=403, detail="Access denied")
        
        user = await _user_service.get_user(user_id)
        if not user:
            raise HTTPException(status_code=404, detail=f"User {user_id} not found")
        return user.to_dict()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[user_endpoints.get_user] ERROR: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/auth/{auth_id}")
async def get_user_by_auth_id(
    auth_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Get user details by auth_id (Google Auth Subject ID).
    
    Users can view their own profile, admins can view any profile.
    """
    logger.debug(f"[user_endpoints.get_user_by_auth_id] auth_id={auth_id}")
    
    try:
        # Temporarily allowing all authenticated users to view any user
        # Check permission: user can view self, admin can view anyone
        # if current_user.auth_id != auth_id and current_user.role != "admin":
        #     raise HTTPException(status_code=403, detail="Access denied")
        
        user = await _user_service.get_user_by_auth_id(auth_id)
        if not user:
            raise HTTPException(status_code=404, detail=f"User with auth_id {auth_id} not found")
        return user.to_dict()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[user_endpoints.get_user_by_auth_id] ERROR: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("", status_code=201)
async def create_user(
    request: CreateUserRequest,
    current_user: User = Depends(get_current_user)  # Temporarily allowing all authenticated users
):
    """
    Create a new user (temporarily allowing all authenticated users).
    """
    logger.debug(f"[user_endpoints.create_user] auth_id={request.auth_id}, email={request.email}")
    
    try:
        user_context = build_user_context(current_user)
        user = await _user_service.create_user(
            auth_id=request.auth_id,
            email=request.email,
            name=request.name,
            role=request.role,
            user_context=user_context
        )
        return user.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"[user_endpoints.create_user] ERROR: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{user_id}")
async def update_user(
    user_id: int,
    request: UpdateUserRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Update user (admin or self).
    """
    logger.debug(f"[user_endpoints.update_user] user_id={user_id}")
    
    try:
        # Check permission: user can update self, admin can update anyone
        # Temporarily allowing all authenticated users to update any user
        # if current_user.id != user_id and current_user.role != "admin":
        #     raise HTTPException(status_code=403, detail="Access denied")
        
        # Temporarily allowing all authenticated users to change role and is_active
        # Non-admins cannot change role or is_active
        # if current_user.role != "admin":
        #     if request.role is not None:
        #         raise HTTPException(status_code=403, detail="Cannot change role")
        #     if request.is_active is not None:
        #         raise HTTPException(status_code=403, detail="Cannot change active status")
        
        user_context = build_user_context(current_user)
        updates = request.model_dump(exclude_unset=True)
        if not updates:
            raise HTTPException(status_code=400, detail="No fields to update")
        
        user = await _user_service.update_user(user_id, updates, user_context)
        if not user:
            raise HTTPException(status_code=404, detail=f"User {user_id} not found")
        
        return user.to_dict()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[user_endpoints.update_user] ERROR: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{user_id}", status_code=204)
async def delete_user(
    user_id: int,
    current_user: User = Depends(get_current_user)  # Temporarily allowing all authenticated users
):
    """
    Delete user (soft delete - sets is_active=false) (temporarily allowing all authenticated users).
    """
    logger.debug(f"[user_endpoints.delete_user] user_id={user_id}")
    
    try:
        user_context = build_user_context(current_user)
        success = await _user_service.delete_user(user_id, user_context)
        if not success:
            raise HTTPException(status_code=404, detail=f"User {user_id} not found")
        return None
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[user_endpoints.delete_user] ERROR: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


