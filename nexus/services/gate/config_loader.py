"""
Gate Config Loader

Loads and validates gate configurations.
Extracted from ShapingManager to separate configuration concerns.
"""

import logging
from typing import Optional, List

from nexus.core.gate_models import GateConfig
from nexus.modules.prompt_manager import prompt_manager

logger = logging.getLogger("nexus.services.gate.config_loader")


class GateConfigLoader:
    """Loads and validates gate configurations."""
    
    async def load(
        self,
        strategy: str,
        session_id: Optional[int] = None
    ) -> Optional[GateConfig]:
        """
        Load gate config from prompt.
        
        Uses new prompt key structure: workflow:eligibility:{strategy}:gate
        - domain: hardcoded to "eligibility"
        - mode: strategy (e.g., "TABULA_RASA")
        - step: "gate" (from gate agent)
        
        Args:
            strategy: The strategy name (e.g., "TABULA_RASA")
            session_id: Optional session ID for context
            
        Returns:
            GateConfig object if found, None otherwise
        """
        prompt_data = await prompt_manager.get_prompt(
            module_name="workflow",
            domain="eligibility",  # Hardcoded for now
            mode=strategy,          # Strategy becomes mode
            step="gate",           # From gate agent
            session_id=session_id
        )
        
        if not prompt_data:
            logger.warning(f"No prompt data found for workflow:eligibility:{strategy}:gate")
            return None
        
        config = prompt_data.get("config", {})
        
        # Check if this is a gate-based prompt (has GATE_ORDER)
        if "GATE_ORDER" not in config:
            logger.warning(f"Prompt config does not have GATE_ORDER")
            return None
        
        gate_config = GateConfig.from_prompt_config(config)
        
        # Log gate config details for debugging
        logger.info(f"Loaded gate config: {len(gate_config.gates)} gates, order: {gate_config.gate_order}")
        for gate_key, gate_def in gate_config.gates.items():
            logger.info(
                f"Gate '{gate_key}': question='{gate_def.question[:50]}...', "
                f"expected_categories={gate_def.expected_categories}"
            )
        
        return gate_config
    
    async def validate(self, config: GateConfig) -> List[str]:
        """
        Validate a gate configuration.
        
        Args:
            config: The GateConfig to validate
            
        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []
        
        # Check gate_order is not empty
        if not config.gate_order:
            errors.append("GATE_ORDER is empty")
        
        # Check all gates in gate_order exist
        for gate_key in config.gate_order:
            if gate_key not in config.gates:
                errors.append(f"Gate '{gate_key}' in GATE_ORDER but not defined in GATES")
        
        # Check all gates have required fields
        for gate_key, gate_def in config.gates.items():
            if not gate_def.question:
                errors.append(f"Gate '{gate_key}' missing question")
            if gate_def.required and not gate_def.expected_categories:
                errors.append(f"Required gate '{gate_key}' missing expected_categories")
        
        # Check for duplicate gate keys
        if len(config.gates) != len(set(config.gates.keys())):
            errors.append("Duplicate gate keys found")
        
        return errors
    
    async def get_default_config(self) -> Optional[GateConfig]:
        """
        Get the default gate configuration (TABULA_RASA strategy).
        
        Returns:
            Default GateConfig or None if not found
        """
        return await self.load("TABULA_RASA")




