"""
Conversational Agent

Post-processing layer that transforms raw LLM responses from other agents
into user-friendly, well-formatted responses based on user communication preferences.
"""
import logging
from typing import Dict, Any, Optional
from nexus.core.memory_logger import MemoryLogger
from nexus.modules.prompt_manager import prompt_manager
from nexus.modules.communication_preferences import communication_preferences
from nexus.modules.llm_gateway import gateway
from nexus.modules.config_manager import config_manager

logger = logging.getLogger("nexus.conversational_agent")


class ConversationalAgent:
    """
    Conversational formatting agent that transforms raw responses into user-friendly formats.
    """
    
    def __init__(self):
        self.mem = MemoryLogger("nexus.conversational_agent")
    
    async def format_response(
        self, 
        raw_response: str, 
        user_id: str, 
        context: Dict[str, Any]
    ) -> str:
        """
        Format a raw LLM response into a user-friendly, well-formatted response.
        
        Args:
            raw_response: The raw response text from another agent
            user_id: User identifier for loading preferences
            context: Additional context (e.g., session_id)
            
        Returns:
            Formatted response string
        """
        session_id = context.get("session_id")
        self.mem.log_thinking(f"[CONVERSATIONAL_AGENT] format_response | User: {user_id} | Response length: {len(raw_response)} chars")
        
        try:
            # 1. Load user communication preferences (or use defaults)
            user_prefs = await communication_preferences.get_user_preferences(user_id)
            self.mem.log_artifact(f"User preferences: {user_prefs}")
            
            # 2. Load base prompt template from prompt_manager
            prompt_data = await prompt_manager.get_prompt(
                module_name="conversational",
                domain="formatting",
                mode="default",
                step="response",
                session_id=session_id
            )
            
            if not prompt_data:
                error_msg = "Conversational agent prompt not found in database. Please seed it using seed_conversational_agent_prompt.py"
                logger.error(f"[CONVERSATIONAL_AGENT] {error_msg}")
                self.mem.log_thinking(error_msg)
                # Fallback: return raw response if prompt not found
                return raw_response
            
            config = prompt_data["config"]
            generation_config = prompt_data.get("generation_config", {})
            
            # 3. Build modular prompt by incorporating user preferences
            system_instruction = self._build_modular_prompt(config, user_prefs)
            self.mem.log_thinking(f"[CONVERSATIONAL_AGENT] Built modular prompt | Length: {len(system_instruction)} chars")
            
            # 4. Build messages for LLM call
            messages = [
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": f"Please format this response:\n\n{raw_response}"}
            ]
            
            # 5. Resolve model context (can use faster/cheaper model for formatting)
            model_context = await config_manager.resolve_app_context(
                module_id="conversational",
                user_id=user_id
            )
            
            # 6. Call LLM Gateway for transformation
            self.mem.log_thinking(f"[CONVERSATIONAL_AGENT] Calling LLM for transformation | Model: {model_context.get('model_id')}")
            
            response = await gateway.chat_completion(
                messages=messages,
                module_id="conversational",
                user_id=user_id
            )
            
            formatted_response = response.get("content", raw_response)
            self.mem.log_artifact(f"Formatted response length: {len(formatted_response)} chars")
            
            return formatted_response
            
        except Exception as e:
            logger.error(f"[CONVERSATIONAL_AGENT] Error formatting response: {e}", exc_info=True)
            self.mem.log_thinking(f"[CONVERSATIONAL_AGENT] Error: {e} - returning raw response as fallback")
            # Fallback: return raw response if formatting fails
            return raw_response
    
    def _build_modular_prompt(self, config: Dict[str, Any], user_prefs: Dict[str, str]) -> str:
        """
        Build the final prompt by incorporating user preferences into the base template.
        
        Args:
            config: Prompt config from database
            user_prefs: User communication preferences (tone, style, engagement_level)
            
        Returns:
            Complete system instruction with preferences incorporated
        """
        system_instruction = config.get("SYSTEM_INSTRUCTIONS", "")
        
        # Replace placeholders with actual user preferences
        system_instruction = system_instruction.replace("{{USER_TONE}}", user_prefs.get("tone", "professional"))
        system_instruction = system_instruction.replace("{{USER_STYLE}}", user_prefs.get("style", "brief"))
        system_instruction = system_instruction.replace("{{USER_ENGAGEMENT}}", user_prefs.get("engagement_level", "engaging"))
        
        return system_instruction


# Singleton instance
conversational_agent = ConversationalAgent()

