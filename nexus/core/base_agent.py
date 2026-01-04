import asyncio
import logging
import json
from abc import ABC
from typing import List, Dict, Any, Optional, Literal
from dataclasses import dataclass, is_dataclass, asdict
from datetime import datetime

from nexus.core.base_tool import NexusTool
from nexus.core.memory_models import MemoryEvent, ThinkingEvent, ArtifactEvent, OutputEvent, PersistenceEvent
from nexus.modules.session_manager import session_manager
from nexus.modules.database import database

logger = logging.getLogger("nexus.core.agent")

# --- The Streaming Base Agent ---
class BaseAgent(ABC):
    """
    The Core Streaming Agent.
    Implements Dual-Path Streaming:
    - Path A: WebSockets (Hot)
    - Path B: Database (Cold/Async)
    """
    def __init__(self, session_id: Optional[int] = None):
        self.session_id = session_id
        self.logger = logger  # Default logger

    def set_session_id(self, session_id: int):
        self.session_id = session_id

    async def emit(self, bucket: Literal["THINKING", "ARTIFACTS", "PERSISTENCE", "OUTPUT"], payload: Dict[str, Any]):
        """
        The unified event emitter.
        Returns memory_event_id for OUTPUT events, None otherwise.
        """
        if not self.session_id:
            self.logger.warning(f"⚠️ Emit called without session_id. Payload: {payload}")
            return None

        # 1. Path A: UI Stream (Hot)
        # We broadcast immediately to any connected websocket for this session
        event_data = {
            "bucket": bucket,
            "session_id": self.session_id,
            "created_at": datetime.now().isoformat(),
            "payload": payload
        }
        await session_manager.broadcast(self.session_id, event_data)
        
        # 2. Path B: Persistence
        # For OUTPUT events, await persistence to get memory_event_id for transcript linking
        # For other events, use background task to avoid blocking
        if bucket == "OUTPUT":
            memory_event_id = await self._persist_event(bucket, payload)
            return memory_event_id
        else:
            # Spawn background task for non-OUTPUT events
            asyncio.create_task(self._persist_event(bucket, payload))
            return None
        
        # 3. CRITICAL: If DRAFT_PLAN artifact, also persist to shaping_sessions.draft_plan
        if bucket == "ARTIFACTS" and payload.get("type") == "DRAFT_PLAN":
            asyncio.create_task(self._persist_draft_plan(payload))
        
        # 4. Artifact Trigger
        if bucket == "ARTIFACTS":
            # Fire and forget the ParallelPlanner
            asyncio.create_task(self._notify_parallel_planner(payload))

    async def _persist_event(self, bucket: str, payload: Dict[str, Any]) -> Optional[int]:
        """
        Internal: Async DB Insert.
        All bucket types are append-only to preserve full history:
        - THINKING: Full reasoning chain over time
        - ARTIFACTS: All draft plan versions, workflow matches, etc.
        - PERSISTENCE: Complete audit trail
        - OUTPUT: Full conversation history
        
        For OUTPUT events, automatically emits feedback UI after persistence.
        Returns memory_event_id for OUTPUT events, None otherwise.
        """
        try:
            # Convert any dataclass objects to dicts for JSON serialization
            serializable_payload = self._make_json_serializable(payload)
            
            # For OUTPUT events, we need the ID to emit feedback UI and return it for transcript linking
            if bucket == "OUTPUT":
                query = """
                INSERT INTO memory_events (session_id, bucket_type, payload)
                VALUES (:sid, :bucket, :payload)
                RETURNING id
                """
                result = await database.fetch_one(query=query, values={
                    "sid": self.session_id,
                    "bucket": bucket,
                    "payload": json.dumps(serializable_payload)
                })
                
                # Emit feedback UI after OUTPUT event is persisted
                if result and "id" in result:
                    memory_event_id = result["id"]
                    self.logger.debug(f"📝 OUTPUT event persisted with id={memory_event_id}, emitting feedback UI")
                    asyncio.create_task(self._emit_feedback_ui(memory_event_id))
                    return memory_event_id
                else:
                    self.logger.warning(f"⚠️ OUTPUT event persisted but no ID returned from database")
                    return None
            else:
                # For other bucket types, use simple INSERT
                query = """
                INSERT INTO memory_events (session_id, bucket_type, payload)
                VALUES (:sid, :bucket, :payload)
                """
                await database.execute(query=query, values={
                    "sid": self.session_id,
                    "bucket": bucket,
                    "payload": json.dumps(serializable_payload)
                })
                return None
        except Exception as e:
            # We log but DO NOT crash the stream
            self.logger.error(f"❌ DB Persistence Failed for {bucket}: {e}")
            return None
    
    async def _emit_feedback_ui(self, memory_event_id: int):
        """
        Internal: Automatically emit feedback UI artifact after OUTPUT event.
        This makes feedback capture automatic and reusable across all agents.
        """
        try:
            from nexus.core.feedback_builder import emit_feedback_ui
            await emit_feedback_ui(
                self,
                memory_event_id,
                metadata={"session_id": self.session_id}
            )
            self.logger.debug(f"✅ Emitted feedback UI for memory_event {memory_event_id}")
        except Exception as e:
            # Log but don't crash - feedback UI is optional
            self.logger.warning(f"⚠️ Failed to emit feedback UI: {e}")

    async def _persist_draft_plan(self, payload: Dict[str, Any]):
        """
        Persist DRAFT_PLAN artifact to shaping_sessions.draft_plan column.
        This ensures the draft plan is available in session data for frontend.
        Called automatically whenever a DRAFT_PLAN artifact is emitted.
        """
        try:
            draft_plan_data = payload.get("data")
            if not draft_plan_data:
                self.logger.warning("DRAFT_PLAN artifact has no 'data' field")
                return
            
            # Convert to JSON-serializable format
            serializable_plan = self._make_json_serializable(draft_plan_data)
            
            query = """
            UPDATE shaping_sessions 
            SET draft_plan = :draft, updated_at = CURRENT_TIMESTAMP 
            WHERE id = :sid
            """
            await database.execute(query=query, values={
                "sid": self.session_id,
                "draft": json.dumps(serializable_plan)
            })
            self.logger.debug(f"✅ Persisted DRAFT_PLAN to shaping_sessions.draft_plan for session {self.session_id}")
        except Exception as e:
            # Log but don't crash - artifact is still in memory_events
            self.logger.error(f"❌ Failed to persist DRAFT_PLAN to shaping_sessions: {e}")

    def _make_json_serializable(self, obj: Any) -> Any:
        """
        Recursively convert dataclass objects and other non-serializable types to JSON-serializable formats.
        Handles: dataclasses, datetime objects, nested dicts/lists.
        """
        if is_dataclass(obj) and not isinstance(obj, type):
            # Convert dataclass to dict
            return asdict(obj)
        elif isinstance(obj, dict):
            return {k: self._make_json_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, (list, tuple)):
            return [self._make_json_serializable(item) for item in obj]
        elif isinstance(obj, datetime):
            return obj.isoformat()
        else:
            # For other types, return as-is (will fail in json.dumps if not serializable)
            return obj

    async def _notify_parallel_planner(self, payload: Dict[str, Any]):
        """
        Internal: Notify Live Builder (Planner) to update draft plan.
        This is called whenever ARTIFACTS are emitted.
        Live builder updates deterministically (no LLM calls during gate stage).
        """
        try:
            artifact_type = payload.get("type")
            
            # Skip DRAFT_PLAN to prevent infinite recursion (DRAFT_PLAN is already the result)
            if artifact_type == "DRAFT_PLAN":
                return  # Don't process DRAFT_PLAN artifacts to prevent recursion
            
            # Only process GATE_STATE_UPDATE and PROBLEM_STATEMENT artifacts
            if artifact_type in ["GATE_STATE_UPDATE", "PROBLEM_STATEMENT"]:
                from nexus.brains.planner import planner_brain
                from nexus.modules.shaping_manager import shaping_manager
                
                # Get session data
                session = await shaping_manager.get_session(self.session_id)
                if not session:
                    return
                
                # Get gate state
                gate_state = await shaping_manager._load_gate_state(self.session_id)
                if not gate_state:
                    # If no gate state yet, skip (session just created)
                    return
                
                # Get transcript and context
                transcript = session.get("transcript", [])
                strategy = session.get("consultant_strategy", "TABULA_RASA")
                rag_data = session.get("rag_citations", [])
                
                context = {
                    "gate_state": gate_state,
                    "session_id": self.session_id,
                    "strategy": strategy,
                    "manuals": rag_data
                }
                
                # If problem_statement is in payload, use it
                if artifact_type == "PROBLEM_STATEMENT":
                    problem_statement = payload.get("data", {}).get("problem_statement")
                    if problem_statement:
                        context["problem_statement"] = problem_statement
                
                # Update draft plan deterministically (no LLM call during gate stage)
                # NOTE: Do NOT emit ARTIFACTS here - shaping_manager already handles that
                # This prevents infinite recursion
                updated_draft = await planner_brain.update_draft(transcript, context)
                
                # DO NOT emit ARTIFACTS here - it would cause infinite recursion
                # The shaping_manager.append_message() already emits ARTIFACTS after calling update_draft
                # We're just updating the draft plan silently here
                
                self.logger.info(f"⚡️ Live Builder updated draft plan for session {self.session_id}")
        except Exception as e:
            self.logger.error(f"⚠️ Live Builder update failed: {e}", exc_info=True)

    # --- Type-Safe Emission Helper Methods ---
    
    async def emit_persistence(self, payload: Dict[str, Any]):
        """
        Emit a PERSISTENCE event - stored in PostgreSQL for long-term audit and history.
        Used for: Audit logs, execution history, session state.
        """
        await self.emit("PERSISTENCE", payload)
    
    async def emit_thinking(self, payload: Dict[str, Any]):
        """
        Emit a THINKING event - stored in special frontend container (latest state only).
        Used for: Consultant strategy, Planner reasoning, Diagnosis analysis.
        """
        await self.emit("THINKING", payload)
    
    async def emit_artifact(self, payload: Dict[str, Any]):
        """
        Emit an ARTIFACTS/INSIGHTS event - important things shared across states and agents.
        Persisted to DB AND streamed via WebSocket for real-time updates.
        Used for: Draft plans, workflow matches, RAG citations, insights.
        """
        await self.emit("ARTIFACTS", payload)
    
    async def emit_response(self, payload: Dict[str, Any]):
        """
        Emit a RETURN/RESPONSE event - final output to user.
        Streamed via WebSocket immediately.
        Used for: Chat messages, execution results, final answers.
        """
        await self.emit("OUTPUT", payload)

