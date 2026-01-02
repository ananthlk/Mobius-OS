"""
Action Button Handler - Reusable module for handling action button decisions and flow progression.

This module provides a standardized way for agents to:
1. Emit action buttons with decision handlers
2. Process button clicks and store decisions
3. Trigger next steps automatically
4. Manage button lifecycle (show/hide based on state)

Usage Example:
    from nexus.core.base_agent import BaseAgent
    from nexus.core.action_button_handler import ActionButtonHandler
    
    # In your agent/brain:
    agent = BaseAgent(session_id=session_id)
    handler = ActionButtonHandler(agent)
    
    # Emit buttons with automatic decision checking
    await handler.emit_decision_buttons(
        buttons=[
            {
                "id": "option_a",
                "label": "Option A",
                "variant": "primary",
                "action": {
                    "type": "api_call",
                    "endpoint": f"/api/endpoint/{session_id}/decision",
                    "method": "POST",
                    "payload": {"choice": "option_a"}
                },
                "enabled": True
            }
        ],
        decision_column="my_decision_column",
        decision_table="my_table",
        message="Choose an option:",
        context="decision_context"
    )
    
    # In your endpoint handler:
    async def handle_decision(session_id: int, choice: str):
        agent = BaseAgent(session_id=session_id)
        handler = ActionButtonHandler(agent)
        
        async def on_decision(button_id: str, decision_value: str):
            # Your custom logic here
            return {
                "status": "success",
                "message": "Decision processed",
                "next_step": "next_action"
            }
        
        result = await handler.process_decision(
            button_id=choice,
            decision_value=choice,
            decision_column="my_decision_column",
            decision_table="my_table",
            on_decision=on_decision
        )
        return result
"""
import logging
from typing import Dict, Any, Optional, Callable, Awaitable, List
from nexus.core.base_agent import BaseAgent
from nexus.core.button_builder import emit_action_buttons
from nexus.modules.database import database

logger = logging.getLogger("nexus.core.action_button_handler")


