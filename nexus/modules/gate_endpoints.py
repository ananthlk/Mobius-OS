"""
Gate API Endpoints

API endpoints for managing gate state in shaping sessions.
Supports:
- GET gate state
- POST override (user override to mark gate as complete)
- POST clear (clear gate value)
"""

import logging
import json
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional
from nexus.modules.database import database
from nexus.core.gate_models import GateState, GateValue, StatusInfo, GateConfig
from nexus.core.gate_models import GateJsonParser
from nexus.brains.gate_engine import GateEngine
from nexus.modules.prompt_manager import prompt_manager

logger = logging.getLogger("nexus.gates")

router = APIRouter(prefix="/api/workflows/gates", tags=["gates"])

# Initialize gate engine
gate_engine = GateEngine()
gate_parser = GateJsonParser()


# --- Pydantic Schemas ---

class GateOverrideRequest(BaseModel):
    """Request to override a gate (mark as complete)."""
    gate_key: str
    reason: Optional[str] = None


class GateClearRequest(BaseModel):
    """Request to clear a gate value."""
    gate_key: str


class GateStateResponse(BaseModel):
    """Response with gate state."""
    session_id: int
    gate_state: Dict[str, Any]
    gate_config: Optional[Dict[str, Any]] = None


# --- Helper Functions ---

