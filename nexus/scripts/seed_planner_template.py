"""
Seed script to load comprehensive planner template for TABULA_RASA strategy into database.
Run this to seed the eligibility_plan_templates table.

This creates the template with key: workflow:eligibility:TABULA_RASA:template
"""
import asyncio
import json
import sys
import os

# Add parent directory to path
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)
# Also set PYTHONPATH for subprocess calls
os.environ['PYTHONPATH'] = parent_dir

from nexus.modules.database import database
from nexus.modules.database import connect_to_db, disconnect_from_db
from nexus.templates.template_manager import eligibility_template_manager
from nexus.core.tree_structure_manager import TreePath

async def seed_planner_template():
    """Load comprehensive planner template from JSON into database."""
    
    # Load the hierarchical template config
    template_path = os.path.join(os.path.dirname(__file__), "..", "configs", "hierarchical_eligibility_template.json")
    
    # Fallback to old template if new one doesn't exist
    if not os.path.exists(template_path):
        template_path = os.path.join(os.path.dirname(__file__), "..", "configs", "comprehensive_eligibility_template.json")
    
    # If file doesn't exist, create it from the structure we defined
    if not os.path.exists(template_path):
        print(f"⚠️  Template file not found at {template_path}")
        print(f"   Creating it from the comprehensive structure...")
        
        # Create the comprehensive template structure
        template_data = {
            "template_key": "workflow:eligibility:TABULA_RASA:template",
            "name": "Eligibility Verification Workflow Template - Comprehensive",
            "description": "Comprehensive template for eligibility verification workflows with detailed steps for all phases",
            "template_config": {
                "name": "Eligibility Verification Workflow",
                "goal": "Verify patient eligibility and determine coverage status through comprehensive data gathering and analysis",
                "phases": [
                    {
                        "id": "phase_a",
                        "name": "Retrieve Basic Information",
                        "description": "Gather patient demographics, identifiers, and insurance information from multiple sources",
                        "steps": [
                            {
                                "id": "step_a1",
                                "description": "Collect patient name (first, middle, last)",
                                "tool_hint": "collect_patient_name",
                                "timeline_estimate": "immediately",
                                "requires_human_action": True,
                                "human_action_description": "User provides patient name"
                            },
                            {
                                "id": "step_a2",
                                "description": "Collect patient date of birth",
                                "tool_hint": "collect_patient_dob",
                                "timeline_estimate": "immediately",
                                "requires_human_action": True,
                                "human_action_description": "User provides patient date of birth"
                            },
                            {
                                "id": "step_a3",
                                "description": "Collect Medical Record Number (MRN) if available",
                                "tool_hint": "collect_mrn",
                                "timeline_estimate": "immediately",
                                "requires_human_action": True,
                                "human_action_description": "User provides MRN or indicates if unavailable"
                            },
                            {
                                "id": "step_a4",
                                "description": "Collect insurance information (payer name, policy number, group number)",
                                "tool_hint": "collect_insurance_info",
                                "timeline_estimate": "immediately",
                                "requires_human_action": True,
                                "human_action_description": "User provides insurance details"
                            },
                            {
                                "id": "step_a5",
                                "description": "Check EMR system for existing patient record",
                                "tool_hint": "check_emr_patient_record",
                                "timeline_estimate": "after step_a3",
                                "requires_human_review": False
                            },
                            {
                                "id": "step_a6",
                                "description": "Retrieve patient demographics from EMR (name, DOB, address, phone)",
                                "tool_hint": "retrieve_emr_demographics",
                                "timeline_estimate": "after step_a5",
                                "requires_human_review": False
                            },
                            {
                                "id": "step_a7",
                                "description": "Check patient master index (PMI) for additional identifiers",
                                "tool_hint": "check_patient_master_index",
                                "timeline_estimate": "after step_a6",
                                "requires_human_review": False
                            },
                            {
                                "id": "step_a8",
                                "description": "Retrieve insurance information from EMR insurance table",
                                "tool_hint": "retrieve_emr_insurance",
                                "timeline_estimate": "after step_a4",
                                "requires_human_review": False
                            },
                            {
                                "id": "step_a9",
                                "description": "Check external patient registries and health information exchanges (HIE)",
                                "tool_hint": "check_hie_registries",
                                "timeline_estimate": "after step_a7",
                                "requires_human_review": False
                            },
                            {
                                "id": "step_a10",
                                "description": "Validate and reconcile patient information from all sources",
                                "tool_hint": "validate_patient_info",
                                "timeline_estimate": "after step_a9",
                                "requires_human_review": True,
                                "human_action_description": "Review and confirm patient information accuracy"
                            }
                        ]
                    },
                    {
                        "id": "phase_b",
                        "name": "Assess Eligibility Risk & Use-Case Specific Checks",
                        "description": "Compute eligibility risk score and perform use-case specific verification tasks",
                        "steps": [
                            {
                                "id": "step_b1",
                                "description": "Compute member eligibility risk score based on available data quality and completeness",
                                "tool_hint": "compute_eligibility_risk_score",
                                "timeline_estimate": "after phase_a",
                                "requires_human_review": False
                            },
                            {
                                "id": "step_b2_insurance_billing",
                                "description": "If use case is Insurance Billing - Retrieve claim details for past event",
                                "tool_hint": "retrieve_claim_details",
                                "timeline_estimate": "after step_b1",
                                "requires_human_review": False,
                                "condition": "use_case == 'Billing'"
                            },
                            {
                                "id": "step_b3_insurance_billing",
                                "description": "If use case is Insurance Billing - Verify service dates match eligibility period",
                                "tool_hint": "verify_service_date_eligibility",
                                "timeline_estimate": "after step_b2_insurance_billing",
                                "requires_human_review": False,
                                "condition": "use_case == 'Billing'"
                            },
                            {
                                "id": "step_b4_insurance_billing",
                                "description": "If use case is Insurance Billing - Check for prior authorization requirements",
                                "tool_hint": "check_prior_authorization",
                                "timeline_estimate": "after step_b3_insurance_billing",
                                "requires_human_review": True,
                                "condition": "use_case == 'Billing'"
                            },
                            {
                                "id": "step_b2_clinical",
                                "description": "If use case is Clinical - Determine eligible dates for scheduling",
                                "tool_hint": "check_eligible_dates",
                                "timeline_estimate": "after step_b1",
                                "requires_human_review": False,
                                "condition": "use_case == 'Clinical'"
                            },
                            {
                                "id": "step_b3_clinical",
                                "description": "If use case is Clinical - Check visit authorization limits and frequency",
                                "tool_hint": "check_visit_authorization",
                                "timeline_estimate": "after step_b2_clinical",
                                "requires_human_review": False,
                                "condition": "use_case == 'Clinical'"
                            },
                            {
                                "id": "step_b4_clinical",
                                "description": "If use case is Clinical - Verify coverage for specific procedure codes",
                                "tool_hint": "verify_procedure_coverage",
                                "timeline_estimate": "after step_b3_clinical",
                                "requires_human_review": True,
                                "condition": "use_case == 'Clinical'"
                            },
                            {
                                "id": "step_b2_financial",
                                "description": "If use case is Financial - Calculate copay estimation",
                                "tool_hint": "calculate_copay_estimate",
                                "timeline_estimate": "after step_b1",
                                "requires_human_review": False,
                                "condition": "use_case == 'Financial'"
                            },
                            {
                                "id": "step_b3_financial",
                                "description": "If use case is Financial - Check deductible status and remaining balance",
                                "tool_hint": "check_deductible_status",
                                "timeline_estimate": "after step_b2_financial",
                                "requires_human_review": False,
                                "condition": "use_case == 'Financial'"
                            },
                            {
                                "id": "step_b4_financial",
                                "description": "If use case is Financial - Calculate out-of-pocket maximum status",
                                "tool_hint": "calculate_oop_max_status",
                                "timeline_estimate": "after step_b3_financial",
                                "requires_human_review": True,
                                "condition": "use_case == 'Financial'"
                            },
                            {
                                "id": "step_b2_other",
                                "description": "If use case is Other - Perform general eligibility verification",
                                "tool_hint": "general_eligibility_check",
                                "timeline_estimate": "after step_b1",
                                "requires_human_review": False,
                                "condition": "use_case == 'Other'"
                            }
                        ]
                    },
                    {
                        "id": "phase_c",
                        "name": "Check Eligibility",
                        "description": "Verify eligibility status through direct insurance transactions and alternative sources",
                        "steps": [
                            {
                                "id": "step_c1",
                                "description": "Check eligibility via direct insurance transaction (270/271 EDI or payer API)",
                                "tool_hint": "check_eligibility_direct",
                                "timeline_estimate": "after phase_b",
                                "requires_human_review": False
                            },
                            {
                                "id": "step_c2",
                                "description": "Parse eligibility response and extract coverage details",
                                "tool_hint": "parse_eligibility_response",
                                "timeline_estimate": "after step_c1",
                                "requires_human_review": False
                            },
                            {
                                "id": "step_c3",
                                "description": "Check eligibility via HIE and historical context if direct unavailable",
                                "tool_hint": "check_eligibility_imputed",
                                "timeline_estimate": "after step_c1 if direct unavailable",
                                "requires_human_review": False
                            },
                            {
                                "id": "step_c4",
                                "description": "Check historical eligibility records from past transactions",
                                "tool_hint": "check_historical_eligibility",
                                "timeline_estimate": "after step_c3",
                                "requires_human_review": False
                            },
                            {
                                "id": "step_c5",
                                "description": "Validate eligibility effective dates and coverage periods",
                                "tool_hint": "validate_eligibility_dates",
                                "timeline_estimate": "after step_c2",
                                "requires_human_review": False
                            },
                            {
                                "id": "step_c6",
                                "description": "Extract benefit details (deductibles, copays, coinsurance, limits)",
                                "tool_hint": "extract_benefit_details",
                                "timeline_estimate": "after step_c5",
                                "requires_human_review": False
                            },
                            {
                                "id": "step_c7",
                                "description": "Check for secondary/tertiary insurance coverage",
                                "tool_hint": "check_secondary_insurance",
                                "timeline_estimate": "after step_c6",
                                "requires_human_review": False
                            },
                            {
                                "id": "step_c8",
                                "description": "Compile comprehensive eligibility report",
                                "tool_hint": "compile_eligibility_report",
                                "timeline_estimate": "after step_c7",
                                "requires_human_review": True,
                                "human_action_description": "Review eligibility report for accuracy"
                            }
                        ]
                    },
                    {
                        "id": "phase_d",
                        "name": "Next Steps & Stakeholder Notification",
                        "description": "Handle outcomes based on eligibility status and notify relevant stakeholders",
                        "steps": [
                            {
                                "id": "step_d_eligible",
                                "description": "If eligible: Confirm coverage status and prepare confirmation document",
                                "tool_hint": "handle_eligible_outcome",
                                "timeline_estimate": "after phase_c",
                                "requires_human_review": True,
                                "human_action_description": "Review and approve eligible outcome"
                            },
                            {
                                "id": "step_d_eligible_notify",
                                "description": "If eligible: Notify clinical staff and billing department of confirmed coverage",
                                "tool_hint": "notify_stakeholders_eligible",
                                "timeline_estimate": "after step_d_eligible",
                                "requires_human_review": False
                            },
                            {
                                "id": "step_d_not_eligible",
                                "description": "If not eligible: Execute handling action based on gate selection (Manual Review/Escalate/Notify Provider/Block Service/Allow with Warning)",
                                "tool_hint": "handle_not_eligible_outcome",
                                "timeline_estimate": "after phase_c",
                                "requires_human_review": True,
                                "human_action_description": "Review ineligibility and confirm handling action"
                            },
                            {
                                "id": "step_d_not_eligible_notify",
                                "description": "If not eligible: Notify provider and patient of ineligibility status",
                                "tool_hint": "notify_ineligibility",
                                "timeline_estimate": "after step_d_not_eligible",
                                "requires_human_review": False
                            },
                            {
                                "id": "step_d_not_eligible_alternatives",
                                "description": "If not eligible: Explore state program alternatives for coverage",
                                "tool_hint": "explore_state_alternatives",
                                "timeline_estimate": "after step_d_not_eligible_notify",
                                "requires_human_review": True,
                                "condition": "ineligibility_handling == 'Manual Review' or ineligibility_handling == 'Other'"
                            },
                            {
                                "id": "step_d_unable",
                                "description": "If unable to determine: Escalate to eligibility specialist for manual review",
                                "tool_hint": "handle_unable_to_determine",
                                "timeline_estimate": "after phase_c",
                                "requires_human_review": True,
                                "human_action_description": "Manual review required - escalate to specialist"
                            },
                            {
                                "id": "step_d_unable_notify",
                                "description": "If unable to determine: Notify provider and patient of pending review",
                                "tool_hint": "notify_pending_review",
                                "timeline_estimate": "after step_d_unable",
                                "requires_human_review": False
                            },
                            {
                                "id": "step_d_finalize",
                                "description": "Finalize eligibility determination and update patient record",
                                "tool_hint": "finalize_eligibility_determination",
                                "timeline_estimate": "after all outcome steps",
                                "requires_human_review": True,
                                "human_action_description": "Final review and approval of eligibility determination"
                            }
                        ]
                    }
                ]
            },
            "match_pattern": {
                "gates": {
                    "1_patient_info_availability": None,
                    "2_use_case": None,
                    "3_ineligibility_handling": None,
                    "4_urgency_timeline": None
                }
            }
        }
        
        # Create configs directory if it doesn't exist
        os.makedirs(os.path.dirname(template_path), exist_ok=True)
        
        # Write the template to file
        with open(template_path, 'w') as f:
            json.dump(template_data, f, indent=2)
        
        print(f"✅ Created template file at {template_path}")
    
    # Load the template
    with open(template_path, 'r') as f:
        template_data = json.load(f)
    
    # Connect to database
    await connect_to_db()
    
    try:
        # Create TreePath
        path = TreePath(
            module="workflow",
            domain="eligibility",
            strategy="TABULA_RASA",
            step="template"
        )
        
        print(f"Creating template with:")
        print(f"  Path: {path.to_key()}")
        print(f"  Name: {template_data['name']}")
        print(f"  Description: {template_data['description']}")
        # Check if using new hierarchical structure (gates) or legacy (phases)
        if "gates" in template_data['template_config']:
            print(f"  Gates: {len(template_data['template_config']['gates'])}")
            total_tasks = 0
            for gate in template_data['template_config']['gates']:
                for sub_level in gate.get('sub_levels', {}).values():
                    total_tasks += len(sub_level.get('tasks', []))
            print(f"  Total Tasks (across all sub-levels): {total_tasks}")
        else:
            print(f"  Phases: {len(template_data['template_config']['phases'])}")
            total_steps = sum(len(phase['steps']) for phase in template_data['template_config']['phases'])
            print(f"  Total Steps: {total_steps}")
        
        # Update existing template if it exists, otherwise create new
        template_key = path.to_key()
        
        # Check if template exists
        check_query = """
            SELECT id FROM eligibility_plan_templates
            WHERE template_key = :key
            LIMIT 1
        """
        existing_id = await database.fetch_val(check_query, {"key": template_key})
        
        if existing_id:
            # Update existing template
            update_query = """
                UPDATE eligibility_plan_templates
                SET name = :name,
                    description = :desc,
                    template_config = :config,
                    match_pattern = :pattern,
                    version = version + 1,
                    updated_at = CURRENT_TIMESTAMP,
                    updated_by = :user,
                    is_active = true
                WHERE id = :id
                RETURNING id
            """
            template_id = await database.fetch_val(update_query, {
                "id": existing_id,
                "name": template_data['name'],
                "desc": template_data['description'],
                "config": json.dumps(template_data['template_config']),
                "pattern": json.dumps(template_data['match_pattern']),
                "user": "system"
            })
            print(f"  Updated existing template (ID: {template_id})")
        else:
            # Create new template
            template_id = await eligibility_template_manager.save_template(
                path=path,
                name=template_data['name'],
                template_config=template_data['template_config'],
                match_pattern=template_data['match_pattern'],
                description=template_data['description'],
                user_id="system"
            )
            print(f"  Created new template (ID: {template_id})")
        
        print(f"✅ Successfully seeded planner template (ID: {template_id})")
        print(f"   Key: {path.to_key()}")
        
        # Verify it was created
        verify = await eligibility_template_manager.get_template(path)
        if verify:
            print(f"✅ Verification: Template found in database")
            print(f"   Template Key: {verify['template_key']}")
            print(f"   Version: {verify['version']}")
        else:
            print(f"⚠️  Verification: Template NOT found in database (but save_template returned ID: {template_id})")
        
    except Exception as e:
        print(f"❌ Error seeding template: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        await disconnect_from_db()

if __name__ == "__main__":
    asyncio.run(seed_planner_template())

