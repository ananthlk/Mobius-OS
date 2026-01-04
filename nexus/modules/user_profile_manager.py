"""
Comprehensive User Profile Management System
Tracks and updates user profiles based on conversation events and interactions.
"""
import logging
import json
import re
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime
from nexus.modules.database import database

logger = logging.getLogger("nexus.user_profile_manager")


class ProfileEvent:
    """Represents an event that might contain profile-relevant information."""
    def __init__(
        self,
        user_id: int,
        event_type: str,
        user_message: str,
        assistant_response: str,
        session_id: Optional[int] = None,
        interaction_id: Optional[str] = None,
        workflow_name: Optional[str] = None,
        strategy: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.user_id = user_id
        self.event_type = event_type
        self.user_message = user_message
        self.assistant_response = assistant_response
        self.session_id = session_id
        self.interaction_id = interaction_id
        self.workflow_name = workflow_name
        self.strategy = strategy
        self.metadata = metadata or {}
        self.extracted_data: Dict[str, Any] = {}


class ProfileExtractor:
    """Extracts profile-relevant information from conversations."""
    
    @staticmethod
    def extract_basic_profile(event: ProfileEvent) -> Dict[str, Any]:
        """Extract basic profile information (name, contacts, etc.)."""
        updates = {}
        text = f"{event.user_message} {event.assistant_response}".lower()
        
        # Extract preferred name
        name_patterns = [
            r"call me (\w+)",
            r"my name is (\w+)",
            r"prefer to be called (\w+)",
            r"you can call me (\w+)",
            r"i'm (\w+)",
            r"i am (\w+)"
        ]
        for pattern in name_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                updates["preferred_name"] = match.group(1).title()
                break
        
        # Extract phone numbers
        phone_pattern = r"phone.*?(\d{3}[-.\s]?\d{3}[-.\s]?\d{4})"
        match = re.search(phone_pattern, text, re.IGNORECASE)
        if match:
            updates["phone"] = match.group(1)
        
        mobile_pattern = r"mobile.*?(\d{3}[-.\s]?\d{3}[-.\s]?\d{4})"
        match = re.search(mobile_pattern, text, re.IGNORECASE)
        if match:
            updates["mobile"] = match.group(1)
        
        # Extract timezone
        timezone_pattern = r"timezone.*?(utc[+-]?\d+|pst|pdt|est|edt|cst|cdt|mst|mdt)"
        match = re.search(timezone_pattern, text, re.IGNORECASE)
        if match:
            updates["timezone"] = match.group(1).upper()
        
        return updates
    
    @staticmethod
    def extract_professional_profile(event: ProfileEvent) -> Dict[str, Any]:
        """Extract professional information (role, manager, department, etc.)."""
        updates = {}
        text = f"{event.user_message} {event.assistant_response}".lower()
        
        # Extract job title
        title_patterns = [
            r"i'm (?:a|an) (\w+(?:\s+\w+)?)\s+(?:at|in)",
            r"my title is (\w+(?:\s+\w+)?)",
            r"i work as (?:a|an) (\w+(?:\s+\w+)?)",
            r"job title.*?(\w+(?:\s+\w+)?)"
        ]
        for pattern in title_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                updates["job_title"] = match.group(1).title()
                break
        
        # Extract department
        dept_pattern = r"(?:department|dept).*?(\w+(?:\s+\w+)?)"
        match = re.search(dept_pattern, text, re.IGNORECASE)
        if match:
            updates["department"] = match.group(1).title()
        
        # Extract organization
        org_pattern = r"work (?:at|for) (\w+(?:\s+\w+)?)"
        match = re.search(org_pattern, text, re.IGNORECASE)
        if match:
            updates["organization"] = match.group(1).title()
        
        return updates
    
    @staticmethod
    def extract_communication_profile(event: ProfileEvent) -> Dict[str, Any]:
        """Extract communication preferences."""
        updates = {}
        text = f"{event.user_message} {event.assistant_response}".lower()
        
        # Extract communication style
        if any(word in text for word in ["casual", "informal", "relaxed"]):
            updates["communication_style"] = "casual"
        elif any(word in text for word in ["formal", "professional", "business"]):
            updates["communication_style"] = "formal"
        elif any(word in text for word in ["friendly", "warm", "conversational"]):
            updates["communication_style"] = "friendly"
        
        # Extract tone preference
        if any(word in text for word in ["brief", "concise", "short", "quick"]):
            updates["tone_preference"] = "concise"
        elif any(word in text for word in ["detailed", "comprehensive", "thorough"]):
            updates["tone_preference"] = "detailed"
        
        # Extract response format
        if any(word in text for word in ["bullet", "list", "points"]):
            updates["response_format_preference"] = "bullet_points"
        elif any(word in text for word in ["structured", "organized", "formatted"]):
            updates["response_format_preference"] = "structured"
        elif any(word in text for word in ["conversational", "natural", "chat"]):
            updates["response_format_preference"] = "conversational"
        
        return updates
    
    @staticmethod
    def extract_ai_preference_profile(event: ProfileEvent) -> Dict[str, Any]:
        """Extract AI interaction preferences."""
        updates = {}
        text = f"{event.user_message} {event.assistant_response}".lower()
        
        # Extract autonomy level
        if any(word in text for word in ["always ask", "confirm", "check with me", "ask first"]):
            updates["autonomy_level"] = "consultative"
        elif any(word in text for word in ["just do it", "auto", "automatic", "proceed"]):
            updates["autonomy_level"] = "autonomous"
        
        # Extract preferred strategy if mentioned
        if event.strategy:
            updates["preferred_strategy"] = event.strategy
        
        return updates


class UserProfileManager:
    """
    Comprehensive user profile management system.
    Listens to conversation events and intelligently updates user profiles.
    """
    
    def __init__(self):
        self.extractors = {
            "basic": ProfileExtractor.extract_basic_profile,
            "professional": ProfileExtractor.extract_professional_profile,
            "communication": ProfileExtractor.extract_communication_profile,
            "ai_preference": ProfileExtractor.extract_ai_preference_profile,
        }
        self.event_listeners: List[Callable] = []
    
    def register_listener(self, listener: Callable):
        """Register a custom event listener."""
        self.event_listeners.append(listener)
    
    async def process_event(self, event: ProfileEvent):
        """
        Main entry point to process a conversation event.
        Extracts relevant information and updates all profile tables.
        """
        try:
            # Extract information from all profile types
            for profile_type, extractor in self.extractors.items():
                try:
                    extracted = extractor(event)
                    if extracted:
                        event.extracted_data[profile_type] = extracted
                        await self._update_profile(profile_type, event.user_id, extracted)
                except Exception as e:
                    logger.error(f"Failed to extract {profile_type} profile: {e}", exc_info=True)
            
            # Update query history and use case profiles
            await self._update_query_history(event)
            await self._update_use_case_profile(event)
            
            # Link to session if available
            if event.session_id:
                await self._link_query_to_session(event)
            
            # Call registered listeners
            for listener in self.event_listeners:
                try:
                    await listener(event)
                except Exception as e:
                    logger.error(f"Listener error: {e}", exc_info=True)
            
            logger.debug(f"Processed profile event for user {event.user_id}")
        except Exception as e:
            logger.error(f"Failed to process profile event: {e}", exc_info=True)
    
    async def _update_profile(
        self,
        profile_type: str,
        user_id: int,
        updates: Dict[str, Any]
    ):
        """Update a specific profile table."""
        table_map = {
            "basic": "user_basic_profiles",
            "professional": "user_professional_profiles",
            "communication": "user_communication_profiles",
            "ai_preference": "user_ai_preference_profiles",
        }
        
        table = table_map.get(profile_type)
        if not table:
            return
        
        await self._ensure_profile_exists(table, user_id)
        
        set_clauses = []
        values = {"user_id": user_id}
        
        for key, value in updates.items():
            set_clauses.append(f"{key} = :{key}")
            values[key] = value
        
        if not set_clauses:
            return
        
        query = f"""
        UPDATE {table}
        SET {', '.join(set_clauses)}, updated_at = CURRENT_TIMESTAMP
        WHERE user_id = :user_id
        """
        
        await database.execute(query, values)
        logger.debug(f"Updated {profile_type} profile for user {user_id}: {list(updates.keys())}")
    
    async def _update_query_history(self, event: ProfileEvent):
        """Update query history profile."""
        await self._ensure_profile_exists("user_query_history_profiles", event.user_id)
        
        query_fetch = """
        SELECT most_common_queries, query_categories, interaction_stats
        FROM user_query_history_profiles
        WHERE user_id = :user_id
        """
        current = await database.fetch_one(query_fetch, {"user_id": event.user_id})
        
        if not current:
            return
        
        # Parse JSONB fields (they may come as strings from PostgreSQL)
        from nexus.modules.database import parse_jsonb
        
        common_queries = parse_jsonb(current["most_common_queries"]) or []
        categories = parse_jsonb(current["query_categories"]) or {}
        stats = parse_jsonb(current["interaction_stats"]) or {}
        
        # Update stats
        stats["total_queries"] = stats.get("total_queries", 0) + 1
        stats["last_query_at"] = datetime.utcnow().isoformat()
        stats[f"{event.event_type}_queries"] = stats.get(f"{event.event_type}_queries", 0) + 1
        avg_length = stats.get("avg_query_length", 0)
        total = stats["total_queries"]
        stats["avg_query_length"] = ((avg_length * (total - 1)) + len(event.user_message)) / total
        
        # Update categories
        categories[event.event_type] = categories.get(event.event_type, 0) + 1
        
        # Add to common queries
        query_lower = event.user_message.lower().strip()[:200]
        found = False
        for item in common_queries:
            if item.get("query", "").lower() == query_lower:
                item["count"] = item.get("count", 0) + 1
                item["last_used"] = datetime.utcnow().isoformat()
                found = True
                break
        
        if not found:
            common_queries.append({
                "query": event.user_message[:200],
                "count": 1,
                "module": event.event_type,
                "first_used": datetime.utcnow().isoformat(),
                "last_used": datetime.utcnow().isoformat()
            })
        
        # Keep top 50
        common_queries.sort(key=lambda x: x.get("count", 0), reverse=True)
        common_queries = common_queries[:50]
        
        update_query = """
        UPDATE user_query_history_profiles
        SET most_common_queries = :queries,
            query_categories = :categories,
            interaction_stats = :stats,
            updated_at = CURRENT_TIMESTAMP
        WHERE user_id = :user_id
        """
        await database.execute(update_query, {
            "user_id": event.user_id,
            "queries": json.dumps(common_queries),
            "categories": json.dumps(categories),
            "stats": json.dumps(stats)
        })
    
    async def _update_use_case_profile(self, event: ProfileEvent):
        """Update use case profile."""
        workflow_name = event.workflow_name or (event.metadata.get("workflow_name") if event.metadata else None)
        if not workflow_name and event.event_type != "workflow":
            return
        
        await self._ensure_profile_exists("user_use_case_profiles", event.user_id)
        
        query_fetch = """
        SELECT primary_workflows, workflow_frequency
        FROM user_use_case_profiles
        WHERE user_id = :user_id
        """
        current = await database.fetch_one(query_fetch, {"user_id": event.user_id})
        
        if not current:
            return
        
        # Parse JSONB fields (they may come as strings from PostgreSQL)
        from nexus.modules.database import parse_jsonb
        
        workflows = parse_jsonb(current["primary_workflows"]) or []
        frequency = parse_jsonb(current["workflow_frequency"]) or {}
        
        if workflow_name:
            if workflow_name not in frequency:
                frequency[workflow_name] = {"count": 0, "last_used": None}
            
            frequency[workflow_name]["count"] = frequency[workflow_name].get("count", 0) + 1
            frequency[workflow_name]["last_used"] = datetime.utcnow().isoformat()
            
            found = False
            for wf in workflows:
                if wf.get("name") == workflow_name:
                    wf["count"] = frequency[workflow_name]["count"]
                    wf["last_used"] = frequency[workflow_name]["last_used"]
                    found = True
                    break
            
            if not found:
                workflows.append({
                    "name": workflow_name,
                    "count": frequency[workflow_name]["count"],
                    "last_used": frequency[workflow_name]["last_used"]
                })
            
            workflows.sort(key=lambda x: x.get("count", 0), reverse=True)
            workflows = workflows[:20]
        
        update_query = """
        UPDATE user_use_case_profiles
        SET primary_workflows = :workflows,
            workflow_frequency = :frequency,
            updated_at = CURRENT_TIMESTAMP
        WHERE user_id = :user_id
        """
        await database.execute(update_query, {
            "user_id": event.user_id,
            "workflows": json.dumps(workflows),
            "frequency": json.dumps(frequency)
        })
    
    async def _link_query_to_session(self, event: ProfileEvent):
        """Link query to session in user_query_session_links table."""
        try:
            query = """
            INSERT INTO user_query_session_links 
            (user_id, session_id, interaction_id, query_text, query_category, module, workflow_name, strategy)
            VALUES (:user_id, :session_id, :interaction_id, :query_text, :category, :module, :workflow_name, :strategy)
            ON CONFLICT (user_id, session_id, interaction_id) DO NOTHING
            """
            
            await database.execute(query, {
                "user_id": event.user_id,
                "session_id": event.session_id,
                "interaction_id": event.interaction_id,
                "query_text": event.user_message[:1000],
                "category": event.metadata.get("category") if event.metadata else None,
                "module": event.event_type,
                "workflow_name": event.workflow_name,
                "strategy": event.strategy
            })
        except Exception as e:
            logger.error(f"Failed to link query to session: {e}", exc_info=True)
    
    async def _ensure_profile_exists(self, table_name: str, user_id: int):
        """Ensure a profile record exists."""
        check_query = f"SELECT 1 FROM {table_name} WHERE user_id = :user_id"
        exists = await database.fetch_one(check_query, {"user_id": user_id})
        
        if not exists:
            insert_query = f"INSERT INTO {table_name} (user_id) VALUES (:user_id) ON CONFLICT (user_id) DO NOTHING"
            await database.execute(insert_query, {"user_id": user_id})


# Global instance
user_profile_manager = UserProfileManager()