async def _load_gate_state(session_id: int) -> Optional[GateState]:
    """
    Load gate state from database.
    
    Returns:
        GateState if found, None otherwise
    """
    query = """
        SELECT gate_state, consultant_strategy
        FROM shaping_sessions
        WHERE id = :session_id
    """
    row = await database.fetch_one(query, {"session_id": session_id})
    
    if not row:
        return None
    
    gate_state_data = row.get("gate_state")
    if not gate_state_data:
        return None
    
    # Parse JSONB to dict
    if isinstance(gate_state_data, str):
        gate_state_data = json.loads(gate_state_data)
    
    # Convert to GateState object
    # Note: This is a simplified conversion - in production, use proper deserialization
    gates = {}
    for gate_key, gate_value_data in gate_state_data.get("gates", {}).items():
        gates[gate_key] = GateValue(
            raw=gate_value_data.get("raw"),
            classified=gate_value_data.get("classified"),
            confidence=gate_value_data.get("confidence"),
            collected_at=None  # Would need to parse datetime if stored
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


async def _save_gate_state(session_id: int, gate_state: GateState) -> None:
    """
    Save gate state to database.
    """
    # Convert GateState to dict
    gate_state_dict = {
        "summary": gate_state.summary,
        "gates": {
            gate_key: {
                "raw": gate_value.raw,
                "classified": gate_value.classified,
                "confidence": gate_value.confidence
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
        SET gate_state = :gate_state::jsonb,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = :session_id
    """
    await database.execute(
        query,
        {
            "session_id": session_id,
            "gate_state": json.dumps(gate_state_dict)
        }
    )


async def _load_gate_config(session_id: int) -> Optional[GateConfig]:
    """
    Load gate config from prompt for the session.
    
    Returns:
        GateConfig if found, None otherwise
    """
    # Get strategy from session
    query = """
        SELECT consultant_strategy
        FROM shaping_sessions
        WHERE id = :session_id
    """
    row = await database.fetch_one(query, {"session_id": session_id})
    
    if not row:
        return None
    
    strategy = row.get("consultant_strategy") or "TABULA_RASA"
    
    # Load prompt config
    # Uses new prompt key structure: workflow:eligibility:{strategy}:gate
    prompt_data = await prompt_manager.get_prompt(
        module_name="workflow",
        domain="eligibility",  # Hardcoded for now
        mode=strategy,          # Strategy becomes mode
        step="gate"            # From gate agent
    )
    
    if not prompt_data:
        return None
    
    config = prompt_data.get("config", {})
    
    # Check if this is a gate-based prompt (has GATE_ORDER)
    if "GATE_ORDER" not in config:
        return None
    
    # Convert to GateConfig
    return GateConfig.from_prompt_config(config)


# --- API Endpoints ---

@router.get("/{session_id}", response_model=GateStateResponse)
async def get_gate_state(session_id: int):
    """
    Get current gate state for a session.
    
    Returns:
        GateStateResponse with gate state and optional gate config
    """
    try:
        gate_state = await _load_gate_state(session_id)
        
        if not gate_state:
            # Return empty state
            gate_state = GateState(
                summary="",
                gates={},
                status=StatusInfo(pass_=False, next_gate=None, next_query=None)
            )
        
        # Convert to dict for response
        gate_state_dict = {
            "summary": gate_state.summary,
            "gates": {
                gate_key: {
                    "raw": gate_value.raw,
                    "classified": gate_value.classified,
                    "confidence": gate_value.confidence
                }
                for gate_key, gate_value in gate_state.gates.items()
            },
            "status": {
                "pass": gate_state.status.pass_,
                "next_gate": gate_state.status.next_gate,
                "next_query": gate_state.status.next_query
            }
        }
        
        # Try to load gate config
        gate_config = await _load_gate_config(session_id)
        gate_config_dict = None
        if gate_config:
            gate_config_dict = {
                "gate_order": gate_config.gate_order,
                "gates": {
                    gate_key: {
                        "question": gate_def.question,
                        "required": gate_def.required,
                        "expected_categories": gate_def.expected_categories
                    }
                    for gate_key, gate_def in gate_config.gates.items()
                }
            }
        
        return GateStateResponse(
            session_id=session_id,
            gate_state=gate_state_dict,
            gate_config=gate_config_dict
        )
    
    except Exception as e:
        logger.error(f"Failed to get gate state for session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{session_id}/override")
async def override_gate(session_id: int, req: GateOverrideRequest):
    """
    User override: mark a gate as complete even if not fully answered.
    
    This sets the gate's classified value to a special "OVERRIDE" marker
    and updates the gate state.
    """
    try:
        # Load current state
        gate_state = await _load_gate_state(session_id)
        if not gate_state:
            gate_state = GateState(
                summary="",
                gates={},
                status=StatusInfo(pass_=False, next_gate=None, next_query=None)
            )
        
        # Load gate config
        gate_config = await _load_gate_config(session_id)
        if not gate_config:
            raise HTTPException(
                status_code=404,
                detail="Gate config not found for this session"
            )
        
        # Validate gate key
        if req.gate_key not in gate_config.gates:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid gate key: {req.gate_key}"
            )
        
        # Set gate value with override marker
        gate_state.gates[req.gate_key] = GateValue(
            raw=gate_state.gates.get(req.gate_key, GateValue()).raw or "USER_OVERRIDE",
            classified="OVERRIDE",  # Special marker
            confidence=1.0,
            collected_at=None
        )
        
        # Recompute status (check completion)
        from nexus.brains.gate_engine import GateEngine
        engine = GateEngine()
        completion_result = engine._check_completion(
            gate_config=gate_config,
            current_state=gate_state,
            user_override=True  # User explicitly overrode
        )
        
        # Update status
        gate_state.status = StatusInfo(
            pass_=completion_result[0],
            next_gate=gate_state.status.next_gate,
            next_query=gate_state.status.next_query
        )
        
        # Save state
        await _save_gate_state(session_id, gate_state)
        
        return {
            "status": "success",
            "message": f"Gate {req.gate_key} overridden",
            "gate_state": {
                "summary": gate_state.summary,
                "gates": {
                    gate_key: {
                        "raw": gate_value.raw,
                        "classified": gate_value.classified
                    }
                    for gate_key, gate_value in gate_state.gates.items()
                },
                "status": {
                    "pass": gate_state.status.pass_,
                    "next_gate": gate_state.status.next_gate,
                    "next_query": gate_state.status.next_query
                }
            }
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to override gate for session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{session_id}/clear")
async def clear_gate(session_id: int, req: GateClearRequest):
    """
    Clear a gate value (remove the answer).
    
    This removes the gate from the state, allowing it to be asked again.
    """
    try:
        # Load current state
        gate_state = await _load_gate_state(session_id)
        if not gate_state:
            raise HTTPException(
                status_code=404,
                detail="Gate state not found for this session"
            )
        
        # Load gate config
        gate_config = await _load_gate_config(session_id)
        if not gate_config:
            raise HTTPException(
                status_code=404,
                detail="Gate config not found for this session"
            )
        
        # Check policy
        if not gate_config.policy.allow_user_clear_values:
            raise HTTPException(
                status_code=403,
                detail="Clearing gate values is not allowed for this session"
            )
        
        # Remove gate value
        if req.gate_key in gate_state.gates:
            del gate_state.gates[req.gate_key]
        
        # Recompute next gate
        from nexus.brains.gate_engine import GateEngine
        engine = GateEngine()
        next_gate_key = engine._select_next_gate(
            gate_config=gate_config,
            current_state=gate_state,
            llm_recommendation=None
        )
        
        # Update status
        gate_state.status = StatusInfo(
            pass_=gate_state.status.pass_,
            next_gate=next_gate_key,
            next_query=engine._get_question_for_gate(next_gate_key, gate_config) if next_gate_key else None
        )
        
        # Save state
        await _save_gate_state(session_id, gate_state)
        
        return {
            "status": "success",
            "message": f"Gate {req.gate_key} cleared",
            "gate_state": {
                "summary": gate_state.summary,
                "gates": {
                    gate_key: {
                        "raw": gate_value.raw,
                        "classified": gate_value.classified
                    }
                    for gate_key, gate_value in gate_state.gates.items()
                },
                "status": {
                    "pass": gate_state.status.pass_,
                    "next_gate": gate_state.status.next_gate,
                    "next_query": gate_state.status.next_query
                }
            }
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to clear gate for session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

