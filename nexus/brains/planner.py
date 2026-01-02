import logging
import json
import re
from typing import List, Dict, Any, Optional
from nexus.modules.llm_service import llm_service
from nexus.core.memory_logger import MemoryLogger
from nexus.core.gate_models import GateState, GateConfig
from nexus.core.base_tool import NexusTool

# logger = logging.getLogger("nexus.planner") # Replaced by MemoryLogger

from nexus.modules.config_manager import config_manager
from nexus.core.prompt_builder import PromptBuilder
from nexus.modules.prompt_manager import prompt_manager
from nexus.brains.planner_parser import PlannerPlanParser


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
        Calls LLM to extract a structured plan from the conversation.
        Uses gate_state.summary as problem statement and matches tools.
        """
        self.mem.log_thinking(f"[PLANNER] update_draft | Transcript Size: {len(transcript)} msgs")
        
        # Extract gate_state from context - this is continuously updated as conversation progresses
        gate_state = context.get("gate_state")
        problem_statement = ""
        if gate_state and hasattr(gate_state, 'summary'):
            problem_statement = gate_state.summary or ""
        elif isinstance(gate_state, dict):
            problem_statement = gate_state.get("summary", "") or ""
        
        # Log the problem statement for debugging
        if problem_statement:
            self.mem.log_thinking(f"[PLANNER] Using problem_statement from gate_state: {problem_statement[:150]}...")
        else:
            self.mem.log_thinking("[PLANNER] No problem_statement found in gate_state")
        
        # 0. Resolve Model (Governance)
        # We assume the 'system' user for background planning, or ideally pass the real user_id.
        # For V1 speed, we use a system override or 'unknown', relying on GLOBAL preferences.
        model_context = await config_manager.resolve_app_context("workflow", "system")

        # Get available tools for matching
        available_tools = await self._get_available_tools()
        tools_list = [t.define_schema().name for t in available_tools]

        # Get session_id from context for prompt_manager
        session_id = context.get("session_id")
        
        # Detect domain and mode from context
        domain = context.get("domain", "eligibility")  # Default to eligibility
        mode = context.get("strategy", "TABULA_RASA")  # Default to TABULA_RASA
        
        # 1. Get prompt from database
        prompt_data = await prompt_manager.get_prompt(
            module_name="workflow",
            domain=domain,
            mode=mode,
            step="planner",
            session_id=session_id
        )
        
        if not prompt_data:
            # Fallback to PromptBuilder if prompt not found in database
            self.mem.log_thinking("[PLANNER] Prompt not found in database, using fallback PromptBuilder")
            pb = PromptBuilder()
            pb.set_role("You are the Planner Module of Mobius OS. Your job is to listen to the conversation and output a structured DRAFT PLAN with user-friendly step descriptions.")
            
            if problem_statement:
                pb.add_context("PROBLEM_STATEMENT", problem_statement)
                pb.set_task(f"Based on the problem statement and what has been agreed upon, output a JSON plan. Each step must directly contribute to solving the problem: {problem_statement}. Write step descriptions in plain, user-friendly language that clearly shows how each step helps achieve the goal.")
            else:
                pb.set_task("Based on what has been agreed upon, output a JSON plan. Write step descriptions in plain, user-friendly language.")
            
            pb.add_context("MANUALS", json.dumps(context.get("manuals", [])))
            if tools_list:
                pb.add_context("AVAILABLE_TOOLS", json.dumps(tools_list))
            
            pb.set_output_format("""
            {
                "problem_statement": "<gate_state.summary or empty string>",
                "name": "Suggested Workflow Name",
                "goal": "Brief goal description",
                "steps": [
                    { 
                        "id": "step_1", 
                        "tool_hint": "e.g. database_lookup", 
                        "description": "User-friendly one-line description that clearly shows how this step helps achieve the goal. Write in plain language, avoid technical jargon. Example: 'Verify the patient has active insurance coverage' instead of 'Check member status'",
                        "solves": "How this step addresses the problem statement"
                    }
                ],
                "missing_info": ["e.g. Payer ID"]
            }
            """)
            pb.add_constraint("Attributes `tool_hint` must be snake_case.")
            pb.add_constraint("Each step's `description` must be a user-friendly, one-line description (max 80 characters) written in plain language that clearly shows how it helps achieve the goal. Avoid technical jargon, database terms, API names, or implementation details. Write from the user's perspective - what they will see accomplished. Examples: 'Verify patient insurance coverage' (not 'Query member_status table'), 'Calculate patient copay amount' (not 'Run billing_eligibility_verifier tool'), 'Send notification to patient' (not 'Invoke notification API').")
            pb.add_constraint("Each step must have a `solves` field explaining how it addresses the problem statement.")
            pb.add_constraint("Output ONLY valid JSON.")
            
            system_prompt = pb.build()
            generation_config = {}
            prompt_key = f"workflow:{domain}:{mode}:planner"
        else:
            # Use prompt from database
            self.mem.log_thinking(f"[PLANNER] Using prompt from database | Key: {prompt_data.get('key')} | Version: {prompt_data.get('version')}")
            config = prompt_data["config"]
            generation_config = prompt_data.get("generation_config", {})
            prompt_key = prompt_data.get("key", f"workflow:{domain}:{mode}:planner")
            
            # Build system prompt using PromptBuilder
            pb = PromptBuilder()
            
            # Set role
            if "ROLE" in config:
                pb.set_role(config["ROLE"])
            
            # Add context with template variable replacement
            if "CONTEXT" in config:
                context_config = config["CONTEXT"]
                if isinstance(context_config, dict):
                    # Replace template variables
                    if "PROBLEM_STATEMENT" in context_config:
                        context_str = context_config["PROBLEM_STATEMENT"]
                        if context_str == "{{PROBLEM_STATEMENT}}":
                            if problem_statement:
                                pb.add_context("PROBLEM_STATEMENT", problem_statement)
                        else:
                            pb.add_context("PROBLEM_STATEMENT", context_str)
                    
                    if "MANUALS" in context_config:
                        context_str = context_config["MANUALS"]
                        if context_str == "{{MANUALS}}":
                            pb.add_context("MANUALS", json.dumps(context.get("manuals", [])))
                        else:
                            pb.add_context("MANUALS", context_str)
                    
                    if "AVAILABLE_TOOLS" in context_config:
                        context_str = context_config["AVAILABLE_TOOLS"]
                        if context_str == "{{AVAILABLE_TOOLS}}":
                            if tools_list:
                                pb.add_context("AVAILABLE_TOOLS", json.dumps(tools_list))
                        else:
                            pb.add_context("AVAILABLE_TOOLS", context_str)
                else:
                    pb.add_context("CONTEXT", context_config)
            
            # Set task/analysis
            if "ANALYSIS" in config:
                analysis = config["ANALYSIS"]
                # Replace problem statement in analysis if needed
                if problem_statement and "{{PROBLEM_STATEMENT}}" in analysis:
                    analysis = analysis.replace("{{PROBLEM_STATEMENT}}", problem_statement)
                pb.set_task(analysis)
            
            # Add constraints
            if "CONSTRAINTS" in config:
                for constraint in config["CONSTRAINTS"]:
                    pb.add_constraint(constraint)
            
            # Set output format
            if "OUTPUT" in config:
                output_config = config["OUTPUT"]
                if isinstance(output_config, dict):
                    if "format" in output_config:
                        pb.set_output_format(output_config["format"])
                    elif "schema" in output_config:
                        schema = output_config["schema"]
                        format_str = schema.get("description", "")
                        if "example" in schema:
                            format_str += "\n\nExample JSON structure:\n" + json.dumps(schema["example"], indent=2)
                        pb.set_output_format(format_str)
                else:
                    pb.set_output_format(output_config)
            
            system_prompt = pb.build()
        
        user_prompt = f"TRANSCRIPT SO FAR:\n{json.dumps(transcript)}"
        
        self.mem.log_thinking(f"LLM CALL [Planner]: Model={model_context.get('model_id')}")
        
        try:
            # Get orchestrator for enriched thinking emissions
            # Note: We need session_id for this - planner is called from orchestrator which has session_id
            # For now, we'll emit basic thinking and let the orchestrator handle enriched emissions
            from nexus.conductors.workflows.orchestrator import orchestrator
            
            # Extract RAG citations from context
            rag_citations = context.get("manuals", [])
            
            # Try to get session_id from context if available
            session_id = context.get("session_id")
            
            # Use generation_config from prompt if available
            if generation_config:
                # Merge generation_config into model_context
                model_context = {**model_context, **generation_config}
            
            if session_id:
                # Emit enriched thinking before LLM call
                await orchestrator.emit_llm_thinking(
                    session_id=session_id,
                    operation="PLANNER",
                    prompt=user_prompt,
                    system_instruction=system_prompt,
                    rag_citations=rag_citations,
                    model_id=model_context.get("model_id"),
                    prompt_key=prompt_key
                )
            
            # 2. Call LLM (Real)
            response, metadata = await llm_service.generate_text(
                prompt=user_prompt,
                system_instruction=system_prompt,
                model_context=model_context,
                return_metadata=True
            )
            
            if session_id:
                # Emit enriched thinking after LLM call with response metadata
                await orchestrator.emit_llm_thinking(
                    session_id=session_id,
                    operation="PLANNER",
                    prompt=user_prompt,
                    system_instruction=system_prompt,
                    rag_citations=rag_citations,
                    model_id=model_context.get("model_id"),
                    response_metadata=metadata,
                    prompt_key=prompt_key
                )
            self.mem.debug(f"   ⚡️ LLM Response: {response[:150]}...")
            
            # 3. Parse JSON using specialized parser
            try:
                parser = PlannerPlanParser()
                parsed_plan = parser.parse(response)
                
                # Convert to dict format
                draft_plan = parser.to_dict(parsed_plan)
                
                self.mem.log_thinking(f"[PLANNER] Parsed plan: {len(parsed_plan.phases)} phases with {sum(len(p.get('steps', [])) for p in parsed_plan.phases)} total steps")
                
            except Exception as e:
                self.mem.error(f"Planner parser failed: {e}")
                raise  # Fail fast - no backward compatibility
            
            # 4. ALWAYS update problem_statement from latest gate_state.summary
            # This ensures the problem statement stays in sync with the conversation
            if problem_statement:
                draft_plan["problem_statement"] = problem_statement
                self.mem.log_thinking(f"[PLANNER] Updated problem_statement from gate_state: {problem_statement[:100]}...")
            elif not draft_plan.get("problem_statement"):
                draft_plan["problem_statement"] = ""
            
            # 5. Post-process phases and steps: tool matching and indicator detection
            if "phases" in draft_plan:
                for phase in draft_plan["phases"]:
                    if "steps" in phase and isinstance(phase["steps"], list):
                        for step in phase["steps"]:
                            await self._process_step(step, available_tools)
            else:
                raise ValueError("Plan must have 'phases' structure")
            
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
            return {"steps": [], "error": "Planning..."}
    
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
