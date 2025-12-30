from nexus.core.base_agent import AgentRecipe, AgentStep
from nexus.workflows.registry import registry

# --- Workflow Definition: Appointment Assurance ---
# This is the "Thin Recipe" (Data)
ASSURANCE_RECIPE = AgentRecipe(
    name="appointment_assurance",
    goal="Analyze next 14 days of appointments for revenue and attendance risks.",
    start_step_id="scan_schedule",
    steps={
        "scan_schedule": AgentStep(
            step_id="scan_schedule",
            tool_name="schedule_scanner",
            description="Fetch appointments for the next 14 days.",
            args_mapping={
                "days_out": "days_to_plan" # Expects 'days_to_plan' in context, or defaults to 14 in tool
            },
            transition_success="calc_risks",
            transition_fail=None # End on fail
        ),
        "calc_risks": AgentStep(
            step_id="calc_risks",
            tool_name="risk_calculator",
            description="Calculate No-Show and Denial risks for the fetched appointments.",
            args_mapping={
                # The output of scan_schedule is a list, typically merged into context
                # But here we need to be careful. The previous tool returned a list.
                # In base_agent.py we implemented: context[step.step_id] = result
                # So the result is at context['scan_schedule']
                "appointments": "scan_schedule" 
            },
            transition_success=None, # End of flow
            transition_fail=None
        )
    }
)

async def register_crm_recipes():
    """
    Called at startup to load these into the registry.
    """
    await registry.register_recipe(ASSURANCE_RECIPE)
