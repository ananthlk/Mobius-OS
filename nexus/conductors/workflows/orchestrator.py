"""
Workflow Orchestrator

Coordinates workflow-related modules:
- ShapingManager (main chat surface)
- DiagnosisBrain (existing workflow analyzer)
- PlannerBrain (workflow planner)
- ConsultantBrain (strategy decisions)
"""
import logging
import asyncio
import json
from typing import Dict, Any, List, Optional
from datetime import datetime

from nexus.conductors.base_orchestrator import BaseOrchestrator
from nexus.modules.shaping_manager import shaping_manager
from nexus.modules.session_manager import session_manager
from nexus.modules.database import database
from nexus.brains.diagnosis import DiagnosisBrain, SolutionCandidate
from nexus.brains.planner import planner_brain
from nexus.brains.consultant import consultant_brain
from nexus.workflows.registry import registry
from nexus.core.base_agent import NexusAgentFactory, AgentRecipe
from nexus.tools.crm.schedule_scanner import ScheduleScannerTool
from nexus.tools.crm.risk_calculator import RiskCalculatorTool

logger = logging.getLogger("nexus.workflows.orchestrator")


class WorkflowOrchestrator(BaseOrchestrator):
    """
    Workflow Orchestrator - coordinates workflow modules and manages workflow lifecycle.
    """
    
    def __init__(self):
        super().__init__()
        self.shaping_manager = shaping_manager
        self.diagnosis_brain = DiagnosisBrain()
        self.planner_brain = planner_brain
        self.consultant_brain = consultant_brain
        
        # Available tools for workflow execution
        self.available_tools = [
            ScheduleScannerTool(),
            RiskCalculatorTool()
        ]
    
    # ============================================================================
    # Implement Abstract Methods from BaseOrchestrator
    # ============================================================================
    
    def _get_module_registry(self) -> Dict[str, Any]:
        """Return workflow-specific modules."""
        return {
            "shaping": self.shaping_manager,
            "diagnosis": self.diagnosis_brain,
            "planner": self.planner_brain,
            "consultant": self.consultant_brain
        }
    
    def _get_session_manager(self):
        """Return session manager instance."""
        return session_manager
    
    def _get_database(self):
        """Return database instance."""
        return database
    
    # ============================================================================
    # Public API - Called by Endpoints
    # ============================================================================
    
    async def start_shaping_session(self, user_id: str, query: str) -> Dict[str, Any]:
        """
        Start a new shaping session.
        Returns: {session_id, candidates, transcript}
        """
        self._log_operation("start_shaping_session", {"user_id": user_id, "query": query})
        
        try:
            # 1. Create session via ShapingManager
            session_id = await self.shaping_manager.create_session(user_id, query)
            
            # 2. Use base class for state management
            await self._set_state(f"session:{session_id}:user_id", user_id, session_id)
            await self._set_state(f"session:{session_id}:query", query, session_id)
            
            # 3. Use base class for error handling with retry
            async def diagnose_query():
                return await self.diagnosis_brain.diagnose(query)
            
            candidates = await self._retry_operation(
                diagnose_query,
                max_retries=3
            )
            
            # Ensure candidates is a list
            if not isinstance(candidates, list):
                candidates = list(candidates) if hasattr(candidates, '__iter__') and not asyncio.iscoroutine(candidates) else []
            
            # 4. Get session data
            session_data = await self.shaping_manager.get_session(session_id)
            
            # 5. Request emissions via base class
            await self._request_emission(
                "shaping", 
                "ARTIFACTS",
                {"type": "SESSION_CREATED", "session_id": session_id},
                session_id
            )
            
            # Convert candidates to dict format for emission
            candidates_data = [
                {
                    "recipe_name": c.recipe_name,
                    "goal": c.goal,
                    "match_score": c.match_score,
                    "missing_info": c.missing_info,
                    "reasoning": c.reasoning,
                    "origin": c.origin
                } for c in candidates
            ]
            
            await self._request_emission(
                "diagnosis",
                "ARTIFACTS",
                {"type": "EXISTING_WORKFLOW_MATCHES", "data": candidates_data},
                session_id
            )
            
            # 6. Use base class for metrics
            self._record_metric("shaping_session.created", 1, {"user_id": user_id})
            
            # 7. Audit
            await self._audit_event(
                "CREATE",
                "SHAPING_SESSION",
                str(session_id),
                {"user_id": user_id, "query": query[:100]}
            )
            
            return {
                "session_id": session_id,
                "candidates": [
                    {
                        "recipe_name": c.recipe_name,
                        "goal": c.goal,
                        "match_score": c.match_score,
                        "missing_info": c.missing_info,
                        "reasoning": c.reasoning,
                        "origin": c.origin
                    } for c in candidates
                ],
                "transcript": session_data.get("transcript", []),
                "system_intro": "Session Initialized"
            }
        except Exception as e:
            await self._handle_error(e, {"operation": "start_shaping_session", "user_id": user_id}, None)
            raise
    
    async def get_session_state(self, session_id: int) -> Dict[str, Any]:
        """
        Get current session state.
        Includes latest thinking message from memory_events.
        """
        try:
            session = await self.shaping_manager.get_session(session_id)
            if not session:
                return {"error": "Session not found"}
            
            # Get recent thinking events from memory_events (return array, not just latest)
            try:
                db = self._get_database()
                # Get last 20 thinking messages to show full sequence (before/after LLM calls)
                thinking_messages_query = """
                    SELECT payload, created_at
                    FROM memory_events 
                    WHERE session_id = :sid AND bucket_type = 'THINKING' 
                    ORDER BY created_at DESC 
                    LIMIT 20
                """
                results = await db.fetch_all(query=thinking_messages_query, values={"sid": session_id})
                
                if results:
                    import json
                    thinking_messages = []
                    latest_message = None
                    latest_created_at = None
                    
                    for row in results:
                        result_dict = dict(row)
                        payload = result_dict.get("payload")
                        created_at = result_dict.get("created_at")
                        
                        # Track the latest one (first in DESC order)
                        if latest_created_at is None:
                            latest_created_at = created_at
                        
                        # Parse JSONB if needed
                        if isinstance(payload, str):
                            try:
                                payload = json.loads(payload)
                            except (json.JSONDecodeError, TypeError):
                                # If it's not valid JSON, treat as plain string
                                if payload:
                                    thinking_messages.append(payload)
                                    if latest_message is None:
                                        latest_message = payload
                                continue
                        
                        # Extract message field from payload
                        if isinstance(payload, dict):
                            message = payload.get("message", "")
                            if message:
                                thinking_messages.append(message)
                                if latest_message is None:
                                    latest_message = message
                        elif payload:
                            msg_str = str(payload)
                            thinking_messages.append(msg_str)
                            if latest_message is None:
                                latest_message = msg_str
                    
                    # Reverse to show oldest first (chronological order)
                    thinking_messages.reverse()
                    
                    # Return both single message (for backward compat) and array
                    session["latest_thought"] = {
                        "message": latest_message or "",  # Keep latest for backward compat
                        "messages": thinking_messages,  # New: array of all messages in chronological order
                        "created_at": latest_created_at
                    }
                else:
                    session["latest_thought"] = None
            except Exception as e:
                # If memory_events table doesn't exist or query fails, just continue without latest_thought
                self.logger.error(f"Could not fetch thinking messages: {e}", exc_info=True)
                session["latest_thought"] = None
            
            # Include gate_state in session response if available
            try:
                db = self._get_database()
                gate_state_query = "SELECT gate_state FROM shaping_sessions WHERE id = :sid"
                gate_state_row = await db.fetch_one(query=gate_state_query, values={"sid": session_id})
                
                if gate_state_row and "gate_state" in gate_state_row and gate_state_row["gate_state"]:
                    gate_state_raw = gate_state_row["gate_state"]
                    
                    # Parse JSONB if it's a string (PostgreSQL returns JSONB as dict, but handle string case)
                    if isinstance(gate_state_raw, str):
                        try:
                            gate_state_raw = json.loads(gate_state_raw)
                        except (json.JSONDecodeError, TypeError):
                            # If parsing fails, keep as string (shouldn't happen with JSONB, but safe)
                            pass
                    
                    session["gate_state"] = gate_state_raw
                    self.logger.debug(f"[ORCHESTRATOR] Loaded gate_state for session {session_id}: next_gate={gate_state_raw.get('status', {}).get('next_gate') if isinstance(gate_state_raw, dict) else 'N/A'}")
            except Exception as e:
                # If gate_state column doesn't exist or query fails, just continue without it
                self.logger.debug(f"Could not fetch gate_state: {e}")
            
            # Get recent ACTION_BUTTONS artifacts from memory_events
            try:
                db = self._get_database()
                
                # Get current gate step from gate_state (most accurate source)
                current_gate_key = None
                current_phase = None
                gates_complete = False
                
                # Try to get gate_state from session
                gate_state_data = session.get("gate_state")
                if gate_state_data:
                    # Handle dict (from JSONB)
                    if isinstance(gate_state_data, dict):
                        gate_status = gate_state_data.get("status", {})
                        current_gate_key = gate_status.get("next_gate")  # e.g., "1_patient_info_availability"
                        gates_complete = gate_status.get("pass", False)
                        
                        if gates_complete:
                            current_phase = "planning_phase"  # Gates complete, move to planning
                        elif current_gate_key:
                            current_phase = "gate_phase"
                        
                        self.logger.debug(f"[ORCHESTRATOR] Gate state from dict: current_gate_key={current_gate_key}, gates_complete={gates_complete}, phase={current_phase}")
                    # If gate_state is a GateState object, extract from it
                    elif hasattr(gate_state_data, 'status'):
                        current_gate_key = gate_state_data.status.next_gate
                        gates_complete = gate_state_data.status.pass_
                        if gates_complete:
                            current_phase = "planning_phase"
                        elif current_gate_key:
                            current_phase = "gate_phase"
                        
                        self.logger.debug(f"[ORCHESTRATOR] Gate state from object: current_gate_key={current_gate_key}, phase={current_phase}")
                    else:
                        self.logger.warning(f"[ORCHESTRATOR] Gate state is unexpected type: {type(gate_state_data)}")
                
                # Fallback to journey_state if gate_state not available
                if not current_phase:
                    from nexus.modules.journey_state import journey_state_manager
                    journey_state = await journey_state_manager.get_journey_state(session_id)
                    
                    if journey_state:
                        current_step = journey_state.get("current_step", "")
                        if current_step.startswith("gate_"):
                            current_phase = "gate_phase"
                            current_gate_key = current_step.replace("gate_", "", 1)
                        elif current_step == "gates_complete":
                            current_phase = "planning_phase"
                            gates_complete = True
                        elif current_step == "planning" or "planning" in current_step.lower():
                            current_phase = "planning_phase"
                    
                    # Final fallback to session status
                    if not current_phase:
                        session_status = session.get("status", "GATHERING")
                        if session_status == "GATHERING":
                            current_phase = "gate_phase"
                        elif session_status == "PLANNING":
                            current_phase = "planning_phase"
                
                # Check if a planning phase decision has been made (only for planning phase)
                decision_made = None
                if current_phase == "planning_phase":
                    from nexus.core.action_button_handler import should_show_action_buttons
                    decision_made = not await should_show_action_buttons(
                        session_id=session_id,
                        decision_column="planning_phase_decision",
                        decision_table="shaping_sessions"
                    )
                
                artifacts_query = """
                    SELECT payload, created_at
                    FROM memory_events 
                    WHERE session_id = :sid AND bucket_type = 'ARTIFACTS'
                    ORDER BY created_at DESC 
                    LIMIT 50
                """
                artifact_results = await db.fetch_all(query=artifacts_query, values={"sid": session_id})
                
                if artifact_results:
                    import json
                    artifacts = []
                    latest_action_buttons = None
                    latest_gate_buttons = {}  # Track most recent buttons per gate_key
                    latest_draft_plan = None  # Track latest DRAFT_PLAN artifact
                    latest_draft_plan_created_at = None
                    
                    for row in artifact_results:
                        result_dict = dict(row)
                        payload = result_dict.get("payload")
                        created_at = result_dict.get("created_at")
                        
                        # Parse JSONB if needed
                        if isinstance(payload, str):
                            try:
                                payload = json.loads(payload)
                            except (json.JSONDecodeError, TypeError):
                                continue
                        
                        if isinstance(payload, dict):
                            artifact_type = payload.get("type")
                            
                            # Extract latest DRAFT_PLAN artifact
                            if artifact_type == "DRAFT_PLAN":
                                if latest_draft_plan_created_at is None or created_at > latest_draft_plan_created_at:
                                    latest_draft_plan = payload.get("data")
                                    latest_draft_plan_created_at = created_at
                                # Don't add to artifacts array (we'll merge it into session separately)
                                continue
                            
                            if artifact_type == "ACTION_BUTTONS":
                                button_context = payload.get("context", "")
                                button_metadata = payload.get("metadata", {})
                                
                                # For gate_confirmation context, show when gates complete but not confirmed
                                # Check transcript for confirmation status instead of relying on phase
                                if button_context == "gate_confirmation" and gates_complete:
                                    # Check if user has confirmed by looking at transcript
                                    awaiting_confirmation = False
                                    user_confirmed = False
                                    
                                    if session.get("transcript"):
                                        transcript = session.get("transcript", [])
                                        # Check last few messages for confirmation status
                                        last_few = transcript[-5:] if len(transcript) >= 5 else transcript
                                        for msg in last_few:
                                            if isinstance(msg, dict):
                                                completion_status = msg.get("completion_status", {})
                                                completion_reason = completion_status.get("completion_reason", "")
                                                
                                                # Check if we're awaiting confirmation
                                                if completion_reason == "awaiting_user_confirmation":
                                                    awaiting_confirmation = True
                                                
                                                # Check if user has confirmed
                                                if completion_reason == "user_confirmed":
                                                    user_confirmed = True
                                                    awaiting_confirmation = False
                                                    break
                                    
                                    # Show confirmation buttons when gates complete but awaiting confirmation
                                    if awaiting_confirmation and not user_confirmed and latest_action_buttons is None:
                                        latest_action_buttons = payload
                                        self.logger.info(f"[ORCHESTRATOR] ✅ Matched gate confirmation buttons (gates complete, awaiting confirmation)")
                                
                                # For gate_question context, match to current gate step
                                elif button_context == "gate_question" and current_phase == "gate_phase":
                                    button_gate_key = button_metadata.get("gate_key")
                                    
                                    self.logger.debug(f"[ORCHESTRATOR] Checking button: button_gate_key={button_gate_key}, current_gate_key={current_gate_key}, gates_complete={gates_complete}")
                                    
                                    # Only show buttons if they match current gate step
                                    if current_gate_key and button_gate_key == current_gate_key:
                                        # Track most recent buttons for this gate_key
                                        # Since we iterate DESC, first match is most recent
                                        if button_gate_key not in latest_gate_buttons:
                                            latest_gate_buttons[button_gate_key] = payload
                                            self.logger.info(f"[ORCHESTRATOR] ✅ Matched buttons for gate '{button_gate_key}'")
                                    # If gates complete, don't show any gate buttons
                                    elif gates_complete:
                                        self.logger.debug(f"[ORCHESTRATOR] Skipping gate buttons - gates complete")
                                        pass  # Skip gate buttons when gates are complete
                                    elif button_gate_key != current_gate_key:
                                        self.logger.debug(f"[ORCHESTRATOR] Skipping buttons for gate '{button_gate_key}' - not current gate '{current_gate_key}'")
                                
                                # For planning_phase_decision context, match to planning phase
                                elif button_context == "planning_phase_decision" and current_phase == "planning_phase":
                                    button_metadata = payload.get("metadata", {})
                                    button_phase = button_metadata.get("phase")
                                    
                                    # decision_made = False means no decision made, show buttons
                                    # Use same pattern as gate buttons - check metadata
                                    if decision_made is False and button_phase == "planning":
                                        if latest_action_buttons is None:
                                            latest_action_buttons = payload
                                            self.logger.info(f"[ORCHESTRATOR] ✅ Matched planning phase buttons")
                                
                                # Don't add to artifacts array
                                continue
                            artifacts.append(payload)
                    
                    # After processing all artifacts, select buttons for current gate OR confirmation
                    if current_phase == "gate_phase":
                        if gates_complete and latest_action_buttons is None:
                            # If gates complete but no confirmation buttons found yet, 
                            # they should have been set above, but this is a fallback
                            # (Confirmation buttons should be set in the loop above)
                            pass
                        elif current_gate_key:
                            # Get the most recent buttons for the current gate step
                            if current_gate_key in latest_gate_buttons:
                                latest_action_buttons = latest_gate_buttons[current_gate_key]
                    
                    session["artifacts"] = artifacts
                    
                    # Merge latest DRAFT_PLAN artifact into session (prefer artifact over DB if newer)
                    if latest_draft_plan:
                        # If we have a DRAFT_PLAN artifact, use it (it's the most up-to-date)
                        session["draft_plan"] = latest_draft_plan
                        self.logger.debug(f"[ORCHESTRATOR] ✅ Merged latest DRAFT_PLAN artifact into session (created_at: {latest_draft_plan_created_at})")
                    elif session.get("draft_plan"):
                        # If no artifact but DB has draft_plan, keep it
                        self.logger.debug(f"[ORCHESTRATOR] Using draft_plan from database (no newer artifact found)")
                    else:
                        # No draft_plan at all
                        session["draft_plan"] = None
                    
                    # Include latest action buttons if they match current phase/step
                    if latest_action_buttons:
                        session["latest_action_buttons"] = latest_action_buttons
                    else:
                        session["latest_action_buttons"] = None
                else:
                    session["artifacts"] = []
                    session["latest_action_buttons"] = None
            except Exception as e:
                # If memory_events table doesn't exist or query fails, just continue without artifacts
                self.logger.debug(f"Could not fetch artifacts: {e}")
                session["artifacts"] = []
                session["latest_action_buttons"] = None
            
            # Get journey state from dedicated table
            try:
                from nexus.modules.journey_state import journey_state_manager
                
                journey_state = await journey_state_manager.get_journey_state(session_id)
                
                if journey_state:
                    # Map to session fields (for frontend compatibility with normalizeProgressState)
                    session["domain"] = journey_state.get("domain")
                    session["current_step"] = journey_state.get("current_step")
                    session["percent_complete"] = journey_state.get("percent_complete", 0.0)
                    session["status"] = journey_state.get("status") or session.get("status", "GATHERING")
                    
                    # Also include nested journey_state for backward compatibility
                    session["journey_state"] = journey_state
                else:
                    # Default values if no journey state exists
                    session["domain"] = "unknown"
                    session["current_step"] = "initializing"
                    session["percent_complete"] = 0.0
                    session["journey_state"] = {
                        "domain": "unknown",
                        "strategy": session.get("consultant_strategy", "TABULA_RASA"),
                        "current_step": "initializing",
                        "percent_complete": 0.0,
                        "status": session.get("status", "GATHERING"),
                        "step_details": {}
                    }
            except Exception as e:
                self.logger.error(f"Could not fetch journey state: {e}", exc_info=True)
                # Default values on error
                session["domain"] = "unknown"
                session["current_step"] = "initializing"
                session["percent_complete"] = 0.0
            
            # Ensure consultant_strategy is included (should already be from session query)
            if "consultant_strategy" not in session:
                session["consultant_strategy"] = "TABULA_RASA"
            
            return session
        except Exception as e:
            await self._handle_error(e, {"operation": "get_session_state", "session_id": session_id}, session_id)
            raise
    
    async def handle_chat_message(self, session_id: int, message: str, user_id: str) -> Dict[str, Any]:
        """
        Handle a chat message in a shaping session.
        Coordinates ShapingManager, DiagnosisBrain, and PlannerBrain.
        Routes to planning phase if gates are complete, otherwise continues with gate flow.
        Returns: {reply, trace_id}
        """
        logger.debug(f"[WorkflowOrchestrator.handle_chat_message] ENTRY | session_id={session_id}, message_length={len(message)}")
        self._log_operation("handle_chat_message", {"session_id": session_id, "user_id": user_id})
        
        try:
            # Check if gates are already complete AND user has confirmed - if so, route to planning phase
            logger.debug(f"[WorkflowOrchestrator.handle_chat_message] Checking gate state")
            gate_state = await self.shaping_manager._load_gate_state(session_id)
            
            # Check if user has explicitly confirmed (look at last transcript message)
            session = await self.shaping_manager.get_session(session_id)
            transcript = session.get("transcript", []) if session else []
            
            # Check if there's a confirmation in recent transcript messages
            has_confirmation = False
            if transcript:
                last_few_messages = transcript[-3:] if len(transcript) >= 3 else transcript
                for msg in last_few_messages:
                    if isinstance(msg, dict):
                        completion_status = msg.get("completion_status", {})
                        if completion_status.get("completion_reason") == "user_confirmed":
                            has_confirmation = True
                            break
            
            if gate_state and gate_state.status.pass_ and has_confirmation:
                logger.debug(f"[WorkflowOrchestrator.handle_chat_message] Gates complete and confirmed - routing to planning phase")
                # Gates complete - route to planning phase
                logger.debug(f"[WorkflowOrchestrator.handle_chat_message] Creating BaseAgent for planning phase")
                from nexus.core.base_agent import BaseAgent
                agent = BaseAgent(session_id=session_id)
                
                # Emit planning phase transition message if not already done
                logger.debug(f"[WorkflowOrchestrator.handle_chat_message] Detecting planning phase transition")
                await self._detect_planning_phase_transition(session_id)
                
                # Format planning phase start message (per UX spec)
                logger.debug(f"[WorkflowOrchestrator.handle_chat_message] Formatting planning phase start message")
                transition_message = """🎯 Planning Phase Started

We've gathered all the information we need. Now let's build your workflow plan.

First, would you like to:
• Build a new workflow from scratch
• Reuse an existing workflow from your repository

Please let me know which option you prefer."""
                
                try:
                    from nexus.brains.conversational_agent import conversational_agent
                    formatted_message = await conversational_agent.format_response(
                        raw_response=transition_message,
                        user_id=user_id,
                        context={"operation": "planning_phase_transition", "source": "orchestrator", "session_id": session_id}
                    )
                except Exception as e:
                    self.logger.warning(f"Conversational agent formatting failed: {e}")
                    formatted_message = transition_message
                
                # Get current transcript and add user message (gates already complete, so we don't call append_message)
                session = await self.shaping_manager.get_session(session_id)
                transcript = session.get("transcript", []) if session else []
                transcript.append({"role": "user", "content": message, "timestamp": "now"})
                
                # Emit user message
                await agent.emit("OUTPUT", {"role": "user", "content": message})
                
                # Emit planning phase response
                await agent.emit("OUTPUT", {"role": "system", "content": formatted_message})
                
                # Emit Build/Reuse decision buttons using ActionButtonHandler
                logger.debug(f"[WorkflowOrchestrator.handle_chat_message] Emitting Build/Reuse decision buttons")
                from nexus.core.action_button_handler import ActionButtonHandler
                
                handler = ActionButtonHandler(agent)
                
                buttons = [
                    {
                        "id": "build_new",
                        "label": "Build New Workflow",
                        "variant": "primary",
                        "action": {
                            "type": "api_call",
                            "endpoint": f"/api/workflows/shaping/{session_id}/planning-phase/decision",
                            "method": "POST",
                            "payload": {
                                "choice": "build_new",
                                "user_id": user_id
                            }
                        },
                        "enabled": True,
                        "icon": "add"
                    },
                    {
                        "id": "reuse",
                        "label": "Reuse from Repository",
                        "variant": "secondary",
                        "action": {
                            "type": "api_call",
                            "endpoint": f"/api/workflows/shaping/{session_id}/planning-phase/decision",
                            "method": "POST",
                            "payload": {
                                "choice": "reuse",
                                "user_id": user_id
                            }
                        },
                        "enabled": False,
                        "tooltip": "Coming soon"
                    }
                ]
                
                await handler.emit_decision_buttons(
                    buttons=buttons,
                    decision_column="planning_phase_decision",
                    decision_table="shaping_sessions",
                    message="First, would you like to:",
                    context="planning_phase_decision",
                    metadata={"phase": "planning", "step": "build_reuse_decision"}
                )
                
                # Add system response to transcript
                transcript.append({"role": "system", "content": formatted_message, "timestamp": "now"})
                
                # Persist transcript
                await database.execute(
                    "UPDATE shaping_sessions SET transcript = :transcript, updated_at = CURRENT_TIMESTAMP WHERE id = :id",
                    {"transcript": json.dumps(transcript), "id": session_id}
                )
                
                # Return planning phase response
                logger.debug(f"[WorkflowOrchestrator.handle_chat_message] EXIT | Returning planning phase response")
                return {
                    "reply": formatted_message,
                    "trace_id": None
                }
            
            # Gates not complete - continue with normal gate flow
            logger.debug(f"[WorkflowOrchestrator.handle_chat_message] Gates not complete - continuing with gate flow")
            # 1. Process chat via ShapingManager (returns raw data)
            logger.debug(f"[WorkflowOrchestrator.handle_chat_message] Calling shaping_manager.append_message")
            result = await self.shaping_manager.append_message(session_id, "user", message)
            
            # 2. Format and emit response through orchestrator
            if result:
                await self._format_and_emit_response(
                    session_id=session_id,
                    user_id=user_id,
                    raw_message=result.get("raw_message", ""),
                    buttons=result.get("buttons"),
                    button_context=result.get("button_context"),
                    button_metadata=result.get("button_metadata")
                )
            
            # 2. Get current transcript for analysis (already includes user message from append_message)
            session = await self.shaping_manager.get_session(session_id)
            transcript = session.get("transcript", []) if session else []
            
            # 3. CRITICAL: Check gate state AGAIN after gate engine execution
            # The gate engine may have just completed all gates with this message
            # BUT: Only route to planning if user has explicitly confirmed (not just completed)
            updated_gate_state = await self.shaping_manager._load_gate_state(session_id)
            
            # Check if user has explicitly confirmed (look at last transcript message)
            has_confirmation = False
            if transcript:
                last_few_messages = transcript[-3:] if len(transcript) >= 3 else transcript
                for msg in last_few_messages:
                    if isinstance(msg, dict):
                        completion_status = msg.get("completion_status", {})
                        if completion_status.get("completion_reason") == "user_confirmed":
                            has_confirmation = True
                            break
            
            if updated_gate_state and updated_gate_state.status.pass_ and has_confirmation:
                # Gates completed AND user confirmed! Route to planning phase
                logger.info(f"[WorkflowOrchestrator.handle_chat_message] ✅ Gates completed and confirmed - routing to planning phase")
                
                # NOW trigger planner (after user confirms)
                # Capture gate data and trigger planner update
                gate_data = await self.shaping_manager._capture_gate_data_for_planner(
                    session_id=session_id,
                    gate_state=updated_gate_state,
                    transcript=transcript,
                    strategy=session.get("consultant_strategy", "TABULA_RASA") if session else "TABULA_RASA",
                    rag_data=session.get("rag_citations", []) if session else []
                )
                
                # Trigger planner update in background (now that user confirmed)
                asyncio.create_task(self._trigger_planner_update(session_id, transcript))
                
                from nexus.core.base_agent import BaseAgent
                agent = BaseAgent(session_id=session_id)
                
                # Emit planning phase transition
                await self._detect_planning_phase_transition(session_id)
                
                # Format planning phase start message (per UX spec)
                transition_message = """🎯 Planning Phase Started

We've gathered all the information we need. Now let's build your workflow plan.

First, would you like to:
• Build a new workflow from scratch
• Reuse an existing workflow from your repository

Please let me know which option you prefer."""
                
                try:
                    from nexus.brains.conversational_agent import conversational_agent
                    formatted_message = await conversational_agent.format_response(
                        raw_response=transition_message,
                        user_id=user_id,
                        context={"operation": "planning_phase_start", "source": "orchestrator", "session_id": session_id}
                    )
                except Exception as e:
                    self.logger.warning(f"Conversational agent formatting failed: {e}")
                    formatted_message = transition_message
                
                # Emit planning phase response
                await agent.emit("OUTPUT", {"role": "system", "content": formatted_message})
                
                # Emit Build/Reuse decision buttons
                logger.debug(f"[WorkflowOrchestrator.handle_chat_message] Emitting Build/Reuse decision buttons")
                from nexus.core.action_button_handler import ActionButtonHandler
                handler = ActionButtonHandler(agent)
                buttons = [
                    {
                        "id": "planning_build_new",
                        "label": "Build New Workflow",
                        "variant": "primary",
                        "action": {
                            "type": "api_call",
                            "endpoint": f"/api/workflows/shaping/{session_id}/chat",
                            "method": "POST",
                            "payload": {
                                "message": "build_new",
                                "user_id": user_id
                            }
                        }
                    },
                    {
                        "id": "planning_reuse_existing",
                        "label": "Reuse Existing Workflow",
                        "variant": "secondary",
                        "action": {
                            "type": "api_call",
                            "endpoint": f"/api/workflows/shaping/{session_id}/chat",
                            "method": "POST",
                            "payload": {
                                "message": "reuse_existing",
                                "user_id": user_id
                            }
                        }
                    }
                ]
                
                await handler.emit_decision_buttons(
                    buttons=buttons,
                    decision_column="planning_phase_decision",
                    decision_table="shaping_sessions",
                    message="First, would you like to:",
                    context="planning_phase_decision"
                )
                
                # Get current transcript - append_message already added the user message
                # DON'T add user message again - it's already in transcript from append_message
                session = await self.shaping_manager.get_session(session_id)
                transcript = session.get("transcript", []) if session else []
                
                # Add planning phase system message to transcript
                transcript.append({"role": "system", "content": formatted_message, "timestamp": "now"})
                
                # Persist transcript
                await database.execute(
                    "UPDATE shaping_sessions SET transcript = :transcript, updated_at = CURRENT_TIMESTAMP WHERE id = :id",
                    {"transcript": json.dumps(transcript), "id": session_id}
                )
                
                # Return planning phase response
                logger.debug(f"[WorkflowOrchestrator.handle_chat_message] EXIT | Returning planning phase response")
                return {
                    "reply": formatted_message,
                    "trace_id": None
                }
            
            # 4. Check for planning phase transition (gate completion) - fire and forget
            asyncio.create_task(self._detect_planning_phase_transition(session_id))
            
            # 5. Trigger workflow analysis (parallel) - re-analyze existing workflows
            # Fire and forget - don't block on these
            asyncio.create_task(self._trigger_workflow_analysis(session_id, message))
            
            # 6. Trigger planner update (parallel) - update draft plan
            asyncio.create_task(self._trigger_planner_update(session_id, transcript))
            
            # 7. Get updated session to get the reply
            updated_session = await self.shaping_manager.get_session(session_id)
            transcript_list = updated_session.get("transcript", []) if updated_session else []
            last_message = transcript_list[-1] if transcript_list else {}
            
            # 8. Metrics
            self._record_metric("chat_message.processed", 1, {"session_id": session_id})
            
            result = {
                "reply": last_message.get("content", ""),
                "trace_id": last_message.get("trace_id")
            }
            logger.debug(f"[WorkflowOrchestrator.handle_chat_message] EXIT | Returning gate flow response")
            return result
        except Exception as e:
            logger.error(f"[WorkflowOrchestrator.handle_chat_message] ERROR | Exception: {e}", exc_info=True)
            await self._handle_error(e, {"operation": "handle_chat_message", "session_id": session_id}, session_id)
            raise
    
    async def analyze_existing_workflows(self, session_id: int, query: str) -> List[SolutionCandidate]:
        """
        Analyze existing workflows matching the query.
        Returns ranked candidates.
        """
        try:
            # Check cache first
            cache_key = f"workflow_analysis:{query}"
            cached = await self._cache_get(cache_key, ttl=300)  # 5 min cache
            if cached:
                return cached
            
            # Run analysis
            candidates = await self.diagnosis_brain.diagnose(query)
            
            # Cache results
            await self._cache_set(cache_key, candidates, ttl=300)
            
            # Request emission
            await self._request_emission(
                "diagnosis",
                "ARTIFACTS",
                {"type": "EXISTING_WORKFLOW_MATCHES", "data": [
                    {
                        "recipe_name": c.recipe_name,
                        "goal": c.goal,
                        "match_score": c.match_score,
                        "missing_info": c.missing_info,
                        "reasoning": c.reasoning,
                        "origin": c.origin
                    } for c in candidates
                ]},
                session_id
            )
            
            return candidates
        except Exception as e:
            await self._handle_error(e, {"operation": "analyze_existing_workflows", "session_id": session_id}, session_id)
            raise
    
    async def update_workflow_plan(self, session_id: int) -> Dict[str, Any]:
        """
        Update the workflow plan based on current session state.
        """
        try:
            session = await self.shaping_manager.get_session(session_id)
            transcript = session.get("transcript", [])
            rag_citations = session.get("rag_citations", [])
            strategy = session.get("consultant_strategy", "TABULA_RASA")
            
            # Load gate_state if available
            gate_state = await self.shaping_manager._load_gate_state(session_id)
            
            context = {
                "manuals": rag_citations,
                "gate_state": gate_state,
                "session_id": session_id,
                "strategy": strategy
            }
            draft_plan = await self.planner_brain.update_draft(transcript, context)
            
            # Request emission
            await self._request_emission(
                "planner",
                "ARTIFACTS",
                {"type": "DRAFT_PLAN", "data": draft_plan},
                session_id
            )
            
            return draft_plan
        except Exception as e:
            await self._handle_error(e, {"operation": "update_workflow_plan", "session_id": session_id}, session_id)
            return {"steps": [], "error": str(e)}
    
    async def execute_workflow(self, recipe_name: str, initial_context: Dict[str, Any], 
                              session_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Execute a workflow recipe.
        Tracks execution in workflow_executions table.
        """
        self._log_operation("execute_workflow", {"recipe_name": recipe_name, "session_id": session_id})
        
        execution_id = None
        start_time = datetime.now()
        
        try:
            # 1. Get recipe
            recipe = await registry.get_recipe(recipe_name)
            if not recipe:
                raise ValueError(f"Recipe '{recipe_name}' not found")
            
            # 2. Create execution record
            db = self._get_database()
            recipe_row = await db.fetch_one(
                "SELECT id FROM agent_recipes WHERE name = :name",
                {"name": recipe_name}
            )
            recipe_id = recipe_row["id"] if recipe_row else None
            
            execution_id = await db.fetch_val(
                """
                INSERT INTO workflow_executions (recipe_id, user_id, status, started_at, shaping_session_id)
                VALUES (:recipe_id, :user_id, 'RUNNING', CURRENT_TIMESTAMP, :session_id)
                RETURNING id
                """,
                {
                    "recipe_id": recipe_id,
                    "user_id": initial_context.get("user_id", "unknown"),
                    "session_id": session_id
                }
            )
            
            # 3. Create factory with session_id if provided
            factory = NexusAgentFactory(available_tools=self.available_tools, session_id=session_id)
            
            # 4. Execute recipe
            result = await factory.run_recipe(recipe, initial_context)
            
            # 5. Update execution record
            end_time = datetime.now()
            duration_ms = int((end_time - start_time).total_seconds() * 1000)
            
            await self._execute_db_write(
                """
                UPDATE workflow_executions 
                SET status = 'SUCCESS', ended_at = CURRENT_TIMESTAMP, duration_ms = :duration
                WHERE id = :id
                """,
                {"id": execution_id, "duration": duration_ms}
            )
            
            # 6. Emit persistence event
            if session_id:
                agent = await self._get_agent_for_session(session_id)
                if agent:
                    await agent.emit_persistence({
                        "action": "WORKFLOW_EXECUTION_COMPLETE",
                        "execution_id": execution_id,
                        "recipe_name": recipe_name,
                        "status": "SUCCESS",
                        "duration_ms": duration_ms
                    })
            
            # 7. Metrics
            self._record_metric("workflow.execution.success", 1, {"recipe": recipe_name})
            
            return {
                "status": "success",
                "execution_id": execution_id,
                "result": result,
                "duration_ms": duration_ms
            }
        except Exception as e:
            # Update execution record on failure
            if execution_id:
                end_time = datetime.now()
                duration_ms = int((end_time - start_time).total_seconds() * 1000)
                await self._execute_db_write(
                    """
                    UPDATE workflow_executions 
                    SET status = 'FAILURE', ended_at = CURRENT_TIMESTAMP, duration_ms = :duration
                    WHERE id = :id
                    """,
                    {"id": execution_id, "duration": duration_ms}
                )
            
            await self._handle_error(e, {"operation": "execute_workflow", "recipe_name": recipe_name}, session_id)
            self._record_metric("workflow.execution.failure", 1, {"recipe": recipe_name})
            raise
    
    async def create_recipe(self, recipe_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new recipe.
        """
        from nexus.core.base_agent import AgentRecipe, AgentStep
        
        try:
            steps = {}
            for step_id, step_data in recipe_data["steps"].items():
                steps[step_id] = AgentStep(
                    step_id=step_id,
                    tool_name=step_data["tool_name"],
                    description=step_data.get("description", ""),
                    args_mapping=step_data.get("args_mapping", {}),
                    transition_success=step_data.get("transition_success"),
                    transition_fail=step_data.get("transition_fail")
                )
            
            recipe = AgentRecipe(
                name=recipe_data["name"],
                goal=recipe_data["goal"],
                steps=steps,
                start_step_id=recipe_data["start_step_id"]
            )
            
            await registry.register_recipe(recipe)
            
            await self._audit_event(
                "CREATE",
                "RECIPE",
                recipe_data["name"],
                {"goal": recipe_data["goal"]}
            )
            
            return {"status": "created", "name": recipe_data["name"]}
        except Exception as e:
            await self._handle_error(e, {"operation": "create_recipe"}, None)
            raise
    
    # ============================================================================
    # Journey State Management
    # ============================================================================
    
    async def _calculate_gate_progress(
        self, 
        gate_state: Optional[Any], 
        gate_config: Optional[Any]
    ) -> Dict[str, Any]:
        """
        Calculate progress from gate state.
        Returns: {current_step, percent_complete, step_details}
        """
        if not gate_state or not gate_config:
            return {
                "current_step": "initializing",
                "percent_complete": 0.0,
                "step_details": {}
            }
        
        # Count required gates
        required_gates = [
            key for key, gate_def in gate_config.gates.items() 
            if gate_def.required
        ]
        total_required = len(required_gates)
        
        # Count completed gates (have classified value)
        completed_gates = [
            key for key in required_gates
            if gate_state.gates.get(key) and gate_state.gates[key].classified
        ]
        completed_count = len(completed_gates)
        
        # Calculate percent complete
        if total_required == 0:
            percent_complete = 100.0 if gate_state.status.pass_ else 0.0
        else:
            percent_complete = (completed_count / total_required) * 100.0
        
        # Determine current step
        if gate_state.status.pass_:
            current_step = "gates_complete"
        elif gate_state.status.next_gate:
            current_step = f"gate_{gate_state.status.next_gate}"
        else:
            current_step = "initializing"
        
        step_details = {
            "completed_gates": completed_count,
            "total_required_gates": total_required,
            "next_gate": gate_state.status.next_gate,
            "next_question": gate_state.status.next_query
        }
        
        return {
            "current_step": current_step,
            "percent_complete": percent_complete,
            "step_details": step_details
        }

    async def _extract_domain_from_gate_config(self, gate_config: Optional[Any]) -> str:
        """Extract domain from gate_config.path."""
        if not gate_config or not hasattr(gate_config, 'path'):
            return "unknown"
        
        # Path structure: {"interaction_type": "workflow", "workflow": "eligibility", ...}
        domain = gate_config.path.get("workflow") or gate_config.path.get("domain") or "unknown"
        return domain

    async def _emit_journey_state_update(
        self,
        session_id: int,
        gate_state: Optional[Any] = None,
        gate_config: Optional[Any] = None,
        strategy: Optional[str] = None,
        current_step: Optional[str] = None,
        percent_complete: Optional[float] = None,
        step_details: Optional[Dict[str, Any]] = None,
        status: Optional[str] = None
    ) -> None:
        """
        Emit journey state update based on current session state.
        Can be called with explicit values or will calculate from gate_state/gate_config.
        """
        # Get strategy from session if not provided
        if not strategy:
            db = self._get_database()
            row = await db.fetch_one(
                "SELECT consultant_strategy FROM shaping_sessions WHERE id = :id",
                {"id": session_id}
            )
            # Fix: Convert row to dict or use dict-style access
            if row:
                row_dict = dict(row)
                strategy = row_dict.get("consultant_strategy", "TABULA_RASA")
            else:
                strategy = "TABULA_RASA"
        
        # Get status from session if not provided
        if not status:
            db = self._get_database()
            row = await db.fetch_one(
                "SELECT status FROM shaping_sessions WHERE id = :id",
                {"id": session_id}
            )
            # Fix: Convert row to dict or use dict-style access
            if row:
                row_dict = dict(row)
                status = row_dict.get("status", "GATHERING")
            else:
                status = "GATHERING"
        
        # If explicit values provided, use them
        if current_step is not None and percent_complete is not None:
            domain = await self._extract_domain_from_gate_config(gate_config) if gate_config else "unknown"
            await self.emit_journey_state(
                session_id=session_id,
                domain=domain,
                strategy=strategy,
                current_step=current_step,
                percent_complete=percent_complete,
                step_details=step_details,
                status=status
            )
            return
        
        # Otherwise calculate from gate state
        if gate_state and gate_config:
            domain = await self._extract_domain_from_gate_config(gate_config)
            progress = await self._calculate_gate_progress(gate_state, gate_config)
            
            await self.emit_journey_state(
                session_id=session_id,
                domain=domain,
                strategy=strategy,
                current_step=progress["current_step"],
                percent_complete=progress["percent_complete"],
                step_details=progress["step_details"],
                status=status
            )
        else:
            # Fallback: emit initializing state
            await self.emit_journey_state(
                session_id=session_id,
                domain="unknown",
                strategy=strategy or "TABULA_RASA",
                current_step="initializing",
                percent_complete=0.0,
                step_details={},
                status=status
            )
    
    async def get_recipe(self, name: str) -> Dict[str, Any]:
        """
        Get a recipe by name.
        """
        try:
            recipe = await registry.get_recipe(name)
            if not recipe:
                return {"error": "Recipe not found"}
            
            # Convert to dict
            return {
                "name": recipe.name,
                "goal": recipe.goal,
                "steps": {
                    step_id: {
                        "step_id": step.step_id,
                        "tool_name": step.tool_name,
                        "description": step.description,
                        "args_mapping": step.args_mapping,
                        "transition_success": step.transition_success,
                        "transition_fail": step.transition_fail
                    } for step_id, step in recipe.steps.items()
                },
                "start_step_id": recipe.start_step_id
            }
        except Exception as e:
            await self._handle_error(e, {"operation": "get_recipe", "name": name}, None)
            raise
    
    async def list_recipes(self) -> List[str]:
        """
        List all active recipes.
        """
        try:
            return await registry.list_recipes()
        except Exception as e:
            await self._handle_error(e, {"operation": "list_recipes"}, None)
            raise
    
    # ============================================================================
    # Internal Workflow-Specific Coordination Methods
    # ============================================================================
    
    async def _trigger_workflow_analysis(self, session_id: int, query: str) -> None:
        """
        Trigger workflow analysis and emit results.
        """
        try:
            candidates = await self.analyze_existing_workflows(session_id, query)
            # Emission is handled in analyze_existing_workflows
        except Exception as e:
            self.logger.warning(f"Workflow analysis failed for session {session_id}: {e}")
    
    async def _detect_planning_phase_transition(self, session_id: int) -> None:
        """
        Detect if gates are complete and trigger planning phase transition.
        """
        logger.debug(f"[WorkflowOrchestrator._detect_planning_phase_transition] ENTRY | session_id={session_id}")
        try:
            # Load gate state
            logger.debug(f"[WorkflowOrchestrator._detect_planning_phase_transition] Loading gate state")
            gate_state = await self.shaping_manager._load_gate_state(session_id)
            
            if not gate_state:
                logger.debug(f"[WorkflowOrchestrator._detect_planning_phase_transition] No gate state found, exiting")
                return
            
            logger.debug(f"[WorkflowOrchestrator._detect_planning_phase_transition] Gate state loaded: pass_={gate_state.status.pass_}")
            
            # Check if gates are complete
            if gate_state.status.pass_:
                logger.debug(f"[WorkflowOrchestrator._detect_planning_phase_transition] Gates are complete, checking if planning phase already started")
                # Check if planning phase already started (handle missing column gracefully)
                db = self._get_database()
                decision = None
                try:
                    query = "SELECT planning_phase_decision FROM shaping_sessions WHERE id = :session_id"
                    row = await db.fetch_one(query, {"session_id": session_id})
                    
                    if row:
                        row_dict = dict(row)
                        decision = row_dict.get("planning_phase_decision")
                        logger.debug(f"[WorkflowOrchestrator._detect_planning_phase_transition] Planning phase decision: {decision}")
                except Exception as col_error:
                    # Column doesn't exist yet - migration not run
                    logger.debug(f"[WorkflowOrchestrator._detect_planning_phase_transition] Planning phase columns not found (migration may not be run): {col_error}")
                    decision = None  # Treat as no decision made yet
                
                # If no decision made yet, emit planning phase started event
                if not decision:
                    logger.debug(f"[WorkflowOrchestrator._detect_planning_phase_transition] No decision yet, emitting PLANNING_PHASE_STARTED artifact")
                    from nexus.core.base_agent import BaseAgent
                    agent = BaseAgent(session_id=session_id)
                    
                    await agent.emit("ARTIFACTS", {
                        "type": "PLANNING_PHASE_STARTED",
                        "message": "Gates complete. Ready to enter planning phase.",
                        "session_id": session_id
                    })
                    
                    # Update journey state
                    logger.debug(f"[WorkflowOrchestrator._detect_planning_phase_transition] Updating journey state to PLANNING")
                    await self._emit_journey_state_update(
                        session_id=session_id,
                        current_step="planning_phase_ready",
                        percent_complete=50.0,
                        step_details={"gate_status": "complete"},
                        status="PLANNING"
                    )
                    logger.debug(f"[WorkflowOrchestrator._detect_planning_phase_transition] Planning phase transition complete")
                else:
                    logger.debug(f"[WorkflowOrchestrator._detect_planning_phase_transition] Planning phase already started (decision={decision}), skipping")
            else:
                logger.debug(f"[WorkflowOrchestrator._detect_planning_phase_transition] Gates not complete yet (pass_={gate_state.status.pass_})")
        except Exception as e:
            logger.error(f"[WorkflowOrchestrator._detect_planning_phase_transition] ERROR | Failed to detect planning phase transition: {e}", exc_info=True)
            self.logger.warning(f"Failed to detect planning phase transition: {e}")
    
    async def _format_and_emit_response(
        self,
        session_id: int,
        user_id: str,
        raw_message: str,
        buttons: Optional[List[Dict]] = None,
        button_context: Optional[str] = None,
        button_metadata: Optional[Dict] = None
    ) -> None:
        """
        Centralized formatting and emission:
        1. Format raw message through conversational agent
        2. Emit formatted OUTPUT
        3. Emit buttons (if any)
        """
        from nexus.core.base_agent import BaseAgent
        from nexus.brains.conversational_agent import conversational_agent
        from nexus.core.button_builder import emit_action_buttons
        
        agent = BaseAgent(session_id=session_id)
        
        # Skip formatting/emission if message is empty (e.g., user confirmed, orchestrator will handle)
        if not raw_message or not raw_message.strip():
            # Only emit buttons if provided (even with empty message)
            if buttons:
                await emit_action_buttons(
                    agent=agent,
                    buttons=buttons,
                    message=None,
                    context=button_context,
                    metadata=button_metadata
                )
            return
        
        # Format through conversational agent
        try:
            formatted_message = await conversational_agent.format_response(
                raw_response=raw_message,
                user_id=user_id,
                context={"operation": "gate_response", "source": "gate_engine", "session_id": session_id}
            )
        except Exception as e:
            self.logger.warning(f"Conversational agent formatting failed: {e}")
            formatted_message = raw_message
        
        # Emit formatted OUTPUT
        if formatted_message and formatted_message.strip():
            await agent.emit("OUTPUT", {"role": "system", "content": formatted_message})
        
        # Emit buttons if provided
        if buttons:
            await emit_action_buttons(
                agent=agent,
                buttons=buttons,
                message=None,
                context=button_context,
                metadata=button_metadata
            )
    
    async def _trigger_planner_update(self, session_id: int, transcript: Optional[List[Dict[str, Any]]] = None) -> None:
        """
        Trigger planner update and emit draft plan.
        Prioritizes gate_state over transcript when available.
        Uses filtered conversation history (only user-facing messages).
        """
        try:
            # Get conversation history from orchestrator (filtered to user-facing messages only)
            conversation_history = await self.build_conversational_history(session_id)
            
            # Get session for RAG citations and other metadata
            session = await self.shaping_manager.get_session(session_id)
            rag_citations = session.get("rag_citations", []) if session else []
            
            # Check if gate_state is available and use it for planner
            gate_state_data = session.get("gate_state") if session else None
            strategy = session.get("consultant_strategy", "TABULA_RASA") if session else "TABULA_RASA"
            
            if gate_state_data:
                try:
                    import json
                    from nexus.core.gate_models import GateState, GateValue, StatusInfo, GateConfig
                    from nexus.modules.prompt_manager import prompt_manager
                    
                    # Parse gate_state
                    if isinstance(gate_state_data, str):
                        gate_state_data = json.loads(gate_state_data)
                    
                    # Convert to GateState object
                    gates = {}
                    for gate_key, gate_value_data in gate_state_data.get("gates", {}).items():
                        gates[gate_key] = GateValue(
                            raw=gate_value_data.get("raw"),
                            classified=gate_value_data.get("classified"),
                            confidence=gate_value_data.get("confidence"),
                            collected_at=None
                        )
                    
                    status_data = gate_state_data.get("status", {})
                    status = StatusInfo(
                        pass_=status_data.get("pass", False),
                        next_gate=status_data.get("next_gate"),
                        next_query=status_data.get("next_query")
                    )
                    
                    gate_state = GateState(
                        summary=gate_state_data.get("summary", ""),
                        gates=gates,
                        status=status
                    )
                    
                    # Load gate_config
                    # Uses new prompt key structure: workflow:eligibility:{strategy}:gate
                    prompt_data = await prompt_manager.get_prompt(
                        module_name="workflow",
                        domain="eligibility",  # Hardcoded for now
                        mode=strategy,          # Strategy becomes mode
                        step="gate"            # From gate agent
                    )
                    
                    if prompt_data and "GATE_ORDER" in prompt_data.get("config", {}):
                        gate_config = GateConfig.from_prompt_config(prompt_data["config"])
                        
                        # Use gate_state to living document mapping
                        living_doc = self.planner_brain.map_gate_state_to_living_document(
                            gate_state=gate_state,
                            gate_config=gate_config
                        )
                        
                        # Use living document as draft plan
                        draft_plan = living_doc
                        
                        # Request emission
                        await self._request_emission(
                            "planner",
                            "ARTIFACTS",
                            {"type": "DRAFT_PLAN", "data": draft_plan},
                            session_id
                        )
                        return
                except Exception as e:
                    self.logger.warning(f"Failed to use gate_state for planner, falling back to transcript: {e}")
            
            # Fallback to old transcript-based planning
            # Get filtered conversation history (only user-facing messages) if not already retrieved
            if 'conversation_history' not in locals():
                conversation_history = await self.build_conversational_history(session_id)
            
            # Load gate_state if available (even in fallback)
            gate_state = await self.shaping_manager._load_gate_state(session_id)
            
            context = {
                "manuals": rag_citations, 
                "session_id": session_id, 
                "strategy": strategy,
                "gate_state": gate_state,
                "transcript": conversation_history  # Use filtered conversation history
            }
            draft_plan = await self.planner_brain.update_draft(conversation_history, context)
            
            # Request emission
            await self._request_emission(
                "planner",
                "ARTIFACTS",
                {"type": "DRAFT_PLAN", "data": draft_plan},
                session_id
            )
        except Exception as e:
            self.logger.warning(f"Planner update failed for session {session_id}: {e}")
    
    async def update_draft_plan(
        self, 
        session_id: int, 
        updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update draft plan for a session.
        Allows CRUD operations on steps.
        """
        try:
            # Get current session
            session = await self.shaping_manager.get_session(session_id)
            if not session:
                raise ValueError(f"Session {session_id} not found")
            
            # Get current draft_plan
            current_plan = session.get("draft_plan", {})
            if isinstance(current_plan, str):
                current_plan = json.loads(current_plan) if current_plan else {}
            
            # Merge updates
            updated_plan = current_plan.copy()
            if updates.get("problem_statement") is not None:
                updated_plan["problem_statement"] = updates["problem_statement"]
            if updates.get("name") is not None:
                updated_plan["name"] = updates["name"]
            if updates.get("goal") is not None:
                updated_plan["goal"] = updates["goal"]
            if updates.get("steps") is not None:
                # Validate steps structure
                steps = updates["steps"]
                if not isinstance(steps, list):
                    raise ValueError("steps must be a list")
                # Validate each step has required fields
                for step in steps:
                    if not isinstance(step, dict):
                        raise ValueError("Each step must be a dict")
                    if "id" not in step:
                        raise ValueError("Each step must have an 'id' field")
                    if "description" not in step:
                        raise ValueError("Each step must have a 'description' field")
                updated_plan["steps"] = steps
            
            # Update database
            from nexus.modules.database import database
            update_query = "UPDATE shaping_sessions SET draft_plan = :draft, updated_at = CURRENT_TIMESTAMP WHERE id = :id"
            await database.execute(
                query=update_query,
                values={
                    "draft": json.dumps(updated_plan),
                    "id": session_id
                }
            )
            
            # Emit ARTIFACTS event
            await self._request_emission(
                "planner",
                "ARTIFACTS",
                {"type": "DRAFT_PLAN", "data": updated_plan},
                session_id
            )
            
            return updated_plan
        except Exception as e:
            await self._handle_error(e, {"operation": "update_draft_plan", "session_id": session_id}, session_id)
            raise


# Singleton instance
orchestrator = WorkflowOrchestrator()

