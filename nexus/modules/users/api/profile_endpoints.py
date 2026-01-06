"""
User Profile API Endpoints

REST API endpoints for user profile management.
Uses new service layer and authentication middleware.
"""
import logging
from fastapi import APIRouter, HTTPException, Query, Depends
from typing import Dict, Any
from nexus.modules.users.domain.user import User
from nexus.modules.users.services.profile_service import ProfileService
from nexus.modules.users.auth.middleware import get_current_user

logger = logging.getLogger("nexus.users.profile_api")

router = APIRouter(prefix="/api/users", tags=["user-profiles"])

# Service instance
_profile_service = ProfileService()


@router.get("/{user_id}/profiles/basic")
async def get_basic_profile(
    user_id: int,
    current_user: User = Depends(get_current_user)
):
    """Get user basic profile."""
    # Check permission: user can view self, admin can view anyone
    if current_user.id != user_id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Access denied")
    
    try:
        profile = await _profile_service.get_basic_profile(user_id)
        return profile
    except Exception as e:
        logger.error(f"[profile_endpoints.get_basic_profile] ERROR: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{user_id}/profiles/basic")
async def update_basic_profile(
    user_id: int,
    updates: Dict[str, Any],
    current_user: User = Depends(get_current_user)
):
    """Update user basic profile."""
    # #region agent log
    import json
    with open('/Users/ananth/Personal AI Projects/Mobius OS/.cursor/debug.log', 'a') as f:
        f.write(json.dumps({"location":"profile_endpoints.py:40","message":"update_basic_profile ENTRY","data":{"user_id":user_id,"updates":str(updates),"updates_keys":list(updates.keys()),"current_user_id":current_user.id,"current_user_role":current_user.role},"timestamp":int(__import__('time').time()*1000),"sessionId":"debug-session","runId":"run1","hypothesisId":"A,B,C,D,E"})+"\n")
    # #endregion
    
    # Check permission: user can update self, admin can update anyone
    if current_user.id != user_id and current_user.role != "admin":
        # #region agent log
        with open('/Users/ananth/Personal AI Projects/Mobius OS/.cursor/debug.log', 'a') as f:
            f.write(json.dumps({"location":"profile_endpoints.py:48","message":"Permission check FAILED","data":{"current_user_id":current_user.id,"target_user_id":user_id,"current_user_role":current_user.role},"timestamp":int(__import__('time').time()*1000),"sessionId":"debug-session","runId":"run1","hypothesisId":"D"})+"\n")
        # #endregion
        raise HTTPException(status_code=403, detail="Access denied")
    
    try:
        # #region agent log
        with open('/Users/ananth/Personal AI Projects/Mobius OS/.cursor/debug.log', 'a') as f:
            f.write(json.dumps({"location":"profile_endpoints.py:52","message":"BEFORE service.update_basic_profile call","data":{"user_id":user_id,"updates":str(updates),"updates_keys":list(updates.keys())},"timestamp":int(__import__('time').time()*1000),"sessionId":"debug-session","runId":"run2","hypothesisId":"A,B,C"})+"\n")
        # #endregion
        success = await _profile_service.update_basic_profile(user_id, updates)
        # #region agent log
        with open('/Users/ananth/Personal AI Projects/Mobius OS/.cursor/debug.log', 'a') as f:
            f.write(json.dumps({"location":"profile_endpoints.py:52","message":"AFTER service.update_basic_profile call","data":{"success":success,"user_id":user_id},"timestamp":int(__import__('time').time()*1000),"sessionId":"debug-session","runId":"run2","hypothesisId":"A,B,C,E"})+"\n")
        # #endregion
        if not success:
            raise HTTPException(status_code=404, detail=f"Failed to update basic profile for user {user_id}")
        
        # #region agent log
        # Get profile after update to verify data was saved
        updated_profile = await _profile_service.get_basic_profile(user_id)
        with open('/Users/ananth/Personal AI Projects/Mobius OS/.cursor/debug.log', 'a') as f:
            f.write(json.dumps({"location":"profile_endpoints.py:55","message":"AFTER get_basic_profile - returning to client","data":{"user_id":user_id,"returned_profile":str(updated_profile),"returned_keys":list(updated_profile.keys())},"timestamp":int(__import__('time').time()*1000),"sessionId":"debug-session","runId":"run2","hypothesisId":"E"})+"\n")
        # #endregion
        return updated_profile
    except HTTPException:
        raise
    except Exception as e:
        # #region agent log
        with open('/Users/ananth/Personal AI Projects/Mobius OS/.cursor/debug.log', 'a') as f:
            f.write(json.dumps({"location":"profile_endpoints.py:58","message":"Exception caught in update_basic_profile","data":{"error":str(e),"error_type":type(e).__name__},"timestamp":int(__import__('time').time()*1000),"sessionId":"debug-session","runId":"run1","hypothesisId":"E"})+"\n")
        # #endregion
        logger.error(f"[profile_endpoints.update_basic_profile] ERROR: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{user_id}/profiles/professional")
