"""
User Management API Endpoints

REST API endpoints for user management, profiles, and preferences.
"""
import logging
from fastapi import APIRouter, HTTPException, Query, Header
from pydantic import BaseModel, EmailStr
from typing import List, Dict, Any, Optional
from nexus.modules.user_manager import user_manager

logger = logging.getLogger("nexus.user_endpoints")

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


class UpdateUserProfileRequest(BaseModel):
    preferences: Optional[Dict[str, Any]] = None
    settings: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None


# Helper function to get user context from header (for now - can be enhanced with proper auth)
async def get_user_context(user_id: Optional[str] = Header(None, alias="X-User-ID")) -> Dict[str, Any]:
    """Extract user context from request headers."""
    # TODO: Replace with proper authentication middleware
    return {"user_id": user_id or "system", "session_id": None}


@router.get("")
async def list_users(
    role: Optional[str] = Query(None, description="Filter by role"),
    active_only: bool = Query(True, description="Only return active users"),
    user_id: Optional[str] = Header(None, alias="X-User-ID")
):
    """
    List users (admin only).
    
    Returns list of users with optional filtering.
    """
    logger.debug(f"[user_endpoints.list_users] ENTRY | role={role}, active_only={active_only}")
    
    try:
        # TODO: Add role-based access control (admin only)
        users = await user_manager.list_users(role_filter=role, active_only=active_only)
        return {"users": users, "count": len(users)}
    except Exception as e:
        logger.error(f"[user_endpoints.list_users] ERROR | error={str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{user_id}")