# --- The Recipe Data Structures (Unchanged) ---
@dataclass
class AgentStep:
    step_id: str
    tool_name: str
    description: str
    args_mapping: Dict[str, str] 
    transition_success: Optional[str] = None
    transition_fail: Optional[str] = None

@dataclass
class AgentRecipe:
    name: str
    goal: str
    steps: Dict[str, AgentStep]
    start_step_id: str
    metadata: Optional[Dict[str, Any]] = None

# --- The Factory Engine (Updated to Inherit) ---
class NexusAgentFactory(BaseAgent):
    """
    The Execution Engine.
    Executes a recipe step-by-step.
    """
    def __init__(self, available_tools: List[NexusTool], session_id: Optional[int] = None):
        super().__init__(session_id)
        self.tool_map = {t.define_schema().name: t for t in available_tools}
        
    async def run_recipe(self, recipe: AgentRecipe, initial_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes the recipe step-by-step.
        """
        context = initial_context.copy()
        current_step_id = recipe.start_step_id
        
        await self.emit("THINKING", {"message": f"🚀 Starting Recipe: {recipe.name}"})
        
        while current_step_id:
            step = recipe.steps.get(current_step_id)
            if not step:
                self.logger.error(f"Step {current_step_id} not found.")
                break
                
            await self.emit("THINKING", {"message": f"▶️ Executing Step: {step.step_id} ({step.tool_name})"})
            
            # ... (Tool execution logic kept brief for brevity, assuming standard run) ...
            tool = self.tool_map.get(step.tool_name)
            if not tool:
                raise ValueError(f"Tool {step.tool_name} not found")
                
            tool_args = {k: context.get(v) for k, v in step.args_mapping.items() if v in context}
            
            try:
                # Execute tool (tools are synchronous)
                result = tool.run(**tool_args)
                
                # Store result in context using step_id as key
                if isinstance(result, dict):
                    context[step.step_id] = result
                    context.update(result)
                else:
                    context[step.step_id] = result
                
                context["last_step_status"] = "success"
                current_step_id = step.transition_success
                
            except Exception as e:
                await self.emit("THINKING", {"message": f"❌ Step Failed: {e}", "error": True})
                context["last_step_status"] = "failure"
                context["last_step_error"] = str(e)
                current_step_id = step.transition_fail

        await self.emit("THINKING", {"message": f"🏁 Recipe Complete."})
        return context
