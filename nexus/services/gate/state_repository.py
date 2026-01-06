"""
Gate State Repository

Handles all gate state persistence operations.
Extracted from ShapingManager to separate persistence concerns.
"""

import json
import logging
from typing import Optional
from datetime import datetime

from nexus.core.gate_models import GateState, GateValue, StatusInfo
from nexus.modules.database import database

logger = logging.getLogger("nexus.services.gate.state_repository")


class GateStateRepository:
    """Handles all gate state persistence operations."""
    
    async def load(self, session_id: int) -> Optional[GateState]:
        """
        Load gate state from database.
        
        Args:
            session_id: The session ID to load state for
            
        Returns:
            GateState object if found, None otherwise
        """
        query = "SELECT gate_state FROM shaping_sessions WHERE id = :session_id"
        row = await database.fetch_one(query, {"session_id": session_id})
        
        if not row or "gate_state" not in row or not row["gate_state"]:
            return None
        
        gate_state_data = row["gate_state"]
        
        # Parse JSONB if it's a string (PostgreSQL returns JSONB as dict, but handle string case)
        if isinstance(gate_state_data, str):
            try:
                gate_state_data = json.loads(gate_state_data)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse gate_state JSON for session {session_id}: {e}")
                return None
        
        # Convert to GateState object
        gates = {}
        for gate_key, gate_value_data in gate_state_data.get("gates", {}).items():
            collected_at = None
            if gate_value_data.get("collected_at"):
                try:
                    if isinstance(gate_value_data["collected_at"], str):
                        collected_at = datetime.fromisoformat(gate_value_data["collected_at"])
                    else:
                        collected_at = gate_value_data["collected_at"]
                except (ValueError, TypeError):
                    pass
            
            gates[gate_key] = GateValue(
                raw=gate_value_data.get("raw"),
                classified=gate_value_data.get("classified"),
                confidence=gate_value_data.get("confidence"),
                collected_at=collected_at
            )
        
        status_data = gate_state_data.get("status", {})
        status = StatusInfo(
            pass_=status_data.get("pass", False),
            next_gate=status_data.get("next_gate"),
            next_query=status_data.get("next_query")
        )
        
        return GateState(
            summary=gate_state_data.get("summary", ""),
            gates=gates,
            status=status
        )
    
    async def save(self, session_id: int, gate_state: GateState) -> None:
        """
        Save gate state to database.
        
        Args:
            session_id: The session ID to save state for
            gate_state: The GateState object to save
        """
        gate_state_dict = {
            "summary": gate_state.summary,
            "gates": {
                gate_key: {
                    "raw": gate_value.raw,
                    "classified": gate_value.classified,
                    "confidence": gate_value.confidence,
                    "collected_at": gate_value.collected_at.isoformat() if gate_value.collected_at else None
                }
                for gate_key, gate_value in gate_state.gates.items()
            },
            "status": {
                "pass": gate_state.status.pass_,
                "next_gate": gate_state.status.next_gate,
                "next_query": gate_state.status.next_query
            }
        }
        
        query = """
            UPDATE shaping_sessions 
            SET gate_state = :gate_state, updated_at = CURRENT_TIMESTAMP 
            WHERE id = :session_id
        """
        await database.execute(
            query,
            {
                "gate_state": json.dumps(gate_state_dict),
                "session_id": session_id
            }
        )
        logger.debug(f"Saved gate state for session {session_id}")
    
    async def exists(self, session_id: int) -> bool:
        """
        Check if gate state exists for a session.
        
        Args:
            session_id: The session ID to check
            
        Returns:
            True if state exists, False otherwise
        """
        query = "SELECT gate_state FROM shaping_sessions WHERE id = :session_id"
        row = await database.fetch_one(query, {"session_id": session_id})
        return row is not None and row.get("gate_state") is not None
    
    async def delete(self, session_id: int) -> None:
        """
        Delete gate state for a session.
        
        Args:
            session_id: The session ID to delete state for
        """
        query = """
            UPDATE shaping_sessions 
            SET gate_state = NULL, updated_at = CURRENT_TIMESTAMP 
            WHERE id = :session_id
        """
        await database.execute(query, {"session_id": session_id})
        logger.debug(f"Deleted gate state for session {session_id}")


