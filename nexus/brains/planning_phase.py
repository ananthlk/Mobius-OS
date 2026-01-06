"""
Planning Phase Brain

Handles the planning phase after gate completion:
- Build New vs Reuse decision
- System computation and ambiguity detection
- Generic overview generation
- Conditional options logic
- Three stages: Approve, Review Plan, Cancel
"""
import logging
import json
import re
from typing import List, Dict, Any, Optional
from nexus.core.memory_logger import MemoryLogger
from nexus.modules.database import database
from nexus.core.gate_models import GateState
from nexus.core.button_builder import emit_action_buttons
from nexus.core.base_agent import BaseAgent
from nexus.core.action_button_handler import ActionButtonHandler

logger = logging.getLogger("nexus.planning_phase")
logger.setLevel(logging.DEBUG)  # Enable debug logging


class PlanningPhaseBrain:
    """
    Handles planning phase operations after gate completion.
    Takes control of all planning phase announcements and message handling.
    """
    
    def __init__(self):
        self.mem = MemoryLogger("nexus.planning_phase")
        from nexus.brains.bounded_plan import bounded_plan_brain
        self.bounded_plan_brain = bounded_plan_brain

    async def announce_planning_phase_start(
        self, 
        session_id: int, 
        user_id: str
    ) -> None:
        """
        Announce the start of planning phase.
        Formats message through conversational agent and emits buttons.
        This is called once when transitioning from gate phase to planning phase.
        """
        logger.debug(f"[PlanningPhaseBrain.announce_planning_phase_start] ENTRY | session_id={session_id}, user_id={user_id}")
        
        agent = BaseAgent(session_id=session_id)
        
        # Raw announcement message
        raw_message = """🎯 Planning Phase Started

We've gathered all the information we need. Now let's build your workflow plan.

What would you like to do next?"""
        
        # Format, emit, and persist to transcript using orchestrator helper
        from nexus.conductors.workflows.orchestrator import orchestrator
        await orchestrator._format_emit_and_persist(
            agent=agent,
            raw_content=raw_message,
            user_id=user_id,
            session_id=session_id,
            context={
                "operation": "planning_phase_announcement",
                "source": "planning_phase_brain",
                "system_generated": True
            }
        )
        
        # Emit buttons using ActionButtonHandler
        handler = ActionButtonHandler(agent)
        buttons = self._build_planning_phase_buttons(session_id, user_id)
        
        await handler.emit_decision_buttons(
            buttons=buttons,
            decision_column="planning_phase_decision",
            decision_table="shaping_sessions",
            context="planning_phase_decision",
            metadata={"phase": "planning"}
        )
        
        logger.debug(f"[PlanningPhaseBrain.announce_planning_phase_start] EXIT | Announcement complete")
    
    def _build_planning_phase_buttons(
        self,
        session_id: int,
        user_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Build planning phase buttons from config (config-driven) or fallback to defaults.
        
        Args:
            session_id: Session ID for endpoint template
            user_id: User ID for payload
            
        Returns:
            List of button configurations
        """
        # TODO: Load from prompt config when planning phase button configs are added
        # For now, use defaults (can be moved to config later)
        endpoint_template = "/api/workflows/shaping/{session_id}/planning-phase/decision"
        endpoint = endpoint_template.format(session_id=session_id)
        
        return [
            {
                "id": "execute_existing",
                "label": "I have an existing saved workflow that I would like to execute",
                "variant": "secondary",
                "action": {
                    "type": "api_call",
                    "endpoint": endpoint,
                    "method": "POST",
                    "payload": {"choice": "execute_existing", "user_id": user_id}
                },
                "enabled": False,
                "tooltip": "Coming soon"
            },
            {
                "id": "create_new",
                "label": "I want to create a new workflow",
                "variant": "primary",
                "action": {
                    "type": "api_call",
                    "endpoint": endpoint,
                    "method": "POST",
                    "payload": {"choice": "create_new", "user_id": user_id}
                },
                "enabled": True,
                "icon": "add"
            },
            {
                "id": "guide_me",
                "label": "Guide me",
                "variant": "secondary",
                "action": {
                    "type": "api_call",
                    "endpoint": endpoint,
                    "method": "POST",
                    "payload": {"choice": "guide_me", "user_id": user_id}
                },
                "enabled": False,
                "tooltip": "Coming soon"
            },
            {
                "id": "refine_answers",
                "label": "Refine my answers (reinvoke gate stage)",
                "variant": "secondary",
                "action": {
                    "type": "api_call",
                    "endpoint": endpoint,
                    "method": "POST",
                    "payload": {"choice": "refine_answers", "user_id": user_id}
                },
                "enabled": False,
                "tooltip": "Coming soon"
            }
        ]
    
    async def handle_message(
        self,
        session_id: int,
        message: str,
        user_id: str
    ) -> Dict[str, Any]:
        """
        Handle a chat message in planning phase.
        Routes to appropriate planning phase logic based on state.
        All responses are formatted through conversational agent.
        """
        logger.debug(f"[PlanningPhaseBrain.handle_message] ENTRY | session_id={session_id}, message_length={len(message)}")
        
        agent = BaseAgent(session_id=session_id)
        
        # Add user message to transcript via orchestrator helper (skips gate engine)
        from nexus.conductors.workflows.orchestrator import orchestrator
        await orchestrator._append_message_to_transcript(
            session_id=session_id,
            role="user",
            content=message,
            skip_gate_engine=True  # Always skip gate engine in planning phase
        )
        
        # Import shaping_manager for formatting responses
        from nexus.modules.shaping_manager import shaping_manager
        
        # Check if decision has been made
        session = await self._get_session(session_id)
        decision = session.get("planning_phase_decision") if session else None
        
        # If no decision made yet, check if this is a decision message
        if not decision:
            # Check if message is a decision choice
            message_lower = message.lower().strip()
            
            # Map natural language to button choices
            if message_lower in ["create new", "create_new", "new", "build", "build new", "i want to create a new workflow"]:
                # handle_build_reuse_decision already emits and persists the response
                result = await self.handle_build_reuse_decision(session_id, "create_new")
                return result
            elif message_lower in ["execute existing", "execute_existing", "existing workflow", "saved workflow", "i have an existing saved workflow"]:
                # handle_build_reuse_decision already emits and persists the response
                result = await self.handle_build_reuse_decision(session_id, "execute_existing")
                return result
            elif message_lower in ["guide me", "guide", "help", "help me"]:
                # handle_build_reuse_decision already emits and persists the response
                result = await self.handle_build_reuse_decision(session_id, "guide_me")
                return result
            elif message_lower in ["refine", "refine answers", "refine_answers", "reinvoke gate", "go back", "refine my answers"]:
                # handle_build_reuse_decision already emits and persists the response
                result = await self.handle_build_reuse_decision(session_id, "refine_answers")
                return result
            else:
                # Not a decision - prompt user to make a decision
                from nexus.conductors.workflows.orchestrator import orchestrator
                response = "I'm ready to help you plan your workflow. Please select one of the options above to get started."
                
                await orchestrator._format_emit_and_persist(
                    agent=agent,
                    raw_content=response,
                    user_id=user_id,
                    session_id=session_id,
                    context={
                        "operation": "planning_phase_chat",
                        "source": "planning_phase_brain",
                        "system_generated": True
                    }
                )
                
                return {"status": "waiting_for_decision", "message": response}
        
        # Decision made - handle based on next step
        from nexus.conductors.workflows.orchestrator import orchestrator
        
        if decision == "create_new" or decision == "build_new":  # Support both for backward compatibility
            # Check if bounded_plan_state exists (bounded plan flow active)
            bounded_plan_state = session.get("bounded_plan_state") if session else None
            
            if bounded_plan_state:
                # Route to bounded plan flow
                logger.debug(f"[PlanningPhaseBrain.handle_message] ROUTING_TO_BOUNDED_PLAN | session_id={session_id}")
                try:
                    # Load session state
                    from nexus.brains.bounded_plan import SessionState
                    session_state = SessionState.from_dict(bounded_plan_state)
                    
                    # Get draft plan, task master catalogue, and tool registry
                    draft_plan = session.get("draft_plan")
                    if isinstance(draft_plan, str):
                        draft_plan = json.loads(draft_plan) if draft_plan else {}
                    
                    # Load task master catalogue
                    from nexus.modules.task_registry import task_registry
                    task_master_catalogue = {}
                    all_tasks = await task_registry.list_tasks({})
                    for task in all_tasks:
                        task_key = task.get("task_key")
                        if task_key:
                            task_master_catalogue[task_key] = task
                    
                    # Get tool registry
                    from nexus.brains.planner import PlannerBrain
                    planner_brain = PlannerBrain()
                    tool_registry = await planner_brain._get_available_tools()
                    
                    # Handle user message in bounded plan flow
                    controller_output = await self.bounded_plan_brain.handle_user_message(
                        session_state=session_state,
                        user_message=message,
                        user_id=user_id,
                        draft_plan=draft_plan,
                        task_master_catalogue=task_master_catalogue,
                        tool_registry=tool_registry
                    )
                    
                    # Format and emit response
                    response_text = controller_output.message
                    if controller_output.question:
                        response_text += f"\n\n{controller_output.question}"
                    
                    await orchestrator._format_emit_and_persist(
                        agent=agent,
                        raw_content=response_text,
                        user_id=user_id,
                        session_id=session_id,
                        context={
                            "operation": "bounded_plan_message",
                            "source": "planning_phase_brain",
                            "system_generated": True
                        }
                    )
                    
                    return {
                        "status": controller_output.plan_readiness.lower().replace("_", " "),
                        "message": controller_output.message,
                        "question": controller_output.question,
                        "plan_readiness": controller_output.plan_readiness
                    }
                except Exception as e:
                    logger.error(f"[PlanningPhaseBrain.handle_message] Bounded plan handling failed: {e}", exc_info=True)
                    # Fallback to old flow
                    pass
            
            # Fallback to old guide_plan_to_implementable flow (for backward compatibility)
            try:
                guidance_result = await self.guide_plan_to_implementable(
                    session_id=session_id,
                    user_id=user_id,
                    user_message=message if message else None
                )
                
                # Format response through conversational agent
                if guidance_result["conversation_state"] == "complete":
                    response = "Your workflow plan is now fully implementable. All steps have owners, execution modes, and failure handling defined."
                elif guidance_result["next_question"]:
                    response = guidance_result["next_question"]
                else:
                    response = "Let me analyze your plan to ensure it's implementable..."
                
                await orchestrator._format_emit_and_persist(
                    agent=agent,
                    raw_content=response,
                    user_id=user_id,
                    session_id=session_id,
                    context={
                        "operation": "plan_implementation_guidance",
                        "source": "planning_phase_brain",
                        "implementation_status": guidance_result["implementation_status"],
                        "system_generated": True
                    }
                )
                
                return {
                    "status": guidance_result["conversation_state"],
                    "message": response,
                    "plan_updates": guidance_result["plan_updates"]
                }
            except Exception as e:
                logger.error(f"[PlanningPhaseBrain.handle_message] Guidance failed: {e}", exc_info=True)
                # Fallback response
                response = f"I'm analyzing your plan. Let me work through the implementation details."
                await orchestrator._format_emit_and_persist(
                    agent=agent,
                    raw_content=response,
                    user_id=user_id,
                    session_id=session_id,
                    context={
                        "operation": "plan_implementation_guidance",
                        "source": "planning_phase_brain",
                        "error": str(e),
                        "system_generated": True
                    }
                )
                return {"status": "error", "message": response}
        
        # Handle other decisions (execute_existing, guide_me, refine_answers)
        elif decision in ["execute_existing", "guide_me", "refine_answers"]:
            # STUB: Acknowledge all messages from planning brain
            response = f"[Planning Phase Brain] I received your message: '{message}'. This is a stub acknowledgment. The '{decision}' feature is coming soon."
            
            await orchestrator._format_emit_and_persist(
                agent=agent,
                raw_content=response,
                user_id=user_id,
                session_id=session_id,
                context={
                    "operation": "planning_phase_chat",
                    "source": "planning_phase_brain",
                    "stub": True,
                    "decision": decision,
                    "system_generated": True
                }
            )
            
            return {"status": "acknowledged", "message": response}
        
        # Default response
        response = f"[Planning Phase Brain] I received your message: '{message}'. This is a stub acknowledgment to confirm messages are reaching the planning phase brain correctly."
        await orchestrator._format_emit_and_persist(
            agent=agent,
            raw_content=response,
            user_id=user_id,
            session_id=session_id,
            context={
                "operation": "planning_phase_chat",
                "source": "planning_phase_brain",
                "stub": True,
                "system_generated": True
            }
        )
        
        return {"status": "acknowledged", "message": response}
    
    async def handle_build_reuse_decision(
        self, 
        session_id: int, 
        choice: str
    ) -> Dict[str, Any]:
        """
        Handle planning phase decision using ActionButtonHandler.
        
        Args:
            session_id: Session ID
            choice: 'create_new', 'execute_existing', 'guide_me', or 'refine_answers'
        
        Returns:
            Decision result with next steps
        """
        logger.debug(f"[PlanningPhaseBrain.handle_build_reuse_decision] ENTRY | session_id={session_id}, choice={choice}")
        self.mem.log_thinking(f"[PLANNING_PHASE] handle_build_reuse_decision | Choice: {choice}")
        
        # Use ActionButtonHandler for decision processing
        agent = BaseAgent(session_id=session_id)
        handler = ActionButtonHandler(agent)
        
        # Get user_id from session for emitting response
        session = await self._get_session(session_id)
        user_id = session.get("user_id", "user_123") if session else "user_123"
        
        # Import orchestrator for formatting responses
        from nexus.conductors.workflows.orchestrator import orchestrator
        
        # Define decision handler callback
        async def on_decision(button_id: str, decision_value: str) -> Dict[str, Any]:
            """Handle decision-specific logic."""
            if decision_value == "create_new":
                # Start bounded plan session
                try:
                    logger.debug(f"[PlanningPhaseBrain.handle_build_reuse_decision] STARTING_BOUNDED_PLAN | session_id={session_id}")
                    
                    # Get draft plan, task master catalogue, and tool registry
                    session = await self._get_session(session_id)
                    if not session:
                        raise ValueError(f"Session {session_id} not found")
                    
                    draft_plan = session.get("draft_plan")
                    if isinstance(draft_plan, str):
                        draft_plan = json.loads(draft_plan) if draft_plan else {}
                    
                    if not draft_plan:
                        raise ValueError("No draft plan found in session")
                    
                    # Load task master catalogue
                    from nexus.modules.task_registry import task_registry
                    task_master_catalogue = {}
                    # Get all tasks from catalog (simplified - in production, filter by domain)
                    all_tasks = await task_registry.list_tasks({})
                    for task in all_tasks:
                        task_key = task.get("task_key")
                        if task_key:
                            task_master_catalogue[task_key] = task
                    
                    # Get tool registry
                    from nexus.brains.planner import PlannerBrain
                    planner_brain = PlannerBrain()
                    tool_registry = await planner_brain._get_available_tools()
                    
                    logger.debug(f"[PlanningPhaseBrain.handle_build_reuse_decision] LOADED_CONTEXT | draft_plan_gates={len(draft_plan.get('gates', []))}, tasks={len(task_master_catalogue)}, tools={len(tool_registry)}")
                    
                    # Start bounded plan session
                    session_state = await self.bounded_plan_brain.start_session(
                        session_id=session_id,
                        draft_plan=draft_plan,
                        task_master_catalogue=task_master_catalogue,
                        tool_registry=tool_registry,
                        initial_known_fields=None
                    )
                    
                    logger.debug(f"[PlanningPhaseBrain.handle_build_reuse_decision] BOUNDED_PLAN_STARTED | known_fields={len(session_state.known_fields)}")
                    
                    # Get initial message from presenter
                    if session_state.last_bound_plan_spec:
                        presenter_result = await self.bounded_plan_brain._call_presenter_llm(
                            bound_plan_spec=session_state.last_bound_plan_spec,
                            session_id=session_id,
                            user_id=user_id
                        )
                        response = presenter_result.get("message", "I'm analyzing your workflow plan. Let me identify what information I need.")
                        question = presenter_result.get("question")
                    else:
                        response = "I'm analyzing your workflow plan. Let me identify what information I need."
                        question = None
                    
                    # Emit the response message
                    await orchestrator._format_emit_and_persist(
                        agent=agent,
                        raw_content=response + (f"\n\n{question}" if question else ""),
                        user_id=user_id,
                        session_id=session_id,
                        context={
                            "operation": "bounded_plan_start",
                            "source": "planning_phase_brain",
                            "system_generated": True
                        }
                    )
                    
                    return {
                        "status": "success",
                        "message": response,
                        "question": question,
                        "next_step": "bounded_plan",
                        "plan_readiness": session_state.last_bound_plan_spec.get("plan_readiness") if session_state.last_bound_plan_spec else "NEEDS_INPUT"
                    }
                except Exception as e:
                    logger.error(f"[PlanningPhaseBrain.handle_build_reuse_decision] Bounded plan start failed: {e}", exc_info=True)
                    # Fallback message
                    return {
                        "status": "success",
                        "message": "Great! Let's create a new workflow from scratch. I'll analyze your requirements and build a plan.",
                        "next_step": "compute_plan"
                    }
            elif decision_value == "execute_existing":
                return {
                    "status": "not_implemented",
                    "message": "Executing existing saved workflows is coming soon. For now, please select 'Create a new workflow'.",
                    "next_step": None
                }
            elif decision_value == "guide_me":
                return {
                    "status": "not_implemented",
                    "message": "The guide me feature is coming soon. For now, please select 'Create a new workflow'.",
                    "next_step": None
                }
            elif decision_value == "refine_answers":
                return {
                    "status": "not_implemented",
                    "message": "Refining answers and reinvoking the gate stage is coming soon. For now, please select 'Create a new workflow'.",
                    "next_step": None
                }
            else:
                # Backward compatibility: map old choices to new ones
                if decision_value == "build_new":
                    return {
                        "status": "success",
                        "message": "Great! Let's create a new workflow from scratch. I'll analyze your requirements and build a plan.",
                        "next_step": "compute_plan"
                    }
                elif decision_value == "reuse":
                    return {
                        "status": "not_implemented",
                        "message": "Reuse from repository is coming soon. For now, please select 'Create a new workflow'.",
                        "next_step": None
                    }
                else:
                    raise ValueError(f"Invalid choice: {decision_value}. Must be one of: 'create_new', 'execute_existing', 'guide_me', 'refine_answers'")
        
        # Process decision using handler
        result = await handler.process_decision(
            button_id=choice,
            decision_value=choice,
            decision_column="planning_phase_decision",
            decision_table="shaping_sessions",
            on_decision=on_decision
        )
        
        # Ensure planning phase is active (in case it wasn't already)
        from nexus.conductors.workflows.orchestrator import orchestrator
        await orchestrator._activate_agent(session_id, "planning")
        
        # Emit the response message to the UI and persist to transcript using orchestrator helper
        response_message = result.get("message", "Decision processed")
        await orchestrator._format_emit_and_persist(
            agent=agent,
            raw_content=response_message,
            user_id=user_id,
            session_id=session_id,
            context={
                "operation": "planning_phase_decision_response",
                "source": "planning_phase_brain",
                "choice": choice,
                "button_generated": True
            }
        )
        
        logger.debug(f"[PlanningPhaseBrain.handle_build_reuse_decision] EXIT | Returning: {result}")
        return result
    
    async def compute_plan_analysis(self, session_id: int) -> Dict[str, Any]:
        """
        Analyze draft plan and detect ambiguous/missing info steps.
        
        Returns:
            {
                "plan": draft_plan,
                "cards_requiring_attention": [...],
                "all_cards_ok": bool
            }
        """
        logger.debug(f"[PlanningPhaseBrain.compute_plan_analysis] ENTRY | session_id={session_id}")
        self.mem.log_thinking(f"[PLANNING_PHASE] compute_plan_analysis | Session: {session_id}")
        
        # Get draft plan from session
        logger.debug(f"[PlanningPhaseBrain.compute_plan_analysis] Fetching session data")
        session = await self._get_session(session_id)
        if not session:
            logger.error(f"[PlanningPhaseBrain.compute_plan_analysis] ERROR | Session {session_id} not found")
            raise ValueError(f"Session {session_id} not found")
        
        draft_plan = session.get("draft_plan")
        if isinstance(draft_plan, str):
            draft_plan = json.loads(draft_plan) if draft_plan else {}
        
        if not draft_plan:
            logger.error(f"[PlanningPhaseBrain.compute_plan_analysis] ERROR | No draft plan found in session")
            raise ValueError("No draft plan found in session")
        
        # CHANGED: Use "gates" (not "phases") - 2-stage document structure
        gates = draft_plan.get("gates", [])
        logger.debug(f"[PlanningPhaseBrain.compute_plan_analysis] Draft plan loaded: {len(gates)} gates")
        
        # Get gate state for context
        logger.debug(f"[PlanningPhaseBrain.compute_plan_analysis] Loading gate state for context")
        gate_state = await self._load_gate_state(session_id)
        
        # Analyze plan
        logger.debug(f"[PlanningPhaseBrain.compute_plan_analysis] Starting plan analysis")
        cards_requiring_attention = []
        
        # Process gates and steps
        for gate in gates:
            gate_id = gate.get("id", "unknown")
            steps = gate.get("steps", [])
            logger.debug(f"[PlanningPhaseBrain.compute_plan_analysis] Processing gate {gate_id} with {len(steps)} steps")
            
            for step in steps:
                step_id = step.get("id", "unknown")
                logger.debug(f"[PlanningPhaseBrain.compute_plan_analysis] Analyzing step {step_id}")
                
                # Check for ambiguity
                logger.debug(f"[PlanningPhaseBrain.compute_plan_analysis] Checking ambiguity for step {step_id}")
                ambiguity_issue = await self.detect_ambiguity(step, gate_state)
                if ambiguity_issue:
                    logger.debug(f"[PlanningPhaseBrain.compute_plan_analysis] Ambiguity detected in step {step_id}: {ambiguity_issue}")
                    cards_requiring_attention.append({
                        "step_id": step_id,
                        "gate_id": gate_id,
                        "issue_type": "ambiguity",
                        "description": ambiguity_issue,
                        "missing_fields": []
                    })
                
                # Check for missing info
                logger.debug(f"[PlanningPhaseBrain.compute_plan_analysis] Checking missing info for step {step_id}")
                missing_info = await self.detect_missing_info(step, gate_state, session)
                if missing_info:
                    logger.debug(f"[PlanningPhaseBrain.compute_plan_analysis] Missing info detected in step {step_id}: {missing_info['fields']}")
                    cards_requiring_attention.append({
                        "step_id": step_id,
                        "gate_id": gate_id,
                        "issue_type": "missing_info",
                        "description": f"Missing required information: {', '.join(missing_info['fields'])}",
                        "missing_fields": missing_info['fields']
                    })
        
        all_cards_ok = len(cards_requiring_attention) == 0
        logger.debug(f"[PlanningPhaseBrain.compute_plan_analysis] Analysis complete: {len(cards_requiring_attention)} cards need attention, all_cards_ok={all_cards_ok}")
        
        result = {
            "plan": draft_plan,
            "cards_requiring_attention": cards_requiring_attention,
            "all_cards_ok": all_cards_ok
        }
        logger.debug(f"[PlanningPhaseBrain.compute_plan_analysis] EXIT | Returning analysis result")
        return result
    
    async def detect_ambiguity(self, step: Dict[str, Any], gate_state: Optional[GateState]) -> Optional[str]:
        """
        Detect ambiguous step descriptions.
        
        Returns:
            Issue description if ambiguous, None otherwise
        """
        logger.debug(f"[PlanningPhaseBrain.detect_ambiguity] ENTRY | step_id={step.get('id')}")
        description = step.get("description", "").strip()
        
        if not description:
            logger.debug(f"[PlanningPhaseBrain.detect_ambiguity] Step description is missing")
            return "Step description is missing"
        
        # Check for vague terms
        vague_terms = [
            "something", "things", "stuff", "etc", "and so on",
            "maybe", "possibly", "might", "could", "perhaps",
            "various", "different", "some", "any"
        ]
        
        desc_lower = description.lower()
        for term in vague_terms:
            if term in desc_lower:
                logger.debug(f"[PlanningPhaseBrain.detect_ambiguity] Found vague term '{term}' in description")
                return f"Step description contains vague term: '{term}'"
        
        # Check for very short descriptions
        if len(description) < 20:
            logger.debug(f"[PlanningPhaseBrain.detect_ambiguity] Description too short ({len(description)} chars)")
            return "Step description is too brief and may be unclear"
        
        # Check for lack of specific action verbs
        action_verbs = [
            "verify", "check", "validate", "retrieve", "get", "fetch",
            "send", "create", "update", "delete", "calculate", "process"
        ]
        
        has_action = any(verb in desc_lower for verb in action_verbs)
        if not has_action:
            logger.debug(f"[PlanningPhaseBrain.detect_ambiguity] No action verb found in description")
            return "Step description lacks a clear action verb"
        
        logger.debug(f"[PlanningPhaseBrain.detect_ambiguity] EXIT | No ambiguity detected")
        return None
    
    async def detect_missing_info(
        self, 
        step: Dict[str, Any], 
        gate_state: Optional[GateState],
        session: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Detect missing required information for a step.
        
        Returns:
            {"fields": [...]} if missing info, None otherwise
        """
        logger.debug(f"[PlanningPhaseBrain.detect_missing_info] ENTRY | step_id={step.get('id')}")
        tool_hint = step.get("tool_hint", "")
        if not tool_hint:
            logger.debug(f"[PlanningPhaseBrain.detect_missing_info] No tool_hint, skipping")
            return None
        
        # Get available tools to check requirements
        logger.debug(f"[PlanningPhaseBrain.detect_missing_info] Getting available tools for tool_hint: {tool_hint}")
        from nexus.brains.planner import planner_brain
        available_tools = await planner_brain._get_available_tools()
        logger.debug(f"[PlanningPhaseBrain.detect_missing_info] Found {len(available_tools)} available tools")
        
        # Try to match tool
        logger.debug(f"[PlanningPhaseBrain.detect_missing_info] Matching tool: {tool_hint}")
        tool_match = await planner_brain._match_tool(tool_hint, available_tools)
        if not tool_match.get("tool_matched"):
            logger.debug(f"[PlanningPhaseBrain.detect_missing_info] Tool not matched, skipping missing info check")
            # Tool not matched - might need manual review, but not "missing info"
            return None
        
        tool_name = tool_match.get("tool_name")
        logger.debug(f"[PlanningPhaseBrain.detect_missing_info] Tool matched: {tool_name}")
        if not tool_name:
            return None
        
        # Get tool schema to check required parameters
        logger.debug(f"[PlanningPhaseBrain.detect_missing_info] Getting tool schema for {tool_name}")
        tool_schema = None
        for tool in available_tools:
            schema = tool.define_schema()
            if schema.name == tool_name:
                tool_schema = schema
                break
        
        if not tool_schema:
            logger.debug(f"[PlanningPhaseBrain.detect_missing_info] Tool schema not found")
            return None
        
        # Extract required parameters
        required_params = []
        parameters = tool_schema.parameters or {}
        
        # Check which parameters are required (basic heuristic)
        # In a real implementation, this would come from the tool schema
        # For now, we'll check common required fields based on tool name
        
        # Check gate_state for available information
        available_info = set()
        if gate_state:
            # Extract info from gate_state summary and gates
            summary = gate_state.summary or ""
            available_info.add("summary")
            
            for gate_key, gate_value in gate_state.gates.items():
                if gate_value.classified:
                    available_info.add(gate_key)
                    available_info.add(gate_value.classified.lower())
        
        # Common required fields for eligibility tools
        common_required = {
            "eligibility_verifier": ["member_id", "payer_name", "dob"],
            "member_lookup": ["member_id"],
            "benefit_calculator": ["member_id", "service_date"]
        }
        
        tool_required = common_required.get(tool_name.lower(), [])
        missing_fields = []
        
        for field in tool_required:
            # Check if field is available in gate_state or session
            field_lower = field.lower()
            found = False
            
            # Check gate_state
            if gate_state:
                for gate_key, gate_value in gate_state.gates.items():
                    if field_lower in gate_key.lower() or (gate_value.classified and field_lower in gate_value.classified.lower()):
                        found = True
                        break
            
            # Check session transcript for mentions
            transcript = session.get("transcript", [])
            for msg in transcript:
                content = msg.get("content", "").lower()
                if field_lower in content:
                    found = True
                    break
            
            if not found:
                missing_fields.append(field)
        
        if missing_fields:
            logger.debug(f"[PlanningPhaseBrain.detect_missing_info] EXIT | Missing fields: {missing_fields}")
            return {"fields": missing_fields}
        
        logger.debug(f"[PlanningPhaseBrain.detect_missing_info] EXIT | No missing info")
        return None
    
    async def generate_plan_overview(self, session_id: int) -> Dict[str, Any]:
        """
        Generate generic overview of the plan.
        
        Returns:
            {
                "overview_text": "...",
                "phases_summary": [...],
                "total_steps": int,
                "expected_timeline": "...",
                "expected_outcomes": [...]
            }
        """
        logger.debug(f"[PlanningPhaseBrain.generate_plan_overview] ENTRY | session_id={session_id}")
        self.mem.log_thinking(f"[PLANNING_PHASE] generate_plan_overview | Session: {session_id}")
        
        # Get draft plan
        logger.debug(f"[PlanningPhaseBrain.generate_plan_overview] Fetching session data")
        session = await self._get_session(session_id)
        if not session:
            logger.error(f"[PlanningPhaseBrain.generate_plan_overview] ERROR | Session {session_id} not found")
            raise ValueError(f"Session {session_id} not found")
        
        draft_plan = session.get("draft_plan")
        if isinstance(draft_plan, str):
            draft_plan = json.loads(draft_plan) if draft_plan else {}
        
        if not draft_plan:
            raise ValueError("No draft plan found in session")
        
        plan_name = draft_plan.get("name", "Workflow")
        goal = draft_plan.get("goal", "")
        
        # Process gates (not phases)
        gates = draft_plan.get("gates", [])
        
        gates_summary = []
        total_steps = 0
        
        for gate in gates:
            gate_id = gate.get("id", "unknown")
            gate_name = gate.get("name", "Unnamed Gate")
            gate_desc = gate.get("description", "")
            steps = gate.get("steps", [])
            step_count = len(steps)
            total_steps += step_count
            
            gates_summary.append({
                "gate_id": gate_id,
                "name": gate_name,
                "step_count": step_count,
                "description": gate_desc or f"{gate_name} gate"
            })
        
        # Generate overview text
        overview_text = f"Your workflow '{plan_name}' consists of {len(gates)} gate(s) with {total_steps} step(s) total."
        if goal:
            overview_text += f"\n\nGoal: {goal}"
        
        # Estimate timeline (basic: ~2-5 seconds per step)
        estimated_seconds = total_steps * 3
        if estimated_seconds < 60:
            expected_timeline = f"~{estimated_seconds} seconds"
        else:
            minutes = estimated_seconds // 60
            seconds = estimated_seconds % 60
            expected_timeline = f"~{minutes} minute{'s' if minutes > 1 else ''}"
            if seconds > 0:
                expected_timeline += f" {seconds} second{'s' if seconds > 1 else ''}"
        
        # Generate expected outcomes from step descriptions
        expected_outcomes = []
        for gate in gates:
            for step in gate.get("steps", []):
                desc = step.get("description", "")
                if desc:
                    # Extract outcome from description (simplified)
                    outcome = desc.strip()
                    if outcome not in expected_outcomes:
                        expected_outcomes.append(outcome)
        
        result = {
            "overview_text": overview_text,
            "gates_summary": gates_summary,  # Changed from phases_summary
            "total_steps": total_steps,
            "expected_timeline": expected_timeline,
            "expected_outcomes": expected_outcomes[:10]  # Limit to 10
        }
        logger.debug(f"[PlanningPhaseBrain.generate_plan_overview] EXIT | Generated overview: {len(gates_summary)} gates, {total_steps} steps")
        return result
    
    async def get_planning_options(self, session_id: int) -> Dict[str, Any]:
        """
        Get conditional options based on card status.
        
        Returns:
            {
                "options": [...],
                "all_cards_ok": bool,
                "auto_select": {...}  # if cards need attention
            }
        """
        logger.debug(f"[PlanningPhaseBrain.get_planning_options] ENTRY | session_id={session_id}")
        self.mem.log_thinking(f"[PLANNING_PHASE] get_planning_options | Session: {session_id}")
        
        # Get plan analysis
        logger.debug(f"[PlanningPhaseBrain.get_planning_options] Computing plan analysis")
        analysis = await self.compute_plan_analysis(session_id)
        all_cards_ok = analysis.get("all_cards_ok", False)
        logger.debug(f"[PlanningPhaseBrain.get_planning_options] Analysis result: all_cards_ok={all_cards_ok}")
        
        if all_cards_ok:
            options = ["approve", "review_edit", "start_new"]
            logger.debug(f"[PlanningPhaseBrain.get_planning_options] All cards OK, returning options: {options}")
            return {
                "options": options,
                "all_cards_ok": True,
                "auto_select": None
            }
        else:
            options = ["select_plan_review", "cancel"]
            cards_requiring_attention = analysis.get("cards_requiring_attention", [])
            logger.debug(f"[PlanningPhaseBrain.get_planning_options] Cards need attention: {len(cards_requiring_attention)}")
            
            # Auto-select first problematic step
            auto_select = None
            if cards_requiring_attention:
                first_card = cards_requiring_attention[0]
                auto_select = {
                    "step_id": first_card.get("step_id"),
                    "gate_id": first_card.get("gate_id"),  # Changed from phase_id
                    "issue_type": first_card.get("issue_type")
                }
                logger.debug(f"[PlanningPhaseBrain.get_planning_options] Auto-selecting step: {auto_select}")
            
            result = {
                "options": options,
                "all_cards_ok": False,
                "auto_select": auto_select
            }
            logger.debug(f"[PlanningPhaseBrain.get_planning_options] EXIT | Returning options: {options}")
            return result
    
    async def handle_approve(self, session_id: int) -> Dict[str, Any]:
        """
        Approve the plan.
        
        Returns:
            Success message and confirmation
        """
        logger.debug(f"[PlanningPhaseBrain.handle_approve] ENTRY | session_id={session_id}")
        self.mem.log_thinking(f"[PLANNING_PHASE] handle_approve | Session: {session_id}")
        
        # Validate all steps are ready
        logger.debug(f"[PlanningPhaseBrain.handle_approve] Validating plan before approval")
        analysis = await self.compute_plan_analysis(session_id)
        if not analysis.get("all_cards_ok"):
            logger.error(f"[PlanningPhaseBrain.handle_approve] ERROR | Cannot approve: steps require attention")
            raise ValueError("Cannot approve plan: some steps require attention")
        
        # Mark plan as approved
        logger.debug(f"[PlanningPhaseBrain.handle_approve] Marking plan as approved")
        await self._mark_plan_approved(session_id)
        
        # Generate confirmation message
        logger.debug(f"[PlanningPhaseBrain.handle_approve] Generating overview for confirmation")
        overview = await self.generate_plan_overview(session_id)
        
        result = {
            "status": "approved",
            "message": "Plan approved successfully! Your workflow is ready to execute.",
            "overview": overview
        }
        logger.debug(f"[PlanningPhaseBrain.handle_approve] EXIT | Plan approved successfully")
        return result
    
    async def handle_review_plan(
        self, 
        session_id: int, 
        selected_step_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Enter review mode for a specific step or auto-select first problematic step.
        
        Returns:
            Review context with step details
        """
        logger.debug(f"[PlanningPhaseBrain.handle_review_plan] ENTRY | session_id={session_id}, selected_step_id={selected_step_id}")
        self.mem.log_thinking(f"[PLANNING_PHASE] handle_review_plan | Session: {session_id} | Step: {selected_step_id}")
        
        # Get plan analysis
        logger.debug(f"[PlanningPhaseBrain.handle_review_plan] Computing plan analysis")
        analysis = await self.compute_plan_analysis(session_id)
        draft_plan = analysis.get("plan", {})
        cards_requiring_attention = analysis.get("cards_requiring_attention", [])
        
        # Find step to review
        review_step = None
        review_phase = None
        
        if selected_step_id:
            # Find specific step
            gates = draft_plan.get("gates", [])
            for gate in gates:
                for step in gate.get("steps", []):
                    if step.get("id") == selected_step_id:
                        review_step = step
                        review_gate = gate  # Changed from review_phase
                        break
                if review_step:
                    break
        else:
            # Auto-select first problematic step
            if cards_requiring_attention:
                first_card = cards_requiring_attention[0]
                step_id = first_card.get("step_id")
                gate_id = first_card.get("gate_id")  # Changed from phase_id
                
                gates = draft_plan.get("gates", [])
                for gate in gates:
                    if gate.get("id") == gate_id:
                        review_gate = gate  # Changed from review_phase
                        for step in gate.get("steps", []):
                            if step.get("id") == step_id:
                                review_step = step
                                break
                        break
        
        if not review_step:
            logger.error(f"[PlanningPhaseBrain.handle_review_plan] ERROR | No step found to review")
            raise ValueError("No step found to review")
        
        logger.debug(f"[PlanningPhaseBrain.handle_review_plan] Reviewing step: {review_step.get('id')}")
        
        # Find issue for this step
        issue = None
        for card in cards_requiring_attention:
            if card.get("step_id") == review_step.get("id"):
                issue = card
                logger.debug(f"[PlanningPhaseBrain.handle_review_plan] Found issue for step: {issue.get('issue_type')}")
                break
        
        result = {
            "status": "review_mode",
            "step": review_step,
            "gate": review_gate,  # Changed from phase to gate
            "issue": issue,
            "message": f"Reviewing step: {review_step.get('description', 'Unknown step')}"
        }
        logger.debug(f"[PlanningPhaseBrain.handle_review_plan] EXIT | Returning review context")
        return result
    
    async def handle_cancel(self, session_id: int) -> Dict[str, Any]:
        """
        Cancel planning phase and return to gate phase.
        
        Returns:
            Cancellation confirmation
        """
        logger.debug(f"[PlanningPhaseBrain.handle_cancel] ENTRY | session_id={session_id}")
        self.mem.log_thinking(f"[PLANNING_PHASE] handle_cancel | Session: {session_id}")
        
        # Reset planning phase state
        logger.debug(f"[PlanningPhaseBrain.handle_cancel] Resetting planning phase state")
        await self._reset_planning_phase(session_id)
        
        result = {
            "status": "cancelled",
            "message": "Planning phase cancelled. Returning to gate phase.",
            "redirect_to": "gate_phase"
        }
        logger.debug(f"[PlanningPhaseBrain.handle_cancel] EXIT | Planning phase cancelled")
        return result
    
    # Helper methods
    
    async def _get_session(self, session_id: int) -> Optional[Dict[str, Any]]:
        """Get session data."""
        from nexus.modules.shaping_manager import shaping_manager
        return await shaping_manager.get_session(session_id)
    
    async def _load_gate_state(self, session_id: int) -> Optional[GateState]:
        """Load gate state from session."""
        from nexus.modules.shaping_manager import shaping_manager
        return await shaping_manager._load_gate_state(session_id)
    
    async def _mark_plan_approved(self, session_id: int):
        """Mark plan as approved in database."""
        try:
            query = """
                UPDATE shaping_sessions 
                SET planning_phase_approved = TRUE,
                    planning_phase_approved_at = CURRENT_TIMESTAMP,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = :session_id
            """
            await database.execute(query, {"session_id": session_id})
        except Exception as e:
            # Column may not exist yet - that's okay for stub
            self.mem.debug(f"Could not mark plan approved (column may not exist): {e}")
    
    async def _reset_planning_phase(self, session_id: int):
        """Reset planning phase state."""
        try:
            query = """
                UPDATE shaping_sessions 
                SET planning_phase_decision = NULL,
                    planning_phase_approved = FALSE,
                    planning_phase_approved_at = NULL,
                    status = 'GATHERING',
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = :session_id
            """
            await database.execute(query, {"session_id": session_id})
        except Exception as e:
            self.mem.debug(f"Could not reset planning phase (columns may not exist): {e}")
    
    # ============================================================================
    # Plan Implementation Guidance (LLM-Guided)
    # ============================================================================
    
    async def guide_plan_to_implementable(
        self,
        session_id: int,
        user_id: str,
        user_message: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        LLM-guided conversation to make plan implementable.
        Uses prompt from prompt_manager database.
        Loads full plan, tool contracts, and guides user through:
        - Step ownership (tool vs user)
        - Data availability for tool steps
        - Execution mode per step (agent/copilot/human-driven)
        - Escalation/failure logic
        - Patient communication permissions
        
        Returns:
            {
                "plan_updates": Dict,  # Updated plan structure
                "conversation_state": str,  # "needs_input"|"complete"|"clarification"
                "next_question": Optional[str],  # Question for user if needed
                "implementation_status": Dict  # What's complete, what's missing
            }
        """
        logger.debug(f"[PlanningPhaseBrain.guide_plan_to_implementable] ENTRY | session_id={session_id}")
        
        # 1. Load full plan
        session = await self._get_session(session_id)
        draft_plan = session.get("draft_plan")
        if isinstance(draft_plan, str):
            draft_plan = json.loads(draft_plan) if draft_plan else {}
        
        if not draft_plan:
            raise ValueError("No draft plan found")
        
        # 2. Load all available tools with their contracts
        from nexus.brains.planner import planner_brain
        available_tools = await planner_brain._get_available_tools()
        
        tool_contracts = []
        for tool in available_tools:
            schema = tool.define_schema()
            tool_contracts.append({
                "name": schema.name,
                "description": schema.description,
                "parameters": schema.parameters,
                "required_parameters": list(schema.parameters.keys()) if schema.parameters else []
            })
        
        # 3. Get gate state for problem context
        gate_state = await self._load_gate_state(session_id)
        problem_statement = gate_state.summary if gate_state else ""
        gate_values = {}
        if gate_state:
            for gate_key, gate_value in gate_state.gates.items():
                gate_values[gate_key] = {
                    "classified": gate_value.classified,
                    "raw": gate_value.raw
                }
        
        # 4. Analyze current implementation status
        implementation_status = self._analyze_implementation_status(draft_plan, tool_contracts, gate_values)
        
        # 5. Get prompt from prompt_manager
        from nexus.modules.prompt_manager import prompt_manager
        from nexus.core.prompt_builder import PromptBuilder
        from nexus.modules.config_manager import config_manager
        from nexus.modules.llm_service import llm_service
        
        # Detect domain (default to eligibility)
        domain = "eligibility"  # Could detect from session or gate state
        strategy = session.get("consultant_strategy", "TABULA_RASA")
        
        prompt_data = await prompt_manager.get_prompt(
            module_name="workflow",
            domain=domain,
            mode=strategy,
            step="plan_implementation",
            session_id=session_id
        )
        
        if not prompt_data:
            logger.warning(f"[PlanningPhaseBrain.guide_plan_to_implementable] Prompt not found, using fallback")
            # Fallback: use hardcoded prompt structure
            return await self._guide_plan_fallback(session_id, user_id, draft_plan, tool_contracts, gate_values, implementation_status, user_message)
        
        # 6. Build prompt with variables using PromptBuilder
        pb = PromptBuilder()
        pb.build_from_config(prompt_data["config"], context={
            "draft_plan": draft_plan,
            "tool_contracts": tool_contracts,
            "problem_statement": problem_statement,
            "gate_values": gate_values,
            "implementation_status": implementation_status,
            "user_message": user_message,
            "transcript": session.get("transcript", [])[-10:] if session else []
        })
        
        # Add dynamic context sections
        pb.add_context("DRAFT_PLAN", json.dumps(draft_plan, indent=2))
        pb.add_context("AVAILABLE_TOOLS", json.dumps(tool_contracts, indent=2))
        pb.add_context("PROBLEM_STATEMENT", problem_statement)
        pb.add_context("GATE_VALUES", json.dumps(gate_values, indent=2))
        pb.add_context("IMPLEMENTATION_STATUS", json.dumps(implementation_status, indent=2))
        
        if user_message:
            pb.add_context("USER_MESSAGE", user_message)
        
        # Build final prompt
        system_prompt = pb.build()
        
        # Add debug logging to see what was built
        logger.debug(f"[PlanningPhaseBrain.guide_plan_to_implementable] System prompt length: {len(system_prompt)} chars")
        logger.debug(f"[PlanningPhaseBrain.guide_plan_to_implementable] System prompt preview (first 500 chars):\n{system_prompt[:500]}")
        if len(system_prompt) > 500:
            logger.debug(f"[PlanningPhaseBrain.guide_plan_to_implementable] System prompt preview (last 500 chars):\n{system_prompt[-500:]}")
        
        # User query for this iteration
        user_query = user_message if user_message else "Analyze the plan and guide me to make it implementable."
        
        # Log the actual full prompt that will be sent
        full_prompt_to_send = f"{system_prompt}\n\n{user_query}" if system_prompt else user_query
        logger.info(f"[PlanningPhaseBrain.guide_plan_to_implementable] 📤 FULL PROMPT BEING SENT ({len(full_prompt_to_send)} chars):")
        logger.info(f"[PlanningPhaseBrain.guide_plan_to_implementable] {'='*80}")
        logger.info(f"[PlanningPhaseBrain.guide_plan_to_implementable] {full_prompt_to_send}")
        logger.info(f"[PlanningPhaseBrain.guide_plan_to_implementable] {'='*80}")
        
        # 7. Make LLM call
        model_context = await config_manager.resolve_app_context("workflow", user_id)
        agent = BaseAgent(session_id=session_id)
        await agent.emit("THINKING", {"message": "Analyzing plan implementation requirements..."})
        
        try:
            llm_response = await llm_service.generate_text(
                prompt=user_query,
                system_instruction=system_prompt,
                model_context=model_context,
                generation_config=prompt_data.get("generation_config", {}),
                return_metadata=False
            )
            
            # Log the actual response received
            logger.info(f"[PlanningPhaseBrain.guide_plan_to_implementable] 📥 FULL RESPONSE RECEIVED ({len(llm_response)} chars):")
            logger.info(f"[PlanningPhaseBrain.guide_plan_to_implementable] {'='*80}")
            logger.info(f"[PlanningPhaseBrain.guide_plan_to_implementable] {llm_response}")
            logger.info(f"[PlanningPhaseBrain.guide_plan_to_implementable] {'='*80}")
            
            # Check if response is empty
            if not llm_response or not llm_response.strip():
                logger.error(f"[PlanningPhaseBrain.guide_plan_to_implementable] ❌ LLM returned empty response")
                raise ValueError("LLM returned empty response. Please try again.")
            
            # 8. Parse structured response
            planning_result = self._parse_planning_response(llm_response)
            
            # 9. Apply updates to plan
            updated_plan = await self._apply_implementation_updates(
                draft_plan=draft_plan,
                updates=planning_result.get("plan_updates", {}),
                tool_contracts=tool_contracts
            )
            
            # 10. Save updated plan
            await self._save_draft_plan(session_id, updated_plan)
            
            return {
                "plan_updates": updated_plan,
                "conversation_state": planning_result.get("conversation_state", "needs_input"),
                "next_question": planning_result.get("next_question"),
                "implementation_status": self._analyze_implementation_status(updated_plan, tool_contracts, gate_values),
                "raw_llm_response": planning_result
            }
            
        except Exception as e:
            logger.error(f"[PlanningPhaseBrain.guide_plan_to_implementable] Failed: {e}", exc_info=True)
            raise
    
    async def _guide_plan_fallback(
        self,
        session_id: int,
        user_id: str,
        draft_plan: Dict[str, Any],
        tool_contracts: List[Dict[str, Any]],
        gate_values: Dict[str, Any],
        implementation_status: Dict[str, Any],
        user_message: Optional[str]
    ) -> Dict[str, Any]:
        """Fallback implementation if prompt not found."""
        logger.debug(f"[PlanningPhaseBrain._guide_plan_fallback] Using fallback implementation")
        
        # Simple fallback: return current status
        return {
            "plan_updates": draft_plan,
            "conversation_state": "needs_input",
            "next_question": "Let me analyze your plan. What would you like to refine?",
            "implementation_status": implementation_status,
            "raw_llm_response": {}
        }
    
    def _analyze_implementation_status(
        self,
        draft_plan: Dict[str, Any],
        tool_contracts: List[Dict[str, Any]],
        gate_values: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze what's complete and what's missing for implementation."""
        
        gates = draft_plan.get("gates", [])
        status = {
            "steps_total": 0,
            "steps_with_owner": 0,
            "steps_with_tool": 0,
            "steps_with_execution_mode": 0,
            "steps_with_failure_logic": 0,
            "steps_with_patient_comm": 0,
            "missing_data": [],
            "incomplete_steps": []
        }
        
        for gate in gates:
            for step in gate.get("steps", []):
                status["steps_total"] += 1
                step_id = step.get("id", "unknown")
                
                # Check owner
                if step.get("owner") in ["tool", "user"]:
                    status["steps_with_owner"] += 1
                else:
                    status["incomplete_steps"].append({
                        "step_id": step_id,
                        "missing": "owner"
                    })
                
                # Check tool assignment
                if step.get("tool_name"):
                    status["steps_with_tool"] += 1
                    # Check if tool parameters are available
                    tool_name = step.get("tool_name")
                    tool_contract = next((t for t in tool_contracts if t["name"] == tool_name), None)
                    if tool_contract:
                        required_params = tool_contract.get("required_parameters", [])
                        provided_params = step.get("tool_parameters", {})
                        missing = [p for p in required_params if p not in provided_params]
                        if missing:
                            status["missing_data"].append({
                                "step_id": step_id,
                                "tool": tool_name,
                                "missing_parameters": missing
                            })
                
                # Check execution mode
                if step.get("execution_mode") in ["agent", "copilot", "human_driven"]:
                    status["steps_with_execution_mode"] += 1
                else:
                    if step_id not in [s["step_id"] for s in status["incomplete_steps"]]:
                        status["incomplete_steps"].append({
                            "step_id": step_id,
                            "missing": "execution_mode"
                        })
                
                # Check failure logic
                if step.get("failure_logic"):
                    status["steps_with_failure_logic"] += 1
                
                # Check patient communication
                if step.get("patient_communication", {}).get("involves_patient"):
                    if step.get("patient_communication", {}).get("method"):
                        status["steps_with_patient_comm"] += 1
        
        status["completion_percentage"] = (
            (status["steps_with_owner"] + 
             status["steps_with_execution_mode"] + 
             status["steps_with_failure_logic"]) / 
            (status["steps_total"] * 3) * 100
        ) if status["steps_total"] > 0 else 0
        
        return status
    
    def _parse_planning_response(self, llm_response: str) -> Dict[str, Any]:
        """Parse LLM JSON response - handles markdown code blocks and extra text."""
        import re
        from typing import Optional
        
        logger.info(f"[PlanningPhaseBrain._parse_planning_response] 📥 Parsing LLM response ({len(llm_response)} chars)")
        logger.debug(f"[PlanningPhaseBrain._parse_planning_response] Full response:\n{llm_response}")
        
        # Helper function: Extract JSON using brace counting (robust for nested JSON)
        def extract_json_with_brace_counting(text: str) -> Optional[str]:
            """Extract JSON object from text using brace counting."""
            start_idx = text.find('{')
            if start_idx == -1:
                return None
            
            brace_count = 0
            for i in range(start_idx, len(text)):
                if text[i] == '{':
                    brace_count += 1
                elif text[i] == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        return text[start_idx:i+1]
            return None
        
        # Step 1: Try to extract JSON from markdown code blocks first
        code_block_pattern = r'```(?:json)?\s*\n?(.*?)\n?```'
        code_block_match = re.search(code_block_pattern, llm_response, re.DOTALL)
        if code_block_match:
            code_block_content = code_block_match.group(1).strip()
            logger.debug(f"[PlanningPhaseBrain._parse_planning_response] Found JSON in code block, trying to parse...")
            
            # Try direct parsing first
            try:
                parsed = json.loads(code_block_content)
                logger.info(f"[PlanningPhaseBrain._parse_planning_response] ✅ Successfully parsed JSON from code block")
                return parsed
            except json.JSONDecodeError:
                # If direct parsing fails, try brace counting on the code block content
                logger.debug(f"[PlanningPhaseBrain._parse_planning_response] Direct parse failed, trying brace counting on code block content...")
                json_candidate = extract_json_with_brace_counting(code_block_content)
                if json_candidate:
                    try:
                        parsed = json.loads(json_candidate)
                        logger.info(f"[PlanningPhaseBrain._parse_planning_response] ✅ Successfully parsed JSON from code block using brace counting")
                        return parsed
                    except json.JSONDecodeError as e:
                        logger.warning(f"[PlanningPhaseBrain._parse_planning_response] Brace counting on code block failed: {e}")
        
        # Step 2: Try to find JSON using brace counting (removed broken regex pattern)
        json_candidate = extract_json_with_brace_counting(llm_response)
        if json_candidate:
            try:
                parsed = json.loads(json_candidate)
                logger.info(f"[PlanningPhaseBrain._parse_planning_response] ✅ Successfully parsed JSON using brace counting")
                return parsed
            except json.JSONDecodeError as e:
                logger.warning(f"[PlanningPhaseBrain._parse_planning_response] Brace counting found candidate but parsing failed: {e}")
        
        # Step 3: Try parsing entire response as JSON (last resort)
        try:
            parsed = json.loads(llm_response.strip())
            logger.info(f"[PlanningPhaseBrain._parse_planning_response] ✅ Successfully parsed entire response as JSON")
            return parsed
        except json.JSONDecodeError as e:
            logger.error(f"[PlanningPhaseBrain._parse_planning_response] ❌ All parsing attempts failed. Last error: {e}")
            logger.error(f"[PlanningPhaseBrain._parse_planning_response] Response that failed to parse:\n{llm_response}")
            
            # Return default structure
            return {
                "conversation_state": "clarification",
                "next_question": "I had trouble parsing the response. Please try again.",
                "plan_updates": {"steps": []},
                "missing_information": [],
                "reasoning": f"Failed to parse LLM response: {str(e)}"
            }
    
    async def _apply_implementation_updates(
        self,
        draft_plan: Dict[str, Any],
        updates: Dict[str, Any],
        tool_contracts: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Apply LLM-suggested updates to the plan."""
        
        step_updates = updates.get("steps", [])
        
        # Create lookup for step updates
        updates_by_step_id = {u["step_id"]: u for u in step_updates}
        
        # Apply updates to each step
        gates = draft_plan.get("gates", [])
        for gate in gates:
            for step in gate.get("steps", []):
                step_id = step.get("id")
                if step_id in updates_by_step_id:
                    update = updates_by_step_id[step_id]
                    
                    # Apply owner
                    if "owner" in update:
                        step["owner"] = update["owner"]
                    
                    # Apply tool assignment
                    if "tool_name" in update:
                        step["tool_name"] = update["tool_name"]
                    if "tool_parameters" in update:
                        step["tool_parameters"] = update["tool_parameters"]
                    
                    # Apply execution mode
                    if "execution_mode" in update:
                        step["execution_mode"] = update["execution_mode"]
                    
                    # Apply required data
                    if "required_data" in update:
                        step["required_data"] = update["required_data"]
                    if "data_sources" in update:
                        step["data_sources"] = update["data_sources"]
                    
                    # Apply failure logic
                    if "failure_logic" in update:
                        step["failure_logic"] = update["failure_logic"]
                    
                    # Apply patient communication
                    if "patient_communication" in update:
                        step["patient_communication"] = update["patient_communication"]
        
        draft_plan["gates"] = gates
        return draft_plan
    
    async def _save_draft_plan(self, session_id: int, draft_plan: Dict[str, Any]) -> None:
        """Save updated draft plan to database."""
        await database.execute(
            "UPDATE shaping_sessions SET draft_plan = :plan, updated_at = CURRENT_TIMESTAMP WHERE id = :id",
            {"plan": json.dumps(draft_plan), "id": session_id}
        )
        
        # Emit artifact for frontend
        agent = BaseAgent(session_id=session_id)
        await agent.emit("ARTIFACTS", {
            "type": "DRAFT_PLAN",
            "data": draft_plan
        })


# Singleton instance
planning_phase_brain = PlanningPhaseBrain()

