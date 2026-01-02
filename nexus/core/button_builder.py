"""
Button Builder - Helper for emitting dynamic action buttons via ARTIFACTS.

Allows any brain/agent to emit button configurations that will be rendered
dynamically in the frontend chat interface.
"""
from typing import List, Dict, Any, Optional, Literal
from nexus.core.base_agent import BaseAgent

async def emit_action_buttons(
    agent: BaseAgent,
    buttons: List[Dict[str, Any]],
    message: Optional[str] = None,
    context: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> None:
    """
    Helper function to emit action buttons via ARTIFACTS.
    
    Args:
        agent: BaseAgent instance
        buttons: List of button configurations. Each button should have:
            - id: Unique identifier
            - label: Display text
            - variant: 'primary', 'secondary', 'danger', 'success', 'warning'
            - action: {
                type: 'api_call' | 'event' | 'navigation'
                endpoint: API endpoint (for api_call)
                method: HTTP method (for api_call)
                payload: Request payload (for api_call)
                eventName: Event name (for event)
                route: Route path (for navigation)
              }
            - enabled: Boolean
            - tooltip: Optional tooltip text
            - icon: Optional icon name ('check', 'edit', 'cancel', 'add', 'warning', 'arrow')
        message: Optional message to display above buttons
        context: Optional context for styling (e.g., 'planning_phase_decision', 'gate_question')
        metadata: Optional metadata for button matching (e.g., {'gate_key': '1_patient_info_availability'})
    
    Example:
        await emit_action_buttons(
            agent,
            [
                {
                    "id": "build_new",
                    "label": "Build New Workflow",
                    "variant": "primary",
                    "action": {
                        "type": "api_call",
                        "endpoint": "/api/workflows/shaping/{session_id}/planning-phase/decision",
                        "method": "POST",
                        "payload": {"choice": "build_new"}
                    },
                    "enabled": True,
                    "icon": "add"
                }
            ],
            message="First, would you like to:",
            context="planning_phase_decision"
        )
    """
    payload = {
        "type": "ACTION_BUTTONS",
        "buttons": buttons,
        "message": message,
        "context": context
    }
    
    # Add metadata if provided
    if metadata:
        payload["metadata"] = metadata
    
    await agent.emit("ARTIFACTS", payload)

