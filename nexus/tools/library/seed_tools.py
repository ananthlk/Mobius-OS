"""
Seed script to populate tool library with eligibility tools
"""
import asyncio
import logging
from nexus.tools.library.registry import tool_registry

logger = logging.getLogger("nexus.tool_seeding")

# Tool definitions organized by gate
TOOLS_TO_SEED = [
    # Gate 1: Patient/Insurance Info Availability
    {
        "name": "patient_demographics_retriever",
        "display_name": "Patient Demographics Retriever",
        "description": "Retrieves patient demographics (name, DOB, address, contact info) from EHR/EMR system.",
        "category": "data_retrieval",
        "version": "1.0.0",
        "schema_definition": {
            "name": "patient_demographics_retriever",
            "description": "Retrieves patient demographics (name, DOB, address, contact info) from EHR/EMR system.",
            "parameters": {
                "patient_id": "str (Patient identifier)",
                "appointment_id": "Optional[str] (Appointment identifier if available)"
            }
        },
        "parameters": [
            {
                "parameter_name": "patient_id",
                "parameter_type": "string",
                "description": "Patient identifier",
                "is_required": True,
                "order_index": 0
            },
            {
                "parameter_name": "appointment_id",
                "parameter_type": "string",
                "description": "Appointment identifier if available",
                "is_required": False,
                "order_index": 1
            }
        ],
        "requires_human_review": False,
        "is_batch_processable": False,
        "estimated_execution_time_ms": 500,
        "is_deterministic": True,
        "is_stateless": True,
        "implementation_type": "python_class",
        "implementation_path": "nexus.tools.eligibility.gate1_data_retrieval.PatientDemographicsRetriever",
        "tags": ["eligibility", "demographics", "patient_data"],
        "author": "System",
        "status": "active"
    },
    {
        "name": "insurance_info_retriever",
        "display_name": "Insurance Info Retriever",
        "description": "Retrieves insurance information from patient record (payer ID, member ID, group number, policy number).",
        "category": "data_retrieval",
        "version": "1.0.0",
        "schema_definition": {
            "name": "insurance_info_retriever",
            "description": "Retrieves insurance information from patient record (payer ID, member ID, group number, policy number).",
            "parameters": {
                "patient_id": "str (Patient identifier)"
            }
        },
        "parameters": [
            {
                "parameter_name": "patient_id",
                "parameter_type": "string",
                "description": "Patient identifier",
                "is_required": True,
                "order_index": 0
            }
        ],
        "requires_human_review": False,
        "is_batch_processable": False,
        "estimated_execution_time_ms": 500,
        "is_deterministic": True,
        "is_stateless": True,
        "implementation_type": "python_class",
        "implementation_path": "nexus.tools.eligibility.gate1_data_retrieval.InsuranceInfoRetriever",
        "tags": ["eligibility", "insurance", "patient_data"],
        "author": "System",
        "status": "active"
    },
    {
        "name": "historical_insurance_lookup",
        "display_name": "Historical Insurance Lookup",
        "description": "Searches historical records for past insurance information when current info is missing.",
        "category": "data_retrieval",
        "version": "1.0.0",
        "schema_definition": {
            "name": "historical_insurance_lookup",
            "description": "Searches historical records for past insurance information when current info is missing.",
            "parameters": {
                "patient_id": "str (Patient identifier)",
                "lookback_days": "int (Number of days to look back, default 365)"
            }
        },
        "parameters": [
            {
                "parameter_name": "patient_id",
                "parameter_type": "string",
                "description": "Patient identifier",
                "is_required": True,
                "order_index": 0
            },
            {
                "parameter_name": "lookback_days",
                "parameter_type": "integer",
                "description": "Number of days to look back",
                "is_required": False,
                "default_value": "365",
                "validation_rules": {"min": 1, "max": 3650},
                "order_index": 1
            }
        ],
        "requires_human_review": False,
        "is_batch_processable": True,
        "estimated_execution_time_ms": 1000,
        "is_deterministic": True,
        "is_stateless": True,
        "implementation_type": "python_class",
        "implementation_path": "nexus.tools.eligibility.gate1_data_retrieval.HistoricalInsuranceLookup",
        "tags": ["eligibility", "history", "lookback"],
        "author": "System",
        "status": "active"
    },
    {
        "name": "hie_insurance_query",
        "display_name": "HIE Insurance Query",
        "description": "Queries Health Information Exchange (HIE) for insurance data when local records are incomplete.",
        "category": "integration",
        "version": "1.0.0",
        "schema_definition": {
            "name": "hie_insurance_query",
            "description": "Queries Health Information Exchange (HIE) for insurance data when local records are incomplete.",
            "parameters": {
                "patient_id": "str (Patient identifier)",
                "hie_network_id": "str (HIE network identifier)",
                "query_type": "str (Type of query: 'insurance', 'demographics', 'both')"
            }
        },
        "parameters": [
            {
                "parameter_name": "patient_id",
                "parameter_type": "string",
                "description": "Patient identifier",
                "is_required": True,
                "order_index": 0
            },
            {
                "parameter_name": "hie_network_id",
                "parameter_type": "string",
                "description": "HIE network identifier",
                "is_required": True,
                "order_index": 1
            },
            {
                "parameter_name": "query_type",
                "parameter_type": "string",
                "description": "Type of query",
                "is_required": False,
                "default_value": "insurance",
                "validation_rules": {"enum": ["insurance", "demographics", "both"]},
                "order_index": 2
            }
        ],
        "requires_human_review": False,
        "is_batch_processable": False,
        "estimated_execution_time_ms": 2000,
        "is_deterministic": False,
        "is_stateless": True,
        "implementation_type": "python_class",
        "implementation_path": "nexus.tools.eligibility.gate1_data_retrieval.HIEInsuranceQuery",
        "tags": ["eligibility", "hie", "integration"],
        "author": "System",
        "status": "active"
    },
    {
        "name": "patient_insurance_collector",
        "display_name": "Patient Insurance Collector",
        "description": "Initiates patient communication to collect insurance information when it must come from patient directly.",
        "category": "communication",
        "version": "1.0.0",
        "schema_definition": {
            "name": "patient_insurance_collector",
            "description": "Initiates patient communication to collect insurance information when it must come from patient directly.",
            "parameters": {
                "patient_id": "str (Patient identifier)",
                "communication_method": "str (Method: 'portal', 'sms', 'email', 'phone')",
                "urgency": "str (Urgency level: 'low', 'medium', 'high')"
            }
        },
        "parameters": [
            {
                "parameter_name": "patient_id",
                "parameter_type": "string",
                "description": "Patient identifier",
                "is_required": True,
                "order_index": 0
            },
            {
                "parameter_name": "communication_method",
                "parameter_type": "string",
                "description": "Communication method",
                "is_required": False,
                "default_value": "portal",
                "validation_rules": {"enum": ["portal", "sms", "email", "phone"]},
                "order_index": 1
            },
            {
                "parameter_name": "urgency",
                "parameter_type": "string",
                "description": "Urgency level",
                "is_required": False,
                "default_value": "medium",
                "validation_rules": {"enum": ["low", "medium", "high"]},
                "order_index": 2
            }
        ],
        "requires_human_review": True,
        "is_batch_processable": False,
        "estimated_execution_time_ms": 1000,
        "is_deterministic": False,
        "is_stateless": False,
        "implementation_type": "python_class",
        "implementation_path": "nexus.tools.eligibility.gate1_data_retrieval.PatientInsuranceCollector",
        "tags": ["eligibility", "communication", "patient"],
        "author": "System",
        "status": "active"
    },
    # Gate 2: Use Case
    {
        "name": "billing_eligibility_verifier",
        "display_name": "Billing Eligibility Verifier",
        "description": "Verifies eligibility specifically for billing purposes (coverage, effective dates, copays).",
        "category": "eligibility",
        "version": "1.0.0",
        "schema_definition": {
            "name": "billing_eligibility_verifier",
            "description": "Verifies eligibility specifically for billing purposes (coverage, effective dates, copays).",
            "parameters": {
                "member_id": "str (Member identifier)",
                "date_of_birth": "str (Date of birth YYYY-MM-DD)",
                "service_date": "str (Service date YYYY-MM-DD)",
                "procedure_codes": "List[str] (Procedure codes)",
                "payer_id": "str (Payer identifier)"
            }
        },
        "parameters": [
            {
                "parameter_name": "member_id",
                "parameter_type": "string",
                "description": "Member identifier",
                "is_required": True,
                "order_index": 0
            },
            {
                "parameter_name": "date_of_birth",
                "parameter_type": "string",
                "description": "Date of birth (YYYY-MM-DD)",
                "is_required": True,
                "order_index": 1
            },
            {
                "parameter_name": "service_date",
                "parameter_type": "string",
                "description": "Service date (YYYY-MM-DD)",
                "is_required": True,
                "order_index": 2
            },
            {
                "parameter_name": "procedure_codes",
                "parameter_type": "array",
                "description": "Procedure codes",
                "is_required": True,
                "order_index": 3
            },
            {
                "parameter_name": "payer_id",
                "parameter_type": "string",
                "description": "Payer identifier",
                "is_required": True,
                "order_index": 4
            }
        ],
        "requires_human_review": False,
        "is_batch_processable": True,
        "estimated_execution_time_ms": 2000,
        "is_deterministic": True,
        "is_stateless": True,
        "implementation_type": "python_class",
        "implementation_path": "nexus.tools.eligibility.gate2_use_case.BillingEligibilityVerifier",
        "tags": ["eligibility", "billing", "verification"],
        "author": "System",
        "status": "active",
        "supports_conditional_execution": True,
        "default_condition_type": "if",
        "execution_conditions": [
            {
                "condition_type": "if",
                "condition_expression": {
                    "field": "eligibility_status",
                    "operator": "equals",
                    "value": "active"
                },
                "action_type": "execute",
                "action_target_tool_name": "copay_deductible_calculator",
                "condition_description": "If eligibility is active, calculate copay and deductible",
                "icon_name": "if-check",
                "icon_color": "green",
                "execution_order": 0
            },
            {
                "condition_type": "on_failure",
                "condition_expression": {},
                "action_type": "escalate",
                "action_target_tool_name": "care_team_notifier",
                "condition_description": "On failure, escalate to care team",
                "icon_name": "on-failure",
                "icon_color": "red",
                "execution_order": 1
            }
        ]
    },
    {
        "name": "clinical_eligibility_checker",
        "display_name": "Clinical Eligibility Checker",
        "description": "Checks eligibility for clinical decision support (coverage for specific services/treatments).",
        "category": "eligibility",
        "version": "1.0.0",
        "schema_definition": {
            "name": "clinical_eligibility_checker",
            "description": "Checks eligibility for clinical decision support (coverage for specific services/treatments).",
            "parameters": {
                "member_id": "str (Member identifier)",
                "date_of_birth": "str (Date of birth YYYY-MM-DD)",
                "service_type": "str (Service type: 'preventive', 'diagnostic', 'treatment', 'specialty')",
                "clinical_indication": "str (Clinical indication or diagnosis)",
                "payer_id": "str (Payer identifier)"
            }
        },
        "parameters": [
            {
                "parameter_name": "member_id",
                "parameter_type": "string",
                "description": "Member identifier",
                "is_required": True,
                "order_index": 0
            },
            {
                "parameter_name": "date_of_birth",
                "parameter_type": "string",
                "description": "Date of birth (YYYY-MM-DD)",
                "is_required": True,
                "order_index": 1
            },
            {
                "parameter_name": "service_type",
                "parameter_type": "string",
                "description": "Service type",
                "is_required": True,
                "validation_rules": {"enum": ["preventive", "diagnostic", "treatment", "specialty"]},
                "order_index": 2
            },
            {
                "parameter_name": "clinical_indication",
                "parameter_type": "string",
                "description": "Clinical indication or diagnosis",
                "is_required": True,
                "order_index": 3
            },
            {
                "parameter_name": "payer_id",
                "parameter_type": "string",
                "description": "Payer identifier",
                "is_required": True,
                "order_index": 4
            }
        ],
        "requires_human_review": False,
        "is_batch_processable": False,
        "estimated_execution_time_ms": 2000,
        "is_deterministic": True,
        "is_stateless": True,
        "implementation_type": "python_class",
        "implementation_path": "nexus.tools.eligibility.gate2_use_case.ClinicalEligibilityChecker",
        "tags": ["eligibility", "clinical", "decision_support"],
        "author": "System",
        "status": "active"
    },
    {
        "name": "financial_eligibility_verifier",
        "display_name": "Financial Eligibility Verifier",
        "description": "Verifies eligibility for patient balance determination and financial responsibility calculation.",
        "category": "eligibility",
        "version": "1.0.0",
        "schema_definition": {
            "name": "financial_eligibility_verifier",
            "description": "Verifies eligibility for patient balance determination and financial responsibility calculation.",
            "parameters": {
                "member_id": "str (Member identifier)",
                "date_of_birth": "str (Date of birth YYYY-MM-DD)",
                "service_date": "str (Service date YYYY-MM-DD)",
                "payer_id": "str (Payer identifier)"
            }
        },
        "parameters": [
            {
                "parameter_name": "member_id",
                "parameter_type": "string",
                "description": "Member identifier",
                "is_required": True,
                "order_index": 0
            },
            {
                "parameter_name": "date_of_birth",
                "parameter_type": "string",
                "description": "Date of birth (YYYY-MM-DD)",
                "is_required": True,
                "order_index": 1
            },
            {
                "parameter_name": "service_date",
                "parameter_type": "string",
                "description": "Service date (YYYY-MM-DD)",
                "is_required": True,
                "order_index": 2
            },
            {
                "parameter_name": "payer_id",
                "parameter_type": "string",
                "description": "Payer identifier",
                "is_required": True,
                "order_index": 3
            }
        ],
        "requires_human_review": False,
        "is_batch_processable": True,
        "estimated_execution_time_ms": 2000,
        "is_deterministic": True,
        "is_stateless": True,
        "implementation_type": "python_class",
        "implementation_path": "nexus.tools.eligibility.gate2_use_case.FinancialEligibilityVerifier",
        "tags": ["eligibility", "financial", "balance_billing"],
        "author": "System",
        "status": "active"
    },
    {
        "name": "copay_deductible_calculator",
        "display_name": "Copay Deductible Calculator",
        "description": "Calculates patient copay and deductible based on eligibility and service details.",
        "category": "financial",
        "version": "1.0.0",
        "schema_definition": {
            "name": "copay_deductible_calculator",
            "description": "Calculates patient copay and deductible based on eligibility and service details.",
            "parameters": {
                "member_id": "str (Member identifier)",
                "service_type": "str (Service type)",
                "procedure_code": "str (Procedure code)",
                "payer_id": "str (Payer identifier)"
            }
        },
        "parameters": [
            {
                "parameter_name": "member_id",
                "parameter_type": "string",
                "description": "Member identifier",
                "is_required": True,
                "order_index": 0
            },
            {
                "parameter_name": "service_type",
                "parameter_type": "string",
                "description": "Service type",
                "is_required": True,
                "order_index": 1
            },
            {
                "parameter_name": "procedure_code",
                "parameter_type": "string",
                "description": "Procedure code",
                "is_required": True,
                "order_index": 2
            },
            {
                "parameter_name": "payer_id",
                "parameter_type": "string",
                "description": "Payer identifier",
                "is_required": True,
                "order_index": 3
            }
        ],
        "requires_human_review": False,
        "is_batch_processable": False,
        "estimated_execution_time_ms": 1000,
        "is_deterministic": True,
        "is_stateless": True,
        "implementation_type": "python_class",
        "implementation_path": "nexus.tools.eligibility.gate2_use_case.CopayDeductibleCalculator",
        "tags": ["financial", "copay", "deductible", "calculation"],
        "author": "System",
        "status": "active"
    }
]

async def seed_tools():
    """Seed the tool library with eligibility tools."""
    logger.info("🌱 Starting tool library seeding...")
    
    # Check if tools already exist
    existing_tools = await tool_registry.get_all_active_tools()
    if existing_tools:
        logger.info(f"Tool library already has {len(existing_tools)} tools. Skipping seed.")
        return
    
    seeded_count = 0
    for tool_data in TOOLS_TO_SEED:
        try:
            # Check if tool already exists (double-check)
            existing = await tool_registry.get_tool_by_name(tool_data["name"])
            if existing:
                logger.debug(f"Tool {tool_data['name']} already exists, skipping...")
                continue
            
            # Register tool
            result = await tool_registry.register_tool(tool_data, created_by=1)
            logger.info(f"✅ Registered tool: {tool_data['name']}")
            seeded_count += 1
        except Exception as e:
            logger.error(f"❌ Failed to register tool {tool_data['name']}: {e}")
    
    logger.info(f"🎉 Tool library seeding complete! Registered {seeded_count} new tools.")

if __name__ == "__main__":
    from nexus.modules.database import database
    import asyncio
    
    async def main():
        await database.connect()
        try:
            await seed_tools()
        finally:
            await database.disconnect()
    
    asyncio.run(main())

