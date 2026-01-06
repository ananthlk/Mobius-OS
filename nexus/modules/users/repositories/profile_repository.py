"""
Profile Repository

Handles all database operations for profile tables.
"""
import logging
import json
from typing import Optional, Dict, Any, List
from nexus.modules.database import database

logger = logging.getLogger("nexus.users.profile_repository")


class ProfileRepository:
    """Repository for profile data access."""
    
    def __init__(self):
        self._parse_jsonb = self._create_jsonb_parser()
    
    @staticmethod
    def _create_jsonb_parser():
        """Create JSONB parser function."""
        def parse_jsonb(value: Any) -> Any:
            """Parse JSONB value from database."""
            if isinstance(value, str):
                try:
                    return json.loads(value)
                except (json.JSONDecodeError, TypeError):
                    return {}
            elif value is None:
                return {}
            return value
        return parse_jsonb
    
    async def ensure_profile_exists(self, table_name: str, user_id: int):
        """Ensure a profile record exists."""
        check_query = f"SELECT 1 FROM {table_name} WHERE user_id = :user_id"
        exists = await database.fetch_one(check_query, {"user_id": user_id})
        
        if not exists:
            insert_query = f"""
                INSERT INTO {table_name} (user_id)
                VALUES (:user_id)
                ON CONFLICT (user_id) DO NOTHING
            """
            await database.execute(insert_query, {"user_id": user_id})
    
    # Basic Profile
    async def get_basic_profile(self, user_id: int) -> Dict[str, Any]:
        """Get basic profile."""
        await self.ensure_profile_exists("user_basic_profiles", user_id)
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
            # #region agent log
            import json
            row_dict_raw = dict(row)
            with open('/Users/ananth/Personal AI Projects/Mobius OS/.cursor/debug.log', 'a') as f:
                f.write(json.dumps({"location":"profile_repository.py:75","message":"get_basic_profile - raw row from DB","data":{"user_id":user_id,"row_dict_raw":str(row_dict_raw),"row_keys":list(row_dict_raw.keys()),"row_values_types":{k:type(v).__name__ + (f"({v})" if v is not None and not isinstance(v, (dict, list)) else "") for k,v in row_dict_raw.items()}},"timestamp":int(__import__('time').time()*1000),"sessionId":"debug-session","runId":"run2","hypothesisId":"E"})+"\n")
            # #endregion
            
            # Process the row - COALESCE in SQL already converted NULL to '', but handle metadata JSONB parsing
            result = {}
            for k, v in row_dict_raw.items():
                if k == "metadata":
                    result[k] = self._parse_jsonb(v)
                else:
                    # All other fields should already be strings (not NULL) due to COALESCE
                    # But add safety check for edge cases
                    if v is None:
                        result[k] = ""
                    elif isinstance(v, dict) and len(v) == 0 and k != "metadata":
                        # Edge case: if somehow an empty dict is returned for non-JSONB field, convert to empty string
                        result[k] = ""
                    else:
                        result[k] = v
            
            # #region agent log
            with open('/Users/ananth/Personal AI Projects/Mobius OS/.cursor/debug.log', 'a') as f:
                f.write(json.dumps({"location":"profile_repository.py:89","message":"get_basic_profile - after processing","data":{"user_id":user_id,"result":str(result),"result_keys":list(result.keys()),"result_values_types":{k:type(v).__name__ + (f"({v})" if v is not None and not isinstance(v, dict) else "") for k,v in result.items()}},"timestamp":int(__import__('time').time()*1000),"sessionId":"debug-session","runId":"run2","hypothesisId":"E"})+"\n")
            # #endregion
            return result
        return {"user_id": user_id}
    
    async def update_basic_profile(self, user_id: int, updates: Dict[str, Any]) -> bool:
        """Update basic profile."""
        # #region agent log
        import json
        with open('/Users/ananth/Personal AI Projects/Mobius OS/.cursor/debug.log', 'a') as f:
            f.write(json.dumps({"location":"profile_repository.py:58","message":"ProfileRepository.update_basic_profile ENTRY","data":{"user_id":user_id,"updates":str(updates),"updates_keys":list(updates.keys())},"timestamp":int(__import__('time').time()*1000),"sessionId":"debug-session","runId":"run1","hypothesisId":"A,B,C"})+"\n")
        # #endregion
        await self.ensure_profile_exists("user_basic_profiles", user_id)
        # Filter out system fields that should never be updated
        # Allow empty strings (""), but filter out None values
        system_fields = {"user_id", "created_at", "updated_at"}
        filtered_updates = {k: v for k, v in updates.items() if k not in system_fields and v is not None}
        # Explicitly allow empty strings - don't filter them out
        # (The check above already allows empty strings since "" is not None)
        # #region agent log
        with open('/Users/ananth/Personal AI Projects/Mobius OS/.cursor/debug.log', 'a') as f:
            f.write(json.dumps({"location":"profile_repository.py:69","message":"AFTER filtering updates","data":{"filtered_updates":str(filtered_updates),"filtered_keys":list(filtered_updates.keys()),"filtered_values_types":{k:type(v).__name__ for k,v in filtered_updates.items()}},"timestamp":int(__import__('time').time()*1000),"sessionId":"debug-session","runId":"run2","hypothesisId":"A,B,C"})+"\n")
        # #endregion
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
                # For string fields, ensure None values are converted to empty string
                # This prevents NULL from being stored, which can cause serialization issues
                if v is None:
                    set_clauses.append(f"{k} = :{k}")
                    values[k] = ""
                else:
                    set_clauses.append(f"{k} = :{k}")
                    values[k] = v
        
        if not set_clauses:
            # #region agent log
            with open('/Users/ananth/Personal AI Projects/Mobius OS/.cursor/debug.log', 'a') as f:
                f.write(json.dumps({"location":"profile_repository.py:80","message":"No set_clauses - returning True early","data":{"user_id":user_id},"timestamp":int(__import__('time').time()*1000),"sessionId":"debug-session","runId":"run1","hypothesisId":"A"})+"\n")
            # #endregion
            # No fields to update except updated_at
            return True
        
        query = f"""
            UPDATE user_basic_profiles
            SET {', '.join(set_clauses)}, updated_at = CURRENT_TIMESTAMP
            WHERE user_id = :user_id
        """
        # #region agent log
        with open('/Users/ananth/Personal AI Projects/Mobius OS/.cursor/debug.log', 'a') as f:
            f.write(json.dumps({"location":"profile_repository.py:108","message":"BEFORE database.execute","data":{"query":query,"values":str(values),"set_clauses":set_clauses,"values_types":{k:type(v).__name__ for k,v in values.items()}},"timestamp":int(__import__('time').time()*1000),"sessionId":"debug-session","runId":"run2","hypothesisId":"A,B,C,E"})+"\n")
        # #endregion
        try:
            # #region agent log
            # Get current state before update
            before_query = "SELECT preferred_name, phone, mobile, timezone, alternate_email, locale, avatar_url, bio FROM user_basic_profiles WHERE user_id = :user_id"
            before_row = await database.fetch_one(before_query, {"user_id": user_id})
            before_data = dict(before_row) if before_row else {}
            # #endregion
            
            await database.execute(query, values)
            
            # #region agent log
            # Get state after update to verify it persisted
            after_query = "SELECT preferred_name, phone, mobile, timezone, alternate_email, locale, avatar_url, bio FROM user_basic_profiles WHERE user_id = :user_id"
            after_row = await database.fetch_one(after_query, {"user_id": user_id})
            after_data = dict(after_row) if after_row else {}
            
            with open('/Users/ananth/Personal AI Projects/Mobius OS/.cursor/debug.log', 'a') as f:
                f.write(json.dumps({"location":"profile_repository.py:133","message":"AFTER database.execute","data":{"user_id":user_id,"before_data":str(before_data),"after_data":str(after_data),"values_sent":str(values),"set_clauses":set_clauses,"query":query},"timestamp":int(__import__('time').time()*1000),"sessionId":"debug-session","runId":"run2","hypothesisId":"A,B,C,E"})+"\n")
            # #endregion
            return True
        except Exception as e:
            # #region agent log
            with open('/Users/ananth/Personal AI Projects/Mobius OS/.cursor/debug.log', 'a') as f:
                f.write(json.dumps({"location":"profile_repository.py:89","message":"database.execute EXCEPTION","data":{"error":str(e),"error_type":type(e).__name__,"user_id":user_id,"query":query,"values":str(values)},"timestamp":int(__import__('time').time()*1000),"sessionId":"debug-session","runId":"run1","hypothesisId":"E"})+"\n")
            # #endregion
            raise
    
    # Professional Profile
    async def get_professional_profile(self, user_id: int) -> Dict[str, Any]:
        """Get professional profile."""
        await self.ensure_profile_exists("user_professional_profiles", user_id)
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
    
    async def update_professional_profile(self, user_id: int, updates: Dict[str, Any]) -> bool:
        """Update professional profile."""
        await self.ensure_profile_exists("user_professional_profiles", user_id)
        # Filter out updated_at from updates to avoid duplicate assignment
        filtered_updates = {k: v for k, v in updates.items() if k != "updated_at" and v is not None}
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
                set_clauses.append(f"{k} = :{k}")
                values[k] = v
        
        if not set_clauses:
            # No fields to update except updated_at
            return True
        
        query = f"""
            UPDATE user_professional_profiles
            SET {', '.join(set_clauses)}, updated_at = CURRENT_TIMESTAMP
            WHERE user_id = :user_id
        """
        await database.execute(query, values)
        return True
    
    # Communication Profile
    async def get_communication_profile(self, user_id: int) -> Dict[str, Any]:
        """Get communication profile."""
        await self.ensure_profile_exists("user_communication_profiles", user_id)
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
    
    async def update_communication_profile(self, user_id: int, updates: Dict[str, Any]) -> bool:
        """Update communication profile."""
        await self.ensure_profile_exists("user_communication_profiles", user_id)
        set_clauses = []
        values = {"user_id": user_id}
        for k, v in updates.items():
            if k == "updated_at":
                continue  # Skip updated_at to avoid duplicate assignment
            if k in ["notification_preferences", "metadata"]:
                set_clauses.append(f"{k} = {k} || :{k}")
                values[k] = json.dumps(v) if isinstance(v, (dict, list)) else v
            else:
                set_clauses.append(f"{k} = :{k}")
                values[k] = v
        query = f"""
            UPDATE user_communication_profiles
            SET {', '.join(set_clauses)}, updated_at = CURRENT_TIMESTAMP
            WHERE user_id = :user_id
        """
        await database.execute(query, values)
        return True
    
    # Use Case Profile
    async def get_use_case_profile(self, user_id: int) -> Dict[str, Any]:
        """Get use case profile."""
        await self.ensure_profile_exists("user_use_case_profiles", user_id)
        query = "SELECT * FROM user_use_case_profiles WHERE user_id = :user_id"
        row = await database.fetch_one(query, {"user_id": user_id})
        if row:
            return {k: self._parse_jsonb(v) for k, v in dict(row).items()}
        return {"user_id": user_id}
    
    async def update_use_case_profile(self, user_id: int, updates: Dict[str, Any]) -> bool:
        """Update use case profile."""
        await self.ensure_profile_exists("user_use_case_profiles", user_id)
        set_clauses = []
        values = {"user_id": user_id}
        for k, v in updates.items():
            if k == "updated_at":
                continue  # Skip updated_at to avoid duplicate assignment
            set_clauses.append(f"{k} = {k} || :{k}")
            values[k] = json.dumps(v) if isinstance(v, (dict, list)) else json.dumps([v])
        query = f"""
            UPDATE user_use_case_profiles
            SET {', '.join(set_clauses)}, updated_at = CURRENT_TIMESTAMP
            WHERE user_id = :user_id
        """
        await database.execute(query, values)
        return True
    
    # AI Preference Profile
    async def get_ai_preference_profile(self, user_id: int) -> Dict[str, Any]:
        """Get AI preference profile."""
        await self.ensure_profile_exists("user_ai_preference_profiles", user_id)
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
    
    async def update_ai_preference_profile(self, user_id: int, updates: Dict[str, Any]) -> bool:
        """Update AI preference profile."""
        await self.ensure_profile_exists("user_ai_preference_profiles", user_id)
        set_clauses = []
        values = {"user_id": user_id}
        for k, v in updates.items():
            if k == "updated_at":
                continue  # Skip updated_at to avoid duplicate assignment
            if k in ["escalation_rules", "require_confirmation_for", "preferred_model_preferences",
                    "feedback_preferences", "strategy_preferences", "task_category_preferences",
                    "task_domain_preferences", "metadata"]:
                set_clauses.append(f"{k} = {k} || :{k}")
                values[k] = json.dumps(v) if isinstance(v, (dict, list)) else v
            else:
                set_clauses.append(f"{k} = :{k}")
                values[k] = v
        query = f"""
            UPDATE user_ai_preference_profiles
            SET {', '.join(set_clauses)}, updated_at = CURRENT_TIMESTAMP
            WHERE user_id = :user_id
        """
        await database.execute(query, values)
        return True
    
    # Query History Profile
    async def get_query_history_profile(self, user_id: int) -> Dict[str, Any]:
        """Get query history profile."""
        await self.ensure_profile_exists("user_query_history_profiles", user_id)
        query = "SELECT * FROM user_query_history_profiles WHERE user_id = :user_id"
        row = await database.fetch_one(query, {"user_id": user_id})
        if row:
            return {k: self._parse_jsonb(v) for k, v in dict(row).items()}
        return {"user_id": user_id}
    
    async def get_user_session_links(self, user_id: int, limit: int = 50) -> List[Dict[str, Any]]:
        """Get session links for a user."""
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
