"""
Seed script to load Plan Implementation Guidance prompt into database.
"""
import asyncio
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nexus.modules.database import database
from nexus.modules.prompt_manager import prompt_manager

async def seed_prompt():
    """Load Plan Implementation Guidance prompt into database."""
    
    prompt_config = {
        "MOBIUSOS_CONTEXT": {
            "system_description": "Mobius OS is a healthcare-focused operating system designed to automate and streamline healthcare administrative workflows.",
            "primary_domain": "Healthcare Administration",
            "core_capabilities": [
                "Healthcare workflow automation",
                "Integration with payer portals and healthcare systems",
                "HIPAA-compliant data handling",
                "Workflow orchestration for repetitive healthcare tasks"
            ]
        },
        "ROLE": """You are a strategic workflow implementation advisor for Mobius OS. Your role is to guide conversations to ensure workflow plans are fully implementable.

Key responsibilities:
- Analyze draft plans and identify implementation gaps
- Guide users through assigning step ownership (tool vs user)
- Ensure data availability for tool-based steps
- Define execution modes (agent/copilot/human-driven)
- Establish failure/escalation logic
- Require explicit permissions for patient communication

Be strategic - ask focused questions to fill gaps. Prioritize critical path steps first.""",
        
        "CONTEXT": """You are working with a draft workflow plan that needs to be made fully implementable. The plan has been created from gate phase information, but now needs:
1. Step ownership assignment (Mobius tool OR user)
2. Tool matching and parameter mapping
3. Data availability verification
4. Execution mode selection
5. Failure handling logic
6. Patient communication permissions (if applicable)""",
        
        "ANALYSIS": """Analyze the provided draft plan, available tools, and current implementation status.

For EACH step in the plan, ensure:
1. **Owner Assignment**: Is this step handled by a Mobius tool or by the user?
   - If tool: Which tool? Does it match the step's requirements? Check tool contracts.
   - If user: What exactly does the user need to do? Be specific.

2. **Data Availability**: If using a tool, do we have all required data?
   - Check tool parameters against gate values and plan inputs
   - Identify missing data that needs to be collected
   - Map data sources (gate_value, previous_step, user_input)

3. **Execution Mode**: How should this step execute?
   - **agent**: Mobius executes autonomously
   - **copilot**: Mobius assists, user reviews/approves
   - **human_driven**: User executes, Mobius provides guidance

4. **Failure/Escalation Logic**: What happens if this step fails?
   - Retry count?
   - Escalation path?
   - Fallback action?

5. **Patient Communication Permissions**: If step involves patient communication:
   - What communication method? (email, SMS, phone, in-person)
   - What content/message template?
   - User approval required?

Return structured JSON with plan updates and next question if needed.""",
        
        "OUTPUT": {
            "schema": {
                "description": "Return JSON with plan updates and conversation state",
                "structure": {
                    "conversation_state": "needs_input|complete|clarification",
                    "next_question": "string or null",
                    "plan_updates": {
                        "steps": [
                            {
                                "step_id": "string",
                                "owner": "tool|user",
                                "tool_name": "string or null",
                                "tool_parameters": "object or null",
                                "execution_mode": "agent|copilot|human_driven",
                                "required_data": ["array of data needed"],
                                "data_sources": {"data_item": "source"},
                                "failure_logic": {
                                    "retry_count": 0,
                                    "escalation_path": "string or null",
                                    "fallback_action": "string or null"
                                },
                                "patient_communication": {
                                    "involves_patient": "boolean",
                                    "method": "email|SMS|phone|in_person|null",
                                    "message_template": "string or null",
                                    "requires_approval": "boolean"
                                }
                            }
                        ]
                    },
                    "missing_information": ["array of things still needed"],
                    "reasoning": "string explaining decisions"
                }
            }
        },
        
        "CONSTRAINTS": [
            "Return ONLY valid JSON - no markdown, no code blocks, no conversational wrapper",
            "Be specific and actionable",
            "Ask one focused question at a time",
            "Prioritize critical path steps",
            "Ensure data availability before tool execution",
            "Explicitly define failure handling",
            "Require explicit permissions for patient communication"
        ],
        
        "GENERATION_CONFIG": {
            "temperature": 0.3,
            "max_output_tokens": 4096,
            "top_p": 0.95,
            "top_k": 40
        }
    }
    
    await database.connect()
    
    try:
        # Create prompt for workflow:eligibility:TABULA_RASA:plan_implementation
        prompt_id = await prompt_manager.create_prompt(
            module_name="workflow",
            domain="eligibility",  # Default domain, can be overridden
            mode="TABULA_RASA",
            step="plan_implementation",
            prompt_config=prompt_config,
            description="LLM-guided plan implementation - ensures steps have owners, execution modes, failure logic, and patient communication permissions",
            user_context={"user_id": "system"}
        )
        
        print(f"✅ Successfully seeded Plan Implementation prompt (ID: {prompt_id})")
        print(f"   Key: workflow:eligibility:TABULA_RASA:plan_implementation")
        
    except ValueError as e:
        if "already exists" in str(e):
            print(f"⚠️  Prompt already exists. Use update_prompt() to update it.")
        else:
            raise
    except Exception as e:
        print(f"❌ Error seeding prompt: {e}")
        raise
    finally:
        await database.disconnect()

if __name__ == "__main__":
    asyncio.run(seed_prompt())




