"""
Gate Selector

Selects the next gate to ask.
Extracted from GateEngine to separate gate selection logic.
"""

import logging
from typing import Optional

from nexus.core.gate_models import GateConfig, GateState

logger = logging.getLogger("nexus.engines.gate.gate_selector")


class GateSelector:
    """Selects the next gate to ask."""
    
    def select_next(
        self,
        gate_config: GateConfig,
        current_state: GateState,
        llm_recommendation: Optional[str] = None
    ) -> Optional[str]:
        """
        Hybrid gate selection: LLM recommendation + deterministic gate_order.
        
        Per MANDATORY_LOGIC:
        - If LLM confidence = 100% (indicated by recommendation) → use LLM recommendation
        - Otherwise → use deterministic gate_order to find first missing required gate
        - Always respect gate_order sequence
        
        Args:
            gate_config: The gate configuration
            current_state: The current gate state
            llm_recommendation: Optional LLM recommendation for next gate
            
        Returns:
            Next gate key to ask, or None if all gates complete
        """
        # Helper to check if gate is missing
        def is_gate_missing(gate_key: str) -> bool:
            gate_value = current_state.gates.get(gate_key)
            gate_def = gate_config.gates.get(gate_key)
            if not gate_def:
                return False
            # Gate is missing if required and classified is None
            if gate_def.required:
                return gate_value is None or gate_value.classified is None
            # For optional gates, missing if no value at all
            return gate_value is None
        
        # 1. Check LLM recommendation (if provided and valid)
        if llm_recommendation:
            if llm_recommendation in gate_config.gate_order:
                gate_def = gate_config.gates.get(llm_recommendation)
                if gate_def and is_gate_missing(llm_recommendation):
                    # LLM recommended a valid missing gate - use it
                    logger.debug(f"Gate selection: Using LLM recommendation: {llm_recommendation}")
                    return llm_recommendation
        
        # 2. Deterministic: find FIRST missing REQUIRED gate in gate_order
        for gate_key in gate_config.gate_order:
            gate_def = gate_config.gates.get(gate_key)
            if not gate_def:
                continue
            if gate_def.required and is_gate_missing(gate_key):
                logger.debug(f"Gate selection: Found missing required gate: {gate_key}")
                return gate_key
        
        # 3. If no required gates missing, check optional gates
        for gate_key in gate_config.gate_order:
            gate_def = gate_config.gates.get(gate_key)
            if not gate_def:
                continue
            if not gate_def.required and is_gate_missing(gate_key):
                logger.debug(f"Gate selection: Found missing optional gate: {gate_key}")
                return gate_key
        
        # All gates complete
        logger.debug("Gate selection: All gates complete")
        return None
    
    def get_question_for_gate(
        self,
        gate_key: Optional[str],
        gate_config: GateConfig
    ) -> Optional[str]:
        """
        Get the question text for a gate key.
        
        Args:
            gate_key: The gate key
            gate_config: The gate configuration
            
        Returns:
            Question text or None if gate not found
        """
        if not gate_key:
            return None
        gate_def = gate_config.gates.get(gate_key)
        if not gate_def:
            return None
        return gate_def.question.strip()




