"""
Base Orchestrator Class

Provides reusable services for all orchestrators:
- DB Management
- Memory Management
- Error Handling
- State Management
- Resource Management
- Performance
- Observability
- Coordination
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Callable
import logging
import asyncio
import time
from functools import wraps

logger = logging.getLogger("nexus.conductors.base")


class BaseOrchestrator(ABC):
    """
    Base orchestrator class providing reusable services for all orchestrators.
    Subclasses implement domain-specific coordination logic.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self._resource_registry: Dict[str, Dict[str, Any]] = {}
        self._state_cache: Dict[str, Any] = {}
        self._operation_cache: Dict[str, Any] = {}
        self._rate_limit_tracker: Dict[str, List[float]] = {}
    
    # ============================================================================
    # Abstract Methods - Must be implemented by subclasses
    # ============================================================================
    
    @abstractmethod
    def _get_module_registry(self) -> Dict[str, Any]:
        """Return dict of available modules for this orchestrator."""
        pass
    
    @abstractmethod
    def _get_session_manager(self):
        """Return session manager instance."""
        pass
    
    @abstractmethod
    def _get_database(self):
        """Return database instance."""
        pass
    
    # ============================================================================
    # DB Management Service
    # ============================================================================
    
    async def _execute_db_write(self, query: str, values: Dict[str, Any], retries: int = 3) -> Any:
        """
        Execute DB write with retry logic.
        """
        db = self._get_database()
        last_error = None
        
        for attempt in range(retries):
            try:
                result = await db.execute(query=query, values=values)
                if attempt > 0:
                    self.logger.info(f"DB write succeeded on retry {attempt + 1}")
                return result
            except Exception as e:
                last_error = e
                if attempt < retries - 1:
                    wait_time = 2 ** attempt  # Exponential backoff
                    self.logger.warning(f"DB write failed (attempt {attempt + 1}/{retries}), retrying in {wait_time}s: {e}")
                    await asyncio.sleep(wait_time)
                else:
                    self.logger.error(f"DB write failed after {retries} attempts: {e}")
        
        raise last_error
    
    async def _execute_db_read(self, query: str, values: Dict[str, Any]) -> Any:
        """
        Execute DB read with connection pooling.
        """
        db = self._get_database()
        try:
            return await db.fetch_all(query=query, values=values)
        except Exception as e:
            self.logger.error(f"DB read failed: {e}")
            raise
    
    async def _execute_db_read_one(self, query: str, values: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Execute DB read for single row.
        """
        db = self._get_database()
        try:
            return await db.fetch_one(query=query, values=values)
        except Exception as e:
            self.logger.error(f"DB read_one failed: {e}")
            raise
    
    async def _ensure_db_connection(self) -> bool:
        """
        Check DB connection health.
        """
        db = self._get_database()
        try:
            # Simple health check query
            await db.fetch_one("SELECT 1")
            return True
        except Exception as e:
            self.logger.error(f"DB connection check failed: {e}")
            return False
    
    # ============================================================================
    # Memory Management Service
    # ============================================================================
    
    async def _request_emission(self, module_name: str, emission_type: str, 
                               payload: Dict[str, Any], session_id: int) -> None:
        """
        Request emission from a module.
        """
        modules = self._get_module_registry()
        module = modules.get(module_name)
        
        if not module:
            self.logger.warning(f"Module '{module_name}' not found in registry")
            return
        
        # Get BaseAgent instance for this session
        agent = await self._get_agent_for_session(session_id)
        
        if not agent:
            self.logger.warning(f"Could not get agent for session {session_id}")
            return
        
        # Map emission type to method
        emission_map = {
            "PERSISTENCE": agent.emit_persistence,
            "THINKING": agent.emit_thinking,
            "ARTIFACTS": agent.emit_artifact,
            "RESPONSE": agent.emit_response,
            "OUTPUT": agent.emit_response,  # Alias
        }
        
        emit_method = emission_map.get(emission_type)
        if emit_method:
            try:
                await emit_method(payload)
            except Exception as e:
                self.logger.error(f"Emission failed for {module_name} ({emission_type}): {e}")
        else:
            self.logger.warning(f"Unknown emission type: {emission_type}")
    
    async def _coordinate_emissions(self, session_id: int, emission_requests: List[Dict[str, Any]]) -> None:
        """
        Batch emission coordination - execute multiple emissions in parallel.
        """
        tasks = []
        for req in emission_requests:
            tasks.append(self._request_emission(
                module_name=req.get("module"),
                emission_type=req.get("type"),
                payload=req.get("payload", {}),
                session_id=session_id
            ))
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _validate_session_id(self, session_id: int) -> bool:
        """
        Ensure session_id is valid before emissions.
        """
        if not session_id:
            return False
        
        # Check if session exists in DB
        try:
            db = self._get_database()
            result = await db.fetch_one(
                "SELECT id FROM shaping_sessions WHERE id = :id",
                {"id": session_id}
            )
            return result is not None
        except Exception:
            return False
    
    async def _get_agent_for_session(self, session_id: int):
        """
        Get BaseAgent instance with session_id set.
        """
        from nexus.core.base_agent import BaseAgent
        
        if not await self._validate_session_id(session_id):
            self.logger.warning(f"Invalid session_id: {session_id}")
            return None
        
        agent = BaseAgent(session_id=session_id)
        return agent
    
    # ============================================================================
    # Error Handling Service
    # ============================================================================
    
    async def _handle_error(self, error: Exception, context: Dict[str, Any], 
                           session_id: Optional[int] = None) -> None:
        """
        Centralized error handling.
        """
        error_info = {
            "error_type": type(error).__name__,
            "error_message": str(error),
            "context": context,
            "session_id": session_id,
            "timestamp": time.time()
        }
        
        self.logger.error(f"Error handled: {error_info}")
        
        # Emit error event if we have a session
        if session_id:
            try:
                agent = await self._get_agent_for_session(session_id)
                if agent:
                    await agent.emit_thinking({
                        "message": f"Error: {str(error)}",
                        "error": True,
                        "context": context
                    })
            except Exception as e:
                self.logger.error(f"Failed to emit error event: {e}")
    
    async def _retry_operation(self, operation: Callable, max_retries: int = 3, 
                               backoff: float = 1.0) -> Any:
        """
        Retry operation with exponential backoff.
        """
        last_error = None
        
        for attempt in range(max_retries):
            try:
                if asyncio.iscoroutinefunction(operation):
                    return await operation()
                else:
                    return operation()
            except Exception as e:
                last_error = e
                if attempt < max_retries - 1:
                    wait_time = backoff * (2 ** attempt)
                    self.logger.warning(f"Operation failed (attempt {attempt + 1}/{max_retries}), retrying in {wait_time}s: {e}")
                    await asyncio.sleep(wait_time)
                else:
                    self.logger.error(f"Operation failed after {max_retries} attempts: {e}")
        
        raise last_error
    
    async def _rollback_on_error(self, operation: Callable, rollback_fn: Callable) -> Any:
        """
        Transaction rollback wrapper.
        """
        try:
            if asyncio.iscoroutinefunction(operation):
                return await operation()
            else:
                return operation()
        except Exception as e:
            self.logger.error(f"Operation failed, executing rollback: {e}")
            try:
                if asyncio.iscoroutinefunction(rollback_fn):
                    await rollback_fn()
                else:
                    rollback_fn()
            except Exception as rollback_error:
                self.logger.error(f"Rollback also failed: {rollback_error}")
            raise
    
    # ============================================================================
    # State Management Service
    # ============================================================================
    
    async def _get_state(self, key: str, session_id: Optional[int] = None) -> Optional[Any]:
        """
        Get state from cache or DB.
        """
        full_key = f"{key}:{session_id}" if session_id else key
        
        # Check cache first
        if full_key in self._state_cache:
            return self._state_cache[full_key]
        
        # Try DB if session_id provided (gracefully handle missing table)
        if session_id:
            try:
                db = self._get_database()
                result = await db.fetch_one(
                    "SELECT state_data FROM session_state WHERE session_id = :sid AND state_key = :key",
                    {"sid": session_id, "key": key}
                )
                if result:
                    import json
                    state_value = json.loads(result.get("state_data", "{}"))
                    self._state_cache[full_key] = state_value
                    return state_value
            except Exception as e:
                # Table might not exist - that's okay, just use cache
                self.logger.debug(f"State not found in DB for {key} (table may not exist): {e}")
        
        return None
    
    async def _set_state(self, key: str, value: Any, session_id: Optional[int] = None, 
                        persist: bool = True) -> None:
        """
        Set state with optional persistence.
        """
        full_key = f"{key}:{session_id}" if session_id else key
        self._state_cache[full_key] = value
        
        if persist and session_id:
            # Fire and forget - don't block the response
            async def _persist_state():
                try:
                    import json
                    db = self._get_database()
                    await self._execute_db_write(
                        """
                        INSERT INTO session_state (session_id, state_key, state_data)
                        VALUES (:sid, :key, :data)
                        ON CONFLICT (session_id, state_key) 
                        DO UPDATE SET state_data = :data, updated_at = CURRENT_TIMESTAMP
                        """,
                        {
                            "sid": session_id,
                            "key": key,
                            "data": json.dumps(value)
                        }
                    )
                except Exception as e:
                    # Table might not exist - that's okay, just use cache
                    self.logger.debug(f"Failed to persist state for {key} (table may not exist): {e}")
            
            # Don't await - fire and forget
            asyncio.create_task(_persist_state())
    
    async def _update_state(self, key: str, updates: Dict[str, Any], 
                           session_id: Optional[int] = None) -> None:
        """
        Partial state updates.
        """
        current_state = await self._get_state(key, session_id) or {}
        if isinstance(current_state, dict):
            current_state.update(updates)
            await self._set_state(key, current_state, session_id)
        else:
            self.logger.warning(f"Cannot update non-dict state for {key}")
    
    # ============================================================================
    # Resource Management Service
    # ============================================================================
    
    def _register_resource(self, resource_id: str, resource_type: str, 
                          cleanup_fn: Optional[Callable] = None) -> None:
        """
        Track resource for cleanup.
        """
        self._resource_registry[resource_id] = {
            "type": resource_type,
            "cleanup_fn": cleanup_fn,
            "created_at": time.time()
        }
    
    async def _cleanup_resources(self, session_id: Optional[int] = None, 
                                resource_type: Optional[str] = None) -> None:
        """
        Cleanup tracked resources.
        """
        to_remove = []
        
        for resource_id, resource_info in self._resource_registry.items():
            if resource_type and resource_info["type"] != resource_type:
                continue
            
            if resource_info.get("cleanup_fn"):
                try:
                    cleanup_fn = resource_info["cleanup_fn"]
                    if asyncio.iscoroutinefunction(cleanup_fn):
                        await cleanup_fn()
                    else:
                        cleanup_fn()
                except Exception as e:
                    self.logger.error(f"Cleanup failed for {resource_id}: {e}")
            
            to_remove.append(resource_id)
        
        for resource_id in to_remove:
            del self._resource_registry[resource_id]
    
    # ============================================================================
    # Performance Service
    # ============================================================================
    
    async def _cache_get(self, key: str, ttl: Optional[int] = None) -> Optional[Any]:
        """
        Get from cache.
        """
        if key in self._operation_cache:
            entry = self._operation_cache[key]
            if ttl is None or (time.time() - entry["timestamp"]) < ttl:
                return entry["value"]
            else:
                # Expired
                del self._operation_cache[key]
        return None
    
    async def _cache_set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """
        Set cache value.
        """
        self._operation_cache[key] = {
            "value": value,
            "timestamp": time.time(),
            "ttl": ttl
        }
    
    async def _rate_limit(self, key: str, max_requests: int, window_seconds: int) -> bool:
        """
        Rate limiting - returns True if allowed, False if rate limited.
        """
        now = time.time()
        
        if key not in self._rate_limit_tracker:
            self._rate_limit_tracker[key] = []
        
        # Clean old entries
        self._rate_limit_tracker[key] = [
            t for t in self._rate_limit_tracker[key] 
            if now - t < window_seconds
        ]
        
        if len(self._rate_limit_tracker[key]) >= max_requests:
            return False
        
        self._rate_limit_tracker[key].append(now)
        return True
    
    async def _throttle_operation(self, operation: Callable, max_concurrent: int = 5) -> Any:
        """
        Throttling helper - limit concurrent operations.
        """
        # Simple semaphore-based throttling
        if not hasattr(self, '_throttle_semaphore'):
            self._throttle_semaphore = asyncio.Semaphore(max_concurrent)
        
        async with self._throttle_semaphore:
            if asyncio.iscoroutinefunction(operation):
                return await operation()
            else:
                return operation()
    
    # ============================================================================
    # Observability Service
    # ============================================================================
    
    def _log_operation(self, operation: str, context: Dict[str, Any], level: str = 'info') -> None:
        """
        Centralized logging.
        """
        log_message = f"[{operation}] {context}"
        
        if level == 'debug':
            self.logger.debug(log_message)
        elif level == 'warning':
            self.logger.warning(log_message)
        elif level == 'error':
            self.logger.error(log_message)
        else:
            self.logger.info(log_message)
    
    def _record_metric(self, name: str, value: float, tags: Optional[Dict[str, str]] = None) -> None:
        """
        Record metric.
        """
        tag_str = ", ".join([f"{k}={v}" for k, v in (tags or {}).items()])
        self.logger.info(f"METRIC: {name}={value} {tag_str}")
        # In production, this would send to metrics system (Prometheus, etc.)
    
    def _start_trace(self, operation_name: str, context: Dict[str, Any]) -> str:
        """
        Start tracing - returns trace_id.
        """
        import uuid
        trace_id = str(uuid.uuid4())
        self.logger.debug(f"TRACE_START: {trace_id} [{operation_name}] {context}")
        return trace_id
    
    async def _audit_event(self, action: str, resource_type: str, resource_id: str, 
                          details: Optional[Dict[str, Any]] = None) -> None:
        """
        Audit logging.
        """
        from nexus.modules.audit_manager import audit_manager
        
        try:
            await audit_manager.log_event(
                user_id=details.get("user_id", "system") if details else "system",
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                session_id=details.get("session_id") if details else None,
                details=details
            )
        except Exception as e:
            self.logger.error(f"Audit logging failed: {e}")
    
    # ============================================================================
    # Coordination Service
    # ============================================================================
    
    async def _execute_sequentially(self, operations: List[Callable]) -> List[Any]:
        """
        Execute operations sequentially respecting dependencies.
        """
        results = []
        for op in operations:
            try:
                if asyncio.iscoroutinefunction(op):
                    result = await op()
                else:
                    result = op()
                results.append(result)
            except Exception as e:
                self.logger.error(f"Sequential operation failed: {e}")
                results.append(None)
        return results
    
    async def _execute_parallel(self, operations: List[Callable], 
                               max_concurrent: Optional[int] = None) -> List[Any]:
        """
        Execute operations in parallel.
        """
        if max_concurrent:
            semaphore = asyncio.Semaphore(max_concurrent)
            
            async def bounded_op(op):
                async with semaphore:
                    if asyncio.iscoroutinefunction(op):
                        return await op()
                    else:
                        return op()
            
            tasks = [bounded_op(op) for op in operations]
        else:
            tasks = [
                op() if asyncio.iscoroutinefunction(op) else asyncio.create_task(asyncio.to_thread(op))
                for op in operations
            ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return results
    
    async def _wait_for_condition(self, condition_fn: Callable, timeout: int = 30, 
                                  check_interval: float = 0.5) -> bool:
        """
        Wait for async condition to be true.
        """
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                if asyncio.iscoroutinefunction(condition_fn):
                    result = await condition_fn()
                else:
                    result = condition_fn()
                
                if result:
                    return True
            except Exception as e:
                self.logger.debug(f"Condition check failed: {e}")
            
            await asyncio.sleep(check_interval)
        
        return False
    
    # ============================================================================
    # Enhanced Thinking Emissions for LLM Calls
    # ============================================================================
    
    async def emit_llm_thinking(
        self,
        session_id: Optional[int],
        operation: str,
        prompt: str,
        system_instruction: Optional[str] = None,
        rag_citations: Optional[List[Dict[str, Any]]] = None,
        model_id: Optional[str] = None,
        response_metadata: Optional[Dict[str, Any]] = None,
        prompt_key: Optional[str] = None
    ) -> None:
        """
        Emit enriched thinking event for LLM calls.
        
        Args:
            session_id: Session ID for emission (None if session not yet created)
            operation: Operation name (e.g., "CONSULTANT", "PLANNER", "DIAGNOSIS")
            prompt: User prompt sent to LLM
            system_instruction: System instruction/prompt (optional)
            rag_citations: List of RAG document citations (just metadata, not full content)
            model_id: Model used for the call
            response_metadata: Metadata from LLM response (tokens, finish_reason, etc.)
            prompt_key: Unique identifier for the prompt template (e.g., "workflow:tabula_rasa:None")
        """
        if session_id is None:
            # Can't emit without session_id - skip silently or log
            self.logger.debug(f"Skipping LLM thinking emission for {operation} - no session_id yet")
            return
        
        agent = await self._get_agent_for_session(session_id)
        if not agent:
            return
        
        # Build human-readable message for frontend display
        if response_metadata:
            # After LLM call - show response metadata AND prompt/RAG info
            tokens = response_metadata.get("total_tokens", 0)
            completion_pct = response_metadata.get("completion_percent", 0)
            finish_reason = response_metadata.get("finish_reason", "unknown")
            estimated = response_metadata.get("estimated", False)
            est_prefix = "~" if estimated else ""
            
            # Build message with all info
            message = f"{operation} response received ({est_prefix}tokens: {tokens}, completion: {completion_pct}%, reason: {finish_reason})"
            
            # Add prompt key if available
            if prompt_key:
                message += f"\nPrompt: {prompt_key}"
            
            # Add system prompt length
            if system_instruction:
                system_length = len(system_instruction)
                message += f"\nSystem prompt used - length: {system_length} chars"
            
            # Add RAG citations
            if rag_citations:
                citation_list = []
                for cit in self._extract_rag_citations(rag_citations):
                    doc_name = cit.get("title") or cit.get("source", "unknown")
                    section = cit.get("section")
                    if section:
                        citation_list.append(f"{doc_name} ({section})")
                    else:
                        citation_list.append(doc_name)
                message += f"\nRAG used - {len(rag_citations)} citation(s): {', '.join(citation_list)}"
            else:
                message += "\nRAG used - none"
        else:
            # Before LLM call - show system prompt and RAG info
            system_length = len(system_instruction) if system_instruction else 0
            message = f"Invoking {operation} ({model_id or 'unknown model'})"
            
            # Add prompt key if available
            if prompt_key:
                message += f"\nPrompt: {prompt_key}"
            
            # Add system prompt info
            if system_instruction:
                message += f"\nSystem prompt used - length: {system_length} chars"
            
            # Add RAG citations info
            if rag_citations:
                citation_list = []
                for cit in self._extract_rag_citations(rag_citations):
                    doc_name = cit.get("title") or cit.get("source", "unknown")
                    section = cit.get("section")
                    if section:
                        citation_list.append(f"{doc_name} ({section})")
                    else:
                        citation_list.append(doc_name)
                message += f"\nRAG used - {len(rag_citations)} citation(s): {', '.join(citation_list)}"
            else:
                message += "\nRAG used - none"
        
        # Build enriched thinking payload
        thinking_payload = {
            "message": message,  # REQUIRED: Frontend expects this field
            "operation": operation,
            "model": model_id or "unknown",
            "prompt_key": prompt_key,  # Include in payload
            "prompt": {
                "user": prompt[:500] + "..." if len(prompt) > 500 else prompt,
                "system": system_instruction[:500] + "..." if system_instruction and len(system_instruction) > 500 else (system_instruction or None),
                "total_length": len(prompt) + (len(system_instruction) if system_instruction else 0)
            },
            "rag_citations": self._extract_rag_citations(rag_citations) if rag_citations else [],
            "response_metadata": response_metadata or {}
        }
        
        await agent.emit_thinking(thinking_payload)
    
    # ============================================================================
    # Journey State Management
    # ============================================================================
    
    async def emit_journey_state(
        self,
        session_id: Optional[int],
        domain: str,
        strategy: str,
        current_step: str,
        percent_complete: float,
        step_details: Optional[Dict[str, Any]] = None,
        status: Optional[str] = None
    ) -> None:
        """
        Emit journey state for frontend header display.
        Stores in dedicated journey_state table for easy querying.
        
        Args:
            session_id: Session ID for emission
            domain: Current domain (e.g., "eligibility", "crm")
            strategy: Current strategy (e.g., "TABULA_RASA", "EVIDENCE_BASED")
            current_step: Current step name (e.g., "gate_1_data_availability", "planning")
            percent_complete: Progress percentage (0.0 to 100.0)
            step_details: Optional additional details about current step
            status: Optional session status (e.g., "GATHERING", "PLANNING")
        """
        if not session_id:
            self.logger.debug(f"Skipping journey state emission - no session_id")
            return
        
        from nexus.modules.journey_state import journey_state_manager
        from datetime import datetime
        
        # Store in dedicated table
        await journey_state_manager.upsert_journey_state(
            session_id=session_id,
            domain=domain,
            strategy=strategy,
            current_step=current_step,
            percent_complete=percent_complete,
            status=status,
            step_details=step_details
        )
        
        # Also emit as ARTIFACTS for WebSocket streaming (optional, for real-time updates)
        from nexus.core.base_agent import BaseAgent
        
        agent = BaseAgent(session_id=session_id)
        
        journey_payload = {
            "type": "JOURNEY_STATE",
            "domain": domain,
            "strategy": strategy,
            "current_step": current_step,
            "percent_complete": round(percent_complete, 1),
            "step_details": step_details or {},
            "status": status,
            "timestamp": datetime.now().isoformat()
        }
        
        await agent.emit_artifact(journey_payload)
        self.logger.debug(f"Emitted journey state: {current_step} ({percent_complete}%)")
    
    # ============================================================================
    # Conversational History Management
    # ============================================================================
    
    async def build_conversational_history(
        self,
        session_id: int,
        max_messages: Optional[int] = None
    ) -> List[Dict[str, str]]:
        """
        Build conversational history from session transcript.
        Only includes messages that were actually shared with the user:
        - User messages (role: "user")
        - System OUTPUT messages (role: "system" from OUTPUT events)
        
        Excludes:
        - Internal LLM thinking/processing messages
        - THINKING events
        - PERSISTENCE events
        - ARTIFACTS events
        
        Args:
            session_id: Session ID to get history for
            max_messages: Optional limit on number of messages to return (most recent)
        
        Returns:
            List of message dicts in format:
            [
                {"role": "user", "content": "..."},
                {"role": "system", "content": "..."},
                ...
            ]
        """
        try:
            # Get session transcript from shaping_sessions table
            db = self._get_database()
            session_query = "SELECT transcript FROM shaping_sessions WHERE id = :session_id"
            session_row = await db.fetch_one(session_query, {"session_id": session_id})
            
            if not session_row:
                self.logger.debug(f"Session {session_id} not found for conversational history")
                return []
            
            # Convert row to dict
            session_dict = dict(session_row)
            transcript = session_dict.get("transcript", [])
            
            # Parse transcript if it's a string
            if isinstance(transcript, str):
                import json
                try:
                    transcript = json.loads(transcript)
                except (json.JSONDecodeError, TypeError):
                    self.logger.warning(f"Failed to parse transcript for session {session_id}")
                    return []
            
            if not isinstance(transcript, list):
                self.logger.warning(f"Transcript for session {session_id} is not a list: {type(transcript)}")
                return []
            
            # Filter to only user-facing messages
            # Transcript format: [{"role": "user|system", "content": "...", ...}, ...]
            # We only want messages with role "user" or "system" (system messages are OUTPUT events)
            user_facing_messages = []
            
            for msg in transcript:
                if not isinstance(msg, dict):
                    continue
                
                role = msg.get("role", "").lower()
                content = msg.get("content", "")
                
                # Only include user and system messages (system = OUTPUT events shown to user)
                if role in ("user", "system") and content:
                    # Clean message - only include role and content
                    clean_msg = {
                        "role": role,
                        "content": content.strip()
                    }
                    user_facing_messages.append(clean_msg)
            
            # Apply max_messages limit if specified (take most recent)
            if max_messages and len(user_facing_messages) > max_messages:
                user_facing_messages = user_facing_messages[-max_messages:]
            
            self.logger.debug(
                f"Built conversational history for session {session_id}: "
                f"{len(user_facing_messages)} user-facing messages "
                f"(from {len(transcript)} total transcript entries)"
            )
            
            return user_facing_messages
            
        except Exception as e:
            self.logger.error(
                f"Failed to build conversational history for session {session_id}: {e}",
                exc_info=True
            )
            return []
    
    def _extract_rag_citations(self, rag_citations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Extract just citation metadata (not full content) from RAG results.
        Returns: List of {source, title, relevance_score, etc.}
        """
        citations = []
        for item in rag_citations:
            citation = {
                "source": item.get("source", "unknown"),
                "title": item.get("title") or item.get("name") or item.get("source"),
                "relevance": item.get("score") or item.get("relevance", 0.0)
            }
            # Add any other metadata fields (but not full content)
            if "chunk_id" in item:
                citation["chunk_id"] = item["chunk_id"]
            if "page" in item:
                citation["page"] = item["page"]
            if "section" in item:
                citation["section"] = item["section"]
            citations.append(citation)
        return citations

