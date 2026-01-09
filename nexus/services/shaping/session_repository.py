"""
Shaping Session Repository

Manages shaping_sessions table operations.
"""
import logging
from typing import Optional, Dict, Any
from nexus.modules.database import database

logger = logging.getLogger("nexus.shaping.session_repository")


class ShapingSessionRepository:
    """Repository for shaping_sessions operations"""
    
    async def create_simple(self, user_id: str) -> int:
        """Create a simple session with minimal initial data"""
        query = """
            INSERT INTO shaping_sessions (user_id, status, created_at, updated_at)
            VALUES (:user_id, 'GATHERING', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            RETURNING id
        """
        result = await database.fetch_one(query=query, values={"user_id": user_id})
        return result["id"]
    
    async def exists(self, session_id: int) -> bool:
        """Check if a session exists"""
        query = "SELECT EXISTS(SELECT 1 FROM shaping_sessions WHERE id = :session_id)"
        result = await database.fetch_one(query=query, values={"session_id": session_id})
        return result["exists"] if result else False
    
    async def get_transcript(self, session_id: int) -> Optional[Dict[str, Any]]:
        """Get session transcript"""
        query = "SELECT transcript FROM shaping_sessions WHERE id = :session_id"
        result = await database.fetch_one(query=query, values={"session_id": session_id})
        if result and result["transcript"]:
            import json
            transcript = result["transcript"] if isinstance(result["transcript"], dict) else json.loads(result["transcript"])
            return {"transcript": transcript}
        return None
