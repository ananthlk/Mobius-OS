"""
Dynamic Router Component

Reusable component for handling dynamic routing through structured options.
Used for gate questions, plan steps, and any hierarchical decision trees.
"""

import logging
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
from enum import Enum
from nexus.core.tree_structure_manager import TreePath, TreeNode, tree_structure_manager

logger = logging.getLogger("nexus.core.dynamic_router")

class RouterOptionType(Enum):
    """Types of router options."""
    BUTTON = "button"  # Simple button selection
    NESTED = "nested"  # Has sub-options
    INPUT = "input"  # Requires user input
    LLM_PARSE = "llm_parse"  # Requires LLM parsing

@dataclass
class RouterOption:
    """
    A single option in the router.
    """
    id: str
    label: str
    value: str
    type: RouterOptionType = RouterOptionType.BUTTON
    icon: Optional[str] = None
    description: Optional[str] = None
    tooltip: Optional[str] = None
    
    # For nested options
    sub_options: List['RouterOption'] = field(default_factory=list)
    
    # For input options
    input_type: Optional[str] = None  # "text", "number", "date", etc.
    input_placeholder: Optional[str] = None
    input_required: bool = False
    
    # For LLM parse options
    requires_llm_parsing: bool = False
    llm_parsing_prompt: Optional[str] = None
    
    # Action configuration
    action: Optional[str] = None  # "continue", "stop", "show_sub_options", "request_input"
    action_target: Optional[str] = None  # Target step or gate
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class RouterState:
    """
    Current state of the router.
    """
    current_path: TreePath
    selected_options: List[str] = field(default_factory=list)  # Selected option IDs
    input_values: Dict[str, Any] = field(default_factory=dict)  # User input values
    history: List[Dict[str, Any]] = field(default_factory=list)  # Navigation history
    
    def add_selection(self, option_id: str, value: Any = None):
        """Add a selection to the state."""
        if option_id not in self.selected_options:
            self.selected_options.append(option_id)
        if value:
            self.input_values[option_id] = value
    
    def get_selected_value(self, option_id: str) -> Optional[Any]:
        """Get the selected value for an option."""
        if option_id in self.input_values:
            return self.input_values[option_id]
        if option_id in self.selected_options:
            return option_id
        return None

class DynamicRouter:
    """
    Reusable dynamic router for navigating through structured options.
    Can be used for gates, plan steps, or any hierarchical decision tree.
    """
    
    def __init__(
        self,
        root_path: TreePath,
        options: List[RouterOption]
    ):
        self.root_path = root_path
        self.options = options
        self.state = RouterState(current_path=root_path)
        self._option_map = {opt.id: opt for opt in options}
    
    def get_current_options(self) -> List[RouterOption]:
        """
        Get current options based on state.
        If nested options are selected, show sub-options.
        """
        if not self.state.selected_options:
            return self.options
        
        # Get the last selected option
        last_selected = self.state.selected_options[-1]
        option = self._option_map.get(last_selected)
        
        if not option:
            return self.options
        
        # If it's a nested option and we should show sub-options
        if option.type == RouterOptionType.NESTED and option.sub_options:
            return option.sub_options
        
        # Otherwise return current level options
        return self.options
    
    def select_option(
        self,
        option_id: str,
        value: Any = None
    ) -> Dict[str, Any]:
        """
        Select an option and determine next action.
        
        Returns:
            {
                "action": "continue" | "stop" | "show_sub_options" | "request_input" | "llm_parse",
                "next_path": TreePath or None,
                "message": str or None,
                "options": List[RouterOption] or None
            }
        """
        option = self._option_map.get(option_id)
        if not option:
            return {
                "action": "error",
                "message": f"Option {option_id} not found"
            }
        
        # Add to state
        self.state.add_selection(option_id, value)
        
        # Record in history
        self.state.history.append({
            "option_id": option_id,
            "option_label": option.label,
            "value": value,
            "timestamp": self._get_timestamp()
        })
        
        # Determine action based on option type
        if option.action:
            action = option.action
        elif option.type == RouterOptionType.NESTED:
            action = "show_sub_options"
        elif option.type == RouterOptionType.INPUT:
            action = "request_input"
        elif option.type == RouterOptionType.LLM_PARSE or option.requires_llm_parsing:
            action = "llm_parse"
        else:
            action = "continue"
        
        # Build next path if continuing
        next_path = None
        if action == "continue" and option.action_target:
            try:
                next_path = TreePath.from_key(option.action_target)
            except ValueError:
                logger.warning(f"Invalid action_target: {option.action_target}")
        
        return {
            "action": action,
            "next_path": next_path,
            "message": option.description,
            "options": option.sub_options if action == "show_sub_options" else None,
            "option": option
        }
    
    def get_selected_path(self) -> List[str]:
        """
        Get the full path of selected options.
        Useful for building gate state or plan structure.
        """
        return self.state.selected_options.copy()
    
    def get_selected_values(self) -> Dict[str, Any]:
        """
        Get all selected values.
        """
        result = {}
        for option_id in self.state.selected_options:
            option = self._option_map.get(option_id)
            if option:
                value = self.state.get_selected_value(option_id)
                result[option_id] = {
                    "label": option.label,
                    "value": value or option.value,
                    "type": option.type.value
                }
        return result
    
    def reset(self):
        """Reset router state."""
        self.state = RouterState(current_path=self.root_path)
    
    def _get_timestamp(self) -> str:
        """Get current timestamp."""
        from datetime import datetime
        return datetime.now().isoformat()
    
    @classmethod
    def from_config(
        cls,
        root_path: TreePath,
        config: Dict[str, Any]
    ) -> 'DynamicRouter':
        """
        Create router from configuration.
        
        Config format:
        {
            "options": [
                {
                    "id": "option_1",
                    "label": "Option 1",
                    "type": "button",
                    "sub_options": [...]
                }
            ]
        }
        """
        options = []
        for opt_data in config.get("options", []):
            option = cls._parse_option(opt_data)
            options.append(option)
        
        return cls(root_path=root_path, options=options)
    
    @classmethod
    def _parse_option(cls, data: Dict[str, Any]) -> RouterOption:
        """Parse option from dictionary."""
        option = RouterOption(
            id=data["id"],
            label=data["label"],
            value=data.get("value", data["id"]),
            type=RouterOptionType(data.get("type", "button")),
            icon=data.get("icon"),
            description=data.get("description"),
            tooltip=data.get("tooltip"),
            action=data.get("action"),
            action_target=data.get("action_target"),
            requires_llm_parsing=data.get("requires_llm_parsing", False),
            metadata=data.get("metadata", {})
        )
        
        # Parse sub-options
        if "sub_options" in data:
            option.sub_options = [cls._parse_option(sub) for sub in data["sub_options"]]
            option.type = RouterOptionType.NESTED
        
        # Parse input config
        if "input_type" in data:
            option.input_type = data["input_type"]
            option.input_placeholder = data.get("input_placeholder")
            option.input_required = data.get("input_required", False)
            option.type = RouterOptionType.INPUT
        
        return option




