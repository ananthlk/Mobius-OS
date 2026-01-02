import logging
from typing import Dict, Any, List, Tuple, Optional
from nexus.modules.rag_service import rag_service
from nexus.core.memory_logger import MemoryLogger
from nexus.modules.prompt_manager import prompt_manager
from nexus.core.prompt_builder import PromptBuilder
import json

logger = logging.getLogger("nexus.consultant")

class ConsultantBrain:
    """
    The High-Level Strategist for the Workflow Builder.
    Decides *HOW* to solve the problem before solving it.
    """
    
    def __init__(self):
        self.mem = MemoryLogger("nexus.consultant")

    async def decide_strategy(self, user_query: str) -> Dict[str, Any]:
        """
        Analyzes the query and RAG hits to pick a strategy.
        
        TEMPORARY: Hardcoded to TABULA_RASA for all scenarios.
        RAG hits are disabled to ensure TABULA_RASA is always selected.
        
        TO REVERT WHEN READY FOR RAG:
        1. Remove the hardcoded strategy assignment block below
        2. Uncomment the RAG lookup code
        3. Restore the original strategy logic (if/elif/else)
        """
        self.mem.log_thinking(f"[CONSULTANT] decide_strategy | Query: '{user_query}'")
        
        # ============================================================================
        # TEMPORARY: HARDCODED TO TABULA_RASA - DISABLE RAG FOR NOW
        # ============================================================================
        # TODO: Remove this block when ready for RAG implementation
        # This ensures TABULA_RASA is always selected regardless of RAG results
        strategy = "TABULA_RASA"
        reasoning = "Using TABULA_RASA strategy (RAG implementation temporarily disabled)."
        context = {
            "manuals": [],  # Empty - RAG disabled
            "history": []   # Empty - RAG disabled
        }
        
        self.mem.log_artifact(f"RAG temporarily disabled - always using TABULA_RASA")
        self.mem.log_artifact(f"Strategy: {strategy} | Reasoning: {reasoning}")
        
        return {
            "strategy": strategy,
            "reasoning": reasoning,
            "context": context
        }
        # ============================================================================
        # END TEMPORARY BLOCK
        # ============================================================================
        
        # ORIGINAL CODE (COMMENTED OUT - UNCOMMENT WHEN READY FOR RAG):
        # # 1. RAG Lookup
        # manual_hits = rag_service.search_provider_manuals(user_query)
        # self.mem.log_artifact(f"RAG Manuals Hit: {len(manual_hits)} found.")
        # history_hits = rag_service.search_workflow_history(user_query)
        # self.mem.log_artifact(f"RAG History Hit: {len(history_hits)} found.")
        # 
        # context = {
        #     "manuals": manual_hits,
        #     "history": history_hits
        # }
        # 
        # # 2. Strategy Logic
        # strategy = "TABULA_RASA" # Default: Start fresh
        # reasoning = "No internal documentation found for this topic."
        # 
        # if history_hits:
        #     strategy = "REPLICATION"
        #     reasoning = f"Found {len(history_hits)} past successful workflows."
        # elif manual_hits:
        #     strategy = "EVIDENCE_BASED"
        #     reasoning = f"Found relevant procedure in {manual_hits[0]['source']}."
        #     
        # return {
        #     "strategy": strategy,
        #     "reasoning": reasoning,
        #     "context": context
        # }
    
    def _detect_domain(self, user_query: str, context: Dict[str, Any]) -> str:
        """
        Detects domain from user query or context.
        Defaults to 'eligibility' if not detected.
        """
        query_lower = user_query.lower()
        
        # Simple keyword-based detection
        if any(keyword in query_lower for keyword in ['eligibility', 'eligible', 'coverage', 'insurance', 'medicaid', 'medicare']):
            return "eligibility"
        elif any(keyword in query_lower for keyword in ['crm', 'customer', 'client', 'contact']):
            return "crm"
        else:
            # Default to eligibility for workflow module
            return "eligibility"
    
    def _detect_step(self, context: Dict[str, Any]) -> str:
        """
        Detects step from context or defaults to 'gate'.
        """
        # For now, default to 'gate' for discovery mode
        # Can be enhanced later to detect from conversation state
        return "gate"
    
    async def build_consultant_prompt(
        self, 
        strategy: str, 
        user_query: str, 
        context: Dict[str, Any],
        session_id: Optional[int] = None
    ) -> Tuple[str, Dict[str, Any], str]:
        """
        Builds prompt from PostgreSQL using unique key pattern.
        New structure: MODULE:DOMAIN:MODE:STEP
        
        Returns:
            (system_instruction: str, generation_config: Dict, prompt_key: str)
        """
        self.mem.log_thinking(f"[CONSULTANT] build_consultant_prompt | Strategy: {strategy}")
        
        # Detect domain and step
        domain = self._detect_domain(user_query, context)
        step = self._detect_step(context)
        mode = strategy  # strategy becomes mode in new structure
        
        # Get prompt from database
        logger.info(f"[CONSULTANT] Requesting prompt from prompt_manager | module=workflow, domain={domain}, mode={mode}, step={step}")
        # Extract session_id from context if available, or use parameter
        session_id = session_id or context.get("session_id")
        prompt_data = await prompt_manager.get_prompt(
            module_name="workflow",
            domain=domain,
            mode=mode,
            step=step,
            session_id=session_id  # Pass session_id so prompt_manager can emit thinking
        )
        
        if not prompt_data:
            # Log detailed error information
            expected_key = f"workflow:{domain}:{mode}:{step}"
            error_msg = (
                f"[CONSULTANT] ERROR - No prompt found in database!\n"
                f"  Module: workflow\n"
                f"  Domain: {domain}\n"
                f"  Mode: {mode}\n"
                f"  Step: {step}\n"
                f"  Expected key: {expected_key}\n"
                f"  This means either:\n"
                f"    1. Migration 015 has not been run (prompt_templates table structure not updated)\n"
                f"    2. Prompt has not been seeded into the database\n"
                f"    3. Prompt exists but is_active = false\n"
                f"    4. Prompt key doesn't match\n"
                f"  Check logs above for detailed error information."
            )
            logger.error(error_msg)
            self.mem.log_thinking(error_msg)
            
            # Fail loudly instead of using fallback
            raise ValueError(
                f"CRITICAL: No prompt found for {expected_key}. "
                f"Please ensure migration 015 is run and prompt is seeded. "
                f"Expected key: '{expected_key}'. "
                f"Check application logs for detailed error information."
            )
        
        logger.info(f"[CONSULTANT] Prompt loaded successfully | Key: {prompt_data.get('key')} | Version: {prompt_data.get('version')}")
        config = prompt_data["config"]
        generation_config = prompt_data["generation_config"]
        
        # Build system instruction - for now, just use what's in the database directly
        # This ensures what's stored is what's sent (no transformation)
        logger.debug(f"[CONSULTANT] Building system instruction directly from config")
        try:
            import json
            # Simple approach: Convert config to readable string format
            # If SYSTEM_INSTRUCTIONS exists, use it as the base
            if "SYSTEM_INSTRUCTIONS" in config:
                parts = []
                
                # Add SYSTEM_INSTRUCTIONS first
                parts.append(config["SYSTEM_INSTRUCTIONS"])
                
                # Add LLM_ROLE if present
                if "LLM_ROLE" in config:
                    parts.append("\n\nLLM_ROLE:")
                    for role_item in config["LLM_ROLE"]:
                        parts.append(f"  - {role_item}")
                
                # Add DISCOVERY_MODE if present
                if "DISCOVERY_MODE" in config:
                    parts.append(f"\n\nDISCOVERY_MODE: {config['DISCOVERY_MODE']}")
                
                # Add MANDATORY_LOGIC
                if "MANDATORY_LOGIC" in config:
                    parts.append("\n\nMANDATORY_LOGIC:")
                    for logic in config["MANDATORY_LOGIC"]:
                        parts.append(f"  {logic}")
                
                # Add GATE_ORDER and GATES if present
                if "GATE_ORDER" in config:
                    parts.append("\n\nGATE_ORDER:")
                    parts.append(f"  {', '.join(config['GATE_ORDER'])}")
                
                if "GATES" in config:
                    parts.append("\n\nGATES:")
                    for gate_key, gate_info in config["GATES"].items():
                        parts.append(f"  {gate_key}:")
                        if isinstance(gate_info, dict):
                            if "question" in gate_info:
                                parts.append(f"    question: {gate_info['question']}")
                            if "expected_categories" in gate_info:
                                parts.append(f"    expected_categories: {', '.join(gate_info['expected_categories'])}")
                            if "optional" in gate_info:
                                parts.append(f"    optional: {gate_info['optional']}")
                
                # Add AGENT_FOCUS_RULES if present
                if "AGENT_FOCUS_RULES" in config:
                    parts.append("\n\nAGENT_FOCUS_RULES:")
                    for rule in config["AGENT_FOCUS_RULES"]:
                        parts.append(f"  - {rule}")
                
                # Add REQUIRED_ANSWERS (for backward compatibility)
                if "REQUIRED_ANSWERS" in config:
                    parts.append("\n\nREQUIRED_ANSWERS:")
                    for key, value in config["REQUIRED_ANSWERS"].items():
                        parts.append(f"  {key}: {value}")
                
                # Add OUTPUT_FORMAT
                if "OUTPUT_FORMAT" in config:
                    parts.append(f"\n\nOUTPUT_FORMAT: {config['OUTPUT_FORMAT']}")
                
                # Add STRICT_JSON_SCHEMA
                if "STRICT_JSON_SCHEMA" in config:
                    parts.append(f"\n\nSTRICT_JSON_SCHEMA:")
                    parts.append(json.dumps(config["STRICT_JSON_SCHEMA"], indent=2))
                
                # Add STRICT_CONSTRAINT
                if "STRICT_CONSTRAINT" in config:
                    parts.append(f"\n\nSTRICT_CONSTRAINT: {config['STRICT_CONSTRAINT']}")
                
                system_instruction = "\n".join(parts)
            else:
                # Fallback: Use PromptBuilder for old format prompts
                pb = PromptBuilder()
                # Get conversation history from prompt_data if available (from orchestrator)
                # Otherwise fall back to transcript from context
                conversation_history = prompt_data.get("conversation_history")
                if conversation_history is None:
                    # Fallback to transcript from context (for backward compatibility)
                    conversation_history = context.get("transcript", [])
                
                pb.build_from_config(config, context={
                    "rag_data": context.get("manuals", []),
                    "transcript": conversation_history,  # Use filtered conversation history
                    "user_query": user_query
                })
                system_instruction = pb.build()
            
            logger.debug(f"[CONSULTANT] System instruction built | Length: {len(system_instruction)} chars")
        except Exception as e:
            logger.error(f"[CONSULTANT] ERROR - Failed to build prompt from config: {e}")
            import traceback
            logger.error(f"[CONSULTANT] Traceback: {traceback.format_exc()}")
            raise
        
        self.mem.log_artifact(f"Prompt built | Key: {prompt_data['key']} | Version: {prompt_data['version']}")
        
        prompt_key = prompt_data.get('key', f"workflow:{domain}:{mode}:{step}")
        return system_instruction, generation_config, prompt_key

consultant_brain = ConsultantBrain()
