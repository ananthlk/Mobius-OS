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
                # Fix: Use dict-style access for Record objects instead of .get()
                if gate_state_row and "gate_state" in gate_state_row and gate_state_row["gate_state"]:
                    session["gate_state"] = gate_state_row["gate_state"]
            except Exception as e:
                # If gate_state column doesn't exist or query fails, just continue without it
                self.logger.debug(f"Could not fetch gate_state: {e}")
            
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
        Returns: {reply, trace_id}
        """
        self._log_operation("handle_chat_message", {"session_id": session_id, "user_id": user_id})
        
        try:
            # 1. Process chat via ShapingManager (this handles the LLM call and response)
            await self.shaping_manager.append_message(session_id, "user", message)
            
            # 2. Get current transcript for analysis
            session = await self.shaping_manager.get_session(session_id)
            transcript = session.get("transcript", []) if session else []
            
            # 3. Trigger workflow analysis (parallel) - re-analyze existing workflows
            # Fire and forget - don't block on these
            asyncio.create_task(self._trigger_workflow_analysis(session_id, message))
            
            # 4. Trigger planner update (parallel) - update draft plan
            asyncio.create_task(self._trigger_planner_update(session_id, transcript))
            
            # 6. Get updated session to get the reply
            updated_session = await self.shaping_manager.get_session(session_id)
            transcript_list = updated_session.get("transcript", []) if updated_session else []
            last_message = transcript_list[-1] if transcript_list else {}
            
            # 7. Metrics
            self._record_metric("chat_message.processed", 1, {"session_id": session_id})
            
            return {
                "reply": last_message.get("content", ""),
                "trace_id": last_message.get("trace_id")
            }
        except Exception as e:
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

