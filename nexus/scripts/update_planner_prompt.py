"""
Update script to update existing PLANNER prompt with nested/phased structure.
This will create a new version of the existing prompt.
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

async def update_planner_prompt():
    """Update existing PLANNER prompt with new nested/phased structure."""
    
    # Build the updated prompt config structure
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

MANDATORY OUTPUT FORMAT: You MUST output a JSON object with a "phases" array. DO NOT use a "steps" array at the top level. Each phase contains a "steps" array.

Example structure:
- Phase: "Get Insurance Information for Patient"
  - Step 1: "Check patient insurance directly from EHR system"
  - Step 2: "If not found or not eligible, query HIE for updated insurance information"
  - Step 3: "Once insurance is confirmed, check patient's next scheduled visit"
  - Step 4: "If patient is not eligible, send text notification to patient about eligibility status"

Write step descriptions in plain, user-friendly language.""",
        "CONSTRAINTS": [
            "MANDATORY: Output MUST have a 'phases' array at the top level. DO NOT use a 'steps' array at the top level.",
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
                    "requires_human_review": False
                }
            ]
        }
    ],
    "missing_info": ["e.g. Payer ID"]
}

IMPORTANT: The output MUST have "phases" (plural) as a top-level array. Each phase contains a "steps" array. DO NOT output a top-level "steps" array.
            """,
            "schema": {
                "description": "JSON structure for phased draft plan with nested steps. MUST use 'phases' array at top level, NOT 'steps' array.",
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
                                    "requires_human_review": True
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
        prompt_key = "workflow:eligibility:TABULA_RASA:planner"
        
        print(f"Updating planner prompt:")
        print(f"  Key: {prompt_key}")
        
        new_id = await prompt_manager.update_prompt(
            prompt_key=prompt_key,
            prompt_config=prompt_config,
            change_reason="Updated to nested phases structure with human intervention support - MANDATORY phases format",
            user_context={"user_id": "system"}
        )
        
        # Get the new version
        version_query = "SELECT version FROM prompt_templates WHERE id = :id"
        version = await database.fetch_val(version_query, {"id": new_id})
        
        print(f"✅ Successfully updated PLANNER prompt (ID: {new_id}, Version: {version})")
        print(f"   Key: {prompt_key}")
        
        # Verify it was updated
        verify = await prompt_manager.get_prompt(
            module_name="workflow",
            domain="eligibility",
            mode="TABULA_RASA",
            step="planner"
        )
        if verify:
            print(f"✅ Verification: Prompt found in database (Version: {verify.get('version')})")
            # Check if it has the new structure
            config = verify.get("config", {})
            output_config = config.get("OUTPUT", {})
            if isinstance(output_config, dict):
                format_str = output_config.get("format", "")
                if "phases" in format_str:
                    print(f"✅ Verification: Prompt has 'phases' structure")
                else:
                    print(f"⚠️  Warning: Prompt format may still reference 'steps'")
        else:
            print(f"⚠️  Verification: Prompt NOT found in database")
        
    except ValueError as e:
        if "not found" in str(e):
            print(f"❌ Prompt not found. Run seed_planner_prompt.py first to create it.")
        else:
            raise
    except Exception as e:
        print(f"❌ Error updating prompt: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        await database.disconnect()

if __name__ == "__main__":
    asyncio.run(update_planner_prompt())

