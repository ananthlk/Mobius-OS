"""
User Provisioning Service

Handles automatic user creation and initialization on first authentication.
"""
import logging
from typing import Optional
from nexus.modules.users.services.user_service import UserService
from nexus.modules.users.services.profile_service import ProfileService
from nexus.modules.users.domain.user import User

logger = logging.getLogger("nexus.users.provisioning")


class UserProvisioningService:
    """Service for automatic user provisioning."""
    
    def __init__(
        self,
        user_service: Optional[UserService] = None,
        profile_service: Optional[ProfileService] = None
    ):
        self.user_service = user_service or UserService()
        self.profile_service = profile_service or ProfileService()
    
    async def get_or_create_user(
        self,
        auth_id: str,
        email: str,
        name: Optional[str] = None,
        role: str = "user"
    ) -> User:
        """
        Get existing user or create new one.
        
        This is the main entry point for user provisioning.
        Called by authentication middleware when a user first authenticates.
        """
        logger.debug(f"[UserProvisioningService.get_or_create_user] auth_id={auth_id}, email={email}")
        
        # Try to get existing user
        user = await self.user_service.get_user_by_auth_id(auth_id)
        if user:
            logger.debug(f"[UserProvisioningService.get_or_create_user] User exists: {user.id}")
            return user
        
        # Create new user
        logger.info(f"[UserProvisioningService.get_or_create_user] Creating new user: {auth_id}")
        user = await self.user_service.create_user(
            auth_id=auth_id,
            email=email,
            name=name,
            role=role,
            user_context={"user_id": "system", "session_id": None}
        )
        
        # Initialize all profile tables
        await self.profile_service.initialize_profiles(user.id)
        
        logger.info(f"[UserProvisioningService.get_or_create_user] User created and profiles initialized: {user.id}")
        return user



