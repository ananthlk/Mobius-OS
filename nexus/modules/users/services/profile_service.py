"""
Profile Service

Business logic for profile management operations.
"""
import logging
from typing import Dict, Any, List, Optional
from nexus.modules.users.repositories.profile_repository import ProfileRepository

logger = logging.getLogger("nexus.users.profile_service")


class ProfileService:
    """Service for profile business logic."""
    
    def __init__(self, repository: Optional[ProfileRepository] = None):
        self.repository = repository or ProfileRepository()
    
    async def get_basic_profile(self, user_id: int) -> Dict[str, Any]:
        """Get user basic profile."""
        try:
            return await self.repository.get_basic_profile(user_id)
        except Exception as e:
            logger.error(f"[ProfileService.get_basic_profile] ERROR: {e}", exc_info=True)
            return {"user_id": user_id}
    
    async def update_basic_profile(self, user_id: int, updates: Dict[str, Any]) -> bool:
        """Update user basic profile."""
        # #region agent log
        import json
        with open('/Users/ananth/Personal AI Projects/Mobius OS/.cursor/debug.log', 'a') as f:
            f.write(json.dumps({"location":"profile_service.py:27","message":"ProfileService.update_basic_profile ENTRY","data":{"user_id":user_id,"updates":str(updates),"updates_keys":list(updates.keys())},"timestamp":int(__import__('time').time()*1000),"sessionId":"debug-session","runId":"run1","hypothesisId":"A,B,C"})+"\n")
        # #endregion
        try:
            result = await self.repository.update_basic_profile(user_id, updates)
            # #region agent log
            with open('/Users/ananth/Personal AI Projects/Mobius OS/.cursor/debug.log', 'a') as f:
                f.write(json.dumps({"location":"profile_service.py:30","message":"ProfileService.update_basic_profile EXIT","data":{"result":result,"user_id":user_id},"timestamp":int(__import__('time').time()*1000),"sessionId":"debug-session","runId":"run1","hypothesisId":"A,B,C,E"})+"\n")
            # #endregion
            return result
        except Exception as e:
            # #region agent log
            with open('/Users/ananth/Personal AI Projects/Mobius OS/.cursor/debug.log', 'a') as f:
                f.write(json.dumps({"location":"profile_service.py:32","message":"ProfileService.update_basic_profile EXCEPTION","data":{"error":str(e),"error_type":type(e).__name__,"user_id":user_id},"timestamp":int(__import__('time').time()*1000),"sessionId":"debug-session","runId":"run1","hypothesisId":"E"})+"\n")
            # #endregion
            logger.error(f"[ProfileService.update_basic_profile] ERROR: {e}", exc_info=True)
            return False
    
    async def get_professional_profile(self, user_id: int) -> Dict[str, Any]:
        """Get user professional profile."""
        try:
            return await self.repository.get_professional_profile(user_id)
        except Exception as e:
            logger.error(f"[ProfileService.get_professional_profile] ERROR: {e}", exc_info=True)
            return {"user_id": user_id}
    
    async def update_professional_profile(self, user_id: int, updates: Dict[str, Any]) -> bool:
        """Update user professional profile."""
        try:
            return await self.repository.update_professional_profile(user_id, updates)
        except Exception as e:
            logger.error(f"[ProfileService.update_professional_profile] ERROR: {e}", exc_info=True)
            return False
    
    async def get_communication_profile(self, user_id: int) -> Dict[str, Any]:
        """Get user communication profile."""
        try:
            return await self.repository.get_communication_profile(user_id)
        except Exception as e:
            logger.error(f"[ProfileService.get_communication_profile] ERROR: {e}", exc_info=True)
            return {"user_id": user_id}
    
    async def update_communication_profile(self, user_id: int, updates: Dict[str, Any]) -> bool:
        """Update user communication profile."""
        try:
            return await self.repository.update_communication_profile(user_id, updates)
        except Exception as e:
            logger.error(f"[ProfileService.update_communication_profile] ERROR: {e}", exc_info=True)
            return False
    
    async def get_use_case_profile(self, user_id: int) -> Dict[str, Any]:
        """Get user use case profile."""
        try:
            return await self.repository.get_use_case_profile(user_id)
        except Exception as e:
            logger.error(f"[ProfileService.get_use_case_profile] ERROR: {e}", exc_info=True)
            return {"user_id": user_id}
    
    async def update_use_case_profile(self, user_id: int, updates: Dict[str, Any]) -> bool:
        """Update user use case profile."""
        try:
            return await self.repository.update_use_case_profile(user_id, updates)
        except Exception as e:
            logger.error(f"[ProfileService.update_use_case_profile] ERROR: {e}", exc_info=True)
            return False
    
    async def get_ai_preference_profile(self, user_id: int) -> Dict[str, Any]:
        """Get user AI preference profile."""
        try:
            return await self.repository.get_ai_preference_profile(user_id)
        except Exception as e:
            logger.error(f"[ProfileService.get_ai_preference_profile] ERROR: {e}", exc_info=True)
            return {"user_id": user_id}
    
    async def update_ai_preference_profile(self, user_id: int, updates: Dict[str, Any]) -> bool:
        """Update user AI preference profile."""
        try:
            return await self.repository.update_ai_preference_profile(user_id, updates)
        except Exception as e:
            logger.error(f"[ProfileService.update_ai_preference_profile] ERROR: {e}", exc_info=True)
            return False
    
    async def get_query_history_profile(self, user_id: int) -> Dict[str, Any]:
        """Get user query history profile."""
        try:
            return await self.repository.get_query_history_profile(user_id)
        except Exception as e:
            logger.error(f"[ProfileService.get_query_history_profile] ERROR: {e}", exc_info=True)
            return {"user_id": user_id}
    
    async def get_user_session_links(self, user_id: int, limit: int = 50) -> List[Dict[str, Any]]:
        """Get session links for a user."""
        try:
            return await self.repository.get_user_session_links(user_id, limit=limit)
        except Exception as e:
            logger.error(f"[ProfileService.get_user_session_links] ERROR: {e}", exc_info=True)
            return []
    
    async def get_all_profiles(self, user_id: int) -> Dict[str, Any]:
        """Get all user profiles in one response."""
        return {
            "basic": await self.get_basic_profile(user_id),
            "professional": await self.get_professional_profile(user_id),
            "communication": await self.get_communication_profile(user_id),
            "use_case": await self.get_use_case_profile(user_id),
            "ai_preference": await self.get_ai_preference_profile(user_id),
            "query_history": await self.get_query_history_profile(user_id)
        }
    
    async def initialize_profiles(self, user_id: int):
        """Initialize all profile tables for a new user."""
        try:
            # Ensure all profile tables have records
            await self.repository.ensure_profile_exists("user_basic_profiles", user_id)
            await self.repository.ensure_profile_exists("user_professional_profiles", user_id)
            await self.repository.ensure_profile_exists("user_communication_profiles", user_id)
            await self.repository.ensure_profile_exists("user_use_case_profiles", user_id)
            await self.repository.ensure_profile_exists("user_ai_preference_profiles", user_id)
            await self.repository.ensure_profile_exists("user_query_history_profiles", user_id)
        except Exception as e:
            logger.error(f"[ProfileService.initialize_profiles] ERROR: {e}", exc_info=True)


