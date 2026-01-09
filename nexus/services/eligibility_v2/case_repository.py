"""
Case Repository - Manages eligibility_case records
"""
import logging
import uuid
from typing import Optional
from nexus.agents.eligibility_v2.models import CaseState
from nexus.modules.database import database

logger = logging.getLogger("nexus.eligibility_v2.case_repository")


class CaseRepository:
    """Repository for eligibility_case operations"""
    
    async def get_or_create_case(self, case_id: str, session_id: Optional[int] = None) -> int:
        """Get or create a case, return case_pk"""
        try:
            # Try to get existing case
            query = "SELECT id FROM eligibility_cases WHERE case_id = :case_id"
            row = await database.fetch_one(query=query, values={"case_id": case_id})
            
            if row:
                return row["id"]
            
            # Create new case with UUID
            case_uuid = str(uuid.uuid4())
            insert_query = """
                INSERT INTO eligibility_cases (case_uuid, case_id, session_id, status, case_state)
                VALUES (:case_uuid, :case_id, :session_id, 'INIT', '{}'::jsonb)
                RETURNING id
            """
            result = await database.fetch_one(
                query=insert_query,
                values={
                    "case_uuid": case_uuid,
                    "case_id": case_id,
                    "session_id": session_id
                }
            )
            return result["id"]
        except Exception as e:
            logger.error(f"Failed to get or create case: {e}")
            raise
    
    async def get_case(self, case_pk: int):
        """Get case record"""
        query = "SELECT * FROM eligibility_cases WHERE id = :pk"
        return await database.fetch_one(query=query, values={"pk": case_pk})
    
    async def get_case_state(self, case_pk: int) -> Optional[CaseState]:
        """Get case state as CaseState model"""
        query = "SELECT case_state FROM eligibility_cases WHERE id = :pk"
        row = await database.fetch_one(query=query, values={"pk": case_pk})
        if row and row["case_state"]:
            import json
            state_dict = row["case_state"] if isinstance(row["case_state"], dict) else json.loads(row["case_state"])
            return CaseState(**state_dict)
        return None
    
    async def update_case_state(self, case_pk: int, case_state: CaseState):
        """Update case state"""
        import json
        from datetime import date, datetime
        
        # Custom JSON encoder to handle date objects
        def json_serial(obj):
            """JSON serializer for objects not serializable by default json code"""
            if isinstance(obj, (date, datetime)):
                return obj.isoformat()
            raise TypeError(f"Type {type(obj)} not serializable")
        
        state_dict = case_state.model_dump()
        state_json = json.dumps(state_dict, default=json_serial)
        query = """
            UPDATE eligibility_cases 
            SET case_state = CAST(:state_json AS jsonb), updated_at = CURRENT_TIMESTAMP
            WHERE id = :pk
        """
        await database.execute(
            query=query,
            values={"pk": case_pk, "state_json": state_json}
        )