async def get_user(user_id: int):
    """
    Get user details by ID.
    """
    logger.debug(f"[user_endpoints.get_user] ENTRY | user_id={user_id}")
    
    try:
        user = await user_manager.get_user(user_id)
        if not user:
            raise HTTPException(status_code=404, detail=f"User {user_id} not found")
        return user
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[user_endpoints.get_user] ERROR | error={str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/auth/{auth_id}")
async def get_user_by_auth_id(auth_id: str):
    """
    Get user details by auth_id (Google Auth Subject ID).
    """
    logger.debug(f"[user_endpoints.get_user_by_auth_id] ENTRY | auth_id={auth_id}")
    
    try:
        user = await user_manager.get_user_by_auth_id(auth_id)
        if not user:
            raise HTTPException(status_code=404, detail=f"User with auth_id {auth_id} not found")
        return user
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[user_endpoints.get_user_by_auth_id] ERROR | error={str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("", status_code=201)
async def create_user(
    request: CreateUserRequest,
    user_id: Optional[str] = Header(None, alias="X-User-ID")
):
    """
    Create a new user (admin only).
    """
    logger.debug(f"[user_endpoints.create_user] ENTRY | auth_id={request.auth_id}, email={request.email}")
    
    try:
        # TODO: Add role-based access control (admin only)
        user_context = await get_user_context(user_id)
        new_user_id = await user_manager.create_user(
            auth_id=request.auth_id,
            email=request.email,
            name=request.name,
            role=request.role,
            user_context=user_context
        )
        user = await user_manager.get_user(new_user_id)
        return user
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"[user_endpoints.create_user] ERROR | error={str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{user_id}")
async def update_user(
    user_id: int,
    request: UpdateUserRequest,
    current_user_id: Optional[str] = Header(None, alias="X-User-ID")
):
    """
    Update user (admin or self).
    """
    logger.debug(f"[user_endpoints.update_user] ENTRY | user_id={user_id}")
    
    try:
        # TODO: Add permission check (admin or self)
        user_context = await get_user_context(current_user_id)
        
        updates = request.model_dump(exclude_unset=True)
        if not updates:
            raise HTTPException(status_code=400, detail="No fields to update")
        
        success = await user_manager.update_user(user_id, updates, user_context)
        if not success:
            raise HTTPException(status_code=404, detail=f"User {user_id} not found")
        
        user = await user_manager.get_user(user_id)
        return user
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[user_endpoints.update_user] ERROR | error={str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{user_id}", status_code=204)
async def delete_user(
    user_id: int,
    current_user_id: Optional[str] = Header(None, alias="X-User-ID")
):
    """
    Delete user (soft delete - sets is_active=false) (admin only).
    """
    logger.debug(f"[user_endpoints.delete_user] ENTRY | user_id={user_id}")
    
    try:
        # TODO: Add role-based access control (admin only)
        user_context = await get_user_context(current_user_id)
        success = await user_manager.delete_user(user_id, user_context)
        if not success:
            raise HTTPException(status_code=404, detail=f"User {user_id} not found")
        return None
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[user_endpoints.delete_user] ERROR | error={str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{user_id}/profile")
async def get_user_profile(user_id: int):
    """
    Get user profile (preferences and settings).
    """
    logger.debug(f"[user_endpoints.get_user_profile] ENTRY | user_id={user_id}")
    
    try:
        profile = await user_manager.get_user_profile(user_id)
        if not profile:
            raise HTTPException(status_code=404, detail=f"User profile {user_id} not found")
        return profile
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[user_endpoints.get_user_profile] ERROR | error={str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{user_id}/profile")
async def update_user_profile(
    user_id: int,
    request: UpdateUserProfileRequest
):
    """
    Update user profile (preferences, settings, metadata).
    """
    logger.debug(f"[user_endpoints.update_user_profile] ENTRY | user_id={user_id}")
    
    try:
        success = await user_manager.update_user_profile(
            user_id=user_id,
            preferences=request.preferences,
            settings=request.settings,
            metadata=request.metadata
        )
        if not success:
            raise HTTPException(status_code=404, detail=f"User profile {user_id} not found")
        
        profile = await user_manager.get_user_profile(user_id)
        return profile
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[user_endpoints.update_user_profile] ERROR | error={str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{user_id}/preferences")
async def get_user_preferences(user_id: int):
    """
    Get user preferences (alias for profile.preferences).
    """
    logger.debug(f"[user_endpoints.get_user_preferences] ENTRY | user_id={user_id}")
    
    try:
        profile = await user_manager.get_user_profile(user_id)
        if not profile:
            raise HTTPException(status_code=404, detail=f"User profile {user_id} not found")
        return {"preferences": profile.get("preferences", {})}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[user_endpoints.get_user_preferences] ERROR | error={str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{user_id}/preferences")
async def update_user_preferences(
    user_id: int,
    preferences: Dict[str, Any]
):
    """
    Update user preferences.
    """
    logger.debug(f"[user_endpoints.update_user_preferences] ENTRY | user_id={user_id}")
    
    try:
        success = await user_manager.update_user_profile(
            user_id=user_id,
            preferences=preferences
        )
        if not success:
            raise HTTPException(status_code=404, detail=f"User profile {user_id} not found")
        
        profile = await user_manager.get_user_profile(user_id)
        return {"preferences": profile.get("preferences", {})}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[user_endpoints.update_user_preferences] ERROR | error={str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# --- Comprehensive Profile Endpoints ---

@router.get("/{user_id}/profiles/basic")
async def get_basic_profile(user_id: int):
    """Get user basic profile."""
    try:
        profile = await user_manager.get_basic_profile(user_id)
        return profile
    except Exception as e:
        logger.error(f"[user_endpoints.get_basic_profile] ERROR: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{user_id}/profiles/basic")
async def update_basic_profile(user_id: int, updates: Dict[str, Any]):
    """Update user basic profile."""
    try:
        success = await user_manager.update_basic_profile(user_id, updates)
        if not success:
            raise HTTPException(status_code=404, detail=f"Failed to update basic profile for user {user_id}")
        return await user_manager.get_basic_profile(user_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[user_endpoints.update_basic_profile] ERROR: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{user_id}/profiles/professional")
async def get_professional_profile(user_id: int):
    """Get user professional profile."""
    try:
        profile = await user_manager.get_professional_profile(user_id)
        return profile
    except Exception as e:
        logger.error(f"[user_endpoints.get_professional_profile] ERROR: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{user_id}/profiles/professional")
async def update_professional_profile(user_id: int, updates: Dict[str, Any]):
    """Update user professional profile."""
    try:
        success = await user_manager.update_professional_profile(user_id, updates)
        if not success:
            raise HTTPException(status_code=404, detail=f"Failed to update professional profile for user {user_id}")
        return await user_manager.get_professional_profile(user_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[user_endpoints.update_professional_profile] ERROR: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{user_id}/profiles/communication")
async def get_communication_profile(user_id: int):
    """Get user communication profile."""
    try:
        profile = await user_manager.get_communication_profile(user_id)
        return profile
    except Exception as e:
        logger.error(f"[user_endpoints.get_communication_profile] ERROR: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{user_id}/profiles/communication")
async def update_communication_profile(user_id: int, updates: Dict[str, Any]):
    """Update user communication profile."""
    try:
        success = await user_manager.update_communication_profile(user_id, updates)
        if not success:
            raise HTTPException(status_code=404, detail=f"Failed to update communication profile for user {user_id}")
        return await user_manager.get_communication_profile(user_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[user_endpoints.update_communication_profile] ERROR: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{user_id}/profiles/use-case")
async def get_use_case_profile(user_id: int):
    """Get user use case profile."""
    try:
        profile = await user_manager.get_use_case_profile(user_id)
        return profile
    except Exception as e:
        logger.error(f"[user_endpoints.get_use_case_profile] ERROR: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{user_id}/profiles/use-case")
async def update_use_case_profile(user_id: int, updates: Dict[str, Any]):
    """Update user use case profile."""
    try:
        success = await user_manager.update_use_case_profile(user_id, updates)
        if not success:
            raise HTTPException(status_code=404, detail=f"Failed to update use case profile for user {user_id}")
        return await user_manager.get_use_case_profile(user_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[user_endpoints.update_use_case_profile] ERROR: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{user_id}/profiles/ai-preference")
async def get_ai_preference_profile(user_id: int):
    """Get user AI preference profile."""
    try:
        profile = await user_manager.get_ai_preference_profile(user_id)
        return profile
    except Exception as e:
        logger.error(f"[user_endpoints.get_ai_preference_profile] ERROR: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{user_id}/profiles/ai-preference")
async def update_ai_preference_profile(user_id: int, updates: Dict[str, Any]):
    """Update user AI preference profile."""
    try:
        success = await user_manager.update_ai_preference_profile(user_id, updates)
        if not success:
            raise HTTPException(status_code=404, detail=f"Failed to update AI preference profile for user {user_id}")
        return await user_manager.get_ai_preference_profile(user_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[user_endpoints.update_ai_preference_profile] ERROR: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{user_id}/profiles/query-history")
async def get_query_history_profile(user_id: int):
    """Get user query history profile."""
    try:
        profile = await user_manager.get_query_history_profile(user_id)
        return profile
    except Exception as e:
        logger.error(f"[user_endpoints.get_query_history_profile] ERROR: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{user_id}/session-links")
async def get_user_session_links(
    user_id: int,
    limit: int = Query(50, ge=1, le=200)
):
    """Get session links for a user (links queries to sessions)."""
    try:
        links = await user_manager.get_user_session_links(user_id, limit=limit)
        return {"links": links, "count": len(links)}
    except Exception as e:
        logger.error(f"[user_endpoints.get_user_session_links] ERROR: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{user_id}/profiles/all")
async def get_all_profiles(user_id: int):
    """Get all user profiles in one response."""
    try:
        return {
            "basic": await user_manager.get_basic_profile(user_id),
            "professional": await user_manager.get_professional_profile(user_id),
            "communication": await user_manager.get_communication_profile(user_id),
            "use_case": await user_manager.get_use_case_profile(user_id),
            "ai_preference": await user_manager.get_ai_preference_profile(user_id),
            "query_history": await user_manager.get_query_history_profile(user_id)
        }
    except Exception as e:
        logger.error(f"[user_endpoints.get_all_profiles] ERROR: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