class ActionButtonHandler:
    """
    Reusable handler for action button workflows.
    
    Manages the complete lifecycle of action buttons:
    - Emission with decision handlers
    - Decision storage and state management
    - Automatic next step triggering
    - Button visibility control
    """
    
    def __init__(self, agent: BaseAgent):
        """
        Initialize handler with an agent instance.
        
        Args:
            agent: BaseAgent instance for emitting events
        """
        self.agent = agent
        self.session_id = agent.session_id
        self.logger = logger
    
    async def emit_decision_buttons(
        self,
        buttons: List[Dict[str, Any]],
        decision_column: str,
        decision_table: str = "shaping_sessions",
        message: Optional[str] = None,
        context: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        on_decision: Optional[Callable[[str, Dict[str, Any]], Awaitable[Dict[str, Any]]]] = None
    ) -> None:
        """
        Emit action buttons with automatic decision handling.
        
        Args:
            buttons: List of button configurations (see button_builder.py for format)
            decision_column: Database column name to store the decision (e.g., 'planning_phase_decision')
            decision_table: Table name where decision is stored (default: 'shaping_sessions')
            message: Optional message to display above buttons
            context: Optional context for styling
            metadata: Optional metadata for button matching (e.g., {'phase': 'planning', 'step': 'build_reuse_decision'})
            on_decision: Optional async callback function(button_id, button_data) -> result_dict
                        Called after decision is stored. Should return dict with:
                        - status: 'success' | 'error'
                        - message: Optional message
                        - next_step: Optional next step identifier
                        - Any other data needed for flow progression
        
        Example:
            handler = ActionButtonHandler(agent)
            await handler.emit_decision_buttons(
                buttons=[
                    {
                        "id": "build_new",
                        "label": "Build New Workflow",
                        "variant": "primary",
                        "action": {
                            "type": "api_call",
                            "endpoint": f"/api/workflows/shaping/{session_id}/planning-phase/decision",
                            "method": "POST",
                            "payload": {"choice": "build_new"}
                        },
                        "enabled": True
                    }
                ],
                decision_column="planning_phase_decision",
                message="First, would you like to:",
                context="planning_phase_decision",
                on_decision=async (button_id, button_data) => {
                    # Custom logic after decision
                    return {"status": "success", "next_step": "compute_plan"}
                }
            )
        """
        if not self.session_id:
            self.logger.warning("Cannot emit decision buttons without session_id")
            return
        
        # Check if decision already exists
        decision_exists = await self._check_decision_exists(decision_column, decision_table)
        
        if decision_exists:
            self.logger.debug(f"Decision already exists in {decision_column}, skipping button emission")
            return
        
        # Emit buttons via button_builder with metadata
        await emit_action_buttons(
            self.agent,
            buttons,
            message=message,
            context=context,
            metadata=metadata
        )
    
    async def process_decision(
        self,
        button_id: str,
        decision_value: str,
        decision_column: str,
        decision_table: str = "shaping_sessions",
        on_decision: Optional[Callable[[str, Dict[str, Any]], Awaitable[Dict[str, Any]]]] = None
    ) -> Dict[str, Any]:
        """
        Process a button decision and store it.
        
        This method should be called by the endpoint handler when a button is clicked.
        
        Args:
            button_id: ID of the button that was clicked
            decision_value: The decision value to store (e.g., 'build_new', 'reuse')
            decision_column: Database column name to store the decision
            decision_table: Table name where decision is stored
            on_decision: Optional async callback function(button_id, decision_value) -> result_dict
                        Called after decision is stored. Should return dict with:
                        - status: 'success' | 'error'
                        - message: Optional message
                        - next_step: Optional next step identifier
        
        Returns:
            Dict with status, message, and optional next_step
        
        Example:
            handler = ActionButtonHandler(agent)
            result = await handler.process_decision(
                button_id="build_new",
                decision_value="build_new",
                decision_column="planning_phase_decision",
                on_decision=async (button_id, decision_value) => {
                    # Trigger next step
                    return {"status": "success", "next_step": "compute_plan"}
                }
            )
        """
        if not self.session_id:
            raise ValueError("Cannot process decision without session_id")
        
        try:
            # Store decision in database
            await self._store_decision(decision_value, decision_column, decision_table)
            
            # Call custom handler if provided
            result = {
                "decision": decision_value,
                "status": "success",
                "message": f"Decision '{decision_value}' recorded"
            }
            
            if on_decision:
                custom_result = await on_decision(button_id, decision_value)
                result.update(custom_result)
            
            self.logger.info(f"Decision processed: {button_id}={decision_value} for session {self.session_id}")
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to process decision: {e}", exc_info=True)
            return {
                "decision": decision_value,
                "status": "error",
                "message": f"Failed to process decision: {str(e)}"
            }
    
    async def check_decision_exists(
        self,
        decision_column: str,
        decision_table: str = "shaping_sessions"
    ) -> bool:
        """
        Check if a decision has already been made.
        
        Useful for filtering buttons in get_session_state.
        
        Args:
            decision_column: Database column name to check
            decision_table: Table name to check
        
        Returns:
            True if decision exists, False otherwise
        """
        return await self._check_decision_exists(decision_column, decision_table)
    
    async def _check_decision_exists(
        self,
        decision_column: str,
        decision_table: str
    ) -> bool:
        """Internal: Check if decision exists in database."""
        try:
            query = f"SELECT {decision_column} FROM {decision_table} WHERE id = :session_id"
            row = await database.fetch_one(query, {"session_id": self.session_id})
            
            if row:
                row_dict = dict(row)
                decision = row_dict.get(decision_column)
                return decision is not None and decision != ""
            
            return False
        except Exception as e:
            # Column or table might not exist - treat as no decision
            self.logger.debug(f"Could not check decision existence: {e}")
            return False
    
    async def _store_decision(
        self,
        decision_value: str,
        decision_column: str,
        decision_table: str
    ) -> None:
        """Internal: Store decision in database."""
        try:
            query = f"""
                UPDATE {decision_table}
                SET {decision_column} = :decision,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = :session_id
            """
            await database.execute(query, {
                "session_id": self.session_id,
                "decision": decision_value
            })
            self.logger.debug(f"Decision stored: {decision_column}={decision_value}")
        except Exception as e:
            self.logger.error(f"Failed to store decision: {e}", exc_info=True)
            raise


async def should_show_action_buttons(
    session_id: int,
    decision_column: str,
    decision_table: str = "shaping_sessions"
) -> bool:
    """
    Utility function to check if action buttons should be shown.
    
    Used by orchestrator.get_session_state() to filter buttons.
    
    Args:
        session_id: Session ID to check
        decision_column: Database column name to check
        decision_table: Table name to check
    
    Returns:
        True if buttons should be shown (no decision made), False otherwise
    """
    try:
        query = f"SELECT {decision_column} FROM {decision_table} WHERE id = :session_id"
        row = await database.fetch_one(query, {"session_id": session_id})
        
        if row:
            row_dict = dict(row)
            decision = row_dict.get(decision_column)
            # Show buttons if no decision has been made
            return decision is None or decision == ""
        
        # If row doesn't exist, show buttons (might be new session)
        return True
    except Exception as e:
        # Column or table might not exist - show buttons by default
        logger.debug(f"Could not check decision for button visibility: {e}")
        return True

