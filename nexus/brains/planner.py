import logging
import json
from typing import List, Dict, Any, Optional, Tuple
from nexus.core.memory_logger import MemoryLogger
from nexus.core.gate_models import GateState, GateConfig
from nexus.core.base_tool import NexusTool

# logger = logging.getLogger("nexus.planner") # Replaced by MemoryLogger


class PlannerBrain:
    """
    The 'Engineer'. Responsible for the Left Rail (Draft Plan).
    Continuously listens to the transcript and updates the structure.
    """
    
    def __init__(self):
        self.mem = MemoryLogger("nexus.planner")
    
    async def _get_available_tools(self) -> List[NexusTool]:
        """Get list of available tools from tool library database."""
        from nexus.tools.library.registry import tool_registry
        from nexus.tools.library.loader import ToolLoader
        
        # Get tools from database
        db_tools = await tool_registry.get_all_active_tools()
        
        # Load tool instances
        loader = ToolLoader()
        loaded_tools = []
        for tool_data in db_tools:
            tool_instance = loader.load_tool(tool_data)
            if tool_instance:
                loaded_tools.append(tool_instance)
        
        # Also include hardcoded tools for backward compatibility
        from nexus.modules.workflow_endpoints import AVAILABLE_TOOLS
        loaded_tools.extend(AVAILABLE_TOOLS)
        
        return loaded_tools
    
    async def _match_tool(self, tool_hint: str, available_tools: List[NexusTool]) -> Dict[str, Any]:
        """
        Match tool_hint against available tools.
        Returns: {"tool_matched": bool, "tool_name": Optional[str]}
        """
        if not tool_hint:
            return {"tool_matched": False, "tool_name": None}
        
        tool_hint_lower = tool_hint.lower().strip()
        
        # Try exact match first
        for tool in available_tools:
            schema = tool.define_schema()
            if schema.name.lower() == tool_hint_lower:
                return {"tool_matched": True, "tool_name": schema.name}
        
        # Try partial match (tool_hint contains tool name or vice versa)
        for tool in available_tools:
            schema = tool.define_schema()
            tool_name_lower = schema.name.lower()
            if tool_hint_lower in tool_name_lower or tool_name_lower in tool_hint_lower:
                return {"tool_matched": True, "tool_name": schema.name}
        
        # Try matching against description keywords
        for tool in available_tools:
            schema = tool.define_schema()
            desc_lower = schema.description.lower()
            # Check if key words from tool_hint appear in description
            hint_words = tool_hint_lower.split('_')
            if any(word in desc_lower for word in hint_words if len(word) > 3):
                return {"tool_matched": True, "tool_name": schema.name}
        
        return {"tool_matched": False, "tool_name": None}
    
    def _detect_human_review(self, description: str, tool_name: Optional[str] = None) -> bool:
        """
        Detect if step requires human review.
        Returns: True if requires human review, False otherwise.
        """
        if not description:
            return False
        
        desc_lower = description.lower()
        
        # Pattern matching for human review keywords
        review_keywords = [
            "review", "approve", "verify", "confirm", "validate",
            "check", "inspect", "audit", "examine", "assess",
            "judgment", "decision", "manual", "human"
        ]
        
        if any(keyword in desc_lower for keyword in review_keywords):
            return True
        
        return False
    
    def _detect_batch(self, description: str, tool_name: Optional[str] = None) -> bool:
        """
        Detect if step is batch (not real-time).
        Returns: True if batch, False if real-time.
        """
        if not description:
            return False
        
        desc_lower = description.lower()
        
        # Batch keywords
        batch_keywords = [
            "batch", "scheduled", "overnight", "bulk", "async",
            "queued", "background", "offline", "periodic"
        ]
        
        # Real-time keywords
        realtime_keywords = [
            "real-time", "realtime", "immediate", "instant", "live",
            "synchronous", "sync", "now", "urgent", "interactive"
        ]
        
        # Check for real-time first (more specific)
        if any(keyword in desc_lower for keyword in realtime_keywords):
            return False
        
        # Check for batch
        if any(keyword in desc_lower for keyword in batch_keywords):
            return True
        
        # Default to real-time if unclear
        return False
    
    async def _process_step(self, step: Dict[str, Any], available_tools: List[NexusTool]) -> None:
        """Process a single step for tool matching and indicators."""
        if not isinstance(step, dict):
            return
        
        tool_hint = step.get("tool_hint", "")
        
        # Check if human intervention
        if tool_hint.lower() in ["human_intervention", "manual_review", "human_review", "manual_task"]:
            step["tool_matched"] = False
            step["tool_name"] = None
            step["requires_human_review"] = True
            self.mem.debug(f"[PLANNER] Step {step.get('id')} marked as human intervention")
            return
        
        # Regular tool matching
        tool_match_result = await self._match_tool(tool_hint, available_tools)
        step["tool_matched"] = tool_match_result["tool_matched"]
        
        if tool_match_result["tool_matched"]:
            step["tool_name"] = tool_match_result["tool_name"]
            
            # Get execution conditions from tool library
            try:
                from nexus.tools.library.registry import tool_registry
                tool_data = await tool_registry.get_tool_by_name(tool_match_result["tool_name"])
                if tool_data and tool_data.get("execution_conditions"):
                    step["execution_conditions"] = tool_data["execution_conditions"]
            except Exception as e:
                self.mem.debug(f"Could not load execution conditions for {tool_match_result['tool_name']}: {e}")
        else:
            step["tool_name"] = None
            # If tool not matched and not explicitly human_intervention, mark for human review
            if not step.get("requires_human_review"):
                step["requires_human_review"] = True
                self.mem.debug(f"[PLANNER] Step {step.get('id')} has no matching tool, marked for human review")
        
        # Human review and batch detection
        description = step.get("description", "")
        if not step.get("requires_human_review"):
            step["requires_human_review"] = self._detect_human_review(description, step.get("tool_name"))
        step["is_batch"] = self._detect_batch(description, step.get("tool_name"))

    async def update_draft(self, transcript: List[Dict[str, Any]], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Deterministic plan generation from templates or gate state.
        NO LLM calls - purely template-based and deterministic.
        """
        self.mem.log_thinking(f"[PLANNER] update_draft | Deterministic mode | Transcript Size: {len(transcript)} msgs")
        
        # Extract gate_state from context
        gate_state = context.get("gate_state")
        if not gate_state:
            self.mem.log_thinking("[PLANNER] No gate_state in context, returning empty plan")
            return {
                "problem_statement": "",
                "name": "Workflow Plan",
                "goal": "",
                "phases": []
            }
        
        # Normalize gate_state if it's a dict
        if isinstance(gate_state, dict):
            from nexus.core.gate_models import GateState, GateValue, StatusInfo
            gates_dict = {}
            for key, value in gate_state.get("gates", {}).items():
                if isinstance(value, dict):
                    gates_dict[key] = GateValue(
                        raw=value.get("raw"),
                        classified=value.get("classified"),
                        confidence=value.get("confidence")
                    )
            gate_state = GateState(
                summary=gate_state.get("summary", ""),
                gates=gates_dict,
                status=StatusInfo(
                    pass_=gate_state.get("status", {}).get("pass", False),
                    next_gate=gate_state.get("status", {}).get("next_gate"),
                    next_query=gate_state.get("status", {}).get("next_query")
                )
            )
        
        # Prioritize explicit problem_statement from context (from confirmation summary)
        # Otherwise use gate_state.summary
        problem_statement = context.get("problem_statement") or gate_state.summary or ""
        
        # Log the problem statement for debugging
        if problem_statement:
            source = "context (confirmation summary)" if context.get("problem_statement") else "gate_state.summary"
            self.mem.log_thinking(f"[PLANNER] Using problem_statement from {source}: {problem_statement[:150]}...")
        else:
            self.mem.log_thinking("[PLANNER] No problem_statement found")
        
        # Get available tools for matching
        available_tools = await self._get_available_tools()
        
        # Get session_id from context
        session_id = context.get("session_id")
        
        # CONTRACT: Planner ONLY uses templates passed from Gate Agent via context.
        # Planner does NOT retrieve templates itself - that is the Gate Agent's responsibility.
        from nexus.core.plan_extractor import plan_extractor
        
        # Build tree path for plan extractor (needed for metadata in both template and deterministic paths)
        from nexus.core.tree_structure_manager import TreePath
        domain = context.get("domain", "eligibility")
        mode = context.get("strategy", "TABULA_RASA")
        path = TreePath(
            module="workflow",
            domain=domain,
            strategy=mode,
            step="template"
        )
        
        template = context.get("template")
        if template:
            self.mem.log_thinking(f"[PLANNER] Using template from Gate Agent: {template.get('template_key', 'unknown')}")
        else:
            self.mem.log_thinking("[PLANNER] No template provided by Gate Agent, using deterministic plan extractor")
        
        # 2. Generate plan deterministically
        try:
            if template:
                # Extract plan from template
                template_config = template.get("template_config", {})
                workflow_plan = plan_extractor.extract_plan_from_template(
                    template_config=template_config,
                    gate_state=gate_state,
                    path=path
                )
            else:
                # Generate plan directly from gate state (deterministic)
                workflow_plan = plan_extractor.extract_plan_from_gate_state(
                    gate_state=gate_state,
                    path=path
                )
            
            # Convert WorkflowPlan to dict format with GATES (not phases)
            # CHANGED: 2-stage document - draft_plan is source of truth with gates mapped 1:1 from gate_state
            draft_plan = {
                "problem_statement": workflow_plan.problem_statement or problem_statement,
                "name": workflow_plan.name or "Eligibility Verification Workflow",
                "goal": workflow_plan.goal or "",
                "gates": []  # Changed from "phases" to "gates"
            }
            
            # Get gate_config from context for gate metadata
            gate_config = context.get("gate_config")
            
            # Map gates 1:1 from gate_state (if available)
            if gate_state and gate_state.gates:
                # Sort gates by their numeric prefix (1, 2, 3, 4, 5)
                sorted_gates = sorted(
                    gate_state.gates.items(),
                    key=lambda x: int(x[0].split("_")[0]) if x[0].split("_")[0].isdigit() else 999
                )
                
                # Create a map of workflow_plan phases by gate_key
                # Phases from plan_extractor now have IDs matching gate structure (gate_1, gate_2, etc.)
                phases_by_gate_key = {}
                for phase in workflow_plan.phases:
                    # Phase ID should match gate structure (e.g., "gate_1", "gate_2")
                    # Extract gate number from phase ID
                    if phase.id.startswith("gate_"):
                        gate_num = phase.id.replace("gate_", "")
                        # Find matching gate_key by number
                        for gate_key in gate_state.gates.keys():
                            if gate_key.split("_")[0] == gate_num:
                                phases_by_gate_key[gate_key] = phase
                                break
                
                # Get template gates structure if available (for metadata)
                template_gates = {}
                if template:
                    template_config = template.get("template_config", {})
                    for gate_data in template_config.get("gates", []):
                        gate_key = gate_data.get("gate_key")
                        if gate_key:
                            template_gates[gate_key] = gate_data
                
                for gate_key, gate_value in sorted_gates:
                    gate_num = gate_key.split("_")[0]  # "1", "2", "3", etc.
                    
                    # Get gate question and name from gate_config
                    gate_question = gate_key
                    gate_name = gate_key
                    if gate_config and gate_key in gate_config.gates:
                        gate_def = gate_config.gates[gate_key]
                        gate_question = gate_def.question
                        # Extract a shorter name from question (first 60 chars)
                        gate_name = gate_question[:60] + "..." if len(gate_question) > 60 else gate_question
                    
                    # Find corresponding phase from workflow_plan (already pruned by plan_extractor)
                    matching_phase = phases_by_gate_key.get(gate_key)
                    
                    # Create gate object with embedded gate metadata
                    gate_dict = {
                        "id": f"gate_{gate_num}",
                        "name": gate_name,
                        "description": gate_question,
                        "gate_key": gate_key,
                        "gate_question": gate_question,
                        "gate_value": gate_value.classified or gate_value.raw or "",
                        "gate_data": {
                            "raw": gate_value.raw,
                            "classified": gate_value.classified,
                            "confidence": gate_value.confidence
                        },
                        "steps": []
                    }
                    
                    # Add steps from pruned phase (already filtered by sub_level selection)
                    if matching_phase:
                        for i, step in enumerate(matching_phase.steps, start=1):
                            # Ensure task exists in catalog before adding to draft_plan
                            task_ref = await self._ensure_task_in_catalog(
                                step.description,
                                context={
                                    "domain": context.get("domain", "eligibility"),
                                    "strategy": context.get("strategy", "TABULA_RASA"),
                                    "gate_key": gate_key,
                                    "user_id": context.get("user_id")
                                }
                            )
                            
                            step_dict = {
                                "id": f"step_{gate_num}.{i}",  # Hierarchical: step_1.1, step_1.2, step_2.1, etc.
                                "task_id": task_ref["task_id"],  # UUID - primary reference for integrity
                                "task_key": task_ref["task_key"],  # Optional: keep for human readability
                                "description": step.description,
                                "tool_hint": step.tool_hint or None
                            }
                            gate_dict["steps"].append(step_dict)
                    else:
                        # If no matching phase (gate not answered or no template), create placeholder
                        if gate_value.classified:
                            step_description = f"Extract gate requirement: {gate_value.classified or gate_value.raw or 'Pending'}"
                            task_ref = await self._ensure_task_in_catalog(
                                step_description,
                                context={
                                    "domain": context.get("domain", "eligibility"),
                                    "strategy": context.get("strategy", "TABULA_RASA"),
                                    "gate_key": gate_key,
                                    "user_id": context.get("user_id")
                                }
                            )
                            
                            gate_dict["steps"].append({
                                "id": f"step_{gate_num}.1",
                                "task_id": task_ref["task_id"],  # UUID - primary reference for integrity
                                "task_key": task_ref["task_key"],  # Optional: keep for human readability
                                "description": step_description,
                                "gate_data": {
                                    "raw": gate_value.raw,
                                    "classified": gate_value.classified,
                                    "confidence": gate_value.confidence
                                }
                            })
                    
                    draft_plan["gates"].append(gate_dict)
            else:
                # Fallback: Convert template phases to gates if no gate_state
                for i, phase in enumerate(workflow_plan.phases, start=1):
                    gate_dict = {
                        "id": f"gate_{i}",
                        "name": phase.name,
                        "description": phase.description or "",
                        "gate_key": None,
                        "gate_question": None,
                        "gate_value": None,
                        "gate_data": None,
                        "steps": []
                    }
                    
                    # Convert steps with hierarchical numbering
                    for j, step in enumerate(phase.steps, start=1):
                        # Ensure task exists in catalog before adding to draft_plan
                        task_ref = await self._ensure_task_in_catalog(
                            step.description,
                            context={
                                "domain": context.get("domain", "eligibility"),
                                "strategy": context.get("strategy", "TABULA_RASA"),
                                "user_id": context.get("user_id")
                            }
                        )
                        
                        step_dict = {
                            "id": f"step_{i}.{j}",  # Hierarchical: step_1.1, step_1.2, etc.
                            "task_id": task_ref["task_id"],  # UUID - primary reference for integrity
                            "task_key": task_ref["task_key"],  # Optional: keep for human readability
                            "description": step.description,
                            "tool_hint": step.tool_hint or None
                        }
                        gate_dict["steps"].append(step_dict)
                    
                    draft_plan["gates"].append(gate_dict)
            
            self.mem.log_thinking(f"[PLANNER] Generated plan: {len(draft_plan['gates'])} gates with {sum(len(g.get('steps', [])) for g in draft_plan['gates'])} total steps")
            
            # 3. Post-process gates and steps: tool matching and indicator detection
            if "gates" in draft_plan:
                for gate in draft_plan["gates"]:
                    if "steps" in gate and isinstance(gate["steps"], list):
                        for step in gate["steps"]:
                            await self._process_step(step, available_tools)
            
            # 4. Validate all tasks in draft_plan exist in catalog
            validation_result = await self._validate_draft_plan_tasks(draft_plan)
            if not validation_result[0]:
                self.mem.log_thinking(f"[PLANNER] Warning: Some tasks in draft_plan not found in catalog: {validation_result[1]}")
            
            # Emit journey state update after draft is created
            if session_id:
                from nexus.conductors.workflows.orchestrator import orchestrator
                await orchestrator._emit_journey_state_update(
                    session_id=session_id,
                    current_step="planning",
                    percent_complete=75.0,  # Planning is typically after gates are complete
                    step_details={"plan_status": "draft_updated", "plan_name": draft_plan.get("name", "Unknown")}
                )
            
            return draft_plan
            
        except Exception as e:
            self.mem.error(f"Planner update failed: {e}")
            # Return minimal plan structure on error
            return {
                "problem_statement": problem_statement,
                "name": "Workflow Plan",
                "goal": "",
                "gates": []  # Changed from "phases" to "gates"
            }
    
    async def _ensure_task_in_catalog(self, step_description: str, context: Dict[str, Any]) -> Dict[str, str]:
        """
        Ensure task exists in catalog before adding to draft_plan.
        This is the enforcement point - tasks MUST exist in catalog.
        
        Uses find_or_create_task() to find existing task or create new one.
        
        Args:
            step_description: Description of the step/task
            context: Context (domain, strategy, etc.)
        
        Returns:
            Dict with 'task_id' (UUID) and 'task_key' (string) for the task
        """
        from nexus.modules.task_registry import task_registry
        
        try:
            # Find existing task or create new one - now returns full task dict
            task = await task_registry.find_or_create_task(
                task_description=step_description,
                context=context,
                created_by=context.get("user_id", "system")
            )
            task_ref = {
                "task_id": task["task_id"],  # UUID - primary reference for integrity
                "task_key": task["task_key"]  # Keep for human readability
            }
            self.mem.log_thinking(f"[PLANNER] Ensured task '{task_ref['task_key']}' (ID: {task_ref['task_id']}) exists in catalog for step: {step_description[:50]}...")
            return task_ref
        except Exception as e:
            self.mem.error(f"[PLANNER] Failed to ensure task in catalog: {e}")
            raise  # Don't fallback - fail explicitly to maintain integrity
    
    async def _validate_draft_plan_tasks(self, draft_plan: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate all tasks in draft_plan exist in catalog.
        
        Args:
            draft_plan: Draft plan dictionary
        
        Returns:
            Tuple of (is_valid, list_of_missing_task_keys)
        """
        from nexus.modules.task_registry import task_registry
        
        missing_tasks = []
        
        if "gates" in draft_plan:
            for gate in draft_plan.get("gates", []):
                for step in gate.get("steps", []):
                    task_key = step.get("task_key")
                    if task_key:
                        exists = await task_registry.validate_task_exists(task_key)
                        if not exists:
                            missing_tasks.append(task_key)
        
        return (len(missing_tasks) == 0, missing_tasks)
    
    def map_gate_state_to_living_document(
        self,
        gate_state: GateState,
        gate_config: Optional[GateConfig] = None
    ) -> Dict[str, Any]:
        """
        Map GateState to living document format for display in UI.
        
        Living document structure:
        {
            "summary": "...",
            "sections": {
                "1": {
                    "label": "Data Availability",
                    "1.1": {"value": "...", "source": "gate_1_data_availability"}
                },
                "2": {
                    "label": "Use Case",
                    "2.1": {"value": "...", "source": "gate_2_use_case"}
                }
            },
            "status": {
                "pass": true/false,
                "next_gate": "...",
                "next_query": "..."
            }
        }
        
        Args:
            gate_state: The GateState to map
            gate_config: Optional GateConfig for gate metadata (questions, labels)
        
        Returns:
            Living document dict
        """
        self.mem.log_thinking(
            f"[PLANNER] map_gate_state_to_living_document | "
            f"Gates: {len(gate_state.gates)}"
        )
        
        # Build sections from gates
        sections = {}
        
        # Group gates by section number (extract numeric prefix)
        # Gate keys like "1_data_availability" -> section "1"
        for gate_key, gate_value in gate_state.gates.items():
            # Extract section number from gate key (e.g., "1_data_availability" -> "1")
            parts = gate_key.split("_", 1)
            section_num = parts[0] if parts else gate_key
            
            # Get section label from gate_config if available
            section_label = gate_key
            if gate_config and gate_key in gate_config.gates:
                # Use question as label (or extract a shorter label)
                question = gate_config.gates[gate_key].question
                # Try to extract a short label from question (first 50 chars)
                section_label = question[:50] + "..." if len(question) > 50 else question
            
            # Initialize section if not exists
            if section_num not in sections:
                sections[section_num] = {
                    "label": section_label,
                    "gate_key": gate_key
                }
            
            # Add sub-points (for now, just one per gate)
            # Use classified value if available, otherwise raw
            value = gate_value.classified if gate_value.classified else gate_value.raw
            if value:
                sub_key = f"{section_num}.1"  # Simple numbering for now
                sections[section_num][sub_key] = {
                    "value": value,
                    "source": f"gate_{gate_key}",
                    "raw": gate_value.raw,
                    "classified": gate_value.classified
                }
        
        # Build status
        status = {
            "pass": gate_state.status.pass_,
            "next_gate": gate_state.status.next_gate,
            "next_query": gate_state.status.next_query
        }
        
        return {
            "summary": gate_state.summary,
            "sections": sections,
            "status": status
        }

planner_brain = PlannerBrain()
