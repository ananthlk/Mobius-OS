import logging
import asyncio
from typing import List, Optional, Dict, Any
import json
from dataclasses import asdict
from nexus.modules.database import database
from nexus.brains.consultant import consultant_brain  # Only for decide_strategy
from nexus.brains.gate_engine import GateEngine
from nexus.brains.planner import planner_brain
from nexus.core.base_agent import BaseAgent # New Streaming Core
from nexus.core.json_parser import json_parser
from nexus.core.gate_models import GateConfig, GateState, GateValue, StatusInfo
from nexus.modules.prompt_manager import prompt_manager

class ShapingManager:
    """
    Manages the 'Workflow Shaping' chat sessions.
    Refactored to use dual-path streaming (BaseAgent.emit).
    """
    
    def __init__(self):
        # We don't maintain a single agent instance because we manage multiple sessions.
        # Ideally, we'd have a registry of active agents per session.
        # For this architecture pivot, we instantiate a ephemeral agent wrapper per request, 
        # or use a helper, since BaseAgent logic is mostly stateless except for session_id.
        self.gate_engine = GateEngine()
    
    async def _load_gate_state(self, session_id: int) -> Optional[GateState]:
        """Load gate state from database."""
        query = "SELECT gate_state FROM shaping_sessions WHERE id = :session_id"
        row = await database.fetch_one(query, {"session_id": session_id})
        
        # Fix: Use dict-style access for Record objects instead of .get()
        if not row or "gate_state" not in row or not row["gate_state"]:
            return None
        
        gate_state_data = row["gate_state"]
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
        
        return GateState(
            summary=gate_state_data.get("summary", ""),
            gates=gates,
            status=status
        )
    
    async def _save_gate_state(self, session_id: int, gate_state: GateState) -> None:
        """Save gate state to database."""
        gate_state_dict = {
            "summary": gate_state.summary,
            "gates": {
                gate_key: {
                    "raw": gate_value.raw,
                    "classified": gate_value.classified,
                    "confidence": gate_value.confidence
                }
                for gate_key, gate_value in gate_state.gates.items()
            },
            "status": {
                "pass": gate_state.status.pass_,
                "next_gate": gate_state.status.next_gate,
                "next_query": gate_state.status.next_query
            }
        }
        
        # Fix: Remove ::jsonb cast - PostgreSQL will handle type conversion automatically
        query = """
            UPDATE shaping_sessions
            SET gate_state = :gate_state,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = :session_id
        """
        await database.execute(
            query,
            {
                "session_id": session_id,
                "gate_state": json.dumps(gate_state_dict)
            }
        )
    
    async def _load_gate_config(self, strategy: str, session_id: Optional[int] = None) -> Optional[GateConfig]:
        """Load gate config from prompt.
        
        Uses new prompt key structure: workflow:eligibility:{strategy}:gate
        - domain: hardcoded to "eligibility"
        - mode: strategy (e.g., "TABULA_RASA")
        - step: "gate" (from gate agent)
        """
        prompt_data = await prompt_manager.get_prompt(
            module_name="workflow",
            domain="eligibility",  # Hardcoded for now
            mode=strategy,          # Strategy becomes mode
            step="gate",           # From gate agent
            session_id=session_id
        )
        
        if not prompt_data:
            logging.warning(f"[SHAPING_MANAGER] No prompt data found for workflow:eligibility:{strategy}:gate")
            return None
        
        config = prompt_data.get("config", {})
        
        # Check if this is a gate-based prompt (has GATE_ORDER)
        if "GATE_ORDER" not in config:
            logging.warning(f"[SHAPING_MANAGER] Prompt config does not have GATE_ORDER")
            return None
        
        gate_config = GateConfig.from_prompt_config(config)
        
        # Log gate config details for debugging
        logging.info(f"[SHAPING_MANAGER] Loaded gate config: {len(gate_config.gates)} gates, order: {gate_config.gate_order}")
        for gate_key, gate_def in gate_config.gates.items():
            logging.info(f"[SHAPING_MANAGER] Gate '{gate_key}': question='{gate_def.question[:50]}...', expected_categories={gate_def.expected_categories}")
        
        return gate_config
    
    async def _format_gate_response(self, result, user_id: Optional[str] = None, session_id: Optional[int] = None) -> str:
        """Format GateEngine result for display, returning raw response (formatting happens at emission)."""
        parts = []
        
        # Summary
        if result.proposed_state.summary:
            parts.append(f"**{result.proposed_state.summary}**")
        
        # Next question (if any)
        if result.next_question:
            parts.append(f"\n**Question:** {result.next_question}")
        
        # Status info
        if result.pass_:
            # When gates complete, provide a more informative completion message
            if not parts:  # If no summary or question, create a completion message
                parts.append("**All required information has been collected.**")
            parts.append("\nWe're ready to proceed with building your workflow plan.")
        else:
            if result.next_gate:
                parts.append(f"\n*Gathering information: {result.next_gate}*")
        
        raw_response = "\n".join(parts) if parts else "Processing your request..."
        
        # NOTE: Conversational formatting is now handled inline before saving to transcript
        # This method just returns the raw formatted response
        return raw_response
    
    async def _emit_gate_router_options(
        self,
        agent: BaseAgent,
        gate_key: str,
        gate_config: GateConfig,
        session_id: int,
        user_id: Optional[str] = None
    ) -> None:
        """
        Emit router options (buttons) for a gate question based on expected_categories.
        Only emits if the gate has expected_categories defined.
        """
        if not gate_key or gate_key not in gate_config.gates:
            logging.warning(f"[SHAPING_MANAGER] Cannot emit router options: gate_key '{gate_key}' not found in gate_config. Available gates: {list(gate_config.gates.keys())}")
            return
        
        gate_def = gate_config.gates[gate_key]
        
        # Only emit router options if gate has expected_categories
        if not gate_def.expected_categories:
            logging.warning(f"[SHAPING_MANAGER] Cannot emit router options: gate '{gate_key}' has no expected_categories. Question: '{gate_def.question}'")
            return
        
        logging.info(f"[SHAPING_MANAGER] Emitting router options for gate '{gate_key}' with {len(gate_def.expected_categories)} categories: {gate_def.expected_categories}")
        
        from nexus.core.button_builder import emit_action_buttons
        
        # Map gate categories to user-friendly display labels
        GATE_DISPLAY_LABELS = {
            "1_patient_info_availability": {
                "Yes": "I have name, DOB, and insurance details",
                "No": "I do not have any patient information",
                "Partial": "I only have name and DOB, no insurance info",
                "Unknown": "I'm not sure what information is available"
            }
            # Add more mappings as needed for other gates
        }
        
        # Get display label mapping for this gate
        display_labels = GATE_DISPLAY_LABELS.get(gate_key, {})
        
        # Build router buttons from expected_categories
        buttons = []
        for category in gate_def.expected_categories:
            # Use display label if available, otherwise use category
            display_label = display_labels.get(category, category)
            
            buttons.append({
                "id": f"gate_{gate_key}_{category.lower().replace(' ', '_').replace('/', '_')}",
                "label": display_label,  # User-friendly display label
                "value": category,  # Original category for LLM classification
                "variant": "secondary",
                "action": {
                    "type": "api_call",
                    "endpoint": f"/api/workflows/shaping/{session_id}/chat",
                    "method": "POST",
                    "payload": {
                        "message": category,  # Send original category as message for LLM classification
                        "user_id": user_id or "user_123"
                    }
                },
                "enabled": True,
                "tooltip": f"Select: {display_label}"
            })
        
        # Add "Other" option if categories exist
        buttons.append({
            "id": f"gate_{gate_key}_other",
            "label": "Other",
            "variant": "secondary",
            "action": {
                "type": "event",
                "eventName": "gate_other_selected",
                "payload": {"gate_key": gate_key}
            },
            "enabled": True,
            "tooltip": "Select if none of the above apply"
        })
        
        logging.info(f"[SHAPING_MANAGER] Emitting {len(buttons)} router buttons for gate '{gate_key}' (session_id={session_id}, agent.session_id={agent.session_id})")
        
        # Emit router options with gate_key in metadata for matching
        await emit_action_buttons(
            agent=agent,
            buttons=buttons,
            message=gate_def.question,
            context="gate_question",
            metadata={"gate_key": gate_key}  # Track which gate step these buttons belong to
        )
        
        logging.info(f"[SHAPING_MANAGER] Router options emitted successfully for gate '{gate_key}'")
    
    async def _format_and_emit_output(
        self, 
        agent: BaseAgent, 
        raw_content: str, 
        user_id: str, 
        session_id: Optional[int] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Centralized method to format OUTPUT through conversational_agent before emitting.
        
        Args:
            agent: BaseAgent instance for emission
            raw_content: Raw response content from consultant/planner/gate engine
            user_id: User identifier for preferences
            session_id: Session ID for context
            context: Additional context (e.g., operation type, metadata)
        """
        try:
            from nexus.brains.conversational_agent import conversational_agent
            
            # Emit thinking before formatting
            await agent.emit("THINKING", {
                "message": f"Formatting response through conversational agent..."
            })
            
            # Build context for conversational agent
            formatting_context = {
                "session_id": session_id,
                **(context or {})
            }
            
            # Format through conversational agent
            formatted_content = await conversational_agent.format_response(
                raw_response=raw_content,
                user_id=user_id,
                context=formatting_context
            )
            
            # Emit thinking after formatting
            await agent.emit("THINKING", {
                "message": f"Response formatted and ready (length: {len(formatted_content)} chars)"
            })
            
            # Emit formatted OUTPUT
            await agent.emit("OUTPUT", {"role": "system", "content": formatted_content})
            
        except Exception as e:
            logging.warning(f"Conversational agent formatting failed: {e}, using raw response")
            # Fallback: emit raw response if formatting fails
            await agent.emit("OUTPUT", {"role": "system", "content": raw_content})

    async def create_session(self, user_id: str, initial_query: str) -> int:
        """
        Starts a new shaping session.
        """
        # Create a temporary agent to handle the emission
        agent = BaseAgent(session_id=None) # We don't have ID yet
        
        # We can't emit session-bound events until we have an ID.
        # But we can log locally.
        logging.info(f"[START] create_session | User: {user_id} | Query: '{initial_query}'")
        
        # 1. Resolve Credentials (Governance)
        from nexus.modules.config_manager import config_manager
        model_context = await config_manager.resolve_app_context("workflow", user_id)

        # 2. Decide Strategy (keep for now, but will be replaced by gate-based flow)
        strategy_result = await consultant_brain.decide_strategy(initial_query)
        strategy = strategy_result['strategy']
        
        # 3. Load GateConfig (but DON'T execute gate engine yet - wait for user response)
        await agent.emit("THINKING", {"message": f"Strategy Selected: {strategy}"})
        
        # Load gate config
        gate_config = await self._load_gate_config(strategy, session_id=None)
        
        if not gate_config:
            error_msg = f"Gate config not found for strategy '{strategy}'. Prompt must have GATE_ORDER and GATES defined."
            logging.error(error_msg)
            await agent.emit("THINKING", {"message": error_msg})
            raise ValueError(error_msg)
        
        # Initialize empty gate state (no LLM call - deterministic)
        from nexus.core.gate_models import GateState, StatusInfo
        
        first_gate_key = gate_config.gate_order[0] if gate_config.gate_order else None
        first_question = gate_config.gates[first_gate_key].question if first_gate_key and first_gate_key in gate_config.gates else "Let's get started"
        
        initial_gate_state = GateState(
            summary="",
            gates={},
            status=StatusInfo(
                pass_=False,
                next_gate=first_gate_key,
                next_query=first_question
            )
        )
        
        # Build initial system message (just show first question, no LLM)
        formatted_system_msg = f"I'll help you set up your eligibility verification workflow.\n\n**{first_question}**"
        plan_data = None  # Will be created from gate_state later
        thought_content = None

        # Build transcript with FORMATTED response
        transcript = [
            {"role": "user", "content": initial_query, "timestamp": "now"},
            {
                "role": "system", 
                "content": formatted_system_msg,  # Use FORMATTED response
                "thought": thought_content or strategy_result['reasoning'],
                "timestamp": "now"
            }
        ]
        
        # 4. Create Session in DB to get ID
        query = """
        INSERT INTO shaping_sessions 
        (user_id, status, transcript, draft_plan, consultant_strategy, rag_citations, consultant_iteration_count, max_iterations, gate_state)
        VALUES (:user_id, 'GATHERING', :transcript, :draft_plan, :strategy, :citations, :iter_count, :max_iter, :gate_state)
        RETURNING id
        """
        
        # Prepare gate_state for insertion
        gate_state_json = "{}"
        if 'initial_gate_state' in locals():
            gate_state_dict = {
                "summary": initial_gate_state.summary,
                "gates": {
                    gate_key: {
                        "raw": gate_value.raw,
                        "classified": gate_value.classified,
                        "confidence": gate_value.confidence
                    }
                    for gate_key, gate_value in initial_gate_state.gates.items()
                },
                "status": {
                    "pass": initial_gate_state.status.pass_,
                    "next_gate": initial_gate_state.status.next_gate,
                    "next_query": initial_gate_state.status.next_query
                }
            }
            gate_state_json = json.dumps(gate_state_dict)
        
        session_id = await database.fetch_val(query=query, values={
            "user_id": user_id,
            "transcript": json.dumps(transcript),
            "draft_plan": json.dumps(plan_data) if plan_data else "{}",
            "strategy": strategy_result["strategy"],
            "citations": json.dumps(strategy_result["context"].get("manuals", [])),
            "iter_count": 1,  # First iteration
            "max_iter": 15,  # Default max iterations
            "gate_state": gate_state_json
        })
        
        # NOW we have a session. Configure Agent & Stream backlog.
        agent.set_session_id(session_id)
        
        # Emit the thoughts that led here (Backfilling the stream)
        await agent.emit("THINKING", {
            "message": f"Strategy Selected: {strategy_result['strategy']}", 
            "reasoning": strategy_result['reasoning']
        })
        
        # Note: Gate Engine handles its own LLM calls internally, so metadata emission
        # is handled within the gate_engine.execute_gate() method
        await agent.emit("ARTIFACTS", {
            "type": "RAG_HITS", 
            "count": len(strategy_result['context'].get('manuals', [])),
            "data": strategy_result['context'].get('manuals', [])
        })
        
        await agent.emit("PERSISTENCE", {"action": "INSERT_SESSION", "id": session_id})
        
        # Emit the formatted OUTPUT (already formatted above, so emit directly)
        await agent.emit("OUTPUT", {"role": "system", "content": formatted_system_msg})
        
        # Emit router options for first gate (if available) - AFTER session_id is set
        if initial_gate_state.status.next_gate:
            logging.info(f"[SHAPING_MANAGER] Attempting to emit router options for gate '{initial_gate_state.status.next_gate}' (session_id={session_id}, agent.session_id={agent.session_id})")
            await self._emit_gate_router_options(
                agent=agent,
                gate_key=initial_gate_state.status.next_gate,
                gate_config=gate_config,
                session_id=session_id,
                user_id=user_id
            )
        else:
            logging.warning(f"[SHAPING_MANAGER] No next_gate in initial_gate_state, cannot emit router options")
        
        # Emit journey state after gate execution and strategy selection
        from nexus.conductors.workflows.orchestrator import orchestrator
        await orchestrator._emit_journey_state_update(
            session_id=session_id,
            gate_state=initial_gate_state,
            gate_config=gate_config,
            strategy=strategy_result["strategy"]
        )
        
        # User Activity Log
        await self._log_activity(user_id, session_id, initial_query)
        
        # --- 4. INITIALIZE LIVE BUILDER (Retrieve Template & Create Initial Draft) ---
        # CONTRACT: Gate Agent retrieves template and passes it to planner
        template = await self._retrieve_template_for_planner(strategy=strategy, domain="eligibility")
        
        # Initialize live builder with empty gate state (no LLM call)
        try:
            initial_draft = await planner_brain.update_draft(
                transcript=transcript,
                context={
                    "gate_state": initial_gate_state,
                    "session_id": session_id,
                    "strategy": strategy,
                    "manuals": strategy_result['context'].get('manuals', []),
                    "template": template  # CONTRACT: Gate Agent passes template to planner
                }
            )
            
            # Emit initial ARTIFACTS for live builder
            # Note: BaseAgent.emit() will automatically persist this to shaping_sessions.draft_plan
            await agent.emit("ARTIFACTS", {
                "type": "DRAFT_PLAN",
                "data": initial_draft,
                "summary": "Initial draft plan created for live builder"
            })
            
            # Also explicitly persist here for immediate availability (BaseAgent does this too, but this ensures it)
            try:
                update_query = "UPDATE shaping_sessions SET draft_plan = :draft WHERE id = :id"
                await database.execute(query=update_query, values={
                    "draft": json.dumps(initial_draft),
                    "id": session_id
                })
                logging.debug(f"[SHAPING_MANAGER] Persisted initial draft plan to database")
            except Exception as e:
                logging.error(f"[SHAPING_MANAGER] Failed to persist initial draft plan: {e}", exc_info=True)
            
            logging.debug(f"[SHAPING_MANAGER] Live builder initialized with template")
        except Exception as e:
            logging.error(f"[SHAPING_MANAGER] Live builder initialization failed: {e}", exc_info=True)

        return session_id

    async def _run_initial_plan(self, session_id: int, transcript: List[Dict[str, Any]], rag_data: List[Any]):
        """
        Helper: Runs the planner for the first time in background.
        """
        agent = BaseAgent(session_id=session_id)
        try:
            # await agent.emit("THINKING", {"message": "Drafting initial plan based on manual..."})
            # (Optional: Don't spam thinking for background tasks if it clashes with main thread)
            
            # Load gate_state and strategy if available
            gate_state = await self._load_gate_state(session_id)
            
            # Get strategy from session
            strategy_query = "SELECT consultant_strategy FROM shaping_sessions WHERE id = :id"
            strategy_row = await database.fetch_one(strategy_query, {"id": session_id})
            strategy = "TABULA_RASA"
            if strategy_row:
                strategy = dict(strategy_row).get("consultant_strategy", "TABULA_RASA")
            
            # CONTRACT: Gate Agent retrieves template and passes it to planner
            template = await self._retrieve_template_for_planner(strategy=strategy, domain="eligibility")
            
            context = {
                "manuals": rag_data,
                "gate_state": gate_state,
                "session_id": session_id,
                "strategy": strategy,
                "template": template  # CONTRACT: Gate Agent passes template to planner
            }
            
            new_draft = await planner_brain.update_draft(transcript, context)
            
            # Emit Update
            await agent.emit("ARTIFACTS", {
                "type": "DRAFT_PLAN", 
                "data": new_draft, 
                "summary": "Initial Draft Created"
            })
            
            # Persist
            update_query = "UPDATE shaping_sessions SET draft_plan = :draft WHERE id = :id"
            await database.execute(query=update_query, values={
                "draft": json.dumps(new_draft), 
                "id": session_id
            })
            await agent.emit("PERSISTENCE", {"action": "UPDATE_SESSION", "id": session_id})
            
        except Exception as e:
            logging.error(f"Initial Planner Failed: {e}")

    async def _retrieve_template_for_planner(
        self,
        strategy: str,
        domain: str = "eligibility"
    ) -> Optional[Dict[str, Any]]:
        """
        CONTRACT: Gate Agent is responsible for retrieving templates.
        This method retrieves the appropriate template(s) based on strategy and domain.
        
        Returns:
            Template dict or None if not found
        """
        from nexus.core.tree_structure_manager import TreePath
        from nexus.templates.template_manager import eligibility_template_manager
        
        path = TreePath(
            module="workflow",
            domain=domain,
            strategy=strategy,
            step="template"
        )
        
        try:
            template = await eligibility_template_manager.get_template(path)
            if template:
                logging.debug(f"[SHAPING_MANAGER] Retrieved template for planner: {template.get('template_key')}")
            return template
        except Exception as e:
            logging.warning(f"[SHAPING_MANAGER] Template retrieval failed: {e}")
            return None

    async def _capture_gate_data_for_planner(
        self,
        session_id: int,
        gate_state: GateState,
        transcript: List[Dict[str, Any]],
        strategy: str,
        rag_data: List[Any]
    ) -> Dict[str, Any]:
        """
        Capture gate data for planner WITHOUT making LLM calls.
        Returns structured data that planner can use later.
        This is called during gate stage to collect data, but planner
        will only be invoked after user confirms.
        """
        # asdict is already imported from dataclasses at the top of the file
        from datetime import datetime
        
        # Get filtered conversation history (only user-facing messages)
        from nexus.conductors.workflows.orchestrator import orchestrator
        conversation_history = await orchestrator.build_conversational_history(session_id)
        planner_transcript = conversation_history if conversation_history else transcript
        
        return {
            "gate_state": asdict(gate_state) if isinstance(gate_state, GateState) else gate_state,
            "summary": gate_state.summary,
            "gates": {
                k: {
                    "classified": v.classified,
                    "raw": v.raw,
                    "confidence": v.confidence
                }
                for k, v in gate_state.gates.items()
            },
            "transcript_snapshot": planner_transcript[-10:],  # Last 10 messages
            "rag_data": rag_data,
            "strategy": strategy,
            "captured_at": datetime.now().isoformat(),
            "session_id": session_id
        }

    async def append_message(self, session_id: int, role: str, content: str) -> Dict[str, Any]:
        """
        Appends a message to the session transcript.
        """
        agent = BaseAgent(session_id=session_id)
        
        # 1. Stream the Output intent immediately (Hot Path)
        await agent.emit("OUTPUT", {"role": role, "content": content})
        
        # 2. Fetch current state (handle missing columns gracefully if migration not run)
        try:
            select_query = "SELECT transcript, rag_citations, consultant_iteration_count, max_iterations, draft_plan FROM shaping_sessions WHERE id = :id"
            row = await database.fetch_one(query=select_query, values={"id": session_id})
            if not row:
                return
            
            transcript = json.loads(row["transcript"])
            transcript.append({"role": role, "content": content, "timestamp": "now"})
            rag_data = json.loads(row["rag_citations"] or "[]")
            
            # Get iteration tracking (with defaults if columns don't exist)
            # Convert to dict for safe access, then use .get()
            row_dict = dict(row)
            iteration_count = row_dict.get("consultant_iteration_count", 0)
            max_iterations = row_dict.get("max_iterations", 15)
            
        except Exception as e:
            # Columns don't exist - use fallback query
            logging.warning(f"Migration columns not found, using fallback query: {e}")
            select_query = "SELECT transcript, rag_citations, draft_plan FROM shaping_sessions WHERE id = :id"
        row = await database.fetch_one(query=select_query, values={"id": session_id})
        if not row:
            return

        transcript = json.loads(row["transcript"])
        transcript.append({"role": role, "content": content, "timestamp": "now"})
        rag_data = json.loads(row["rag_citations"] or "[]")
        
        # Default values when columns don't exist
        iteration_count = 0
        max_iterations = 15
        
        # --- 3. CHECK ITERATION LIMIT ---
        
        if iteration_count >= max_iterations:
            await agent.emit("THINKING", {
                "message": f"Iteration limit reached ({max_iterations}). Stopping Consultant loop and using best available plan."
            })
            # Extract best plan from current state and hand off
            row_dict = dict(row)
            current_plan = json.loads(row_dict.get("draft_plan", "{}") or "{}")
            await agent.emit("ARTIFACTS", {
                "type": "DRAFT_PLAN",
                "data": current_plan,
                "summary": "Using best available plan (iteration limit reached)"
            })
            logging.warning(f"Session {session_id} hit iteration limit ({max_iterations})")
            return
        
        # Increment iteration count (skip if column doesn't exist)
        try:
            await database.execute(
                "UPDATE shaping_sessions SET consultant_iteration_count = consultant_iteration_count + 1 WHERE id = :id",
                {"id": session_id}
            )
        except Exception as e:
            # Column doesn't exist yet (migration not run) - skip increment
            logging.debug(f"Could not increment iteration count: {e}")
        
        # --- 4. GATE ENGINE EXECUTION ---
        await agent.emit("THINKING", {"message": "Processing your input..."})

        # A. Resolve Strategy and Load GateConfig
        uid_query = "SELECT user_id, consultant_strategy FROM shaping_sessions WHERE id = :id"
        session_row = await database.fetch_one(uid_query, {"id": session_id})
        if not session_row:
            logging.error(f"Session {session_id} not found")
            return
        session_row_dict = dict(session_row)
        user_id = session_row_dict.get("user_id")
        strategy = session_row_dict.get("consultant_strategy", "TABULA_RASA")
        
        # Load gate config
        gate_config = await self._load_gate_config(strategy, session_id=session_id)
        
        if not gate_config:
            error_msg = f"Gate config not found for strategy '{strategy}'. Prompt must have GATE_ORDER and GATES defined."
            logging.error(error_msg)
            await agent.emit("THINKING", {"message": error_msg})
            raise ValueError(error_msg)
        
        # Use Gate Engine
        # Load previous gate state
        previous_state = await self._load_gate_state(session_id)
        
        # Check if we're waiting for gate confirmation (gates complete but not confirmed)
        if previous_state and previous_state.status.pass_:
            # Gates were complete - check if user is confirming or editing
            user_text_lower = transcript[-1]['content'].lower().strip()
            
            # Detect confirmation phrases
            confirmation_phrases = ["okay", "ok", "yes", "correct", "that's right", "proceed", 
                                   "that works", "looks good", "sounds good", "confirmed", "good", "fine"]
            is_confirmation = any(phrase in user_text_lower for phrase in confirmation_phrases)
            
            # Detect edit requests
            edit_phrases = ["edit", "change", "modify", "update", "wrong", "incorrect", "fix", "no", "not"]
            is_edit = any(phrase in user_text_lower for phrase in edit_phrases)
            
            if is_confirmation:
                # User confirmed - mark as confirmed and proceed with planning phase transition
                logging.debug(f"[SHAPING_MANAGER] User confirmed gate answers - proceeding to planning phase")
                
                # User confirmed - mark as confirmed and let orchestrator handle transition
                # Mark completion status as confirmed
                completion_status = {
                    "is_complete": True,
                    "completion_reason": "user_confirmed",
                    "ready_for_handoff": True
                }
                
                # Add confirmation to transcript with completion status (no message - orchestrator will emit planning phase message)
                transcript.append({
                    "role": "system", 
                    "content": "",  # No message - orchestrator will emit planning phase message
                    "timestamp": "now",
                    "completion_status": completion_status
                })
                
                # Persist transcript
                await database.execute(
                    "UPDATE shaping_sessions SET transcript = :transcript, updated_at = CURRENT_TIMESTAMP WHERE id = :id",
                    {"transcript": json.dumps(transcript), "id": session_id}
                )
                
                # Emit HANDOFF artifact for planning phase
                gate_state = await self._load_gate_state(session_id)
                if gate_state and gate_config:
                    # CHANGED: No longer use living_document - draft_plan is source of truth
                    # Get draft_plan from database or generate it
                    template = await self._retrieve_template_for_planner(strategy=strategy, domain="eligibility")
                    draft_plan = await planner_brain.update_draft(
                        transcript=transcript,
                        context={
                            "gate_state": gate_state,
                            "gate_config": gate_config,
                            "session_id": session_id,
                            "strategy": strategy,
                            "manuals": [],
                            "template": template
                        }
                    )
                    await agent.emit("ARTIFACTS", {
                        "type": "HANDOFF",
                        "data": {
                            "status": "confirmed", 
                            "gate_state": asdict(gate_state) if isinstance(gate_state, GateState) else gate_state,
                            "draft_plan": draft_plan  # Use draft_plan instead of living_doc
                        },
                        "summary": "User confirmed gate answers - ready for planning phase"
                    })
                
                # Return early - don't execute gate engine
                # User confirmed - orchestrator will handle planning phase transition
                return {
                    "raw_message": "",  # No message - orchestrator will emit planning phase message
                    "buttons": None,
                    "button_context": None,
                    "button_metadata": None,
                    "completion_status": completion_status,
                    "gate_state": gate_state
                }
            
            elif is_edit:
                # User wants to edit - reset pass status to allow editing
                logging.debug(f"[SHAPING_MANAGER] User wants to edit gate answers - resetting gate state")
                
                edit_message = "I can help you update your answers. Which information would you like to change?\n\n"
                edit_message += "You can say things like:\n"
                edit_message += "• \"Change the urgency to...\"\n"
                edit_message += "• \"Update the use case to...\"\n"
                edit_message += "• \"The patient info should be...\"\n\n"
                edit_message += "Or just tell me what needs to be corrected."
                
                # Reset gate state to allow editing (clear pass status)
                reset_gate_state = GateState(
                    summary=previous_state.summary,
                    gates=previous_state.gates,
                    status=StatusInfo(
                        pass_=False,  # Reset to allow editing
                        next_gate=None,
                        next_query=None
                    )
                )
                await self._save_gate_state(session_id, reset_gate_state)
                
                # Persist transcript
                await database.execute(
                    "UPDATE shaping_sessions SET transcript = :transcript, updated_at = CURRENT_TIMESTAMP WHERE id = :id",
                    {"transcript": json.dumps(transcript), "id": session_id}
                )
                
                # Return edit message - orchestrator will format and emit
                return {
                    "raw_message": edit_message,
                    "buttons": None,
                    "button_context": None,
                    "button_metadata": None,
                    "completion_status": None,
                    "gate_state": reset_gate_state
                }
            else:
                # User said something else - treat as edit request and continue with gate execution
                logging.debug(f"[SHAPING_MANAGER] User response unclear - treating as edit request")
                # Reset pass status to allow processing
                reset_gate_state = GateState(
                    summary=previous_state.summary,
                    gates=previous_state.gates,
                    status=StatusInfo(
                        pass_=False,  # Reset to allow editing
                        next_gate=None,
                        next_query=None
                    )
                )
                await self._save_gate_state(session_id, reset_gate_state)
                # Continue with gate execution to process the change
        
        # Execute gate
        await agent.emit("THINKING", {"message": "Executing gate engine..."})
        
        gate_result = await self.gate_engine.execute_gate(
            user_text=transcript[-1]['content'],
            gate_config=gate_config,
            previous_state=previous_state,
            actor="user",
            session_id=session_id,
            user_id=user_id,
            conversation_history=transcript
        )
        
        # Save updated gate state
        await self._save_gate_state(session_id, gate_result.proposed_state)
        
        # Get RAG data from session for planner context
        rag_query = "SELECT rag_citations FROM shaping_sessions WHERE id = :id"
        rag_row = await database.fetch_one(rag_query, {"id": session_id})
        rag_data = []
        if rag_row:
            rag_dict = dict(rag_row)
            citations_str = rag_dict.get("rag_citations", "[]")
            try:
                rag_data = json.loads(citations_str) if isinstance(citations_str, str) else citations_str
            except Exception:
                rag_data = []
        
        # --- EMIT ARTIFACTS FOR LIVE BUILDER (After Each Gate Execution) ---
        # Every time user reacts, gate agent emits for live builder to capture and update
        # Live builder will update plan deterministically (no LLM call)
        # CONTRACT: Gate Agent retrieves template and passes it to planner
        template = await self._retrieve_template_for_planner(strategy=strategy, domain="eligibility")
        try:
            updated_draft = await planner_brain.update_draft(
                transcript=transcript,
                context={
                    "gate_state": gate_result.proposed_state,
                    "gate_config": gate_config,  # Pass gate_config for gate metadata
                    "session_id": session_id,
                    "strategy": strategy,
                    "manuals": rag_data,
                    "template": template  # CONTRACT: Gate Agent passes template to planner
                }
            )
            
            # Emit ARTIFACTS for live builder to update
            await agent.emit("ARTIFACTS", {
                "type": "DRAFT_PLAN",
                "data": updated_draft,
                "summary": f"Draft plan updated with gate state (gate: {gate_result.next_gate or 'complete'})"
            })
            
            logging.debug(f"[SHAPING_MANAGER] Emitted ARTIFACTS for live builder after gate execution")
        except Exception as e:
            logging.error(f"[SHAPING_MANAGER] Live builder update failed: {e}", exc_info=True)
        
        # NOTE: Planner should NOT make LLM calls during gate stage
        # It will only make LLM calls after user confirms (handled by orchestrator)
        
        # Format response (raw gate response) - return raw, orchestrator will format
        raw_ai_reply = await self._format_gate_response(gate_result, user_id=user_id, session_id=session_id)
        
        # Initialize return data structure
        buttons = None
        button_context = None
        button_metadata = None
        completion_status = {
            "is_complete": gate_result.pass_,
            "completion_reason": gate_result.decision.value if hasattr(gate_result.decision, 'value') else str(gate_result.decision),
            "ready_for_handoff": gate_result.pass_
        }
        
        # CRITICAL: If gates are complete, build confirmation message and buttons
        if gate_result.pass_:
            # Gates complete - show dynamic summary and ask for confirmation
            gate_state = gate_result.proposed_state
            
            # Build dynamic summary of collected answers
            summary_parts = ["## Summary of Collected Information\n\n"]
            summary_parts.append(f"**Problem Statement:** {gate_state.summary}\n\n")
            summary_parts.append("**Your Answers:**\n\n")
            
            # Dynamically iterate through all gates in order
            for gate_key in gate_config.gate_order:
                gate_def = gate_config.gates.get(gate_key)
                gate_value = gate_state.gates.get(gate_key)
                
                if gate_def and gate_value and gate_value.classified:
                    summary_parts.append(f"**{gate_def.question}**\n")
                    summary_parts.append(f"→ {gate_value.classified}")
                    if gate_value.raw:
                        summary_parts.append(f" (from: \"{gate_value.raw}\")")
                    summary_parts.append("\n\n")
            
            summary_parts.append("---\n\n")
            summary_parts.append("**Please review the information above.**\n\n")
            summary_parts.append("Is this correct?")
            
            raw_ai_reply = "".join(summary_parts)
            
            # --- EMIT ARTIFACTS WITH PROBLEM STATEMENT (Confirmation Summary) ---
            # The confirmation summary becomes the problem statement for live builder
            problem_statement = gate_state.summary  # This is the synthesized summary
            
            # Emit PROBLEM_STATEMENT artifact
            await agent.emit("ARTIFACTS", {
                "type": "PROBLEM_STATEMENT",
                "data": {
                    "problem_statement": problem_statement,
                    "gate_state": asdict(gate_state) if isinstance(gate_state, GateState) else gate_state
                },
                "summary": "Problem statement finalized from gate collection"
            })
            
            # Update draft plan with this problem statement (no LLM call)
            # CONTRACT: Gate Agent retrieves template and passes it to planner
            template = await self._retrieve_template_for_planner(strategy=strategy, domain="eligibility")
            try:
                updated_draft = await planner_brain.update_draft(
                    transcript=transcript,
                    context={
                        "gate_state": gate_state,
                        "gate_config": gate_config,  # Pass gate_config for gate metadata
                        "session_id": session_id,
                        "strategy": strategy,
                        "manuals": rag_data,
                        "problem_statement": problem_statement,  # Explicit problem statement from confirmation
                        "template": template  # CONTRACT: Gate Agent passes template to planner
                    }
                )
                
                # Emit updated draft plan with problem statement
                await agent.emit("ARTIFACTS", {
                    "type": "DRAFT_PLAN",
                    "data": updated_draft,
                    "summary": "Draft plan updated with final problem statement"
                })
                
                logging.debug(f"[SHAPING_MANAGER] Emitted problem statement and updated draft plan for live builder")
            except Exception as e:
                logging.error(f"[SHAPING_MANAGER] Failed to update draft with problem statement: {e}", exc_info=True)
            
            # Build confirmation buttons (don't emit - return for orchestrator)
            buttons = [
                {
                    "id": "gate_confirm_yes",
                    "label": "Confirm & Proceed",
                    "variant": "primary",
                    "action": {
                        "type": "api_call",
                        "endpoint": f"/api/workflows/shaping/{session_id}/chat",
                        "method": "POST",
                        "payload": {
                            "message": "okay",
                            "user_id": user_id or "user_123"
                        }
                    },
                    "enabled": True,
                    "icon": "check",
                    "tooltip": "Confirm the information is correct and proceed to planning"
                },
                {
                    "id": "gate_confirm_edit",
                    "label": "Edit Answers",
                    "variant": "secondary",
                    "action": {
                        "type": "api_call",
                        "endpoint": f"/api/workflows/shaping/{session_id}/chat",
                        "method": "POST",
                        "payload": {
                            "message": "edit",
                            "user_id": user_id or "user_123"
                        }
                    },
                    "enabled": True,
                    "icon": "edit",
                    "tooltip": "Modify your answers"
                }
            ]
            button_context = "gate_confirmation"
            button_metadata = {"gate_key": "confirmation", "session_id": session_id}
            
            # Mark that we're waiting for confirmation (don't transition yet)
            completion_status = {
                "is_complete": False,  # Not complete until user confirms
                "completion_reason": "awaiting_user_confirmation",
                "ready_for_handoff": False  # Don't hand off until confirmed
            }
            
            logging.debug(f"[SHAPING_MANAGER] Gates complete - returning confirmation data")
        else:
            # Gates not complete - prepare router buttons for next gate
            if gate_result.next_gate:
                # Build router buttons (don't emit - return for orchestrator)
                gate_def = gate_config.gates.get(gate_result.next_gate)
                if gate_def and gate_def.expected_categories:
                    buttons = []
                    for category in gate_def.expected_categories:
                        buttons.append({
                            "id": f"gate_{gate_result.next_gate}_{category.lower().replace(' ', '_').replace('/', '_')}",
                            "label": category,
                            "variant": "secondary",
                            "action": {
                                "type": "api_call",
                                "endpoint": f"/api/workflows/shaping/{session_id}/chat",
                                "method": "POST",
                                "payload": {
                                    "message": category,
                                    "user_id": user_id or "user_123"
                                }
                            },
                            "enabled": True,
                            "tooltip": f"Select: {category}"
                        })
                    
                    # Add "Other" option
                    buttons.append({
                        "id": f"gate_{gate_result.next_gate}_other",
                        "label": "Other",
                        "variant": "secondary",
                        "action": {
                            "type": "event",
                            "eventName": "gate_other_selected",
                            "payload": {"gate_key": gate_result.next_gate}
                        },
                        "enabled": True,
                        "tooltip": "Select if none of the above apply"
                    })
                    button_context = "gate_question"
                    button_metadata = {"gate_key": gate_result.next_gate}
        
        # Persist raw response in transcript (orchestrator will format before emitting)
        msg_obj = {"role": "system", "content": raw_ai_reply, "timestamp": "now"}
        if completion_status:
            msg_obj["completion_status"] = completion_status
            
        transcript.append(msg_obj)

        # Persist transcript immediately so orchestrator can see completion_status
        transcript_query = "UPDATE shaping_sessions SET transcript = :transcript, updated_at = CURRENT_TIMESTAMP WHERE id = :id"
        await database.execute(query=transcript_query, values={
            "transcript": json.dumps(transcript),
            "id": session_id
        })
        
        # Return raw data for orchestrator to format and emit
        return {
            "raw_message": raw_ai_reply,
            "buttons": buttons,
            "button_context": button_context,
            "button_metadata": button_metadata,
            "completion_status": completion_status,
            "gate_state": gate_result.proposed_state
        }
        

    async def get_session(self, session_id: int) -> Optional[Dict[str, Any]]:
        query = "SELECT * FROM shaping_sessions WHERE id = :id"
        row = await database.fetch_one(query=query, values={"id": session_id})
        if not row:
            return None
        
        session_data = dict(row)
        for field in ["transcript", "draft_plan", "rag_citations"]:
            if isinstance(session_data.get(field), str):
                try:
                    session_data[field] = json.loads(session_data[field])
                except Exception:
                    session_data[field] = [] if field == "transcript" else {} 
        return session_data

    async def _log_activity(self, user_id: int, session_id: int, query: str):
        # Quick helper to feed the 'Recent Activity' sidebar
        # Fire and forget - don't block the response
        async def _log():
            from nexus.modules.database import database
            meta = json.dumps({"title": f"{query[:30]}...", "status": "Drafting"})
            q = """
            INSERT INTO user_activity (user_id, module, resource_id, resource_metadata)
            VALUES (:uid, 'WORKFLOW', :rid, :meta)
            """
            try:
                await database.execute(query=q, values={"uid": user_id, "rid": str(session_id), "meta": meta})
            except Exception as e:
                logging.warning(f"Failed to log activity: {e}")
        
        # Don't await - fire and forget
        asyncio.create_task(_log())

shaping_manager = ShapingManager()
