"""
Conversational Agent

Entry point for all user messages and post-processing layer that transforms raw LLM responses 
from other agents into user-friendly, well-formatted responses based on user communication preferences.
"""
import logging
from typing import Dict, Any, Optional
from nexus.core.memory_logger import MemoryLogger
from nexus.core.base_agent import BaseAgent
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
        
        Args:
            raw_response: The raw response text from another agent
            user_id: User identifier for loading preferences
            context: Additional context (e.g., session_id, conversation_history)
            
        Returns:
            Formatted response string
        """
        session_id = context.get("session_id")
        conversation_history = context.get("conversation_history", [])
        self.mem.log_thinking(f"[CONVERSATIONAL_AGENT] format_response | User: {user_id} | Response length: {len(raw_response)} chars | History: {len(conversation_history)} messages")
        
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
            
            # 4. Build messages for LLM call with conversation history
            messages = [{"role": "system", "content": system_instruction}]
            
            # Add conversation history (last 10 messages for context)
            if conversation_history:
                # Filter to only user and assistant messages, limit to last 10
                recent_history = [
                    {"role": msg.get("role", "user"), "content": msg.get("content", "")}
                    for msg in conversation_history[-10:]
                    if msg.get("role") in ["user", "assistant", "system"] and msg.get("content")
                ]
                messages.extend(recent_history)
                self.mem.log_artifact(f"Included {len(recent_history)} messages from conversation history")
            
            # Add the current response to format
            messages.append({"role": "user", "content": f"Please format this response:\n\n{raw_response}"})
            
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
    
    async def receive_and_acknowledge(
        self,
        user_message: str,
        user_id: str,
        session_id: Optional[int] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        First point of contact for user messages.
        Acknowledges receipt, shows understanding, then routes to appropriate handler.
        
        Args:
            user_message: The user's message
            user_id: User identifier
            session_id: Optional session ID for context
            context: Additional context (e.g., operation type, metadata, button_label)
            
        Returns:
            {
                "acknowledgment": str,  # Echo/confirmation message
                "routing_decision": str,  # Which agent to route to
                "processed_message": str  # Potentially cleaned/normalized message
            }
        """
        self.mem.log_thinking(f"[CONVERSATIONAL_AGENT] receive_and_acknowledge | User: {user_id} | Message length: {len(user_message)} chars")
        
        try:
            agent = BaseAgent(session_id=session_id)
            
            # Check if this is from a button click (via context)
            is_button_click = context and context.get("is_button_click", False)
            button_label = context.get("button_label") if context else None
            
            # Try to detect button clicks from session state or common patterns
            if not is_button_click:
                button_label = await self._detect_button_label(user_message, session_id)
                if button_label:
                    is_button_click = True
                    logger.info(f"[CONVERSATIONAL_AGENT] Detected button click: message='{user_message}' -> label='{button_label}'")
            
            # 1. Generate and emit acknowledgment immediately
            acknowledgment = await self._generate_acknowledgment(
                user_message, 
                user_id, 
                session_id,
                is_button_click=is_button_click,
                button_label=button_label
            )
            logger.info(f"[CONVERSATIONAL_AGENT] Emitting acknowledgment: '{acknowledgment}' (is_button_click={is_button_click})")
            
            # For button clicks, emit the button label as user message for display
            # But keep original message (category value) for gate engine processing
            processed_message = user_message  # Keep original message for gate engine processing
            if is_button_click and button_label:
                logger.info(f"[CONVERSATIONAL_AGENT] Button click detected: label='{button_label}', original message='{user_message}'")
                # Emit the button label as a user message immediately for visual feedback
                memory_event_id = await agent.emit("OUTPUT", {"role": "user", "content": button_label})
                
                # Save button label to transcript as user message (for display)
                # The gate engine will process the original category value from processed_message
                if session_id and memory_event_id:
                    try:
                        from nexus.modules.database import database
                        import json
                        # Get current transcript
                        select_query = "SELECT transcript FROM shaping_sessions WHERE id = :id"
                        row = await database.fetch_one(query=select_query, values={"id": session_id})
                        if row:
                            transcript = json.loads(row["transcript"] or "[]")
                            # Append button label as user message to transcript (for display)
                            transcript.append({
                                "role": "user",
                                "content": button_label,
                                "timestamp": "now",
                                "memory_event_id": memory_event_id,
                                "original_value": user_message  # Store original category value for reference
                            })
                            # Save updated transcript
                            update_query = "UPDATE shaping_sessions SET transcript = :transcript WHERE id = :id"
                            await database.execute(
                                query=update_query,
                                values={"id": session_id, "transcript": json.dumps(transcript)}
                            )
                            logger.debug(f"[CONVERSATIONAL_AGENT] Saved button label '{button_label}' to transcript (original value: '{user_message}')")
                    except Exception as e:
                        logger.warning(f"[CONVERSATIONAL_AGENT] Could not save button label to transcript: {e}", exc_info=True)
            else:
                # For regular messages, emit acknowledgment as system message
                memory_event_id = await agent.emit("OUTPUT", {"role": "system", "content": acknowledgment})
                
                # Save acknowledgment to transcript if session_id is available
                if session_id and memory_event_id:
                    try:
                        from nexus.modules.database import database
                        import json
                        # Get current transcript
                        select_query = "SELECT transcript FROM shaping_sessions WHERE id = :id"
                        row = await database.fetch_one(query=select_query, values={"id": session_id})
                        if row:
                            transcript = json.loads(row["transcript"] or "[]")
                            # Append acknowledgment to transcript
                            transcript.append({
                                "role": "system",
                                "content": acknowledgment,
                                "timestamp": "now",
                                "memory_event_id": memory_event_id
                            })
                            # Save updated transcript
                            update_query = "UPDATE shaping_sessions SET transcript = :transcript WHERE id = :id"
                            await database.execute(
                                query=update_query,
                                values={"id": session_id, "transcript": json.dumps(transcript)}
                            )
                            logger.debug(f"[CONVERSATIONAL_AGENT] Saved acknowledgment to transcript (memory_event_id={memory_event_id})")
                    except Exception as e:
                        logger.warning(f"[CONVERSATIONAL_AGENT] Could not save acknowledgment to transcript: {e}")
            
            # 2. Show thinking status
            await agent.emit("THINKING", {"message": "Processing your request..."})
            
            # 3. Determine routing (optional: can do intent detection here)
            routing_decision = await self._determine_routing(user_message, session_id, context)
            
            # 4. Return routing info for orchestrator
            result = {
                "acknowledgment": acknowledgment,
                "routing_decision": routing_decision,
                "processed_message": processed_message  # Use button label if button click, otherwise original message
            }
            
            self.mem.log_artifact(f"Routing decision: {routing_decision}")
            return result
            
        except Exception as e:
            logger.error(f"[CONVERSATIONAL_AGENT] Error in receive_and_acknowledge: {e}", exc_info=True)
            self.mem.log_thinking(f"[CONVERSATIONAL_AGENT] Error: {e} - using fallback")
            # Fallback: return simple acknowledgment and default routing
            return {
                "acknowledgment": "Got it. Processing your request...",
                "routing_decision": "gate",
                "processed_message": user_message
            }
    
    async def _detect_button_label(self, message: str, session_id: Optional[int] = None) -> Optional[str]:
        """
        Try to detect if a message is from a button click and return the button label.
        First tries to look up from session's latest action buttons, then falls back to common mappings.
        
        Args:
            message: The message to check
            session_id: Optional session ID to look up buttons from session state
            
        Returns:
            Button label if detected, None otherwise
        """
        message_trimmed = message.strip()
        
        # First, try to look up from session's latest action buttons
        if session_id:
            try:
                from nexus.conductors.workflows.orchestrator import orchestrator
                session = await orchestrator.get_session_state(session_id)
                
                # Check latest_action_buttons in session
                latest_action_buttons = session.get("latest_action_buttons")
                logger.debug(f"[CONVERSATIONAL_AGENT] Looking up button for message '{message_trimmed}' in session {session_id}. Found action_buttons: {latest_action_buttons is not None}")
                
                if latest_action_buttons and isinstance(latest_action_buttons, dict):
                    buttons = latest_action_buttons.get("buttons", [])
                    if isinstance(buttons, list):
                        logger.debug(f"[CONVERSATIONAL_AGENT] Checking {len(buttons)} buttons for match")
                        # Try to match message to button value or label
                        for button in buttons:
                            if isinstance(button, dict):
                                # Check if message matches button value (for gate buttons)
                                button_value = button.get("value", "")
                                button_label = button.get("label", "")
                                button_id = button.get("id", "")
                                
                                logger.debug(f"[CONVERSATIONAL_AGENT] Checking button: value='{button_value}', label='{button_label}', id='{button_id}'")
                                
                                # Match by value (gate buttons send category as message)
                                if button_value and message_trimmed.lower() == button_value.lower():
                                    logger.info(f"[CONVERSATIONAL_AGENT] Matched button by value: '{button_value}' -> '{button_label}'")
                                    return button_label
                                
                                # Match by label (exact match)
                                if button_label and message_trimmed.lower() == button_label.lower():
                                    logger.info(f"[CONVERSATIONAL_AGENT] Matched button by label: '{button_label}'")
                                    return button_label
                                
                                # Match by ID pattern (gate buttons have pattern like "gate_{gate_key}_{category}")
                                if button_id and message_trimmed.lower() in button_id.lower():
                                    logger.info(f"[CONVERSATIONAL_AGENT] Matched button by ID pattern: '{button_id}' -> '{button_label}'")
                                    return button_label
            except Exception as e:
                logger.warning(f"[CONVERSATIONAL_AGENT] Could not look up button from session: {e}", exc_info=True)
        
        # Fallback: Common gate button value mappings
        # These match the expected_categories from gate configs
        button_value_to_label = {
            "Yes": "Yes - I have name + DOB or insurance information",
            "No": "No - I do not have either name+DOB or insurance",
            "Partial": "Partial - I have one of name+DOB or insurance (but not both)",
            "Unknown": "Unknown - not sure what information is available",
            "Other": "Other"
        }
        
        # Check if message matches a known button value
        if message_trimmed in button_value_to_label:
            return button_value_to_label[message_trimmed]
        
        # Check case-insensitive
        for value, label in button_value_to_label.items():
            if message_trimmed.lower() == value.lower():
                return label
        
        return None
    
    async def _generate_acknowledgment(
        self,
        user_message: str,
        user_id: str,
        session_id: Optional[int] = None,
        is_button_click: bool = False,
        button_label: Optional[str] = None
    ) -> str:
        """
        Generate a brief acknowledgment/echo of user message.
        Can use LLM for natural acknowledgment, or simple template for speed.
        
        Args:
            user_message: The user's message
            user_id: User identifier for preferences
            session_id: Optional session ID for context
            is_button_click: Whether this is from a button click
            button_label: Optional button label to display instead of message
            
        Returns:
            Acknowledgment string
        """
        try:
            # Load user preferences for tone/style
            user_prefs = await communication_preferences.get_user_preferences(user_id)
            tone = user_prefs.get("tone", "professional")
            style = user_prefs.get("style", "brief")
            
            # If this is a button click, use the button label
            display_text = button_label if (is_button_click and button_label) else user_message
            
            # For button clicks, format differently
            if is_button_click and button_label:
                if tone == "casual":
                    acknowledgment = f"Got it! You selected: **{button_label}**"
                elif tone == "formal":
                    acknowledgment = f"I understand. You have selected: **{button_label}**"
                else:  # professional (default)
                    acknowledgment = f"Understood. You selected: **{button_label}**"
                
                # If style is brief, keep it shorter
                if style == "brief":
                    acknowledgment = f"Selected: **{button_label}**"
            else:
                # Regular message acknowledgment
                message_preview = display_text[:100]
                if len(display_text) > 100:
                    message_preview += "..."
                
                # Generate acknowledgment based on tone
                if tone == "casual":
                    acknowledgment = f"Got it! {message_preview}"
                elif tone == "formal":
                    acknowledgment = f"I understand. {message_preview}"
                else:  # professional (default)
                    acknowledgment = f"Understood. {message_preview}"
                
                # If style is brief, keep it short
                if style == "brief" and len(acknowledgment) > 50:
                    acknowledgment = "Got it. Processing..."
            
            return acknowledgment
            
        except Exception as e:
            logger.warning(f"[CONVERSATIONAL_AGENT] Error generating acknowledgment: {e}, using fallback")
            # Fallback: simple acknowledgment
            if is_button_click and button_label:
                return f"Selected: **{button_label}**"
            return "Got it. Processing your request..."
    
    async def _determine_routing(
        self,
        message: str,
        session_id: Optional[int] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Determine which agent should handle this message.
        Can be enhanced with intent detection, session state analysis, etc.
        
        Args:
            message: The user's message
            session_id: Optional session ID to check session state
            context: Additional context
            
        Returns:
            Routing decision string ("gate", "planning", "execution", etc.)
        """
        try:
            # For now, return "gate" as default
            # The orchestrator will handle actual routing based on session state
            # This method can be enhanced later to:
            # - Check session state (active_agent)
            # - Analyze message intent
            # - Detect urgency/priority
            # - Route based on keywords/phrases
            
            # If context provides routing hint, use it
            if context and "suggested_routing" in context:
                return context["suggested_routing"]
            
            # Default: gate agent (orchestrator will override based on session state)
            return "gate"
            
        except Exception as e:
            logger.warning(f"[CONVERSATIONAL_AGENT] Error determining routing: {e}, using fallback")
            return "gate"
    
    async def acknowledge_button_click(
        self,
        button_label: str,
        button_id: Optional[str] = None,
        user_id: str = "anonymous",
        session_id: Optional[int] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Acknowledge a button click by playing back the button label.
        
        Args:
            button_label: The label/text of the button that was clicked
            button_id: Optional button ID for logging
            user_id: User identifier for preferences
            session_id: Optional session ID for context
            context: Additional context (e.g., button type, action)
        """
        self.mem.log_thinking(f"[CONVERSATIONAL_AGENT] acknowledge_button_click | Button: {button_label} | ID: {button_id}")
        
        try:
            agent = BaseAgent(session_id=session_id)
            
            # Generate acknowledgment based on user preferences
            user_prefs = await communication_preferences.get_user_preferences(user_id)
            tone = user_prefs.get("tone", "professional")
            style = user_prefs.get("style", "brief")
            
            # Generate acknowledgment based on tone
            if tone == "casual":
                acknowledgment = f"Got it! You selected: **{button_label}**"
            elif tone == "formal":
                acknowledgment = f"I understand. You have selected: **{button_label}**"
            else:  # professional (default)
                acknowledgment = f"Understood. You selected: **{button_label}**"
            
            # If style is brief, keep it shorter
            if style == "brief":
                acknowledgment = f"Selected: **{button_label}**"
            
            # Emit acknowledgment
            await agent.emit("OUTPUT", {"role": "system", "content": acknowledgment})
            
            # Show thinking status
            await agent.emit("THINKING", {"message": "Processing your selection..."})
            
            self.mem.log_artifact(f"Button acknowledged: {button_label}")
            
        except Exception as e:
            logger.error(f"[CONVERSATIONAL_AGENT] Error acknowledging button click: {e}", exc_info=True)
            self.mem.log_thinking(f"[CONVERSATIONAL_AGENT] Error: {e} - using fallback")
            # Fallback: simple acknowledgment
            try:
                agent = BaseAgent(session_id=session_id)
                await agent.emit("OUTPUT", {"role": "system", "content": f"Selected: **{button_label}**"})
                await agent.emit("THINKING", {"message": "Processing your selection..."})
            except Exception as fallback_error:
                logger.error(f"[CONVERSATIONAL_AGENT] Fallback acknowledgment also failed: {fallback_error}")


# Singleton instance
conversational_agent = ConversationalAgent()





