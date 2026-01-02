import logging
from typing import Dict, Any, Optional, List
from nexus.modules.database import database
from nexus.modules.audit_manager import audit_manager
import json

logger = logging.getLogger("nexus.prompt_manager")

class PromptManager:
    """
    Manages prompt templates stored in PostgreSQL.
    Handles versioning, history, and retrieval with unique key pattern.
    New structure: MODULE:DOMAIN:MODE:STEP (e.g., workflow:eligibility:TABULA_RASA:gate)
    """
    
    def __init__(self):
        pass
    
    def _build_prompt_key(self, module_name: str, domain: str, mode: str, step: str) -> str:
        """
        Builds unique prompt key: MODULE:DOMAIN:MODE:STEP
        
        Args:
            module_name: e.g., 'workflow', 'chat'
            domain: e.g., 'eligibility', 'crm'
            mode: e.g., 'TABULA_RASA', 'EVIDENCE_BASED', 'REPLICATION'
            step: e.g., 'gate', 'clarification', 'planning'
        
        Returns:
            Prompt key string in format: "module:domain:mode:step"
        """
        return f"{module_name}:{domain}:{mode}:{step}"
    
    async def get_prompt(
        self, 
        module_name: str,
        domain: str,
        mode: str,
        step: str,
        session_id: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieves active prompt by unique identifier.
        Exact match only - no fallback logic.
        
        Args:
            module_name: e.g., 'workflow', 'chat'
            domain: e.g., 'eligibility', 'crm'
            mode: e.g., 'TABULA_RASA', 'EVIDENCE_BASED', 'REPLICATION'
            step: e.g., 'gate', 'clarification', 'planning'
            session_id: Optional session ID for logging
        
        Returns:
            {
                "config": {...},  # Full prompt config
                "generation_config": {...},  # Extracted generation params
                "version": 1,
                "key": "workflow:eligibility:TABULA_RASA:gate"
            } or None if not found
        """
        prompt_key = self._build_prompt_key(module_name, domain, mode, step)
        logger.info(f"[PROMPT_MANAGER] get_prompt | Looking for key: '{prompt_key}' | module={module_name}, domain={domain}, mode={mode}, step={step}")
        
        # Try exact match first
        query = """
            SELECT prompt_config, version, description 
            FROM prompt_templates 
            WHERE prompt_key = :key AND is_active = true
            ORDER BY version DESC
            LIMIT 1
        """
        try:
            logger.debug(f"[PROMPT_MANAGER] Executing query for key: '{prompt_key}'")
            row = await database.fetch_one(query, {"key": prompt_key})
            logger.debug(f"[PROMPT_MANAGER] Query result: {row is not None}")
        except Exception as e:
            # Table might not exist yet (migration not run), return None to use fallback
            logger.error(f"[PROMPT_MANAGER] ERROR - prompt_templates table not found or query failed: {e}")
            logger.error(f"[PROMPT_MANAGER] Query was: {query}")
            logger.error(f"[PROMPT_MANAGER] Key was: '{prompt_key}'")
            import traceback
            logger.error(f"[PROMPT_MANAGER] Traceback: {traceback.format_exc()}")
            return None
        
        if row:
            row_dict = dict(row)
            logger.info(f"[PROMPT_MANAGER] Found prompt for key '{prompt_key}' | Version: {row_dict.get('version')}")
            try:
                from nexus.modules.database import parse_jsonb
                config = parse_jsonb(row["prompt_config"])
                
                # Ensure config is a dict
                if not isinstance(config, dict):
                    logger.error(f"[PROMPT_MANAGER] ERROR - prompt_config for {prompt_key} is not a valid dict: {type(config)}")
                    logger.error(f"[PROMPT_MANAGER] Config value: {config}")
                    return None
                    
                generation_config = config.get("GENERATION_CONFIG", {})
                
                # Estimate prompt length from config (will be more accurate after building, but this gives an idea)
                # We can estimate by serializing the config
                import json
                estimated_length = len(json.dumps(config))
                
                # Emit thinking message about prompt usage
                if session_id:
                    from nexus.core.thinking_emitter import emit_prompt_usage
                    try:
                        await emit_prompt_usage(
                            session_id=session_id,
                            prompt_key=prompt_key,
                            prompt_length=estimated_length,
                            strategy=mode,  # Use mode instead of strategy
                            module_name=module_name
                        )
                    except Exception as e:
                        logger.warning(f"[PROMPT_MANAGER] Failed to emit thinking message: {e}")
                
                logger.info(f"[PROMPT_MANAGER] Successfully loaded prompt '{prompt_key}' | Version: {row_dict.get('version')}")
                
                # Get conversational history from orchestrator if session_id provided and prompt needs it
                conversation_history = None
                if session_id and "CONVERSATION_HISTORY" in config:
                    try:
                        # Import orchestrator to get conversation history
                        # Try to get the workflow orchestrator (most common case)
                        from nexus.conductors.workflows.orchestrator import orchestrator
                        conversation_history = await orchestrator.build_conversational_history(
                            session_id=session_id,
                            max_messages=config.get("CONVERSATION_HISTORY", {}).get("use_last_n", 5)
                        )
                        logger.debug(f"[PROMPT_MANAGER] Retrieved {len(conversation_history)} messages from conversation history")
                    except Exception as e:
                        logger.warning(f"[PROMPT_MANAGER] Failed to get conversation history: {e}")
                        conversation_history = []
                
                return {
                    "config": config,
                    "generation_config": generation_config,
                    "version": row_dict.get("version"),
                    "description": row_dict.get("description"),
                    "key": prompt_key,
                    "conversation_history": conversation_history  # Add conversation history for use in context
                }
            except Exception as e:
                logger.error(f"[PROMPT_MANAGER] ERROR - Failed to parse prompt_config for '{prompt_key}': {e}")
                import traceback
                logger.error(f"[PROMPT_MANAGER] Traceback: {traceback.format_exc()}")
                return None
        
        # No exact match found - exact match only, no fallback
        logger.warning(f"[PROMPT_MANAGER] No prompt found for key '{prompt_key}' (exact match only, no fallback)")
        return None
    
    async def create_prompt(
        self,
        module_name: str,
        domain: str,
        mode: str,
        step: str,
        prompt_config: Dict[str, Any],
        description: str = None,
        user_context: Dict = None
    ) -> int:
        """
        Creates a new prompt template.
        
        Args:
            module_name: e.g., 'workflow', 'chat'
            domain: e.g., 'eligibility', 'crm'
            mode: e.g., 'TABULA_RASA', 'EVIDENCE_BASED', 'REPLICATION'
            step: e.g., 'gate', 'clarification', 'planning'
            prompt_config: The prompt configuration dictionary
            description: Optional description
            user_context: Optional user context with user_id, session_id
        """
        prompt_key = self._build_prompt_key(module_name, domain, mode, step)
        
        # Check if exists
        check_query = "SELECT id FROM prompt_templates WHERE prompt_key = :key"
        existing = await database.fetch_one(check_query, {"key": prompt_key})
        
        if existing:
            # Update existing (version increment handled separately)
            raise ValueError(f"Prompt {prompt_key} already exists. Use update_prompt() instead.")
        
        query = """
            INSERT INTO prompt_templates 
            (prompt_key, module_name, domain, mode, step, prompt_config, description, created_by, is_active)
            VALUES (:key, :module, :domain, :mode, :step, :config, :desc, :user, true)
            RETURNING id
        """
        
        prompt_id = await database.fetch_val(query, {
            "key": prompt_key,
            "module": module_name,
            "domain": domain,
            "mode": mode,
            "step": step,
            "config": json.dumps(prompt_config),
            "desc": description,
            "user": user_context.get("user_id", "system") if user_context else "system"
        })
        
        # Audit log
        await audit_manager.log_event(
            user_id=user_context.get("user_id", "system") if user_context else "system",
            session_id=user_context.get("session_id") if user_context else None,
            action="CREATE",
            resource_type="PROMPT",
            resource_id=str(prompt_id),
            details={"prompt_key": prompt_key, "module": module_name}
        )
        
        return prompt_id
    
    async def update_prompt(
        self,
        prompt_key: str,
        prompt_config: Dict[str, Any],
        change_reason: str = None,
        user_context: Dict = None
    ) -> int:
        """
        Updates a prompt (creates new version, archives old).
        Uses a transaction to ensure atomicity - if any step fails, all changes are rolled back.
        """
        # Use transaction to ensure atomicity
        async with database.transaction():
            # Get current version
            current_query = "SELECT id, version FROM prompt_templates WHERE prompt_key = :key AND is_active = true"
            current = await database.fetch_one(current_query, {"key": prompt_key})
            
            if not current:
                raise ValueError(f"Prompt {prompt_key} not found")
            
            old_version = current["version"]
            new_version = old_version + 1
            
            # Archive old version to history (only if not already archived)
            archive_query = """
                INSERT INTO prompt_history 
                (prompt_template_id, prompt_key, version, prompt_config, changed_by, change_reason)
                SELECT id, prompt_key, version, prompt_config, updated_by, :reason
                FROM prompt_templates
                WHERE id = :id
                ON CONFLICT (prompt_template_id, version) DO NOTHING
            """
            await database.execute(archive_query, {
                "id": current["id"],
                "reason": change_reason
            })
            
            # Deactivate old version
            deactivate_query = "UPDATE prompt_templates SET is_active = false WHERE id = :id"
            await database.execute(deactivate_query, {"id": current["id"]})
            
            # Create new version
            new_query = """
                INSERT INTO prompt_templates 
                (prompt_key, module_name, domain, mode, step, prompt_config, version, created_by)
                SELECT prompt_key, module_name, domain, mode, step, :config, :version, :user
                FROM prompt_templates
                WHERE id = :id
                RETURNING id
            """
            
            new_id = await database.fetch_val(new_query, {
                "id": current["id"],
                "config": json.dumps(prompt_config),
                "version": new_version,
                "user": user_context.get("user_id", "system") if user_context else "system"
            })
            
            # Audit log (outside transaction - audit failures shouldn't rollback the update)
            try:
                await audit_manager.log_event(
                    user_id=user_context.get("user_id", "system") if user_context else "system",
                    session_id=user_context.get("session_id") if user_context else None,
                    action="UPDATE",
                    resource_type="PROMPT",
                    resource_id=str(new_id),
                    details={"prompt_key": prompt_key, "old_version": old_version, "new_version": new_version}
                )
            except Exception as e:
                # Log but don't fail the update if audit fails
                logger.warning(f"Failed to log audit event for prompt update: {e}")
            
            return new_id
    
    async def list_prompts(
        self,
        module_name: str = None,
        domain: str = None,
        mode: str = None,
        step: str = None,
        active_only: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Lists prompts with optional filtering.
        
        Args:
            module_name: Filter by module (e.g., 'workflow', 'chat')
            domain: Filter by domain (e.g., 'eligibility', 'crm')
            mode: Filter by mode (e.g., 'TABULA_RASA', 'EVIDENCE_BASED')
            step: Filter by step (e.g., 'gate', 'clarification')
            active_only: Only return active prompts
        """
        conditions = []
        params = {}
        
        if module_name:
            conditions.append("module_name = :module")
            params["module"] = module_name
        if domain:
            conditions.append("domain = :domain")
            params["domain"] = domain
        if mode:
            conditions.append("mode = :mode")
            params["mode"] = mode
        if step:
            conditions.append("step = :step")
            params["step"] = step
        if active_only:
            conditions.append("is_active = true")
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        
        query = f"""
            SELECT id, prompt_key, module_name, domain, mode, step, version, 
                   description, created_at, updated_at
            FROM prompt_templates
            WHERE {where_clause}
            ORDER BY module_name, domain, mode, step, version DESC
        """
        
        rows = await database.fetch_all(query, params)
        return [dict(r) for r in rows]
    
    async def get_prompt_history(self, prompt_key: str) -> List[Dict[str, Any]]:
        """
        Gets version history for a prompt.
        """
        query = """
            SELECT ph.version, ph.prompt_config, ph.changed_by, ph.change_reason, ph.created_at
            FROM prompt_history ph
            JOIN prompt_templates pt ON ph.prompt_template_id = pt.id
            WHERE pt.prompt_key = :key
            ORDER BY ph.version DESC
        """
        rows = await database.fetch_all(query, {"key": prompt_key})
        return [dict(r) for r in rows]
    
    async def get_prompt_by_id(self, prompt_id: int) -> Optional[Dict[str, Any]]:
        """
        Gets a prompt by its database ID.
        
        Returns:
            {
                "id": int,
                "prompt_key": str,
                "module_name": str,
                "strategy": str or None,
                "sub_level": str or None,
                "version": int,
                "config": {...},
                "generation_config": {...},
                "description": str or None,
                "created_at": datetime,
                "updated_at": datetime or None
            } or None
        """
        query = """
            SELECT id, prompt_key, module_name, domain, mode, step, version,
                   prompt_config, description, created_at, updated_at
            FROM prompt_templates
            WHERE id = :id AND is_active = true
        """
        try:
            row = await database.fetch_one(query, {"id": prompt_id})
        except Exception as e:
            logger.warning(f"Error fetching prompt by ID {prompt_id}: {e}")
            return None
        
        if not row:
            return None
        
        from nexus.modules.database import parse_jsonb
        # Convert row to dict for safe access
        row_dict = dict(row)
        config = parse_jsonb(row_dict["prompt_config"])
        
        # Ensure config is a dict
        if not isinstance(config, dict):
            logger.error(f"prompt_config for ID {prompt_id} is not a valid dict: {type(config)}")
            return None
            
        generation_config = config.get("GENERATION_CONFIG", {})
        
        return {
            "id": row_dict["id"],
            "prompt_key": row_dict["prompt_key"],
            "module_name": row_dict["module_name"],
            "domain": row_dict.get("domain"),
            "mode": row_dict.get("mode"),
            "step": row_dict.get("step"),
            "version": row_dict["version"],
            "config": config,
            "generation_config": generation_config,
            "description": row_dict.get("description"),
            "created_at": row_dict["created_at"],
            "updated_at": row_dict.get("updated_at")
        }

prompt_manager = PromptManager()

