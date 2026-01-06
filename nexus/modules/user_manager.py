"""
User Manager Module

Manages user accounts, profiles, and permissions.
Provides CRUD operations for users and user profiles.
"""
import logging
import json
from typing import Dict, Any, Optional, List
from datetime import datetime
from nexus.modules.database import database
from nexus.modules.audit_manager import audit_manager

logger = logging.getLogger("nexus.user_manager")


class UserManager:
    """
    Manages user accounts, profiles, and permissions.
    """
    
    async def create_user(
        self,
        auth_id: str,
        email: str,
        name: Optional[str] = None,
        role: str = "user",
        user_context: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Create a new user account.
        
        Args:
            auth_id: Google Auth Subject ID
            email: User email address
            name: User name (optional)
            role: User role (default: 'user')
            user_context: Context of user creating this account (for audit)
        
        Returns:
            User ID (integer)
        """
        logger.debug(f"[UserManager.create_user] ENTRY | auth_id={auth_id}, email={email}, role={role}")
        
        try:
            query = """
                INSERT INTO users (auth_id, email, name, role)
                VALUES (:auth_id, :email, :name, :role)
                RETURNING id
            """
            
            user_id = await database.fetch_val(query, {
                "auth_id": auth_id,
                "email": email,
                "name": name,
                "role": role
            })
            
            # Create empty profile
            await self._create_user_profile(user_id)
            
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
            
            logger.info(f"[UserManager.create_user] EXIT | user_id={user_id}")
            return user_id
            
        except Exception as e:
            logger.error(f"[UserManager.create_user] ERROR | error={str(e)}", exc_info=True)
            raise ValueError(f"Failed to create user: {e}")
    
    async def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user by ID."""
        logger.debug(f"[UserManager.get_user] ENTRY | user_id={user_id}")
        
        try:
            query = "SELECT id, auth_id, email, name, role, is_active, created_at, updated_at FROM users WHERE id = :user_id"
            row = await database.fetch_one(query, {"user_id": user_id})
            
            if not row:
                return None
            
            return dict(row)
        except Exception as e:
            logger.error(f"[UserManager.get_user] ERROR | error={str(e)}", exc_info=True)
            return None
    
    async def get_user_by_auth_id(self, auth_id: str) -> Optional[Dict[str, Any]]:
        """Get user by auth_id (Google Auth Subject ID)."""
        logger.debug(f"[UserManager.get_user_by_auth_id] ENTRY | auth_id={auth_id}")
        
        try:
            query = "SELECT id, auth_id, email, name, role, is_active, created_at, updated_at FROM users WHERE auth_id = :auth_id"
            row = await database.fetch_one(query, {"auth_id": auth_id})
            
            if not row:
                return None
            
            return dict(row)
        except Exception as e:
            logger.error(f"[UserManager.get_user_by_auth_id] ERROR | error={str(e)}", exc_info=True)
            return None
    
    async def update_user(
        self,
        user_id: int,
        updates: Dict[str, Any],
        user_context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Update user account.
        
        Args:
            user_id: User ID to update
            updates: Dictionary of fields to update (email, name, role, is_active)
            user_context: Context of user making the update (for audit)
        
        Returns:
            True if successful
        """
        logger.debug(f"[UserManager.update_user] ENTRY | user_id={user_id}, updates={list(updates.keys())}")
        
        try:
            # Build dynamic update query
            allowed_fields = ["email", "name", "role", "is_active"]
            set_clauses = []
            values = {"user_id": user_id}
            
            for field in allowed_fields:
                if field in updates:
                    set_clauses.append(f"{field} = :{field}")
                    values[field] = updates[field]
            
            if not set_clauses:
                logger.warning(f"[UserManager.update_user] No valid fields to update")
                return False
            
            set_clauses.append("updated_at = CURRENT_TIMESTAMP")
            
            query = f"UPDATE users SET {', '.join(set_clauses)} WHERE id = :user_id"
            await database.execute(query, values)
            
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
            
            logger.info(f"[UserManager.update_user] EXIT | user_id={user_id}")
            return True
            
        except Exception as e:
            logger.error(f"[UserManager.update_user] ERROR | error={str(e)}", exc_info=True)
            return False
    
    async def delete_user(
        self,
        user_id: int,
        user_context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Soft delete user (set is_active = false).
        
        Args:
            user_id: User ID to delete
            user_context: Context of user making the deletion (for audit)
        
        Returns:
            True if successful
        """
        logger.debug(f"[UserManager.delete_user] ENTRY | user_id={user_id}")
        
        try:
            query = "UPDATE users SET is_active = false, updated_at = CURRENT_TIMESTAMP WHERE id = :user_id"
            await database.execute(query, {"user_id": user_id})
            
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
            
            logger.info(f"[UserManager.delete_user] EXIT | user_id={user_id}")
            return True
            
        except Exception as e:
            logger.error(f"[UserManager.delete_user] ERROR | error={str(e)}", exc_info=True)
            return False
    
    async def list_users(
        self,
        role_filter: Optional[str] = None,
        active_only: bool = True
    ) -> List[Dict[str, Any]]:
        """
        List users with optional filtering.
        
        Args:
            role_filter: Filter by role (optional)
            active_only: Only return active users (default: True)
        
        Returns:
            List of user dictionaries
        """
        logger.debug(f"[UserManager.list_users] ENTRY | role_filter={role_filter}, active_only={active_only}")
        
        try:
            query = "SELECT id, auth_id, email, name, role, is_active, created_at, updated_at FROM users WHERE 1=1"
            values = {}
            
            if active_only:
                query += " AND is_active = true"
            
            if role_filter:
                query += " AND role = :role"
                values["role"] = role_filter
            
            query += " ORDER BY created_at DESC"
            
            rows = await database.fetch_all(query, values)
            return [dict(row) for row in rows]
            
        except Exception as e:
            logger.error(f"[UserManager.list_users] ERROR | error={str(e)}", exc_info=True)
            return []
    
    async def get_user_profile(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user profile (preferences and settings) - legacy user_account_profiles table."""
        logger.debug(f"[UserManager.get_user_profile] ENTRY | user_id={user_id}")
        
        try:
            query = """
                SELECT user_id, preferences, settings, metadata, created_at, updated_at
                FROM user_account_profiles
                WHERE user_id = :user_id
            """
            row = await database.fetch_one(query, {"user_id": user_id})
            
            if not row:
                # Return default profile if doesn't exist
                return {
                    "user_id": user_id,
                    "preferences": {},
                    "settings": {},
                    "metadata": {}
                }
            
            return {
                "user_id": row["user_id"],
                "preferences": self._parse_jsonb(row.get("preferences")),
                "settings": self._parse_jsonb(row.get("settings")),
                "metadata": self._parse_jsonb(row.get("metadata"))
            }
        except Exception as e:
            logger.error(f"[UserManager.get_user_profile] ERROR | error={str(e)}", exc_info=True)
            return None
    
    # --- Comprehensive Profile Methods ---
    
    async def get_basic_profile(self, user_id: int) -> Dict[str, Any]:
        """Get user basic profile."""
        try:
            await self._ensure_profile_exists("user_basic_profiles", user_id)
            # Use COALESCE to convert NULL to empty string at database level for string fields
            # This ensures we never get NULL values that could be serialized as {}
            query = """
                SELECT 
                    user_id,
                    COALESCE(preferred_name, '') as preferred_name,
                    COALESCE(phone, '') as phone,
                    COALESCE(mobile, '') as mobile,
                    COALESCE(alternate_email, '') as alternate_email,
                    COALESCE(timezone, '') as timezone,
                    COALESCE(locale, '') as locale,
                    COALESCE(avatar_url, '') as avatar_url,
                    COALESCE(bio, '') as bio,
                    metadata,
                    created_at,
                    updated_at
                FROM user_basic_profiles 
                WHERE user_id = :user_id
            """
            row = await database.fetch_one(query, {"user_id": user_id})
            if row:
                # Process the row - only parse JSONB for metadata field, others are already strings due to COALESCE
                result = {}
                for k, v in dict(row).items():
                    if k == "metadata":
                        result[k] = self._parse_jsonb(v)
                    else:
                        result[k] = v
                return result
            return {"user_id": user_id}
        except Exception as e:
            logger.error(f"[UserManager.get_basic_profile] ERROR: {e}", exc_info=True)
            return {"user_id": user_id}
    
    async def update_basic_profile(self, user_id: int, updates: Dict[str, Any]) -> bool:
        """Update user basic profile."""
        try:
            await self._ensure_profile_exists("user_basic_profiles", user_id)
            
            # Whitelist of allowed fields for basic profile (matches database schema)
            ALLOWED_FIELDS = {
                "preferred_name", "phone", "mobile", "alternate_email", 
                "timezone", "locale", "avatar_url", "bio", "metadata"
            }
            
            # Filter to only allowed fields and exclude system fields
            filtered_updates = {}
            for k, v in updates.items():
                if k in ["updated_at", "created_at", "user_id"]:
                    continue  # Skip system fields
                if k not in ALLOWED_FIELDS:
                    logger.warning(f"[UserManager.update_basic_profile] Ignoring unknown field: {k}")
                    continue
                if v is None:
                    continue
                # Convert empty dicts to None for optional string fields
                if isinstance(v, dict) and len(v) == 0 and k != "metadata":
                    logger.debug(f"[UserManager.update_basic_profile] Converting empty dict to None for field: {k}")
                    continue  # Skip empty dicts for non-JSONB fields
                filtered_updates[k] = v
            
            # Handle JSONB fields - serialize dict/list to JSON string BEFORE building query
            values = {"user_id": user_id}
            set_clauses = []
            
            for k, v in filtered_updates.items():
                # Handle metadata (JSONB field) - always serialize dict/list to JSON string
                if k == "metadata":
                    if isinstance(v, (dict, list)):
                        set_clauses.append(f"{k} = :{k}")
                        values[k] = json.dumps(v)  # Serialize to JSON string
                        logger.debug(f"[UserManager.update_basic_profile] Serialized metadata: {type(v).__name__} -> JSON string")
                    elif isinstance(v, str):
                        # Already a JSON string, use as-is
                        set_clauses.append(f"{k} = :{k}")
                        values[k] = v
                    else:
                        # Skip other types for metadata
                        logger.warning(f"[UserManager.update_basic_profile] Skipping metadata with unexpected type: {type(v).__name__}")
                else:
                    # Regular field - check if it's a dict/list (shouldn't be, but be safe)
                    if isinstance(v, (dict, list)):
                        # Frontend might send objects for fields that should be primitives
                        logger.warning(f"[UserManager.update_basic_profile] Non-JSONB field {k} has {type(v).__name__} value: {v}. Skipping this field.")
                        continue  # Skip this field instead of raising an error
                    # Regular field - add as-is (strings, numbers, booleans, etc.)
                    set_clauses.append(f"{k} = :{k}")
                    values[k] = v
            
            if not set_clauses:
                # No fields to update except updated_at
                return True
            
            # Verify all values are serialized (no dicts/lists except in JSON strings)
            # This is a critical safety check - asyncpg cannot handle Python dicts/lists directly
            for k, v in list(values.items()):  # Use list() to avoid modification during iteration
                if k == "user_id":
                    continue
                if isinstance(v, (dict, list)):
                    logger.error(f"[UserManager.update_basic_profile] CRITICAL: Found unserialized {type(v).__name__} for field {k}: {v}")
                    logger.error(f"[UserManager.update_basic_profile] Values dict: {values}")
                    logger.error(f"[UserManager.update_basic_profile] Set clauses: {set_clauses}")
                    # Force serialize it as a last resort
                    values[k] = json.dumps(v)
                    logger.warning(f"[UserManager.update_basic_profile] Force-serialized field {k} as fallback")
            
            query = f"UPDATE user_basic_profiles SET {', '.join(set_clauses)}, updated_at = CURRENT_TIMESTAMP WHERE user_id = :user_id"
            logger.debug(f"[UserManager.update_basic_profile] Executing query with {len(values)} parameters: {list(values.keys())}")
            await database.execute(query, values)
            return True
        except Exception as e:
            logger.error(f"[UserManager.update_basic_profile] ERROR: {e}", exc_info=True)
            return False
    
    async def get_professional_profile(self, user_id: int) -> Dict[str, Any]:
        """Get user professional profile."""
        try:
            await self._ensure_profile_exists("user_professional_profiles", user_id)
            # Use COALESCE to convert NULL to empty string at database level for string fields
            query = """
                SELECT 
                    user_id,
                    COALESCE(job_title, '') as job_title,
                    COALESCE(department, '') as department,
                    COALESCE(organization, '') as organization,
                    manager_id,
                    COALESCE(team_name, '') as team_name,
                    COALESCE(employee_id, '') as employee_id,
                    COALESCE(office_location, '') as office_location,
                    start_date,
                    metadata,
                    created_at,
                    updated_at
                FROM user_professional_profiles 
                WHERE user_id = :user_id
            """
            row = await database.fetch_one(query, {"user_id": user_id})
            if row:
                # Process the row - only parse JSONB for metadata field
                result = {}
                for k, v in dict(row).items():
                    if k == "metadata":
                        result[k] = self._parse_jsonb(v)
                    else:
                        result[k] = v
                return result
            return {"user_id": user_id}
        except Exception as e:
            logger.error(f"[UserManager.get_professional_profile] ERROR: {e}", exc_info=True)
            return {"user_id": user_id}
    
    async def update_professional_profile(self, user_id: int, updates: Dict[str, Any]) -> bool:
        """Update user professional profile."""
        try:
            await self._ensure_profile_exists("user_professional_profiles", user_id)
            
            # Whitelist of allowed fields for professional profile (matches database schema)
            ALLOWED_FIELDS = {
                "job_title", "department", "organization", "manager_id", 
                "team_name", "employee_id", "office_location", "start_date", "metadata"
            }
            
            # Filter to only allowed fields and exclude system fields
            filtered_updates = {}
            for k, v in updates.items():
                if k in ["updated_at", "created_at", "user_id"]:
                    continue  # Skip system fields
                if k not in ALLOWED_FIELDS:
                    logger.warning(f"[UserManager.update_professional_profile] Ignoring unknown field: {k}")
                    continue
                if v is None:
                    continue
                # Convert empty dicts to None for optional fields
                if isinstance(v, dict) and len(v) == 0 and k != "metadata":
                    logger.debug(f"[UserManager.update_professional_profile] Converting empty dict to None for field: {k}")
                    continue  # Skip empty dicts for non-JSONB fields
                filtered_updates[k] = v
            
            # Handle JSONB fields - serialize dict/list to JSON string
            values = {"user_id": user_id}
            set_clauses = []
            for k, v in filtered_updates.items():
                if k == "metadata":
                    # Serialize JSONB to string - PostgreSQL will handle type conversion
                    if isinstance(v, (dict, list)):
                        set_clauses.append(f"{k} = :{k}")
                        values[k] = json.dumps(v)
                    elif isinstance(v, str):
                        # Already a string, use as-is
                        set_clauses.append(f"{k} = :{k}")
                        values[k] = v
                else:
                    # Regular field - check if it's a dict/list
                    if isinstance(v, (dict, list)):
                        logger.warning(f"[UserManager.update_professional_profile] Non-JSONB field {k} has {type(v).__name__} value. Skipping.")
                        continue
                    set_clauses.append(f"{k} = :{k}")
                    values[k] = v
            
            if not set_clauses:
                # No fields to update except updated_at
                return True
            
            query = f"UPDATE user_professional_profiles SET {', '.join(set_clauses)}, updated_at = CURRENT_TIMESTAMP WHERE user_id = :user_id"
            await database.execute(query, values)
            return True
        except Exception as e:
            logger.error(f"[UserManager.update_professional_profile] ERROR: {e}", exc_info=True)
            return False
    
    async def get_communication_profile(self, user_id: int) -> Dict[str, Any]:
        """Get user communication profile."""
        try:
            await self._ensure_profile_exists("user_communication_profiles", user_id)
            # Use COALESCE to convert NULL to empty string at database level for string fields
            query = """
                SELECT 
                    user_id,
                    COALESCE(communication_style, '') as communication_style,
                    COALESCE(tone_preference, '') as tone_preference,
                    prompt_style_id,
                    COALESCE(preferred_language, '') as preferred_language,
                    COALESCE(response_format_preference, '') as response_format_preference,
                    notification_preferences,
                    COALESCE(engagement_level, '') as engagement_level,
                    metadata,
                    created_at,
                    updated_at
                FROM user_communication_profiles 
                WHERE user_id = :user_id
            """
            row = await database.fetch_one(query, {"user_id": user_id})
            if row:
                # Process the row - parse JSONB for notification_preferences and metadata
                result = {}
                for k, v in dict(row).items():
                    if k in ["notification_preferences", "metadata"]:
                        result[k] = self._parse_jsonb(v)
                    else:
                        result[k] = v
                return result
            return {"user_id": user_id}
        except Exception as e:
            logger.error(f"[UserManager.get_communication_profile] ERROR: {e}", exc_info=True)
            return {"user_id": user_id}
    
    async def update_communication_profile(self, user_id: int, updates: Dict[str, Any]) -> bool:
        """Update user communication profile."""
        try:
            await self._ensure_profile_exists("user_communication_profiles", user_id)
            
            # Whitelist of allowed fields for communication profile (matches database schema)
            ALLOWED_FIELDS = {
                "communication_style", "tone_preference", "prompt_style_id",
                "preferred_language", "response_format_preference", 
                "notification_preferences", "engagement_level", "metadata"
            }
            
            # Filter to only allowed fields and exclude system fields
            # Allow empty strings (""), but filter out None values
            filtered_updates = {}
            for k, v in updates.items():
                if k in ["updated_at", "created_at", "user_id"]:
                    continue  # Skip system fields
                if k not in ALLOWED_FIELDS:
                    logger.warning(f"[UserManager.update_communication_profile] Ignoring unknown field: {k}")
                    continue
                if v is None:
                    continue  # Skip None, but allow empty strings
                filtered_updates[k] = v
            
            # Handle JSONB fields specially, filter out updated_at
            set_clauses = []
            values = {"user_id": user_id}
            for k, v in filtered_updates.items():
                if k in ["notification_preferences", "metadata"]:
                    # JSONB fields - merge with existing
                    if isinstance(v, (dict, list)):
                        set_clauses.append(f"{k} = {k} || :{k}")
                        values[k] = json.dumps(v)
                    elif isinstance(v, str):
                        set_clauses.append(f"{k} = {k} || :{k}")
                        values[k] = v
                else:
                    # Regular field - check if it's a dict/list
                    if isinstance(v, (dict, list)):
                        logger.warning(f"[UserManager.update_communication_profile] Non-JSONB field {k} has {type(v).__name__} value. Skipping.")
                        continue
                    set_clauses.append(f"{k} = :{k}")
                    values[k] = v
            
            if not set_clauses:
                return True
            
            query = f"UPDATE user_communication_profiles SET {', '.join(set_clauses)}, updated_at = CURRENT_TIMESTAMP WHERE user_id = :user_id"
            await database.execute(query, values)
            return True
        except Exception as e:
            logger.error(f"[UserManager.update_communication_profile] ERROR: {e}", exc_info=True)
            return False
    
    async def get_use_case_profile(self, user_id: int) -> Dict[str, Any]:
        """Get user use case profile."""
        try:
            await self._ensure_profile_exists("user_use_case_profiles", user_id)
            query = "SELECT * FROM user_use_case_profiles WHERE user_id = :user_id"
            row = await database.fetch_one(query, {"user_id": user_id})
            if row:
                return {k: self._parse_jsonb(v) for k, v in dict(row).items()}
            return {"user_id": user_id}
        except Exception as e:
            logger.error(f"[UserManager.get_use_case_profile] ERROR: {e}", exc_info=True)
            return {"user_id": user_id}
    
    async def update_use_case_profile(self, user_id: int, updates: Dict[str, Any]) -> bool:
        """Update user use case profile."""
        try:
            await self._ensure_profile_exists("user_use_case_profiles", user_id)
            # All fields are JSONB, merge them, filter out updated_at
            set_clauses = []
            values = {"user_id": user_id}
            for k, v in updates.items():
                if k == "updated_at":
                    continue  # Skip updated_at to avoid duplicate assignment
                set_clauses.append(f"{k} = {k} || :{k}")
                values[k] = json.dumps(v) if isinstance(v, (dict, list)) else json.dumps([v])
            query = f"UPDATE user_use_case_profiles SET {', '.join(set_clauses)}, updated_at = CURRENT_TIMESTAMP WHERE user_id = :user_id"
            await database.execute(query, values)
            return True
        except Exception as e:
            logger.error(f"[UserManager.update_use_case_profile] ERROR: {e}", exc_info=True)
            return False
    
    async def get_ai_preference_profile(self, user_id: int) -> Dict[str, Any]:
        """Get user AI preference profile."""
        try:
            await self._ensure_profile_exists("user_ai_preference_profiles", user_id)
            # Use COALESCE to convert NULL to empty string at database level for string fields
            query = """
                SELECT 
                    user_id,
                    escalation_rules,
                    COALESCE(autonomy_level, '') as autonomy_level,
                    confidence_threshold,
                    require_confirmation_for,
                    preferred_model_preferences,
                    feedback_preferences,
                    COALESCE(preferred_strategy, '') as preferred_strategy,
                    strategy_preferences,
                    task_category_preferences,
                    task_domain_preferences,
                    metadata,
                    created_at,
                    updated_at
                FROM user_ai_preference_profiles 
                WHERE user_id = :user_id
            """
            row = await database.fetch_one(query, {"user_id": user_id})
            if row:
                # Process the row - parse JSONB for JSONB fields, handle confidence_threshold as float
                result = {}
                for k, v in dict(row).items():
                    if k in ["escalation_rules", "require_confirmation_for", "preferred_model_preferences", 
                             "feedback_preferences", "strategy_preferences", "task_category_preferences", 
                             "task_domain_preferences", "metadata"]:
                        result[k] = self._parse_jsonb(v)
                    elif k == "confidence_threshold" and v is not None:
                        result[k] = float(v)
                    else:
                        result[k] = v
                return result
            return {"user_id": user_id}
        except Exception as e:
            logger.error(f"[UserManager.get_ai_preference_profile] ERROR: {e}", exc_info=True)
            return {"user_id": user_id}
    
    async def update_ai_preference_profile(self, user_id: int, updates: Dict[str, Any]) -> bool:
        """Update user AI preference profile."""
        try:
            await self._ensure_profile_exists("user_ai_preference_profiles", user_id)
            
            # Whitelist of allowed fields for AI preference profile (matches database schema)
            ALLOWED_FIELDS = {
                "escalation_rules", "autonomy_level", "confidence_threshold",
                "require_confirmation_for", "preferred_model_preferences",
                "feedback_preferences", "preferred_strategy", "strategy_preferences",
                "task_category_preferences", "task_domain_preferences", "metadata"
            }
            
            # Filter to only allowed fields and exclude system fields
            filtered_updates = {}
            for k, v in updates.items():
                if k in ["updated_at", "created_at", "user_id"]:
                    continue  # Skip system fields
                if k not in ALLOWED_FIELDS:
                    logger.warning(f"[UserManager.update_ai_preference_profile] Ignoring unknown field: {k}")
                    continue
                if v is None:
                    continue
                # Convert empty dicts to None for optional fields
                if isinstance(v, dict) and len(v) == 0 and k not in ["escalation_rules", "preferred_model_preferences", 
                                                                      "feedback_preferences", "strategy_preferences",
                                                                      "task_category_preferences", "task_domain_preferences", "metadata"]:
                    continue  # Skip empty dicts for non-JSONB fields
                filtered_updates[k] = v
            
            set_clauses = []
            values = {"user_id": user_id}
            for k, v in filtered_updates.items():
                if k in ["escalation_rules", "require_confirmation_for", "preferred_model_preferences", 
                        "feedback_preferences", "strategy_preferences", "task_category_preferences", 
                        "task_domain_preferences", "metadata"]:
                    # JSONB fields - merge with existing
                    if isinstance(v, (dict, list)):
                        set_clauses.append(f"{k} = {k} || :{k}")
                        values[k] = json.dumps(v)
                    elif isinstance(v, str):
                        set_clauses.append(f"{k} = {k} || :{k}")
                        values[k] = v
                else:
                    # Regular field - check if it's a dict/list
                    if isinstance(v, (dict, list)):
                        logger.warning(f"[UserManager.update_ai_preference_profile] Non-JSONB field {k} has {type(v).__name__} value. Skipping.")
                        continue
                    set_clauses.append(f"{k} = :{k}")
                    values[k] = v
            
            if not set_clauses:
                return True
            
            query = f"UPDATE user_ai_preference_profiles SET {', '.join(set_clauses)}, updated_at = CURRENT_TIMESTAMP WHERE user_id = :user_id"
            await database.execute(query, values)
            return True
        except Exception as e:
            logger.error(f"[UserManager.update_ai_preference_profile] ERROR: {e}", exc_info=True)
            return False
    
    async def get_query_history_profile(self, user_id: int) -> Dict[str, Any]:
        """Get user query history profile."""
        try:
            await self._ensure_profile_exists("user_query_history_profiles", user_id)
            query = "SELECT * FROM user_query_history_profiles WHERE user_id = :user_id"
            row = await database.fetch_one(query, {"user_id": user_id})
            if row:
                return {k: self._parse_jsonb(v) for k, v in dict(row).items()}
            return {"user_id": user_id}
        except Exception as e:
            logger.error(f"[UserManager.get_query_history_profile] ERROR: {e}", exc_info=True)
            return {"user_id": user_id}
    
    async def get_user_session_links(self, user_id: int, limit: int = 50) -> List[Dict[str, Any]]:
        """Get session links for a user."""
        try:
            query = """
                SELECT uqsl.*, ss.status as session_status, ss.consultant_strategy
                FROM user_query_session_links uqsl
                LEFT JOIN shaping_sessions ss ON uqsl.session_id = ss.id
                WHERE uqsl.user_id = :user_id
                ORDER BY uqsl.created_at DESC
                LIMIT :limit
            """
            rows = await database.fetch_all(query, {"user_id": user_id, "limit": limit})
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"[UserManager.get_user_session_links] ERROR: {e}", exc_info=True)
            return []
    
    async def _ensure_profile_exists(self, table_name: str, user_id: int):
        """Ensure a profile record exists (internal helper)."""
        check_query = f"SELECT 1 FROM {table_name} WHERE user_id = :user_id"
        exists = await database.fetch_one(check_query, {"user_id": user_id})
        
        if not exists:
            insert_query = f"INSERT INTO {table_name} (user_id) VALUES (:user_id) ON CONFLICT (user_id) DO NOTHING"
            await database.execute(insert_query, {"user_id": user_id})
    
    async def update_user_profile(
        self,
        user_id: int,
        preferences: Optional[Dict[str, Any]] = None,
        settings: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Update user profile (preferences, settings, metadata).
        
        Args:
            user_id: User ID
            preferences: Preferences to update (merged with existing)
            settings: Settings to update (merged with existing)
            metadata: Metadata to update (merged with existing)
        
        Returns:
            True if successful
        """
        logger.debug(f"[UserManager.update_user_profile] ENTRY | user_id={user_id}")
        
        try:
            # Get existing profile
            existing = await self.get_user_profile(user_id)
            if not existing:
                # Create profile if doesn't exist
                await self._create_user_profile(user_id)
                existing = {"preferences": {}, "settings": {}, "metadata": {}}
            
            # Merge updates
            new_preferences = {**existing.get("preferences", {}), **(preferences or {})}
            new_settings = {**existing.get("settings", {}), **(settings or {})}
            new_metadata = {**existing.get("metadata", {}), **(metadata or {})}
            
            query = """
                UPDATE user_account_profiles
                SET preferences = :preferences, settings = :settings, metadata = :metadata,
                    updated_at = CURRENT_TIMESTAMP
                WHERE user_id = :user_id
            """
            await database.execute(query, {
                "user_id": user_id,
                "preferences": json.dumps(new_preferences),
                "settings": json.dumps(new_settings),
                "metadata": json.dumps(new_metadata)
            })
            
            logger.info(f"[UserManager.update_user_profile] EXIT | user_id={user_id}")
            return True
            
        except Exception as e:
            logger.error(f"[UserManager.update_user_profile] ERROR | error={str(e)}", exc_info=True)
            return False
    
    async def get_user_role(self, user_id: int) -> Optional[str]:
        """Get user role."""
        logger.debug(f"[UserManager.get_user_role] ENTRY | user_id={user_id}")
        
        try:
            query = "SELECT role FROM users WHERE id = :user_id"
            role = await database.fetch_val(query, {"user_id": user_id})
            return role
        except Exception as e:
            logger.error(f"[UserManager.get_user_role] ERROR | error={str(e)}", exc_info=True)
            return None
    
    async def has_permission(self, user_id: int, permission: str) -> bool:
        """
        Check if user has permission.
        
        Args:
            user_id: User ID
            permission: Permission to check (e.g., 'admin', 'manage_users')
        
        Returns:
            True if user has permission
        """
        logger.debug(f"[UserManager.has_permission] ENTRY | user_id={user_id}, permission={permission}")
        
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
            logger.error(f"[UserManager.has_permission] ERROR | error={str(e)}", exc_info=True)
            return False
    
    # Private helper methods
    
    async def _create_user_profile(self, user_id: int) -> None:
        """Create empty user profile."""
        try:
            query = """
                INSERT INTO user_account_profiles (user_id, preferences, settings, metadata)
                VALUES (:user_id, '{}', '{}', '{}')
                ON CONFLICT (user_id) DO NOTHING
            """
            await database.execute(query, {"user_id": user_id})
        except Exception as e:
            logger.warning(f"[UserManager._create_user_profile] Failed to create profile: {e}")
    
    def _parse_jsonb(self, value: Any) -> Any:
        """Parse JSONB value from database."""
        if isinstance(value, str):
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return {}
        elif value is None:
            return {}
        return value


# Singleton instance
user_manager = UserManager()

# Compatibility shim: Import new services for gradual migration
try:
    from nexus.modules.users.services.user_service import UserService as NewUserService
    from nexus.modules.users.services.profile_service import ProfileService as NewProfileService
    _new_user_service = NewUserService()
    _new_profile_service = NewProfileService()
except ImportError:
    # New module not available yet
    _new_user_service = None
    _new_profile_service = None
