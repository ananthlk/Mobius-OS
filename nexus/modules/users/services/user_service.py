"""
User Service

Business logic for user management operations.
"""
import logging
from typing import Optional, List, Dict, Any
from nexus.modules.users.domain.user import User
from nexus.modules.users.repositories.user_repository import UserRepository
from nexus.modules.audit_manager import audit_manager

logger = logging.getLogger("nexus.users.service")


class UserService:
    """Service for user business logic."""
    
    def __init__(self, repository: Optional[UserRepository] = None):
        self.repository = repository or UserRepository()
    
    async def create_user(
        self,
        auth_id: str,
        email: str,
        name: Optional[str] = None,
        role: str = "user",
        user_context: Optional[Dict[str, Any]] = None
    ) -> User:
        """Create a new user account."""
        logger.debug(f"[UserService.create_user] auth_id={auth_id}, email={email}, role={role}")
        
        try:
            user_id = await self.repository.create(
                auth_id=auth_id,
                email=email,
                name=name,
                role=role
            )
            
            # Create empty profiles (delegated to profile service)
            # This will be handled by provisioning service
            
            # Audit log
            creator_id = user_context.get("user_id", "system") if user_context else "system"
            await audit_manager.log_event(
                user_id=creator_id,
                action="CREATE",
                resource_type="USER",
                resource_id=str(user_id),
                details={"auth_id": auth_id, "email": email, "role": role},
                session_id=user_context.get("session_id") if user_context else None
            )
            
            # Return created user
            user_data = await self.repository.get_by_id(user_id)
            return User.from_dict(user_data)
            
        except Exception as e:
            logger.error(f"[UserService.create_user] ERROR: {e}", exc_info=True)
            raise ValueError(f"Failed to create user: {e}")
    
    async def get_user(self, user_id: int) -> Optional[User]:
        """Get user by ID."""
        logger.debug(f"[UserService.get_user] user_id={user_id}")
        
        try:
            user_data = await self.repository.get_by_id(user_id)
            if not user_data:
                return None
            return User.from_dict(user_data)
        except Exception as e:
            logger.error(f"[UserService.get_user] ERROR: {e}", exc_info=True)
            return None
    
    async def get_user_by_auth_id(self, auth_id: str) -> Optional[User]:
        """Get user by auth_id (Google Auth Subject ID)."""
        logger.debug(f"[UserService.get_user_by_auth_id] auth_id={auth_id}")
        
        try:
            user_data = await self.repository.get_by_auth_id(auth_id)
            if not user_data:
                return None
            return User.from_dict(user_data)
        except Exception as e:
            logger.error(f"[UserService.get_user_by_auth_id] ERROR: {e}", exc_info=True)
            return None
    
    async def update_user(
        self,
        user_id: int,
        updates: Dict[str, Any],
        user_context: Optional[Dict[str, Any]] = None
    ) -> Optional[User]:
        """Update user account."""
        logger.debug(f"[UserService.update_user] user_id={user_id}, updates={list(updates.keys())}")
        
        try:
            success = await self.repository.update(user_id, updates)
            if not success:
                return None
            
            # Audit log
            updater_id = user_context.get("user_id", "system") if user_context else "system"
            await audit_manager.log_event(
                user_id=updater_id,
                action="UPDATE",
                resource_type="USER",
                resource_id=str(user_id),
                details=updates,
                session_id=user_context.get("session_id") if user_context else None
            )
            
            # Return updated user
            user_data = await self.repository.get_by_id(user_id)
            return User.from_dict(user_data)
            
        except Exception as e:
            logger.error(f"[UserService.update_user] ERROR: {e}", exc_info=True)
            return None
    
    async def delete_user(
        self,
        user_id: int,
        user_context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Soft delete user (set is_active = false)."""
        logger.debug(f"[UserService.delete_user] user_id={user_id}")
        
        try:
            success = await self.repository.delete(user_id)
            
            # Audit log
            deleter_id = user_context.get("user_id", "system") if user_context else "system"
            await audit_manager.log_event(
                user_id=deleter_id,
                action="DELETE",
                resource_type="USER",
                resource_id=str(user_id),
                details={},
                session_id=user_context.get("session_id") if user_context else None
            )
            
            return success
            
        except Exception as e:
            logger.error(f"[UserService.delete_user] ERROR: {e}", exc_info=True)
            return False
    
    async def list_users(
        self,
        role_filter: Optional[str] = None,
        active_only: bool = True
    ) -> List[User]:
        """List users with optional filtering."""
        logger.debug(f"[UserService.list_users] role_filter={role_filter}, active_only={active_only}")
        
        try:
            users_data = await self.repository.list(
                role_filter=role_filter,
                active_only=active_only
            )
            return [User.from_dict(user_data) for user_data in users_data]
        except Exception as e:
            logger.error(f"[UserService.list_users] ERROR: {e}", exc_info=True)
            return []
    
    async def get_user_role(self, user_id: int) -> Optional[str]:
        """Get user role."""
        try:
            return await self.repository.get_role(user_id)
        except Exception as e:
            logger.error(f"[UserService.get_user_role] ERROR: {e}", exc_info=True)
            return None
    
    async def has_permission(self, user_id: int, permission: str) -> bool:
        """Check if user has permission."""
        try:
            role = await self.get_user_role(user_id)
            if not role:
                return False
            
            # Simple role-based permissions
            if role == "admin":
                return True
            elif permission == "view" and role in ["admin", "user", "viewer"]:
                return True
            elif permission == "edit" and role in ["admin", "user"]:
                return True
            elif permission == "admin" and role == "admin":
                return True
            
            return False
        except Exception as e:
            logger.error(f"[UserService.has_permission] ERROR: {e}", exc_info=True)
            return False