async def get_professional_profile(
    user_id: int,
    current_user: User = Depends(get_current_user)
):
    """Get user professional profile."""
    if current_user.id != user_id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Access denied")
    
    try:
        profile = await _profile_service.get_professional_profile(user_id)
        return profile
    except Exception as e:
        logger.error(f"[profile_endpoints.get_professional_profile] ERROR: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{user_id}/profiles/professional")
async def update_professional_profile(
    user_id: int,
    updates: Dict[str, Any],
    current_user: User = Depends(get_current_user)
):
    """Update user professional profile."""
    if current_user.id != user_id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Access denied")
    
    try:
        success = await _profile_service.update_professional_profile(user_id, updates)
        if not success:
            raise HTTPException(status_code=404, detail=f"Failed to update professional profile for user {user_id}")
        return await _profile_service.get_professional_profile(user_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[profile_endpoints.update_professional_profile] ERROR: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{user_id}/profiles/communication")
async def get_communication_profile(
    user_id: int,
    current_user: User = Depends(get_current_user)
):
    """Get user communication profile."""
    if current_user.id != user_id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Access denied")
    
    try:
        profile = await _profile_service.get_communication_profile(user_id)
        return profile
    except Exception as e:
        logger.error(f"[profile_endpoints.get_communication_profile] ERROR: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{user_id}/profiles/communication")
async def update_communication_profile(
    user_id: int,
    updates: Dict[str, Any],
    current_user: User = Depends(get_current_user)
):
    """Update user communication profile."""
    if current_user.id != user_id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Access denied")
    
    try:
        success = await _profile_service.update_communication_profile(user_id, updates)
        if not success:
            raise HTTPException(status_code=404, detail=f"Failed to update communication profile for user {user_id}")
        return await _profile_service.get_communication_profile(user_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[profile_endpoints.update_communication_profile] ERROR: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{user_id}/profiles/use-case")
async def get_use_case_profile(
    user_id: int,
    current_user: User = Depends(get_current_user)
):
    """Get user use case profile."""
    if current_user.id != user_id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Access denied")
    
    try:
        profile = await _profile_service.get_use_case_profile(user_id)
        return profile
    except Exception as e:
        logger.error(f"[profile_endpoints.get_use_case_profile] ERROR: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{user_id}/profiles/use-case")
async def update_use_case_profile(
    user_id: int,
    updates: Dict[str, Any],
    current_user: User = Depends(get_current_user)
):
    """Update user use case profile."""
    if current_user.id != user_id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Access denied")
    
    try:
        success = await _profile_service.update_use_case_profile(user_id, updates)
        if not success:
            raise HTTPException(status_code=404, detail=f"Failed to update use case profile for user {user_id}")
        return await _profile_service.get_use_case_profile(user_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[profile_endpoints.update_use_case_profile] ERROR: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{user_id}/profiles/ai-preference")
async def get_ai_preference_profile(
    user_id: int,
    current_user: User = Depends(get_current_user)
):
    """Get user AI preference profile."""
    if current_user.id != user_id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Access denied")
    
    try:
        profile = await _profile_service.get_ai_preference_profile(user_id)
        return profile
    except Exception as e:
        logger.error(f"[profile_endpoints.get_ai_preference_profile] ERROR: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{user_id}/profiles/ai-preference")
async def update_ai_preference_profile(
    user_id: int,
    updates: Dict[str, Any],
    current_user: User = Depends(get_current_user)
):
    """Update user AI preference profile."""
    if current_user.id != user_id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Access denied")
    
    try:
        success = await _profile_service.update_ai_preference_profile(user_id, updates)
        if not success:
            raise HTTPException(status_code=404, detail=f"Failed to update AI preference profile for user {user_id}")
        return await _profile_service.get_ai_preference_profile(user_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[profile_endpoints.update_ai_preference_profile] ERROR: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{user_id}/profiles/query-history")
async def get_query_history_profile(
    user_id: int,
    current_user: User = Depends(get_current_user)
):
    """Get user query history profile."""
    if current_user.id != user_id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Access denied")
    
    try:
        profile = await _profile_service.get_query_history_profile(user_id)
        return profile
    except Exception as e:
        logger.error(f"[profile_endpoints.get_query_history_profile] ERROR: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{user_id}/session-links")
async def get_user_session_links(
    user_id: int,
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_user)
):
    """Get session links for a user (links queries to sessions)."""
    if current_user.id != user_id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Access denied")
    
    try:
        links = await _profile_service.get_user_session_links(user_id, limit=limit)
        return {"links": links, "count": len(links)}
    except Exception as e:
        logger.error(f"[profile_endpoints.get_user_session_links] ERROR: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{user_id}/profiles/all")
async def get_all_profiles(
    user_id: int,
    current_user: User = Depends(get_current_user)
):
    """Get all user profiles in one response."""
    if current_user.id != user_id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Access denied")
    
    try:
        return await _profile_service.get_all_profiles(user_id)
    except Exception as e:
        logger.error(f"[profile_endpoints.get_all_profiles] ERROR: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# Compatibility routes for legacy frontend
@router.get("/{user_id}/profile")
async def get_user_profile(
    user_id: int,
    current_user: User = Depends(get_current_user)
):
    """
    Get user profile (legacy compatibility endpoint).
    Returns aggregated profile data in legacy format matching user_account_profiles table structure.
    """
    if current_user.id != user_id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Access denied")
    
    try:
        # Get all profiles and aggregate into legacy format
        all_profiles = await _profile_service.get_all_profiles(user_id)
        basic = all_profiles.get("basic", {})
        communication = all_profiles.get("communication", {})
        ai_pref = all_profiles.get("ai_preference", {})
        
        # Build legacy format: preferences, settings, metadata
        # Legacy format expects: { preferences: {}, settings: {}, metadata: {} }
        return {
            "preferences": ai_pref.get("preferences", {}),
            "settings": {
                "communication_style": communication.get("communication_style", "professional"),
                "tone_preference": communication.get("tone_preference", "balanced"),
                "timezone": basic.get("timezone", "UTC"),
                "locale": basic.get("locale", "en-US"),
            },
            "metadata": basic.get("metadata", {})
        }
    except Exception as e:
        logger.error(f"[profile_endpoints.get_user_profile] ERROR: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{user_id}/profile")
async def update_user_profile(
    user_id: int,
    updates: Dict[str, Any],
    current_user: User = Depends(get_current_user)
):
    """
    Update user profile (legacy compatibility endpoint).
    Maps legacy format to new profile structure.
    """
    if current_user.id != user_id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Access denied")
    
    try:
        # Map legacy fields to new profile structure
        if "preferences" in updates:
            # Store preferences in ai_preference profile metadata or as a separate field
            # For now, store in metadata since ai_preference_profile doesn't have a direct "preferences" field
            await _profile_service.update_ai_preference_profile(user_id, {"metadata": {"preferences": updates["preferences"]}})
        
        if "settings" in updates:
            settings = updates["settings"]
            comm_updates = {}
            basic_updates = {}
            
            if "communication_style" in settings:
                comm_updates["communication_style"] = settings["communication_style"]
            if "tone_preference" in settings:
                comm_updates["tone_preference"] = settings["tone_preference"]
            if "timezone" in settings:
                basic_updates["timezone"] = settings["timezone"]
            if "locale" in settings:
                basic_updates["locale"] = settings["locale"]
            
            if comm_updates:
                await _profile_service.update_communication_profile(user_id, comm_updates)
            if basic_updates:
                await _profile_service.update_basic_profile(user_id, basic_updates)
        
        if "metadata" in updates:
            await _profile_service.update_basic_profile(user_id, {"metadata": updates["metadata"]})
        
        # Return updated profile in legacy format
        all_profiles = await _profile_service.get_all_profiles(user_id)
        basic = all_profiles.get("basic", {})
        communication = all_profiles.get("communication", {})
        ai_pref = all_profiles.get("ai_preference", {})
        
        return {
            "preferences": ai_pref.get("metadata", {}).get("preferences", {}),
            "settings": {
                "communication_style": communication.get("communication_style", "professional"),
                "tone_preference": communication.get("tone_preference", "balanced"),
                "timezone": basic.get("timezone", "UTC"),
                "locale": basic.get("locale", "en-US"),
            },
            "metadata": basic.get("metadata", {})
        }
    except Exception as e:
        logger.error(f"[profile_endpoints.update_user_profile] ERROR: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{user_id}/preferences")
async def get_user_preferences(
    user_id: int,
    current_user: User = Depends(get_current_user)
):
    """Get user preferences (legacy compatibility endpoint)."""
    if current_user.id != user_id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Access denied")
    
    try:
        profile = await _profile_service.get_ai_preference_profile(user_id)
        # Preferences are stored in metadata for compatibility
        return {"preferences": profile.get("metadata", {}).get("preferences", {})}
    except Exception as e:
        logger.error(f"[profile_endpoints.get_user_preferences] ERROR: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{user_id}/preferences")
async def update_user_preferences(
    user_id: int,
    preferences: Dict[str, Any],
    current_user: User = Depends(get_current_user)
):
    """Update user preferences (legacy compatibility endpoint)."""
    if current_user.id != user_id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Access denied")
    
    try:
        # Get existing metadata and merge preferences
        existing = await _profile_service.get_ai_preference_profile(user_id)
        existing_metadata = existing.get("metadata", {})
        existing_metadata["preferences"] = preferences
        await _profile_service.update_ai_preference_profile(user_id, {"metadata": existing_metadata})
        
        profile = await _profile_service.get_ai_preference_profile(user_id)
        return {"preferences": profile.get("metadata", {}).get("preferences", {})}
    except Exception as e:
        logger.error(f"[profile_endpoints.update_user_preferences] ERROR: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

