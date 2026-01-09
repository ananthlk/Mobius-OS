"""
Conversational Agent

Entry point for all user messages and post-processing layer that transforms raw LLM responses 
from other agents into user-friendly, well-formatted responses based on user communication preferences.
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
    Conversational agent that:
    1. Receives and acknowledges all user messages (entry point)
    2. Formats raw responses from other agents into user-friendly formats
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
        Uses conversation history to contextualize the response.
        """
        session_id = context.get("session_id")
        conversation_history = context.get("conversation_history", [])
        self.mem.log_thinking(f"[CONVERSATIONAL_AGENT] format_response | User: {user_id} | Response length: {len(raw_response)} chars")
        
        try:
            # 1. Load user communication preferences
            user_prefs = await communication_preferences.get_user_preferences(user_id)
            self.mem.log_artifact(f"User preferences: {user_prefs}")
            
            # 2. Detect domain from context
            source = context.get("source", "")
            operation = context.get("operation", "")
            
            domain = "formatting"  # Default
            if source == "eligibility_v2" or operation == "eligibility_response" or operation == "eligibility_question":
                domain = "eligibility"
            elif "gate" in operation.lower() or "workflow" in source.lower():
                domain = "eligibility"
            
            logger.info(f"[CONVERSATIONAL_AGENT] Detected domain: {domain} from source={source}, operation={operation}")
            
            # 3. Load prompt template
            prompt_data = await prompt_manager.get_prompt(
                module_name="conversational",
                domain=domain,
                mode="default",
                step="response",
                session_id=session_id
            )
            
            if not prompt_data and domain != "formatting":
                prompt_data = await prompt_manager.get_prompt(
                    module_name="conversational",
                    domain="formatting",
                    mode="default",
                    step="response",
                    session_id=session_id
                )
            
            if not prompt_data:
                logger.error("[CONVERSATIONAL_AGENT] Prompt not found, returning raw response")
                return raw_response
            
            config = prompt_data["config"]
            generation_config = prompt_data.get("generation_config", {})
            
            # 4. Build modular prompt
            system_instruction = self._build_modular_prompt(config, user_prefs)
            self.mem.log_thinking(f"[CONVERSATIONAL_AGENT] Built modular prompt | Length: {len(system_instruction)} chars")
            
            # 5. Build messages for LLM call
            messages = [{"role": "system", "content": system_instruction}]
            
            # Add conversation history
            if conversation_history:
                recent_history = [
                    {"role": msg.get("role", "user"), "content": msg.get("content", "")}
                    for msg in conversation_history[-10:]
                    if msg.get("role") in ["user", "assistant", "system"] and msg.get("content")
                ]
                messages.extend(recent_history)
                self.mem.log_artifact(f"Included {len(recent_history)} messages from conversation history")
            
            # Add the current response to format
            # Include visit-specific probability data if available
            visit_probabilities = context.get("visit_probabilities", [])
            formatting_request = f"Please format this response:\n\n{raw_response}"
            
            if visit_probabilities:
                formatting_request += "\n\n**IMPORTANT: Date-of-Service-Specific Data**\n"
                formatting_request += "The following visits have been analyzed with specific eligibility probabilities:\n\n"
                for visit in visit_probabilities:
                    visit_date = visit.get("visit_date", "Unknown date")
                    probability = visit.get("eligibility_probability", 0)
                    status = visit.get("eligibility_status", "UNKNOWN")
                    event_tense = visit.get("event_tense", "UNKNOWN")
                    visit_type = visit.get("visit_type", "")
                    
                    formatting_request += f"- **Date: {visit_date}** ({event_tense})\n"
                    formatting_request += f"  - Eligibility Status: {status}\n"
                    formatting_request += f"  - Probability: {probability:.1%}\n"
                    if visit_type:
                        formatting_request += f"  - Visit Type: {visit_type}\n"
                    formatting_request += "\n"
                
                formatting_request += "**Your Task:**\n"
                formatting_request += "Organize your response by date of service. For each visit date, provide:\n"
                formatting_request += "1. The eligibility probability for that specific date\n"
                formatting_request += "2. Recommendations specific to that date (e.g., whether to proceed, what to check, etc.)\n"
                formatting_request += "3. Any date-specific considerations (e.g., coverage window, past vs future visit)\n"
                formatting_request += "\nFormat the response so it's clear which recommendations apply to which date."
            
            messages.append({"role": "user", "content": formatting_request})
            
            # 6. Resolve model context
            model_context = await config_manager.resolve_app_context(
                module_id="conversational",
                user_id=user_id
            )
            
            # 7. Call LLM Gateway
            self.mem.log_thinking(f"[CONVERSATIONAL_AGENT] Calling LLM for transformation | Model: {model_context.get('model_id')}")
            
            response = await gateway.chat_completion(
                messages=messages,
                module_id="conversational",
                user_id=user_id
            )
            
            formatted_response = response.get("content", raw_response)
            self.mem.log_artifact(f"Formatted response length: {len(formatted_response)} chars")
            logger.info(f"[CONVERSATIONAL_AGENT] Formatted response preview: {formatted_response[:200]}...")
            
            return formatted_response
            
        except Exception as e:
            logger.error(f"[CONVERSATIONAL_AGENT] Error formatting response: {e}", exc_info=True)
            self.mem.log_thinking(f"[CONVERSATIONAL_AGENT] Error: {e} - returning raw response as fallback")
            return raw_response
    
    def _build_modular_prompt(self, config: Dict[str, Any], user_prefs: Dict[str, str]) -> str:
        """Build the final prompt by incorporating user preferences"""
        system_instruction = config.get("SYSTEM_INSTRUCTIONS", "")
        
        # Replace placeholders with actual user preferences
        system_instruction = system_instruction.replace("{{USER_TONE}}", user_prefs.get("tone", "professional"))
        system_instruction = system_instruction.replace("{{USER_STYLE}}", user_prefs.get("style", "brief"))
        system_instruction = system_instruction.replace("{{USER_ENGAGEMENT}}", user_prefs.get("engagement_level", "engaging"))
        
        return system_instruction


# Singleton instance
conversational_agent = ConversationalAgent()
