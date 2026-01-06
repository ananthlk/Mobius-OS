"""
Gate State Merger

Merges new gate values into existing state.
Extracted from GateEngine to separate state management logic.
"""

import logging
from typing import Optional
from datetime import datetime

from nexus.core.gate_models import GateConfig, GateState, GateValue, StatusInfo

logger = logging.getLogger("nexus.engines.gate.state_merger")


class GateStateMerger:
    """Merges new gate values into existing state."""
    
    def merge(
        self,
        previous_state: Optional[GateState],
        parsed_state: GateState,
        gate_config: GateConfig,
        user_text: str
    ) -> GateState:
        """
        Merge parsed state with previous state.
        
        Rules:
        - Start from previous_state if present
        - Only update gates that were explicitly answered
        - Preserve all existing values unless explicitly changed
        
        Args:
            previous_state: Previous gate state (if any)
            parsed_state: New state parsed from LLM response
            gate_config: The gate configuration
            user_text: The user's input text (for context)
            
        Returns:
            Merged GateState
        """
        # Start with previous state (preserve all existing values)
        if previous_state:
            merged = GateState(
                summary=previous_state.summary,
                gates={gate_key: GateValue(
                    raw=gate_value.raw,
                    classified=gate_value.classified,
                    confidence=gate_value.confidence,
                    collected_at=gate_value.collected_at
                ) for gate_key, gate_value in previous_state.gates.items()},
                status=previous_state.status
            )
        else:
            merged = GateState(
                summary="",
                gates={},
                status=StatusInfo(pass_=False, next_gate=None, next_query=None)
            )
        
        # Update summary if parsed state has a new one
        if parsed_state.summary and parsed_state.summary.strip():
            merged.summary = parsed_state.summary.strip()[:2000]  # Enforce 2000 char limit
            logger.debug("State merge: Updated summary")
        
        # Update gates that were explicitly answered (have raw values in parsed_state)
        updated_gates = []
        for gate_key in gate_config.gate_order:
            parsed_gate_value = parsed_state.gates.get(gate_key)
            if not parsed_gate_value:
                continue
            
            # Only update if raw value is present (user explicitly answered)
            if parsed_gate_value.raw:
                merged.gates[gate_key] = GateValue(
                    raw=parsed_gate_value.raw,
                    classified=parsed_gate_value.classified,
                    confidence=parsed_gate_value.confidence,
                    collected_at=datetime.now()
                )
                updated_gates.append(gate_key)
            # Also handle explicit clearing (raw is None but gate exists in parsed_state)
            elif gate_key in parsed_state.gates and parsed_gate_value.raw is None:
                # Check if user explicitly cleared (would need more sophisticated detection)
                # For now, only update if classified is also None (clear signal)
                if parsed_gate_value.classified is None:
                    # User cleared - remove gate value
                    if gate_key in merged.gates:
                        del merged.gates[gate_key]
                        updated_gates.append(gate_key)
        
        if updated_gates:
            logger.debug(f"State merge: Updated gates: {updated_gates}")
        
        return merged


