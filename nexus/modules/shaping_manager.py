import logging
import asyncio
from typing import List, Optional, Dict, Any
import json
from dataclasses import asdict
from nexus.brains.consultant import consultant_brain  # Only for decide_strategy
from nexus.brains.gate_engine import GateEngine
from nexus.brains.planner import planner_brain
from nexus.core.base_agent import BaseAgent # New Streaming Core
from nexus.core.json_parser import json_parser
from nexus.core.gate_models import GateConfig, GateDef, GateState, GateValue, StatusInfo
from nexus.modules.prompt_manager import prompt_manager
from nexus.services.gate.state_repository import GateStateRepository
from nexus.services.gate.config_loader import GateConfigLoader
from nexus.services.shaping.session_repository import ShapingSessionRepository

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
        self.state_repository = GateStateRepository()
        self.config_loader = GateConfigLoader()
        self.session_repository = ShapingSessionRepository()
    
    async def _load_gate_state(self, session_id: int) -> Optional[GateState]:
        """Load gate state from database. Delegates to GateStateRepository."""
        return await self.state_repository.load(session_id)
    
    async def _save_gate_state(self, session_id: int, gate_state: GateState) -> None:
        """Save gate state to database. Delegates to GateStateRepository."""
        await self.state_repository.save(session_id, gate_state)
    
    async def _load_gate_config(self, strategy: str, session_id: Optional[int] = None) -> Optional[GateConfig]:
        """Load gate config from prompt. Delegates to GateConfigLoader."""
        return await self.config_loader.load(strategy, session_id)
    
    async def _format_gate_response(self, result, user_id: Optional[str] = None, session_id: Optional[int] = None) -> str:
        """
        Format GateEngine result for display, returning raw response (formatting happens at emission).
        
        For gate questions, we send a simple, structured message to the conversational agent.
        For LLM responses (summaries, status updates), we pass them through as-is so the
        conversational agent can contextualize them using conversation history.
        """
        # If we have a next question, send simple instruction to conversational agent
        if result.next_question:
            # Simple, structured message: tell conversational agent exactly what to do
            # This prevents it from interpreting summaries or adding context
            gate_number = result.next_gate.split('_')[0] if result.next_gate and '_' in result.next_gate else "next"
            raw_response = f"GATE_QUESTION: Ask the user this question:\n\n{result.next_question}"
            logging.debug(f"[SHAPING_MANAGER] Formatting gate question (gate {gate_number}): {result.next_question}")
            return raw_response
        
        # For LLM responses (summaries, status updates), pass through as-is
        # Conversational agent will contextualize using conversation history
        if result.proposed_state.summary:
            # Just return the summary - conversational agent will format it with context
            return result.proposed_state.summary
        
        # If gates are complete but no summary, return completion message
        if result.pass_:
            return "All required information has been collected. Ready to proceed with building your workflow plan."
        
        return "Processing your request..."
    
    def _build_gate_buttons_from_config(
        self,
        gate_key: str,
        gate_def: GateDef,
        session_id: int,
        user_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Build buttons from gate config (config-driven) or fallback to defaults.
        
        Args:
            gate_key: The gate key
            gate_def: The gate definition
            session_id: Session ID for endpoint template
            user_id: User ID for payload
            
        Returns:
            List of button configurations
        """
        if not gate_def.expected_categories:
            return []
        
        buttons = []
        button_config = gate_def.button_config or {}
        
        # Get display labels from config or use defaults
        display_labels = button_config.get("display_labels", {})
        
        # Get button template from config or use defaults
        button_template = button_config.get("button_template", {})
        default_variant = button_template.get("variant", "secondary")
        default_action_type = button_template.get("action_type", "api_call")
        default_endpoint_template = button_template.get("endpoint_template", "/api/workflows/shaping/{session_id}/chat")
        default_method = button_template.get("method", "POST")
        default_tooltip_template = button_template.get("tooltip_template", "Select: {label}")
        
        # CRITICAL: Deduplicate expected_categories to prevent duplicate buttons
        # Use a set to track seen categories (case-insensitive for labels, but preserve original case)
        seen_categories = set()
        unique_categories = []
        duplicates_found = []
        for category in gate_def.expected_categories:
            category_lower = category.lower().strip()
            if category_lower not in seen_categories:
                seen_categories.add(category_lower)
                unique_categories.append(category)
            else:
                duplicates_found.append(category)
        
        # Build buttons for each unique category
        # Also track button IDs to prevent duplicates (in case category normalization creates same ID)
        seen_button_ids = set()
        for category in unique_categories:
            display_label = display_labels.get(category, category)
            button_id = f"gate_{gate_key}_{category.lower().replace(' ', '_').replace('/', '_')}"
            
            # Skip if button ID already exists (prevents duplicates from category normalization edge cases)
            if button_id in seen_button_ids:
                continue
            
            seen_button_ids.add(button_id)
            
            # Resolve endpoint template
            endpoint = default_endpoint_template.format(session_id=session_id)
            
            button = {
                "id": button_id,
                "label": display_label,
                "value": category,  # Original category for LLM classification
                "variant": default_variant,
                "action": {
                    "type": default_action_type,
                    "endpoint": endpoint,
                    "method": default_method,
                    "payload": {
                        "message": category,  # Send original category as message
                        "user_id": user_id or "user_123"
                    }
                },
                "enabled": True,
                "tooltip": default_tooltip_template.format(label=display_label)
            }
            buttons.append(button)
        
        # Add "Other" button if configured
        # CRITICAL: Only add "Other" button if it's not already in expected_categories
        # This prevents duplicate "Other" buttons
        include_other = button_config.get("include_other", True)  # Default: include "Other"
        other_already_in_categories = "Other" in gate_def.expected_categories or any(
            cat.lower() == "other" for cat in gate_def.expected_categories
        )
        
        if include_other and not other_already_in_categories:
            other_config = button_config.get("other_button", {})
            other_button = {
                "id": f"gate_{gate_key}_other",
                "label": other_config.get("label", "Other"),
                "variant": other_config.get("variant", "secondary"),
                "action": {
                    "type": other_config.get("action_type", "event"),
                    "eventName": other_config.get("event_name", "gate_other_selected"),
                    "payload": {"gate_key": gate_key}
                },
                "enabled": True,
                "tooltip": other_config.get("tooltip", "Select if none of the above apply")
            }
            buttons.append(other_button)
        
        return buttons
    
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
        Uses config-driven button building with fallback to defaults.
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
        
        # Build buttons from config (with fallback to defaults)
        buttons = self._build_gate_buttons_from_config(
            gate_key=gate_key,
            gate_def=gate_def,
            session_id=session_id,
            user_id=user_id
        )
        
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
    
    def _build_confirmation_buttons_from_config(
        self,
        gate_config: GateConfig,
        session_id: int,
        user_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Build confirmation buttons from config (config-driven) or fallback to defaults.
        
        Args:
            gate_config: The gate configuration
            session_id: Session ID for endpoint template
            user_id: User ID for payload
            
        Returns:
            List of button configurations
        """
        confirmation_config = gate_config.confirmation_buttons
        
        # If no config, use defaults
        if not confirmation_config or not confirmation_config.get("buttons"):
            return self._get_default_confirmation_buttons(session_id, user_id)
        
        buttons = []
        for button_def in confirmation_config.get("buttons", []):
            # Resolve template variables in action
            action = button_def.get("action", {})
            endpoint_template = action.get("endpoint_template", "/api/workflows/shaping/{session_id}/chat")
            endpoint = endpoint_template.format(session_id=session_id)
            
            # Build payload
            payload = action.get("payload", {}).copy()
            payload["user_id"] = user_id or "user_123"
            
            button = {
                "id": button_def.get("id"),
                "label": button_def.get("label"),
                "variant": button_def.get("variant", "secondary"),
                "action": {
                    "type": action.get("type", "api_call"),
                    "endpoint": endpoint,
                    "method": action.get("method", "POST"),
                    "payload": payload
                },
                "enabled": button_def.get("enabled", True),
                "icon": button_def.get("icon"),
                "tooltip": button_def.get("tooltip")
            }
            buttons.append(button)
        
        return buttons
    
    def _get_default_confirmation_buttons(
        self,
        session_id: int,
        user_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get default confirmation buttons (fallback when config not available).
        
        Args:
            session_id: Session ID for endpoint
            user_id: User ID for payload
            
        Returns:
            List of default button configurations
        """
        return [
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
            
            # Emit formatted OUTPUT and return memory_event_id
            memory_event_id = await agent.emit("OUTPUT", {"role": "system", "content": formatted_content})
            return memory_event_id
            
        except Exception as e:
            logging.warning(f"Conversational agent formatting failed: {e}, using raw response")
            # Fallback: emit raw response if formatting fails
            memory_event_id = await agent.emit("OUTPUT", {"role": "system", "content": raw_content})
            return memory_event_id

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
        
        # Build transcript with just the user message
        # System message will be added by append_message after processing the initial query
        # This allows the gate engine to extract all gates from the initial query
        transcript = [
            {"role": "user", "content": initial_query, "timestamp": "now"}
            # System message will be added by append_message after gate processing
        ]
        
        plan_data = None  # Will be created from gate_state later
        thought_content = None
        
        # 4. Create Session in DB to get ID
        # Prepare gate_state for insertion
        gate_state_dict = None
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
        
        session_id = await self.session_repository.create(
            user_id=user_id,
            strategy=strategy_result["strategy"],
            transcript=transcript,
            draft_plan=plan_data,
            rag_citations=strategy_result["context"].get("manuals", []),
            gate_state=gate_state_dict,
            iteration_count=1,  # First iteration
            max_iterations=15  # Default max iterations
        )
        
        # Set initial active_agent to 'gate'
        await self.session_repository.update_active_agent(session_id, 'gate')
        
        # NOW we have a session. Configure Agent & Stream backlog.
        agent.set_session_id(session_id)
        
        # Store initial query as OUTPUT event for timestamp tracking
        await agent.emit("OUTPUT", {"role": "user", "content": initial_query})
        
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
        
        # Note: System message will be emitted by append_message after processing the initial query
        # This allows the gate engine to extract all gates from the initial query first
        
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
                await self.session_repository.update_draft_plan(session_id, initial_draft)
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
            strategy = await self.session_repository.get_strategy(session_id) or "TABULA_RASA"
            
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
            await self.session_repository.update_draft_plan(session_id, new_draft)
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

    async def _step1_set_current_gate(
        self,
        previous_state: Optional[GateState],
        gate_config: GateConfig,
        transcript: List[Dict[str, Any]],
        session_id: int,
        user_id: str,
        strategy: str,
        agent: BaseAgent
    ) -> tuple[Optional[str], bool, Optional[Dict[str, Any]]]:
        """
        Step 1: Set Current Gate
        
        Returns:
            (current_gate, should_exit, exit_result)
            - current_gate: The gate key to process, or None
            - should_exit: True if we should exit early (confirmation handled)
            - exit_result: Result dict if should_exit is True
        """
        # If first time: Set current gate to gate 1
        if not previous_state or not previous_state.gates:
            first_gate = gate_config.gate_order[0] if gate_config.gate_order else None
            logging.debug(f"[SHAPING_MANAGER] Step 1: First time - setting current_gate to {first_gate}")
            return (first_gate, False, None)
        
        # Check if awaiting confirmation
        is_awaiting_confirmation = (
            not previous_state.status.pass_ and 
            previous_state.status.next_gate is None and
            len(previous_state.gates) > 0
        )
        
        gates_already_complete = previous_state.status.pass_
        
        if is_awaiting_confirmation or gates_already_complete:
            # Awaiting confirmation - check user action
            if not transcript:
                # No transcript - use next_gate from state
                return (previous_state.status.next_gate, False, None)
            
            user_text_lower = transcript[-1].get('content', '').lower().strip()
            
            # Detect confirmation phrases
            confirmation_phrases = ["okay", "ok", "yes", "correct", "that's right", "proceed", 
                                   "that works", "looks good", "sounds good", "confirmed", "good", "fine"]
            is_confirmation = any(phrase in user_text_lower for phrase in confirmation_phrases)
            
            # Detect edit requests
            edit_phrases = ["edit", "change", "modify", "update", "wrong", "incorrect", "fix", "no", "not"]
            is_edit = any(phrase in user_text_lower for phrase in edit_phrases)
            
            if is_confirmation:
                # User confirmed - mark as complete and exit
                logging.debug(f"[SHAPING_MANAGER] Step 1: User confirmed - marking complete and exiting")
                
                confirmed_gate_state = GateState(
                    summary=previous_state.summary,
                    gates=previous_state.gates,
                    status=StatusInfo(
                        pass_=True,
                        next_gate=None,
                        next_query=None
                    )
                )
                await self._save_gate_state(session_id, confirmed_gate_state)
                
                completion_status = {
                    "is_complete": True,
                    "completion_reason": "user_confirmed",
                    "ready_for_handoff": True
                }
                
                transcript.append({
                    "role": "system", 
                    "content": "",
                    "timestamp": "now",
                    "completion_status": completion_status
                })
                
                await self.session_repository.update_transcript(session_id, transcript)
                
                # Emit HANDOFF artifact
                gate_state = await self._load_gate_state(session_id)
                if gate_state and gate_config:
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
                    # Save draft plan to database after handoff/confirmation
                    try:
                        await self.session_repository.update_draft_plan(session_id, draft_plan)
                        logging.debug(f"[SHAPING_MANAGER] Saved draft plan to database after handoff | gates_count={len(draft_plan.get('gates', []))}")
                    except Exception as e:
                        logging.error(f"[SHAPING_MANAGER] Failed to save draft plan to database: {e}", exc_info=True)
                    
                    await agent.emit("ARTIFACTS", {
                        "type": "HANDOFF",
                        "data": {
                            "status": "confirmed", 
                            "gate_state": asdict(gate_state) if isinstance(gate_state, GateState) else gate_state,
                            "draft_plan": draft_plan
                        },
                        "summary": "User confirmed gate answers - ready for planning phase"
                    })
                
                return (None, True, {
                    "raw_message": "",
                    "buttons": None,
                    "button_context": None,
                    "button_metadata": None,
                    "completion_status": completion_status,
                    "gate_state": gate_state
                })
            
            else:
                # User said something else (not confirmation) - reset confirmation state
                # Step 2 will handle both button clicks and text input, so no special processing needed
                logging.debug(f"[SHAPING_MANAGER] Step 1: User response not confirmation - resetting confirmation state, using next_gate")
                
                # Reset state to allow editing - use next_gate from state
                # If next_gate is None, find last answered gate (better UX than starting from first)
                next_gate = previous_state.status.next_gate
                if next_gate is None:
                    # Find first missing gate (if any)
                    for gate_key in gate_config.gate_order:
                        gate_value = previous_state.gates.get(gate_key)
                        if not gate_value or not gate_value.classified:
                            next_gate = gate_key
                            break
                    # If all gates are answered, use last answered gate (better than first)
                    if next_gate is None:
                        # Find last answered gate (most recent)
                        for gate_key in reversed(gate_config.gate_order):
                            gate_value = previous_state.gates.get(gate_key)
                            if gate_value and gate_value.classified:
                                next_gate = gate_key
                                break
                        # Fallback to first gate if no gates answered (shouldn't happen)
                        if next_gate is None:
                            next_gate = gate_config.gate_order[0] if gate_config.gate_order else None
                
                reset_gate_state = GateState(
                    summary=previous_state.summary,
                    gates=previous_state.gates,
                    status=StatusInfo(
                        pass_=False,
                        next_gate=next_gate,
                        next_query=None
                    )
                )
                await self._save_gate_state(session_id, reset_gate_state)
                return (next_gate, False, None)
        
        # Normal flow: Use previous_state.status.next_gate
        current_gate = previous_state.status.next_gate if previous_state else None
        
        # Exception: If confirmation state exists but user did not confirm → Reset as starting fresh
        if current_gate is None and previous_state and len(previous_state.gates) > 0:
            # Check if we're in a confirmation state (gates complete but not confirmed)
            if not previous_state.status.pass_ and previous_state.status.next_gate is None:
                logging.debug(f"[SHAPING_MANAGER] Step 1: Confirmation state exists but not confirmed - resetting to gate 1")
                # Reset as starting fresh
                reset_state = GateState(
                    summary="",
                    gates={},
                    status=StatusInfo(
                        pass_=False,
                        next_gate=gate_config.gate_order[0] if gate_config.gate_order else None,
                        next_query=None
                    )
                )
                await self._save_gate_state(session_id, reset_state)
                return (gate_config.gate_order[0] if gate_config.gate_order else None, False, None)
        
        # If still no current_gate, default to first gate
        if current_gate is None:
            current_gate = gate_config.gate_order[0] if gate_config.gate_order else None
        
        logging.debug(f"[SHAPING_MANAGER] Step 1: Current gate set to {current_gate}")
        return (current_gate, False, None)

    async def _step2_determine_pass_fail(
        self,
        current_gate: Optional[str],
        gate_config: GateConfig,
        previous_state: Optional[GateState],
        user_text: str,
        transcript: List[Dict[str, Any]],
        session_id: int,
        user_id: str,
        agent: BaseAgent
    ) -> tuple[Optional[Any], bool, Optional[Dict[str, Any]], bool]:
        """
        Step 2: Determine Pass/Fail Status
        
        Returns:
            (gate_result, should_stop, stop_result, state_already_saved)
            - gate_result: ConsultantResult from gate processing, or None if stopped early
            - should_stop: True if workflow should stop (limiting value found)
            - stop_result: Result dict if should_stop is True
            - state_already_saved: True if state was already saved in this step
        """
        if not current_gate:
            return (None, False, None, False)
        
        gate_def = gate_config.gates.get(current_gate)
        if not gate_def:
            return (None, False, None, False)
        
        # Get user input - use original_value if available (button clicks)
        last_user_msg = transcript[-1] if transcript else {}
        user_text_for_gate = last_user_msg.get("original_value") or user_text
        
        # Check if this is a button click (has original_value)
        is_button_click = last_user_msg.get("original_value") is not None
        
        # Also check if content itself matches an expected category (fallback for button clicks not detected)
        # This handles cases where conversational agent didn't set original_value
        if not is_button_click and gate_def.expected_categories:
            user_input_normalized = user_text.strip()
            user_input_lower = user_input_normalized.lower()
            for category in gate_def.expected_categories:
                if user_input_normalized == category or user_input_lower == category.lower():
                    # Content matches expected category - treat as button click
                    is_button_click = True
                    user_text_for_gate = category  # Use exact category value
                    logging.debug(f"[SHAPING_MANAGER] Step 2: Detected button click pattern - content '{user_text}' matches category '{category}'")
                    # Update transcript to set original_value for future reference
                    if transcript and last_user_msg.get("role") == "user":
                        last_user_msg["original_value"] = category
                    break
        
        gate_result = None
        state_already_saved = False
        
        # If gate 1: Check if we should use LLM (first time with complex input) or direct matching (button clicks)
        if current_gate == gate_config.gate_order[0] if gate_config.gate_order else None:
            # If first time (no previous state) and not a button click, use LLM to extract all gates
            # This allows users to provide all gate information in the first message
            is_first_time = not previous_state or not previous_state.gates
            
            if is_first_time and not is_button_click:
                # First message and not a button click - likely contains all gate info
                # Use LLM to extract all gates
                logging.debug(f"[SHAPING_MANAGER] Step 2: Gate 1 - first time with text input, using LLM to extract all gates")
                # Fall through to LLM extraction path below (skip direct matching)
            else:
                # Button click or not first time - use direct matching for gate 1
                logging.debug(f"[SHAPING_MANAGER] Step 2: Gate 1 - using direct matching only")
                
                # Check for direct category match
                if gate_def.expected_categories:
                    user_input_normalized = user_text_for_gate.strip()
                    user_input_lower = user_input_normalized.lower()
                    
                    matched_category = None
                    for category in gate_def.expected_categories:
                        if user_input_normalized == category:
                            matched_category = category
                            break
                        elif user_input_lower == category.lower():
                            matched_category = category
                            break
                    
                    if matched_category:
                        # Direct match - set gate value
                        from datetime import datetime
                        updated_gates = previous_state.gates.copy() if previous_state else {}
                        updated_gates[current_gate] = GateValue(
                            raw=user_text_for_gate,
                            classified=matched_category,
                            confidence=1.0,
                            collected_at=datetime.now()
                        )
                        
                        updated_state = GateState(
                            summary=previous_state.summary if previous_state else "",
                            gates=updated_gates,
                            status=previous_state.status if previous_state else StatusInfo(pass_=False, next_gate=None, next_query=None)
                        )
                        
                        # Check limiting_values
                        if gate_def.limiting_values and matched_category in gate_def.limiting_values:
                            # Gate failed - stop workflow
                            stop_state = GateState(
                                summary=f"Cannot proceed: {gate_def.question}",
                                gates=updated_gates,
                                status=StatusInfo(
                                    pass_=True,
                                    next_gate=None,
                                    next_query=None
                                )
                            )
                            await self._save_gate_state(session_id, stop_state)
                            stop_message = gate_def.stop_message or f"I understand. Based on your answer, we cannot proceed with this workflow."
                            return (None, True, {
                                "raw_message": stop_message,
                                "buttons": None,
                                "button_context": None,
                                "button_metadata": None,
                                "completion_status": {
                                    "is_complete": True,
                                    "completion_reason": f"gate_{current_gate}_limiting_value",
                                    "ready_for_handoff": False
                                },
                                "gate_state": stop_state
                            }, True)
                        
                        # Gate passed - continue
                        from nexus.engines.gate.gate_selector import GateSelector
                        from nexus.engines.gate.completion_checker import GateCompletionChecker
                        from nexus.core.gate_models import ConsultantResult, GateDecision
                        
                        gate_selector = GateSelector()
                        completion_checker = GateCompletionChecker()
                        
                        next_gate_key = gate_selector.select_next(
                            gate_config=gate_config,
                            current_state=updated_state,
                            llm_recommendation=None
                        )
                        
                        completion_result = completion_checker.check(
                            gate_config=gate_config,
                            current_state=updated_state,
                            user_override=False
                        )
                        
                        final_state = GateState(
                            summary=updated_state.summary,
                            gates=updated_state.gates,
                            status=StatusInfo(
                                pass_=completion_result[0],
                                next_gate=next_gate_key,
                                next_query=gate_selector.get_question_for_gate(next_gate_key, gate_config) if next_gate_key else None
                            )
                        )
                        
                        gate_result = ConsultantResult(
                            decision=completion_result[1],
                            pass_=completion_result[0],
                            next_gate=next_gate_key,
                            next_question=final_state.status.next_query,
                            proposed_state=final_state,
                            updated_gates=[current_gate]
                        )
                        
                        await self._save_gate_state(session_id, final_state)
                        state_already_saved = True
                        return (gate_result, False, None, state_already_saved)
                    else:
                        # Gate 1: No match found - if first time, fall through to LLM; otherwise return None
                        if is_first_time and not is_button_click:
                            # First time with no match - use LLM to extract all gates
                            logging.debug(f"[SHAPING_MANAGER] Step 2: Gate 1 - first time, no direct match, using LLM to extract all gates")
                            # Fall through to LLM extraction path below
                        else:
                            # Not first time or button click - return None to trigger extraction failure handling
                            logging.warning(f"[SHAPING_MANAGER] Step 2: Gate 1 - no category match for input '{user_text_for_gate}'. Expected: {gate_def.expected_categories}")
                            return (None, False, None, False)
                else:
                    # Gate 1: No expected_categories defined - if first time, use LLM; otherwise error
                    if is_first_time and not is_button_click:
                        logging.debug(f"[SHAPING_MANAGER] Step 2: Gate 1 - first time, no expected_categories, using LLM to extract all gates")
                        # Fall through to LLM extraction path below
                    else:
                        logging.error(f"[SHAPING_MANAGER] Step 2: Gate 1 has no expected_categories defined")
                        return (None, False, None, False)
        
        # For other gates: If button click, check limiting_values directly; else call LLM
        if is_button_click:
            # Button click - check if value matches limiting_values
            if gate_def.limiting_values:
                user_input_normalized = user_text_for_gate.strip()
                user_input_lower = user_input_normalized.lower()
                limiting_values_lower = [v.lower() for v in gate_def.limiting_values]
                
                if user_text_for_gate in gate_def.limiting_values or user_input_lower in limiting_values_lower:
                    # Gate failed - stop workflow
                    from datetime import datetime
                    matched_value = user_text_for_gate if user_text_for_gate in gate_def.limiting_values else next((v for v in gate_def.limiting_values if v.lower() == user_input_lower), user_text_for_gate)
                    
                    stop_gates = previous_state.gates.copy() if previous_state else {}
                    stop_gates[current_gate] = GateValue(
                        raw=user_text_for_gate,
                        classified=matched_value,
                        confidence=1.0,
                        collected_at=datetime.now()
                    )
                    
                    stop_state = GateState(
                        summary=f"Cannot proceed: {gate_def.question}",
                        gates=stop_gates,
                        status=StatusInfo(
                            pass_=True,
                            next_gate=None,
                            next_query=None
                        )
                    )
                    await self._save_gate_state(session_id, stop_state)
                    stop_message = gate_def.stop_message or f"I understand. Based on your answer, we cannot proceed with this workflow."
                    return (None, True, {
                        "raw_message": stop_message,
                        "buttons": None,
                        "button_context": None,
                        "button_metadata": None,
                        "completion_status": {
                            "is_complete": True,
                            "completion_reason": f"gate_{current_gate}_limiting_value",
                            "ready_for_handoff": False
                        },
                        "gate_state": stop_state
                    }, True)
            
            # Button click but not limiting - use direct matching
            if gate_def.expected_categories:
                user_input_normalized = user_text_for_gate.strip()
                user_input_lower = user_input_normalized.lower()
                
                matched_category = None
                for category in gate_def.expected_categories:
                    if user_input_normalized == category:
                        matched_category = category
                        break
                    elif user_input_lower == category.lower():
                        matched_category = category
                        break
                
                if matched_category:
                    # Direct match - set gate value
                    from datetime import datetime
                    updated_gates = previous_state.gates.copy() if previous_state else {}
                    updated_gates[current_gate] = GateValue(
                        raw=user_text_for_gate,
                        classified=matched_category,
                        confidence=1.0,
                        collected_at=datetime.now()
                    )
                    
                    updated_state = GateState(
                        summary=previous_state.summary if previous_state else "",
                        gates=updated_gates,
                        status=previous_state.status if previous_state else StatusInfo(pass_=False, next_gate=None, next_query=None)
                    )
                    
                    from nexus.engines.gate.gate_selector import GateSelector
                    from nexus.engines.gate.completion_checker import GateCompletionChecker
                    from nexus.core.gate_models import ConsultantResult, GateDecision
                    
                    gate_selector = GateSelector()
                    completion_checker = GateCompletionChecker()
                    
                    next_gate_key = gate_selector.select_next(
                        gate_config=gate_config,
                        current_state=updated_state,
                        llm_recommendation=None
                    )
                    
                    completion_result = completion_checker.check(
                        gate_config=gate_config,
                        current_state=updated_state,
                        user_override=False
                    )
                    
                    final_state = GateState(
                        summary=updated_state.summary,
                        gates=updated_state.gates,
                        status=StatusInfo(
                            pass_=completion_result[0],
                            next_gate=next_gate_key,
                            next_query=gate_selector.get_question_for_gate(next_gate_key, gate_config) if next_gate_key else None
                        )
                    )
                    
                    gate_result = ConsultantResult(
                        decision=completion_result[1],
                        pass_=completion_result[0],
                        next_gate=next_gate_key,
                        next_question=final_state.status.next_query,
                        proposed_state=final_state,
                        updated_gates=[current_gate]
                    )
                    
                    await self._save_gate_state(session_id, final_state)
                    state_already_saved = True
                    return (gate_result, False, None, state_already_saved)
                else:
                    # Button click but no match - this shouldn't happen, but handle gracefully
                    logging.error(f"[SHAPING_MANAGER] Step 2: Button click '{user_text_for_gate}' doesn't match any expected category: {gate_def.expected_categories}")
                    # Return None to trigger extraction failure handling
                    return (None, False, None, False)
            else:
                # Button click but no expected_categories - this shouldn't happen
                logging.error(f"[SHAPING_MANAGER] Step 2: Button click for gate '{current_gate}' but gate has no expected_categories")
                return (None, False, None, False)
        
        # User text input (not button click) - call LLM to extract
        logging.debug(f"[SHAPING_MANAGER] Step 2: User text input - calling LLM for extraction")
        try:
            gate_result = await self.gate_engine.execute_gate(
                user_text=user_text_for_gate,
                gate_config=gate_config,
                previous_state=previous_state,
                actor="user",
                session_id=session_id,
                user_id=user_id,
                conversation_history=transcript
            )
        except Exception as e:
            # LLM call failed - log error and return None to trigger extraction failure handling
            logging.error(f"[SHAPING_MANAGER] Step 2: LLM extraction failed: {e}", exc_info=True)
            return (None, False, None, False)
        
        # Check if gate_result is None (shouldn't happen, but handle gracefully)
        if gate_result is None:
            logging.error(f"[SHAPING_MANAGER] Step 2: gate_engine.execute_gate returned None")
            return (None, False, None, False)
        
        # Check if any gate has limiting_values after LLM extraction
        should_stop = False
        stop_gate_key = None
        stop_classification = None
        stop_message = None
        
        for gate_key, g_def in gate_config.gates.items():
            if not g_def.limiting_values:
                continue
            
            gate_value = gate_result.proposed_state.gates.get(gate_key)
            if gate_value and gate_value.classified in g_def.limiting_values:
                should_stop = True
                stop_gate_key = gate_key
                stop_classification = gate_value.classified
                stop_message = g_def.stop_message
                break
        
        if should_stop:
            stop_state = GateState(
                summary=gate_result.proposed_state.summary or f"Cannot proceed: {gate_config.gates[stop_gate_key].question}",
                gates=gate_result.proposed_state.gates,
                status=StatusInfo(
                    pass_=True,
                    next_gate=None,
                    next_query=None
                )
            )
            await self._save_gate_state(session_id, stop_state)
            
            from nexus.core.gate_models import ConsultantResult, GateDecision
            gate_result = ConsultantResult(
                decision=GateDecision.PASS_REQUIRED_GATES,
                pass_=True,
                next_gate=None,
                next_question=None,
                proposed_state=stop_state,
                updated_gates=gate_result.updated_gates if gate_result else []
            )
            
            final_stop_message = stop_message or f"I understand. Based on your answer, we cannot proceed with this workflow."
            return (gate_result, True, {
                "raw_message": final_stop_message,
                "buttons": None,
                "button_context": None,
                "button_metadata": None,
                "completion_status": {
                    "is_complete": True,
                    "completion_reason": f"gate_{stop_gate_key}_limiting_value",
                    "ready_for_handoff": False
                },
                "gate_state": stop_state
            }, True)
        
        return (gate_result, False, None, False)

    async def _step3_set_next_question(
        self,
        gate_result: Any,
        gate_config: GateConfig,
        extraction_failed: bool,
        gate_failed: bool,
        agent: BaseAgent,
        session_id: int,
        strategy: str,
        transcript: List[Dict[str, Any]],
        rag_data: List[Any]
    ) -> str:
        """
        Step 3: Set Next Question
        
        Returns:
            raw_message: The message/question to send to user
        """
        # If LLM extraction failed: Send error/fail message
        if extraction_failed:
            error_msg = "I'm having trouble understanding your response. Could you please rephrase or select one of the options?"
            await agent.emit("THINKING", {"message": "LLM extraction failed - requesting clarification"})
            return error_msg
        
        # Else if gate failed (limiting_value matched): Send stop message from config
        if gate_failed:
            # Stop message should have been set in Step 2
            # This shouldn't be reached, but handle it gracefully
            return "I understand. Based on your answer, we cannot proceed with this workflow."
        
        # Safety check: gate_result should not be None at this point, but handle gracefully
        if not gate_result:
            logging.error(f"[SHAPING_MANAGER] Step 3: gate_result is None - this should not happen")
            return "I'm having trouble processing your response. Please try again."
        
        # Else if last gate (all gates answered): Send user confirmation summary
        if gate_result.pass_:
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
            
            # Emit PROBLEM_STATEMENT artifact
            problem_statement = gate_state.summary
            try:
                await agent.emit("ARTIFACTS", {
                    "type": "PROBLEM_STATEMENT",
                    "data": {
                        "problem_statement": problem_statement,
                        "gate_state": asdict(gate_state) if isinstance(gate_state, GateState) else gate_state
                    },
                    "summary": "Problem statement finalized from gate collection"
                })
            except Exception as e:
                logging.error(f"[SHAPING_MANAGER] Failed to emit PROBLEM_STATEMENT artifact: {e}", exc_info=True)
            
            # Update draft plan with problem statement
            try:
                template = await self._retrieve_template_for_planner(strategy=strategy, domain="eligibility")
                updated_draft = await planner_brain.update_draft(
                    transcript=transcript,
                    context={
                        "gate_state": gate_state,
                        "gate_config": gate_config,
                        "session_id": session_id,
                        "strategy": strategy,
                        "manuals": rag_data,
                        "problem_statement": problem_statement,
                        "template": template
                    }
                )
                # Save draft plan to database after problem statement update
                try:
                    await self.session_repository.update_draft_plan(session_id, updated_draft)
                    logging.debug(f"[SHAPING_MANAGER] Saved draft plan to database after problem statement update | gates_count={len(updated_draft.get('gates', []))}")
                except Exception as e:
                    logging.error(f"[SHAPING_MANAGER] Failed to save draft plan to database: {e}", exc_info=True)
                
                await agent.emit("ARTIFACTS", {
                    "type": "DRAFT_PLAN",
                    "data": updated_draft,
                    "summary": "Draft plan updated with final problem statement"
                })
            except Exception as e:
                logging.error(f"[SHAPING_MANAGER] Failed to update draft with problem statement: {e}", exc_info=True)
            
            # Prefix with GATES_COMPLETE: so conversational agent knows to format it properly
            # This ensures the summary is always shown when all gates are complete
            summary_text = "".join(summary_parts)
            return f"GATES_COMPLETE: {summary_text}"
        
        # Else: Send next gate question text
        # Format response using gate result
        raw_ai_reply = await self._format_gate_response(gate_result, user_id=None, session_id=session_id)
        return raw_ai_reply

    async def _step4_establish_buttons(
        self,
        gate_result: Any,
        gate_config: GateConfig,
        current_gate: Optional[str],
        session_id: int,
        user_id: str
    ) -> tuple[Optional[List[Dict[str, Any]]], Optional[str], Optional[Dict[str, Any]], Dict[str, Any]]:
        """
        Step 4: Establish Buttons & Update Status
        
        Returns:
            (buttons, button_context, button_metadata, completion_status)
        """
        buttons = None
        button_context = None
        button_metadata = None
        completion_status = {
            "is_complete": gate_result.pass_ if gate_result else False,
            "completion_reason": gate_result.decision.value if gate_result and hasattr(gate_result.decision, 'value') else str(gate_result.decision) if gate_result else "unknown",
            "ready_for_handoff": gate_result.pass_ if gate_result else False
        }
        
        # If gates complete (awaiting confirmation): Build confirmation buttons
        if gate_result and gate_result.pass_:
            try:
                buttons = self._build_confirmation_buttons_from_config(
                    gate_config=gate_config,
                    session_id=session_id,
                    user_id=user_id
                )
                button_context = "gate_confirmation"
                button_metadata = {"gate_key": "confirmation", "session_id": session_id}
            except Exception as e:
                logging.error(f"[SHAPING_MANAGER] Failed to build confirmation buttons: {e}", exc_info=True)
                buttons = None
                button_context = None
                button_metadata = None
            
            # Mark that we're waiting for confirmation
            completion_status = {
                "is_complete": False,  # Not complete until user confirms
                "completion_reason": "awaiting_user_confirmation",
                "ready_for_handoff": False
            }
            
            # Save state with pass_ = False (awaiting confirmation)
            gate_state = gate_result.proposed_state
            try:
                confirmation_pending_state = GateState(
                    summary=gate_state.summary,
                    gates=gate_state.gates,
                    status=StatusInfo(
                        pass_=False,  # NOT complete until user confirms
                        next_gate=None,
                        next_query=None
                    )
                )
                await self._save_gate_state(session_id, confirmation_pending_state)
            except Exception as e:
                logging.error(f"[SHAPING_MANAGER] Failed to save confirmation pending state: {e}", exc_info=True)
                raise
        
        # Else if current gate has expected_categories: Build buttons for current gate
        elif gate_result and gate_result.next_gate:
            gate_def = gate_config.gates.get(gate_result.next_gate)
            if gate_def and gate_def.expected_categories:
                buttons = self._build_gate_buttons_from_config(
                    gate_key=gate_result.next_gate,
                    gate_def=gate_def,
                    session_id=session_id,
                    user_id=user_id
                )
                button_context = "gate_question"
                button_metadata = {"gate_key": gate_result.next_gate}
        
        # Else: No buttons (handled by buttons = None above)
        
        return (buttons, button_context, button_metadata, completion_status)

    async def append_message(self, session_id: int, role: str, content: str) -> Dict[str, Any]:
        """
        Appends a message to the session transcript.
        """
        agent = BaseAgent(session_id=session_id)
        
        # 2. Fetch current state using repository
        transcript = await self.session_repository.get_transcript(session_id)
        if transcript is None:
            return
        
        # Check if this is a button click that was already saved by conversational agent
        # If the last message is a user message with original_value matching this content, skip duplicate
        if role == "user" and transcript:
            last_msg = transcript[-1]
            if (last_msg.get("role") == "user" and 
                last_msg.get("original_value") == content and
                last_msg.get("content") != content):  # Button label was saved, but we have the category value
                # Update the last message to use the category value for processing
                # But keep the button label for display
                logging.debug(f"[SHAPING_MANAGER] Button click detected: updating last message to use category value '{content}' for processing")
                # Ensure original_value is set correctly (in case it wasn't set by conversational agent)
                if not last_msg.get("original_value"):
                    last_msg["original_value"] = content
                    # Update transcript in database to persist the fix
                    await self.session_repository.update_transcript(session_id, transcript)
                # Don't add duplicate - the button label is already in transcript
                # But we need to process the category value, so continue with gate engine
            else:
                # Regular message or button label not yet saved - add to transcript
                # 1. Stream the Output intent immediately (Hot Path) - only if not already emitted
                await agent.emit("OUTPUT", {"role": role, "content": content})
                transcript.append({"role": role, "content": content, "timestamp": "now"})
        else:
            # System message or first message - always emit and add
            # 1. Stream the Output intent immediately (Hot Path)
            await agent.emit("OUTPUT", {"role": role, "content": content})
            transcript.append({"role": role, "content": content, "timestamp": "now"})
        
        rag_data = await self.session_repository.get_rag_citations(session_id)
        
        # Get iteration tracking
        iteration_info = await self.session_repository.get_iteration_info(session_id)
        iteration_count = iteration_info.get("iteration_count", 0)
        max_iterations = iteration_info.get("max_iterations", 15)
        
        # --- 3. CHECK ITERATION LIMIT ---
        
        if iteration_count >= max_iterations:
            await agent.emit("THINKING", {
                "message": f"Iteration limit reached ({max_iterations}). Stopping Consultant loop and using best available plan."
            })
            # Extract best plan from current state and hand off
            current_plan = await self.session_repository.get_draft_plan(session_id) or {}
            await agent.emit("ARTIFACTS", {
                "type": "DRAFT_PLAN",
                "data": current_plan,
                "summary": "Using best available plan (iteration limit reached)"
            })
            logging.warning(f"Session {session_id} hit iteration limit ({max_iterations})")
            return
        
        # Increment iteration count (repository handles missing column gracefully)
        await self.session_repository.increment_iteration_count(session_id)
        
        # --- 4. GATE ENGINE EXECUTION ---
        await agent.emit("THINKING", {"message": "Processing your input..."})

        # A. Resolve Strategy and Load GateConfig
        user_and_strategy = await self.session_repository.get_user_and_strategy(session_id)
        if not user_and_strategy:
            logging.error(f"Session {session_id} not found")
            return
        user_id = user_and_strategy.get("user_id")
        strategy = user_and_strategy.get("consultant_strategy", "TABULA_RASA")
        
        # Load gate config
        gate_config = await self._load_gate_config(strategy, session_id=session_id)
        
        if not gate_config:
            error_msg = f"Gate config not found for strategy '{strategy}'. Prompt must have GATE_ORDER and GATES defined."
            logging.error(error_msg)
            await agent.emit("THINKING", {"message": error_msg})
            raise ValueError(error_msg)
        
        # ====================================================================
        # STEP 0: Load Gate Config & State (already done above)
        # ====================================================================
        # Gate config loaded at line 809
        # Previous state will be loaded below
        
        # Use Gate Engine
        # Load previous gate state
        previous_state = await self._load_gate_state(session_id)
        
        # ====================================================================
        # STEP 1: Set Current Gate
        # ====================================================================
        current_gate, should_exit, exit_result = await self._step1_set_current_gate(
            previous_state=previous_state,
            gate_config=gate_config,
            transcript=transcript,
            session_id=session_id,
            user_id=user_id,
            strategy=strategy,
            agent=agent
        )
        
        if should_exit:
            return exit_result
        
        # Step 1 has handled confirmation - continue with gate processing
        # current_gate is now set
        
        # ====================================================================
        # STEP 2: Determine Pass/Fail Status
        # ====================================================================
        await agent.emit("THINKING", {"message": "Executing gate engine..."})
        
        user_input = transcript[-1].get('content', content) if transcript else content
        gate_result, should_stop, stop_result, state_already_saved = await self._step2_determine_pass_fail(
            current_gate=current_gate,
            gate_config=gate_config,
            previous_state=previous_state,
            user_text=user_input,
            transcript=transcript,
            session_id=session_id,
            user_id=user_id,
            agent=agent
        )
        
        if should_stop:
            return stop_result
        
        # Save updated gate state (only if we didn't stop and haven't already saved)
        # BUT: If gates are complete, we'll save with pass_=False later (awaiting confirmation)
        # Only save here if gates are NOT complete yet AND we haven't already saved in Step 2
        if gate_result and not gate_result.pass_ and not state_already_saved:
            await self._save_gate_state(session_id, gate_result.proposed_state)
        
        # Get RAG data from session for planner context
        rag_data = await self.session_repository.get_rag_citations(session_id)
        
        # --- EMIT ARTIFACTS FOR LIVE BUILDER (After Each Gate Execution) ---
        # Every time user reacts, gate agent emits for live builder to capture and update
        # Live builder will update plan deterministically (no LLM call)
        # CONTRACT: Gate Agent retrieves template and passes it to planner
        # Only emit if gate_result is valid (not None)
        if gate_result and gate_result.proposed_state:
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
                
                # Save draft plan to database after each gate interaction
                try:
                    await self.session_repository.update_draft_plan(session_id, updated_draft)
                    logging.debug(f"[SHAPING_MANAGER] Saved draft plan to database after gate execution | gates_count={len(updated_draft.get('gates', []))}")
                except Exception as e:
                    logging.error(f"[SHAPING_MANAGER] Failed to save draft plan to database: {e}", exc_info=True)
                
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
        
        # ====================================================================
        # STEP 3: Set Next Question
        # ====================================================================
        # Check if extraction failed (gate_result is None - should not happen, but handle gracefully)
        extraction_failed = gate_result is None
        gate_failed = False  # Gate failure is handled in Step 2 (limiting_values)
        
        if extraction_failed:
            # This shouldn't happen, but handle gracefully
            logging.error(f"[SHAPING_MANAGER] Step 3: gate_result is None - this should not happen")
            return {
                "raw_message": "I'm having trouble processing your response. Please try again.",
                "buttons": None,
                "button_context": None,
                "button_metadata": None,
                "completion_status": {
                    "is_complete": False,
                    "completion_reason": "extraction_failed",
                    "ready_for_handoff": False
                },
                "gate_state": previous_state
            }
        
        raw_ai_reply = await self._step3_set_next_question(
            gate_result=gate_result,
            gate_config=gate_config,
            extraction_failed=extraction_failed,
            gate_failed=gate_failed,
            agent=agent,
            session_id=session_id,
            strategy=strategy,
            transcript=transcript,
            rag_data=rag_data
        )
        
        # ====================================================================
        # STEP 4: Establish Buttons & Update Status
        # ====================================================================
        buttons, button_context, button_metadata, completion_status = await self._step4_establish_buttons(
            gate_result=gate_result,
            gate_config=gate_config,
            current_gate=current_gate,
            session_id=session_id,
            user_id=user_id
        )
        
        # Don't persist transcript here - orchestrator will format and persist
        # The orchestrator is responsible for formatting the message and adding it to transcript
        # We just return the raw data for orchestrator to handle
        
        # Return raw data for orchestrator to format and emit
        # Use previous_state if gate_result is None (shouldn't happen, but handle gracefully)
        final_gate_state = gate_result.proposed_state if gate_result and gate_result.proposed_state else previous_state
        
        return {
            "raw_message": raw_ai_reply,
            "buttons": buttons,
            "button_context": button_context,
            "button_metadata": button_metadata,
            "completion_status": completion_status,
            "gate_state": final_gate_state
        }
        

    async def get_session(self, session_id: int) -> Optional[Dict[str, Any]]:
        return await self.session_repository.get(session_id)

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
