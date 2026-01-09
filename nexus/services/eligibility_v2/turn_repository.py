"""
Turn Repository - Manages eligibility_case_turns
"""
import logging
from typing import Optional, Dict, Any
from nexus.modules.database import database

logger = logging.getLogger("nexus.eligibility_v2.turn_repository")


class TurnRepository:
    """Repository for eligibility_case_turns operations"""
    
    async def get_latest_plan(self, case_pk: int) -> Optional[Dict[str, Any]]:
        """Get the latest plan response for a case"""
        query = """
            SELECT plan_response FROM eligibility_case_turns
            WHERE case_pk = :case_pk
            ORDER BY created_at DESC
            LIMIT 1
        """
        row = await database.fetch_one(query=query, values={"case_pk": case_pk})
        if row and row.get("plan_response"):
            import json
            plan_dict = row["plan_response"] if isinstance(row["plan_response"], dict) else json.loads(row["plan_response"])
            return plan_dict
        return None
