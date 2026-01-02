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
            return None
        
        config = prompt_data.get("config", {})
        
        # Check if this is a gate-based prompt (has GATE_ORDER)
        if "GATE_ORDER" not in config:
            return None
        
        return GateConfig.from_prompt_config(config)
    
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
        
        # 3. Load GateConfig and execute Gate Engine
        await agent.emit("THINKING", {"message": f"Strategy Selected: {strategy}"})
        
        # Load gate config
        gate_config = await self._load_gate_config(strategy, session_id=None)
        
        if not gate_config:
            error_msg = f"Gate config not found for strategy '{strategy}'. Prompt must have GATE_ORDER and GATES defined."
            logging.error(error_msg)
            await agent.emit("THINKING", {"message": error_msg})
            raise ValueError(error_msg)
        
        # Use Gate Engine
        await agent.emit("THINKING", {"message": "Executing gate engine..."})
        
        # Execute gate (first turn, no previous state)
        # Note: session_id is None initially, but we'll backfill thinking after session creation
        gate_result = await self.gate_engine.execute_gate(
            user_text=initial_query,
            gate_config=gate_config,
            previous_state=None,
            actor="user",
            session_id=None,  # Will be set after session creation
            user_id=user_id
        )
        
        # Format response (pass user_id for conversational formatting)
        raw_system_msg = await self._format_gate_response(gate_result, user_id=user_id, session_id=None)
        plan_data = None  # Will be created from gate_state later
        thought_content = None
        
        # Store gate_state (will be saved after session creation)
        initial_gate_state = gate_result.proposed_state

        # Format through conversational agent BEFORE saving to transcript
        formatted_system_msg = raw_system_msg  # Default to raw if formatting fails
        try:
            from nexus.brains.conversational_agent import conversational_agent
            
            formatted_system_msg = await conversational_agent.format_response(
                raw_response=raw_system_msg,
                user_id=user_id,
                context={"operation": "session_creation", "source": "gate_engine"}
            )
        except Exception as e:
            logging.warning(f"Conversational agent formatting failed during session creation: {e}, using raw response")
            formatted_system_msg = raw_system_msg

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
        
        # Emit journey state after gate execution and strategy selection
        from nexus.conductors.workflows.orchestrator import orchestrator
        await orchestrator._emit_journey_state_update(
            session_id=session_id,
            gate_state=gate_result.proposed_state,
            gate_config=gate_config,
            strategy=strategy_result["strategy"]
        )
        
        # User Activity Log
        await self._log_activity(user_id, session_id, initial_query)
        
        # --- 4. INITIAL PLANNER TRIGGER ---
        # We spawn this in background so the UI loads the chat immediately
        # The 'ARTIFACTS' event will push the plan to the sidebar when ready
        asyncio.create_task(self._run_initial_plan(session_id, transcript, strategy_result['context'].get('manuals', [])))

        return session_id

    async def _run_initial_plan(self, session_id: int, transcript: List[Dict[str, Any]], rag_data: List[Any]):
        """
        Helper: Runs the planner for the first time in background.
        """
        agent = BaseAgent(session_id=session_id)
        try:
            # await agent.emit("THINKING", {"message": "Drafting initial plan based on manual..."})
            # (Optional: Don't spam thinking for background tasks if it clashes with main thread)
            
            # Load gate_state if available
            gate_state = await self._load_gate_state(session_id)
            context = {"manuals": rag_data, "gate_state": gate_state, "session_id": session_id}
            
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

    async def append_message(self, session_id: int, role: str, content: str) -> None:
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
        
        # Format response (raw gate response)
        raw_ai_reply = await self._format_gate_response(gate_result, user_id=user_id, session_id=session_id)
        plan_data = None  # Will be created from gate_state if needed
        completion_status = {
            "is_complete": gate_result.pass_,
            "completion_reason": gate_result.decision.value if hasattr(gate_result.decision, 'value') else str(gate_result.decision),
            "ready_for_handoff": gate_result.pass_
        }
        thought_content = None

        # Format through conversational agent BEFORE saving to transcript
        formatted_ai_reply = raw_ai_reply  # Default to raw if formatting fails
        
        # Ensure we always format completion messages through conversational agent
        # If response is empty or just whitespace, create a meaningful completion message
        if not raw_ai_reply or not raw_ai_reply.strip():
            raw_ai_reply = "All required information has been collected. Ready to proceed with workflow planning."
        
        try:
            from nexus.brains.conversational_agent import conversational_agent
            
            logging.debug(f"[SHAPING_MANAGER] Formatting response through conversational agent (length: {len(raw_ai_reply)})")
            formatted_ai_reply = await conversational_agent.format_response(
                raw_response=raw_ai_reply,
                user_id=user_id,
                context={"operation": "chat_response", "source": "gate_engine", "session_id": session_id}
            )
            logging.debug(f"[SHAPING_MANAGER] Conversational agent returned formatted response (length: {len(formatted_ai_reply)})")
        except Exception as e:
            logging.error(f"[SHAPING_MANAGER] Conversational agent formatting failed during append_message: {e}", exc_info=True)
            formatted_ai_reply = raw_ai_reply

        # Emit the formatted OUTPUT (already formatted, so emit directly)
        await agent.emit("OUTPUT", {"role": "system", "content": formatted_ai_reply})
        
        # Emit journey state update after gate execution
        from nexus.conductors.workflows.orchestrator import orchestrator
        await orchestrator._emit_journey_state_update(
            session_id=session_id,
            gate_state=gate_result.proposed_state,
            gate_config=gate_config,
            strategy=strategy
        )
        
        # Persist FORMATTED response in transcript
        msg_obj = {"role": "system", "content": formatted_ai_reply, "timestamp": "now"}
        if thought_content:
            msg_obj["thought"] = thought_content
        if completion_status:
            msg_obj["completion_status"] = completion_status
            
        transcript.append(msg_obj)
        
        # --- 5. CHECK COMPLETION STATUS ---
        if completion_status and completion_status.get("is_complete"):
            await agent.emit("THINKING", {
                "message": f"Gate collection complete: {completion_status.get('completion_reason', 'unknown')}"
            })
            # Reset iteration count on completion (skip if column doesn't exist)
            try:
                await database.execute(
                    "UPDATE shaping_sessions SET consultant_iteration_count = 0 WHERE id = :id",
                    {"id": session_id}
                )
            except Exception as e:
                logging.debug(f"Could not reset iteration count: {e}")
            # Hand off to Planner
            if completion_status.get("ready_for_handoff"):
                # Load gate_state and convert to living document format
                gate_state = await self._load_gate_state(session_id)
                if gate_state and gate_config:
                    # Use module-level planner_brain import (line 8), not local import
                    living_doc = planner_brain.map_gate_state_to_living_document(
                        gate_state=gate_state,
                        gate_config=gate_config
                    )
                    await agent.emit("ARTIFACTS", {
                        "type": "HANDOFF",
                        "data": {
                            "status": "ready", 
                            "gate_state": asdict(gate_state) if isinstance(gate_state, GateState) else gate_state, 
                            "living_doc": living_doc
                        },
                        "summary": "Ready for Planner handoff"
                    })
                
                # --- TRANSITION TO PLANNING PHASE ---
                # Emit user-facing message about transition to planning
                transition_message = "All required information has been collected. Moving to the planning phase to build your workflow."
                
                # Format through conversational agent
                formatted_transition = transition_message
                try:
                    from nexus.brains.conversational_agent import conversational_agent
                    
                    logging.debug(f"[SHAPING_MANAGER] Formatting planning transition message through conversational agent")
                    formatted_transition = await conversational_agent.format_response(
                        raw_response=transition_message,
                        user_id=user_id,
                        context={"operation": "planning_transition", "source": "gate_engine", "session_id": session_id}
                    )
                except Exception as e:
                    logging.warning(f"Conversational agent formatting failed for transition message: {e}, using raw response")
                    formatted_transition = transition_message
                
                # Emit the formatted transition message
                await agent.emit("OUTPUT", {"role": "system", "content": formatted_transition})
                
                # Add transition message to transcript
                transcript.append({"role": "system", "content": formatted_transition, "timestamp": "now"})
                
                # Persist transcript with transition message
                transcript_query = "UPDATE shaping_sessions SET transcript = :transcript, updated_at = CURRENT_TIMESTAMP WHERE id = :id"
                await database.execute(query=transcript_query, values={
                    "transcript": json.dumps(transcript),
                    "id": session_id
                })
                await agent.emit("PERSISTENCE", {"action": "UPDATE_TRANSCRIPT", "id": session_id})
                
                # --- INVOKE PLANNER (STUB) ---
                await agent.emit("THINKING", {"message": "Invoking Planner (Engineer) to build workflow plan..."})
                
                # Get RAG data from session
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
                
                # Build context for planner
                planner_context = {
                    "manuals": rag_data,
                    "session_id": session_id,
                    "strategy": strategy
                }
                
                # STUB: Invoke planner (for now, just emit thinking and artifact)
                # TODO: Replace with actual planner invocation
                try:
                    # Get filtered conversation history for planner
                    from nexus.conductors.workflows.orchestrator import orchestrator
                    conversation_history = await orchestrator.build_conversational_history(session_id)
                    
                    # Use conversation_history instead of full transcript for planner
                    planner_transcript = conversation_history if conversation_history else transcript
                    
                    # STUB: For now, create a placeholder plan
                    # In production, this would call: new_draft = await planner_brain.update_draft(planner_transcript, planner_context)
                    await agent.emit("THINKING", {"message": "Planner (Engineer) is analyzing requirements and building workflow plan..."})
                    
                    # Placeholder draft plan
                    placeholder_draft = {
                        "name": "Workflow Plan (Draft)",
                        "goal": "Workflow plan is being generated based on collected information",
                        "steps": [],
                        "missing_info": [],
                        "status": "drafting"
                    }
                    
                    # Emit placeholder artifact
                    await agent.emit("ARTIFACTS", {
                        "type": "DRAFT_PLAN",
                        "data": placeholder_draft,
                        "summary": "Planner is building workflow plan..."
                    })
                    
                    # TODO: Uncomment when ready to invoke actual planner
                    # new_draft = await planner_brain.update_draft(planner_transcript, planner_context)
                    # 
                    # # Emit the actual draft plan
                    # await agent.emit("ARTIFACTS", {
                    #     "type": "DRAFT_PLAN",
                    #     "data": new_draft,
                    #     "summary": f"Workflow plan created with {len(new_draft.get('steps', []))} steps"
                    # })
                    # 
                    # # Persist draft plan
                    # draft_query = "UPDATE shaping_sessions SET draft_plan = :draft WHERE id = :id"
                    # await database.execute(query=draft_query, values={
                    #     "draft": json.dumps(new_draft),
                    #     "id": session_id
                    # })
                    # await agent.emit("PERSISTENCE", {"action": "UPDATE_PLAN", "id": session_id})
                    
                except Exception as e:
                    logging.error(f"Planner invocation failed: {e}", exc_info=True)
                    await agent.emit("THINKING", {"message": f"Planner encountered an error: {str(e)}"})
            
            # RETURN EARLY - gates are complete, planner has been invoked
            return

        # --- 4. PERSIST TRANSCRIPT (Immediate UX) ---
        # We save the chat history NOW so the user sees the reply while the Planner thinks
        transcript_query = "UPDATE shaping_sessions SET transcript = :transcript, updated_at = CURRENT_TIMESTAMP WHERE id = :id"
        await database.execute(query=transcript_query, values={
            "transcript": json.dumps(transcript),
            "id": session_id
        })
        await agent.emit("PERSISTENCE", {"action": "UPDATE_TRANSCRIPT", "id": session_id})

        # --- 5. PLANNER UPDATE (Backgroundable) ---
        await agent.emit("THINKING", {"message": "Consultant finished. Triggering Planner for Draft Update..."})
        
        # We yield to the planner now. 
        # Ideally this could be backgrounded entirely if we didn't care about the final draft_plan consistency *in this request scope*.
        # But for reliability, awaiting it is fine IF we already saved the chat.
        
        # Load gate_state if available
        gate_state = await self._load_gate_state(session_id)
        context = {"manuals": rag_data, "gate_state": gate_state, "session_id": session_id, "strategy": strategy}
        
        new_draft = await planner_brain.update_draft(transcript, context)
        
        # EMIT THE ARTIFACT
        await agent.emit("ARTIFACTS", {
            "type": "DRAFT_PLAN", 
            "data": new_draft, 
            "summary": f"Updated plan with {len(new_draft.get('steps', []))} steps"
        })

        # 6. Update DB (Draft Plan)
        draft_query = "UPDATE shaping_sessions SET draft_plan = :draft WHERE id = :id"
        await database.execute(query=draft_query, values={
            "draft": json.dumps(new_draft),
            "id": session_id
        })
        await agent.emit("PERSISTENCE", {"action": "UPDATE_PLAN", "id": session_id})

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
