from abc import ABC
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from nexus.core.base_tool import NexusTool
import logging

# --- The Recipe Definition ---
@dataclass
class AgentStep:
    step_id: str
    tool_name: str
    description: str
    # Map context keys to tool arguments. 
    # e.g. {"target_date": "user_date"} means use context["user_date"] as "target_date" arg.
    args_mapping: Dict[str, str] 
    transition_success: Optional[str] = None # Next step ID or None if end
    transition_fail: Optional[str] = None    # Error handler step

@dataclass
class AgentRecipe:
    name: str
    goal: str
    steps: Dict[str, AgentStep] # Keyed by step_id
    start_step_id: str

# --- The Factory Engine ---
class NexusAgentFactory:
    """
    A Generic State Machine that executes a generic AgentRecipe.
    'The Engine'.
    """
    def __init__(self, available_tools: List[NexusTool]):
        self.tool_map = {t.define_schema().name: t for t in available_tools}
        self.logger = logging.getLogger("NexusAgent")

    async def run_recipe(self, recipe: AgentRecipe, initial_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes the recipe step-by-step.
        Returns the final enriched context.
        """
        context = initial_context.copy()
        current_step_id = recipe.start_step_id
        
        self.logger.info(f"🚀 Starting Agent Recipe: {recipe.name}")
        
        while current_step_id:
            step = recipe.steps.get(current_step_id)
            if not step:
                self.logger.error(f"Step {current_step_id} not found in recipe.")
                break
                
            self.logger.info(f"▶️ Executing Step: {step.step_id} ({step.tool_name})")
            
            # 1. Resolve Tool
            tool = self.tool_map.get(step.tool_name)
            if not tool:
                raise ValueError(f"Tool {step.tool_name} not found in Factory registry.")
                
            # 2. Map Arguments
            tool_args = {}
            for arg_name, context_key in step.args_mapping.items():
                if context_key in context:
                    tool_args[arg_name] = context[context_key]
                else:
                    self.logger.warning(f"⚠️ Missing context key '{context_key}' for tool '{step.tool_name}' arg '{arg_name}'")
            
            # 3. Execute Tool
            try:
                # TODO: In future, this could be async
                result = tool.run(**tool_args)
                
                # 4. Update Context
                # We assume tools return a dict to merge, or a value to store under step_id
                if isinstance(result, dict):
                    context.update(result)
                else:
                    context[step.step_id] = result
                
                context["last_step_status"] = "success"
                current_step_id = step.transition_success
                
            except Exception as e:
                self.logger.error(f"❌ Step Failed: {e}")
                context["error"] = str(e)
                context["last_step_status"] = "error"
                current_step_id = step.transition_fail
        
        self.logger.info(f"🏁 Recipe Complete.")
        return context
