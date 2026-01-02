"""
Journey State Database Module

Provides a clean interface for reading/writing journey state.
Shared by both backend orchestrators and frontend API endpoints.
"""
import logging
import json
from typing import Dict, Any, Optional
from nexus.modules.database import database

logger = logging.getLogger("nexus.journey_state")


class JourneyStateManager:
    """
    Manages journey state persistence and retrieval.
    """
    
    async def get_journey_state(self, session_id: int) -> Optional[Dict[str, Any]]:
        """
        Get current journey state for a session.
        
        Returns:
            {
                "domain": str,
                "strategy": str,
                "current_step": str,
                "percent_complete": float,
                "status": str,
                "step_details": dict,
                "updated_at": str (ISO format)
            } or None if not found
        """
        query = """
            SELECT 
                domain,
                strategy,
                current_step,
                percent_complete,
                status,
                step_details,
                updated_at
            FROM journey_state
            WHERE session_id = :session_id
        """
        
        row = await database.fetch_one(query, {"session_id": session_id})
        
        if row:
            row_dict = dict(row)
            return {
                "domain": row_dict.get("domain"),
                "strategy": row_dict.get("strategy"),
                "current_step": row_dict.get("current_step"),
                "percent_complete": float(row_dict.get("percent_complete", 0.0)) if row_dict.get("percent_complete") is not None else 0.0,
                "status": row_dict.get("status"),
                "step_details": row_dict.get("step_details") or {},
                "updated_at": row_dict.get("updated_at").isoformat() if row_dict.get("updated_at") else None
            }
        
        return None
    
    async def upsert_journey_state(
        self,
        session_id: int,
        domain: Optional[str] = None,
        strategy: Optional[str] = None,
        current_step: Optional[str] = None,
        percent_complete: Optional[float] = None,
        status: Optional[str] = None,
        step_details: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Upsert journey state for a session.
        Only updates provided fields (partial updates supported).
        
        Args:
            session_id: Session ID
            domain: Domain name (optional)
            strategy: Strategy name (optional)
            current_step: Current step identifier (optional)
            percent_complete: Progress percentage 0-100 (optional)
            status: Session status (optional)
            step_details: Additional step metadata (optional)
        """
        # Build update query dynamically based on provided fields
        updates = []
        insert_fields = []
        insert_values = []
        values = {"session_id": session_id}
        
        if domain is not None:
            updates.append("domain = :domain")
            insert_fields.append("domain")
            insert_values.append(":domain")
            values["domain"] = domain
        
        if strategy is not None:
            updates.append("strategy = :strategy")
            insert_fields.append("strategy")
            insert_values.append(":strategy")
            values["strategy"] = strategy
        
        if current_step is not None:
            updates.append("current_step = :current_step")
            insert_fields.append("current_step")
            insert_values.append(":current_step")
            values["current_step"] = current_step
        
        if percent_complete is not None:
            updates.append("percent_complete = :percent_complete")
            insert_fields.append("percent_complete")
            insert_values.append(":percent_complete")
            values["percent_complete"] = percent_complete
        
        if status is not None:
            updates.append("status = :status")
            insert_fields.append("status")
            insert_values.append(":status")
            values["status"] = status
        
        if step_details is not None:
            # Use CAST instead of ::jsonb in parameter placeholder for databases library compatibility
            updates.append("step_details = CAST(:step_details AS jsonb)")
            insert_fields.append("step_details")
            insert_values.append("CAST(:step_details AS jsonb)")
            values["step_details"] = json.dumps(step_details)
        
        if not updates:
            logger.warning(f"No fields provided for journey state update for session {session_id}")
            return
        
        # Always update updated_at
        updates.append("updated_at = CURRENT_TIMESTAMP")
        
        # Build upsert query
        insert_fields_str = ", ".join(["session_id"] + insert_fields)
        insert_values_str = ", ".join([":session_id"] + insert_values)
        updates_str = ", ".join(updates)
        
        query = f"""
            INSERT INTO journey_state ({insert_fields_str})
            VALUES ({insert_values_str})
            ON CONFLICT (session_id)
            DO UPDATE SET {updates_str}
        """
        
        try:
            await database.execute(query, values)
            logger.debug(f"Journey state updated for session {session_id}")
        except Exception as e:
            logger.error(f"Failed to upsert journey state for session {session_id}: {e}", exc_info=True)
            raise
    
    async def delete_journey_state(self, session_id: int) -> None:
        """
        Delete journey state for a session (typically called when session is deleted).
        """
        query = "DELETE FROM journey_state WHERE session_id = :session_id"
        await database.execute(query, {"session_id": session_id})


# Singleton instance
journey_state_manager = JourneyStateManager()

