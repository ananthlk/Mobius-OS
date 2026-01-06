"""
Gate Completion Checker

Determines if all gates are complete.
Extracted from GateEngine to separate completion validation logic.
"""

import logging
from typing import Tuple, List

from nexus.core.gate_models import GateConfig, GateState, GateDecision

logger = logging.getLogger("nexus.engines.gate.completion_checker")


class GateCompletionChecker:
    """Determines if all gates are complete."""
    
    def check(
        self,
        gate_config: GateConfig,
        current_state: GateState,
        user_override: bool = False
    ) -> Tuple[bool, GateDecision]:
        """
        Check completion status using hierarchy:
        1. User override (highest)
        2. All required gates met
        3. Fail (some required gates missing)
        
        Per MANDATORY_LOGIC step 7: "If no required gates are missing, set status.pass=true"
        
        Args:
            gate_config: The gate configuration
            current_state: The current gate state
            user_override: Whether user explicitly overrode completion
            
        Returns:
            Tuple of (is_complete: bool, decision: GateDecision)
        """
        if user_override:
            logger.debug("Completion check: User override detected")
            return (True, GateDecision.PASS_OVERRIDE)
        
        # Check required gates
        missing_gates = []
        for gate_key in gate_config.gate_order:
            gate_def = gate_config.gates.get(gate_key)
            if not gate_def or not gate_def.required:
                continue
            
            gate_value = current_state.gates.get(gate_key)
            # Gate is missing if classified is None
            if gate_value is None or gate_value.classified is None:
                missing_gates.append(gate_key)
        
        if missing_gates:
            logger.debug(f"Completion check: Missing required gates: {missing_gates}")
            return (False, GateDecision.FAIL_REQUIRED_MISSING)
        
        # All required gates have classified values
        logger.info(f"Completion check: All {len(gate_config.gate_order)} gates complete")
        return (True, GateDecision.PASS_REQUIRED_GATES)
    
    def get_missing_gates(
        self,
        gate_config: GateConfig,
        current_state: GateState
    ) -> List[str]:
        """
        Get list of missing required gates.
        
        Args:
            gate_config: The gate configuration
            current_state: The current gate state
            
        Returns:
            List of gate keys that are missing
        """
        missing = []
        for gate_key in gate_config.gate_order:
            gate_def = gate_config.gates.get(gate_key)
            if not gate_def or not gate_def.required:
                continue
            
            gate_value = current_state.gates.get(gate_key)
            if gate_value is None or gate_value.classified is None:
                missing.append(gate_key)
        
        return missing
    
    def detect_user_override(self, user_text: str) -> bool:
        """
        Detect if user explicitly overrides (says "skip", "move on", etc.).
        
        Args:
            user_text: The user's input text
            
        Returns:
            True if override detected, False otherwise
        """
        override_phrases = [
            "skip", "move on", "next", "continue", "proceed",
            "that's fine", "good enough", "let's go"
        ]
        user_lower = user_text.lower()
        return any(phrase in user_lower for phrase in override_phrases)


