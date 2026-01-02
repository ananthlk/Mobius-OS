"""
Seed script to load PLANNER prompt for Live Builder into database.
Run this after migration 014_prompt_management.sql

This creates the prompt with key: workflow:eligibility:TABULA_RASA:planner
"""
import asyncio
import json
import sys
import os

# Add parent directory to path
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)
os.environ['PYTHONPATH'] = parent_dir

from nexus.modules.database import database
from nexus.modules.prompt_manager import prompt_manager

async def seed_planner_prompt():
    """Load PLANNER prompt config into database."""
    
    # Build the prompt config structure
    prompt_config = {
        "ROLE": "You are the Planner Module of Mobius OS. Your job is to create a COHESIVE, PHASED workflow plan with nested structure. Organize steps into logical phases that tell a coherent story.",
        "CONTEXT": {
            "PROBLEM_STATEMENT": "{{PROBLEM_STATEMENT}}",
            "MANUALS": "{{MANUALS}}",
            "AVAILABLE_TOOLS": "{{AVAILABLE_TOOLS}}"
        },
        "ANALYSIS": """Based on the problem statement and conversation, create a COHESIVE, PHASED workflow plan.

CRITICAL REQUIREMENTS:
1. ORGANIZE INTO PHASES: Group related steps into phases (e.g., "Get Insurance Information", "Verify Eligibility", "Handle Ineligibility")
2. NESTED STRUCTURE: Each phase can contain multiple steps that work together toward a sub-goal
3. LOGICAL FLOW: Steps within a phase should flow logically (e.g., "First check X, if not found then check Y, once confirmed then do Z")
4. CONDITIONAL LOGIC: Use clear conditional language in step descriptions (e.g., "If not eligible, then...", "Once confirmed, then...")
5. MISSING TOOLS: If a task requires a tool that doesn't exist in AVAILABLE_TOOLS, create a HUMAN_INTERVENTION step with:
   - tool_hint: "human_intervention" or "manual_review"
   - description: Clear instruction for what the human needs to do
   - requires_human_review: true
6. COHESIVENESS: Each phase should tell a story - explain WHY steps are in that order and how they build on each other
7. DEPENDENCIES: Clearly show what information each step needs and where it comes from

Example structure:
- Phase: "Get Insurance Information for Patient"
  - Step 1: "Check patient insurance directly from EHR system"
  - Step 2: "If not found or not eligible, query HIE for updated insurance information"
  - Step 3: "Once insurance is confirmed, check patient's next scheduled visit"
  - Step 4: "If patient is not eligible, send text notification to patient about eligibility status"

Write step descriptions in plain, user-friendly language.""",
        "CONSTRAINTS": [
            "Attributes `tool_hint` must be snake_case. Use 'human_intervention' or 'manual_review' if no tool exists.",
            "Each step's `description` must be a user-friendly, one-line description (max 100 characters) written in plain language.",
            "Each step must have a `solves` field explaining how it addresses the problem statement AND how it fits into the phase.",
            "Steps MUST be ordered logically within each phase - consider dependencies, data flow, and prerequisites.",
            "If a tool is missing for a required task, create a HUMAN_INTERVENTION step instead of leaving it out.",
            "Output ONLY valid JSON with nested phases structure."
        ],
        "OUTPUT": {
            "format": """
{
    "problem_statement": "<gate_state.summary or empty string>",
    "name": "Suggested Workflow Name",
    "goal": "Brief goal description",
    "phases": [
        {
            "id": "phase_1",
            "name": "Phase Name (e.g., 'Get Insurance Information')",
            "description": "What this phase accomplishes",
            "steps": [
                { 
                    "id": "step_1_1", 
                    "tool_hint": "e.g. patient_demographics_retriever OR 'human_intervention' if no tool",
                    "description": "User-friendly description showing logical flow (e.g., 'Check patient insurance directly from EHR', 'If not found, query HIE for updated information')",
                    "solves": "How this step addresses the problem and fits in the phase",
                    "requires_human_review": false
                }
            ]
        }
    ],
    "missing_info": ["e.g. Payer ID"]
}
            """,
            "schema": {
                "description": "JSON structure for phased draft plan with nested steps",
                "example": {
                    "problem_statement": "Verify patient insurance eligibility for clinical visits within 24 hours",
                    "name": "Insurance Eligibility Verification with Fallback",
                    "goal": "Confirm patient has active insurance coverage, with fallback to alternative programs if ineligible",
                    "phases": [
                        {
                            "id": "phase_1",
                            "name": "Get Insurance Information",
                            "description": "Retrieve patient insurance information from available sources",
                            "steps": [
                                {
                                    "id": "step_1_1",
                                    "tool_hint": "patient_demographics_retriever",
                                    "description": "Check patient insurance directly from EHR system",
                                    "solves": "Primary source for insurance information"
                                },
                                {
                                    "id": "step_1_2",
                                    "tool_hint": "hie_insurance_query",
                                    "description": "If not found or not eligible, query HIE for updated insurance information",
                                    "solves": "Fallback source when primary check fails"
                                }
                            ]
                        },
                        {
                            "id": "phase_2",
                            "name": "Verify Eligibility Status",
                            "description": "Confirm eligibility and determine next actions",
                            "steps": [
                                {
                                    "id": "step_2_1",
                                    "tool_hint": "billing_eligibility_verifier",
                                    "description": "Verify patient eligibility for billing purposes",
                                    "solves": "Determines if patient can proceed with clinical visit"
                                },
                                {
                                    "id": "step_2_2",
                                    "tool_hint": "human_intervention",
                                    "description": "If eligibility unclear, manually review patient records and insurance documents",
                                    "solves": "Handles edge cases where automated verification fails",
                                    "requires_human_review": true
                                }
                            ]
                        },
                        {
                            "id": "phase_3",
                            "name": "Handle Ineligibility",
                            "description": "Take action based on eligibility status",
                            "steps": [
                                {
                                    "id": "step_3_1",
                                    "tool_hint": "clinical_eligibility_checker",
                                    "description": "Check patient's next scheduled clinical visit",
                                    "solves": "Identifies when eligibility check is needed"
                                },
                                {
                                    "id": "step_3_2",
                                    "tool_hint": "patient_notification_sender",
                                    "description": "If patient is not eligible, send text notification about eligibility status and alternative programs",
                                    "solves": "Keeps patient informed and provides next steps"
                                },
                                {
                                    "id": "step_3_3",
                                    "tool_hint": "alternative_program_finder",
                                    "description": "If patient is ineligible, search for alternative state programs they may qualify for",
                                    "solves": "Provides fallback options for patient care"
                                }
                            ]
                        }
                    ],
                    "missing_info": []
                }
            }
        },
        "GENERATION_CONFIG": {
            "temperature": 0.3,
            "max_tokens": 3000
        }
    }
    
    # Connect to database
    await database.connect()
    
    try:
        # Create the prompt using new API signature: module_name, domain, mode, step
        print(f"Creating planner prompt with:")
        print(f"  module_name: workflow")
        print(f"  domain: eligibility")
        print(f"  mode: TABULA_RASA")
        print(f"  step: planner")
        print(f"  prompt_key will be: workflow:eligibility:TABULA_RASA:planner")
        
        prompt_id = await prompt_manager.create_prompt(
            module_name="workflow",
            domain="eligibility",
            mode="TABULA_RASA",
            step="planner",
            prompt_config=prompt_config,
            description="Planner prompt for Live Builder - generates user-friendly draft plans with step descriptions",
            user_context={"user_id": "system"}
        )
        
        print(f"✅ Successfully seeded PLANNER prompt (ID: {prompt_id})")
        print(f"   Key: workflow:eligibility:TABULA_RASA:planner")
        
        # Verify it was created
        verify = await prompt_manager.get_prompt(
            module_name="workflow",
            domain="eligibility",
            mode="TABULA_RASA",
            step="planner"
        )
        if verify:
            print(f"✅ Verification: Prompt found in database")
        else:
            print(f"⚠️  Verification: Prompt NOT found in database (but create_prompt returned ID: {prompt_id})")
        
    except ValueError as e:
        if "already exists" in str(e):
            print(f"⚠️  Prompt already exists. Use update_prompt() to update it.")
            print(f"   To update, use the API: PUT /api/admin/prompts/workflow:eligibility:TABULA_RASA:planner")
        else:
            raise
    except Exception as e:
        print(f"❌ Error seeding prompt: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        await database.disconnect()

if __name__ == "__main__":
    asyncio.run(seed_planner_prompt())

