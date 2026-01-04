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
        "name": "emr_patient_demographics_retriever",
        "display_name": "EMR Patient Demographics Retriever",
        "description": "Retrieves patient demographics (name, DOB, address, contact info) from EMR system. Uses patient_id (EMR identifier).",
        "category": "data_retrieval",
        "version": "1.0.0",
        "implementation_status": "REAL",  # REAL: Uses API endpoints (/api/user-profiles/{patient_id}/system)
        "schema_definition": {
            "name": "emr_patient_demographics_retriever",
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
        "implementation_path": "nexus.tools.eligibility.gate1_data_retrieval.EMRPatientDemographicsRetriever",
        "tags": ["eligibility", "demographics", "patient_data"],
        "author": "System",
        "status": "active"
    },
    {
        "name": "emr_patient_insurance_info_retriever",
        "display_name": "EMR Patient Insurance Info Retriever",
        "description": "Retrieves insurance information FROM patient record/EMR system (payer ID, member ID, group number, policy number). Uses patient_id (EMR identifier).",
        "category": "data_retrieval",
        "version": "1.0.0",
        "implementation_status": "REAL",  # REAL: Uses API endpoints (/api/user-profiles/{patient_id}/health-plan) to get insurance info FROM patient record
        "schema_definition": {
            "name": "emr_patient_insurance_info_retriever",
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
        "implementation_path": "nexus.tools.eligibility.gate1_data_retrieval.EMRPatientInsuranceInfoRetriever",
        "tags": ["eligibility", "insurance", "patient_data"],
        "author": "System",
        "status": "active"
    },
    {
        "name": "emr_patient_historical_insurance_lookup",
        "display_name": "EMR Patient Historical Insurance Lookup",
        "description": "Searches historical insurance records from EMR system when current info is missing. Uses patient_id (EMR identifier).",
        "category": "data_retrieval",
        "version": "1.0.0",
        "implementation_status": "PARTIAL",  # PARTIAL: Uses API but returns current coverage as historical (not true historical lookup)
        "schema_definition": {
            "name": "emr_patient_historical_insurance_lookup",
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
        "implementation_path": "nexus.tools.eligibility.gate1_data_retrieval.EMRPatientHistoricalInsuranceLookup",
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
        "implementation_status": "STUB",  # STUB: Mock implementation - returns hardcoded data, no real HIE integration
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
        "description": "Initiates patient communication to collect insurance information when it must come from patient directly. Uses patient_id (EMR identifier).",
        "category": "communication",
        "version": "1.0.0",
        "implementation_status": "STUB",  # STUB: Mock implementation - returns hardcoded data, no real communication integration
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
        "implementation_status": "STUB",  # STUB: Mock implementation, returns hardcoded data
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
        "implementation_status": "STUB",  # STUB: Mock implementation, returns hardcoded data
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
    },
    # Communication Tools
    {
        "name": "system_email_sender",
        "display_name": "System Email Sender",
        "description": "Sends email from system account (mobiushealthai@gmail.com) via SMTP. Requires EMAIL_PASSWORD or EMAIL_APP_PASSWORD environment variable. Supports attachments and CC. Use this for system-generated emails.",
        "category": "communication",
        "version": "1.0.0",
        "schema_definition": {
            "name": "system_email_sender",
            "description": "Sends email from system account (mobiushealthai@gmail.com) via SMTP. Requires EMAIL_PASSWORD environment variable. Supports attachments and CC.",
            "parameters": {
                "to": "str (Recipient email address)",
                "subject": "str (Email subject line)",
                "message": "str (Email body content)",
                "cc": "Optional[List[str]] (List of CC email addresses)",
                "attachments": "Optional[List[Dict]] (List of attachments, each with 'filename', 'content' (bytes), 'content_type')"
            }
        },
        "parameters": [
            {
                "parameter_name": "to",
                "parameter_type": "string",
                "description": "Recipient email address",
                "is_required": True,
                "order_index": 0
            },
            {
                "parameter_name": "subject",
                "parameter_type": "string",
                "description": "Email subject line",
                "is_required": True,
                "order_index": 1
            },
            {
                "parameter_name": "message",
                "parameter_type": "string",
                "description": "Email body content",
                "is_required": True,
                "order_index": 2
            },
            {
                "parameter_name": "cc",
                "parameter_type": "array",
                "description": "List of CC email addresses",
                "is_required": False,
                "order_index": 3
            },
            {
                "parameter_name": "attachments",
                "parameter_type": "array",
                "description": "List of attachments (each with filename, content (bytes), content_type)",
                "is_required": False,
                "order_index": 4
            }
        ],
        "requires_human_review": False,
        "is_batch_processable": False,
        "estimated_execution_time_ms": 1000,
        "is_deterministic": False,
        "is_stateless": False,
        "implementation_type": "python_class",
        "implementation_path": "nexus.tools.communication.system_email_sender.SystemEmailSender",
        "tags": ["communication", "email", "system", "smtp"],
        "author": "System",
        "status": "active",
        "example_usage": "Send system emails from mobiushealthai@gmail.com. Requires EMAIL_PASSWORD or EMAIL_APP_PASSWORD environment variable. Use for automated system notifications."
    },
    {
        "name": "user_email_sender",
        "display_name": "User Email Sender",
        "description": "Sends email from user's authenticated Gmail account via Gmail API with OAuth2. User must have authorized Gmail access via OAuth. Supports attachments and CC. Use this for user-initiated emails.",
        "category": "communication",
        "version": "1.0.0",
        "schema_definition": {
            "name": "user_email_sender",
            "description": "Sends email from user's authenticated Gmail account via Gmail API with OAuth2. User must have authorized Gmail access via OAuth. Supports attachments and CC.",
            "parameters": {
                "to": "str (Recipient email address)",
                "subject": "str (Email subject line)",
                "message": "str (Email body content)",
                "cc": "Optional[List[str]] (List of CC email addresses)",
                "attachments": "Optional[List[Dict]] (List of attachments, each with 'filename', 'content' (bytes), 'content_type')",
                "user_id": "Optional[str] (User ID for OAuth - defaults to system user)",
                "sender_email": "Optional[str] (Gmail account to send from - uses first connected account if not specified)"
            }
        },
        "parameters": [
            {
                "parameter_name": "to",
                "parameter_type": "string",
                "description": "Recipient email address",
                "is_required": True,
                "order_index": 0
            },
            {
                "parameter_name": "subject",
                "parameter_type": "string",
                "description": "Email subject line",
                "is_required": True,
                "order_index": 1
            },
            {
                "parameter_name": "message",
                "parameter_type": "string",
                "description": "Email body content",
                "is_required": True,
                "order_index": 2
            },
            {
                "parameter_name": "cc",
                "parameter_type": "array",
                "description": "List of CC email addresses",
                "is_required": False,
                "order_index": 3
            },
            {
                "parameter_name": "attachments",
                "parameter_type": "array",
                "description": "List of attachments (each with filename, content (bytes), content_type)",
                "is_required": False,
                "order_index": 4
            },
            {
                "parameter_name": "user_id",
                "parameter_type": "string",
                "description": "User ID for OAuth (defaults to system user if not provided)",
                "is_required": False,
                "order_index": 5
            },
            {
                "parameter_name": "sender_email",
                "parameter_type": "string",
                "description": "Gmail account to send from (uses first connected account if not specified)",
                "is_required": False,
                "order_index": 6
            }
        ],
        "requires_human_review": False,
        "is_batch_processable": False,
        "estimated_execution_time_ms": 1000,
        "is_deterministic": False,
        "is_stateless": False,
        "implementation_type": "python_class",
        "implementation_path": "nexus.tools.communication.user_email_sender.UserEmailSender",
        "tags": ["communication", "email", "user", "oauth", "gmail"],
        "author": "System",
        "status": "active",
        "example_usage": "Send emails from user's Gmail account. Requires OAuth authorization via /api/google/oauth/authorize or /api/gmail/oauth/authorize. Use for user-initiated emails from their personal/work Gmail account."
    },
    {
        "name": "system_sms_sender",
        "display_name": "System SMS Sender",
        "description": "Sends SMS from system account via SMS service provider (e.g., Twilio). Requires TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, and TWILIO_PHONE_NUMBER environment variables. Supports sending to any phone number. ⚠️ WARNING: SMS is unencrypted. Only send pre-approved, non-clinical messages with patient consent.",
        "category": "communication",
        "version": "1.0.0",
        "implementation_status": "PARTIAL",  # PARTIAL: Real Twilio integration, but requires credentials
        "schema_definition": {
            "name": "system_sms_sender",
            "description": "Sends SMS from system account via SMS service provider (e.g., Twilio). Requires TWILIO credentials.",
            "parameters": {
                "to": "str (Recipient phone number in E.164 format, e.g., +1234567890)",
                "message": "str (SMS message content, max 160 characters recommended per segment)"
            }
        },
        "parameters": [
            {
                "parameter_name": "to",
                "parameter_type": "string",
                "description": "Recipient phone number in E.164 format",
                "is_required": True,
                "order_index": 0
            },
            {
                "parameter_name": "message",
                "parameter_type": "string",
                "description": "SMS message content",
                "is_required": True,
                "validation_rules": {"max_length": 500},
                "order_index": 1
            }
        ],
        "requires_human_review": True,
        "is_batch_processable": False,
        "estimated_execution_time_ms": 1000,
        "is_deterministic": False,
        "is_stateless": False,
        "implementation_type": "python_class",
        "implementation_path": "nexus.tools.communication.system_sms_sender.SystemSMSSender",
        "tags": ["communication", "sms", "system"],
        "author": "System",
        "status": "active",
        "example_usage": "✅ APPROVED: Send appointment reminder SMS using pre-approved template. ❌ NOT APPROVED: Sending test results, diagnoses, or any clinical information via SMS (unencrypted channel)."
    },
    {
        "name": "user_sms_sender",
        "display_name": "User SMS Sender",
        "description": "Sends SMS from user's authenticated SMS account. User must have authorized SMS service access. Currently supports Twilio integration. ⚠️ WARNING: SMS is unencrypted. Only send pre-approved, non-clinical messages with patient consent.",
        "category": "communication",
        "version": "1.0.0",
        "implementation_status": "STUB",  # STUB: Stub implementation, user SMS authentication not yet implemented
        "schema_definition": {
            "name": "user_sms_sender",
            "description": "Sends SMS from user's authenticated SMS account. User must have authorized SMS service access.",
            "parameters": {
                "to": "str (Recipient phone number in E.164 format, e.g., +1234567890)",
                "message": "str (SMS message content, max 160 characters recommended per segment)",
                "user_id": "Optional[str] (User ID for authentication - defaults to system user)",
                "sender_phone": "Optional[str] (Phone number to send from - uses user's configured number if not specified)"
            }
        },
        "parameters": [
            {
                "parameter_name": "to",
                "parameter_type": "string",
                "description": "Recipient phone number in E.164 format",
                "is_required": True,
                "order_index": 0
            },
            {
                "parameter_name": "message",
                "parameter_type": "string",
                "description": "SMS message content",
                "is_required": True,
                "validation_rules": {"max_length": 500},
                "order_index": 1
            },
            {
                "parameter_name": "user_id",
                "parameter_type": "string",
                "description": "User ID for authentication",
                "is_required": False,
                "order_index": 2
            },
            {
                "parameter_name": "sender_phone",
                "parameter_type": "string",
                "description": "Phone number to send from",
                "is_required": False,
                "order_index": 3
            }
        ],
        "requires_human_review": True,
        "is_batch_processable": False,
        "estimated_execution_time_ms": 1000,
        "is_deterministic": False,
        "is_stateless": False,
        "implementation_type": "python_class",
        "implementation_path": "nexus.tools.communication.user_sms_sender.UserSMSSender",
        "tags": ["communication", "sms", "user"],
        "author": "System",
        "status": "active",
        "example_usage": "✅ APPROVED: Send appointment reminder SMS using pre-approved template. ❌ NOT APPROVED: Sending test results, diagnoses, or any clinical information via SMS (unencrypted channel)."
    },
    {
        "name": "system_calendar_manager",
        "display_name": "System Calendar Manager",
        "description": "Manages calendar events in the system calendar. Can read events and create new events. Uses system account (mobiushealthai@gmail.com).",
        "category": "communication",
        "version": "1.0.0",
        "schema_definition": {
            "name": "system_calendar_manager",
            "description": "Manages calendar events in the system calendar. Can read events and create new events. Uses system account (mobiushealthai@gmail.com).",
            "parameters": {
                "operation": "str (Operation: 'list_events', 'create_event', 'get_event')",
                "calendar_id": "Optional[str] (Calendar ID, default: 'primary')",
                "time_min": "Optional[str] (Start time for list_events, ISO 8601 format)",
                "time_max": "Optional[str] (End time for list_events, ISO 8601 format)",
                "max_results": "Optional[int] (Max results for list_events, default: 10)",
                "event_id": "Optional[str] (Event ID for get_event operation)",
                "event_summary": "Optional[str] (Event title for create_event)",
                "event_start": "Optional[str] (Event start time for create_event, ISO 8601 format)",
                "event_end": "Optional[str] (Event end time for create_event, ISO 8601 format)",
                "event_description": "Optional[str] (Event description for create_event)",
                "event_location": "Optional[str] (Event location for create_event)",
                "attendees": "Optional[List[str]] (List of attendee email addresses for create_event)"
            }
        },
        "parameters": [
            {
                "parameter_name": "operation",
                "parameter_type": "string",
                "description": "Operation to perform",
                "is_required": True,
                "validation_rules": {"enum": ["list_events", "create_event", "get_event"]},
                "order_index": 0
            },
            {
                "parameter_name": "calendar_id",
                "parameter_type": "string",
                "description": "Calendar ID (default: 'primary')",
                "is_required": False,
                "default_value": "primary",
                "order_index": 1
            },
            {
                "parameter_name": "event_summary",
                "parameter_type": "string",
                "description": "Event title (required for create_event)",
                "is_required": False,
                "order_index": 2
            },
            {
                "parameter_name": "event_start",
                "parameter_type": "string",
                "description": "Event start time in ISO 8601 format (required for create_event)",
                "is_required": False,
                "order_index": 3
            },
            {
                "parameter_name": "event_end",
                "parameter_type": "string",
                "description": "Event end time in ISO 8601 format (required for create_event)",
                "is_required": False,
                "order_index": 4
            },
            {
                "parameter_name": "event_description",
                "parameter_type": "string",
                "description": "Event description",
                "is_required": False,
                "order_index": 5
            },
            {
                "parameter_name": "event_location",
                "parameter_type": "string",
                "description": "Event location",
                "is_required": False,
                "order_index": 6
            },
            {
                "parameter_name": "attendees",
                "parameter_type": "array",
                "description": "List of attendee email addresses",
                "is_required": False,
                "order_index": 7
            }
        ],
        "requires_human_review": False,
        "is_batch_processable": False,
        "estimated_execution_time_ms": 1000,
        "is_deterministic": False,
        "is_stateless": False,
        "implementation_type": "python_class",
        "implementation_path": "nexus.tools.communication.system_calendar_manager.SystemCalendarManager",
        "tags": ["communication", "calendar", "system", "scheduling"],
        "author": "System",
        "status": "active",
        "example_usage": "Read and create calendar events in the system calendar account."
    },
    {
        "name": "user_calendar_manager",
        "display_name": "User Calendar Manager",
        "description": "Manages calendar events in user's Google Calendar. Can read events and create new events. User must have authorized Google Calendar access via OAuth.",
        "category": "communication",
        "version": "1.0.0",
        "schema_definition": {
            "name": "user_calendar_manager",
            "description": "Manages calendar events in user's Google Calendar. Can read events and create new events. User must have authorized Google Calendar access via OAuth.",
            "parameters": {
                "operation": "str (Operation: 'list_events', 'create_event', 'get_event')",
                "calendar_id": "Optional[str] (Calendar ID, default: 'primary')",
                "time_min": "Optional[str] (Start time for list_events, ISO 8601 format)",
                "time_max": "Optional[str] (End time for list_events, ISO 8601 format)",
                "max_results": "Optional[int] (Max results for list_events, default: 10)",
                "event_id": "Optional[str] (Event ID for get_event operation)",
                "event_summary": "Optional[str] (Event title for create_event)",
                "event_start": "Optional[str] (Event start time for create_event, ISO 8601 format)",
                "event_end": "Optional[str] (Event end time for create_event, ISO 8601 format)",
                "event_description": "Optional[str] (Event description for create_event)",
                "event_location": "Optional[str] (Event location for create_event)",
                "attendees": "Optional[List[str]] (List of attendee email addresses for create_event)",
                "user_id": "Optional[str] (User ID for OAuth - defaults to system user)",
                "calendar_email": "Optional[str] (Calendar account email - uses first connected account if not specified)"
            }
        },
        "parameters": [
            {
                "parameter_name": "operation",
                "parameter_type": "string",
                "description": "Operation to perform",
                "is_required": True,
                "validation_rules": {"enum": ["list_events", "create_event", "get_event"]},
                "order_index": 0
            },
            {
                "parameter_name": "calendar_id",
                "parameter_type": "string",
                "description": "Calendar ID (default: 'primary')",
                "is_required": False,
                "default_value": "primary",
                "order_index": 1
            },
            {
                "parameter_name": "event_summary",
                "parameter_type": "string",
                "description": "Event title (required for create_event)",
                "is_required": False,
                "order_index": 2
            },
            {
                "parameter_name": "event_start",
                "parameter_type": "string",
                "description": "Event start time in ISO 8601 format (required for create_event)",
                "is_required": False,
                "order_index": 3
            },
            {
                "parameter_name": "event_end",
                "parameter_type": "string",
                "description": "Event end time in ISO 8601 format (required for create_event)",
                "is_required": False,
                "order_index": 4
            },
            {
                "parameter_name": "event_description",
                "parameter_type": "string",
                "description": "Event description",
                "is_required": False,
                "order_index": 5
            },
            {
                "parameter_name": "event_location",
                "parameter_type": "string",
                "description": "Event location",
                "is_required": False,
                "order_index": 6
            },
            {
                "parameter_name": "attendees",
                "parameter_type": "array",
                "description": "List of attendee email addresses",
                "is_required": False,
                "order_index": 7
            },
            {
                "parameter_name": "user_id",
                "parameter_type": "string",
                "description": "User ID for OAuth (defaults to system user if not provided)",
                "is_required": False,
                "order_index": 8
            },
            {
                "parameter_name": "calendar_email",
                "parameter_type": "string",
                "description": "Calendar account email (uses first connected account if not specified)",
                "is_required": False,
                "order_index": 9
            }
        ],
        "requires_human_review": False,
        "is_batch_processable": False,
        "estimated_execution_time_ms": 1000,
        "is_deterministic": False,
        "is_stateless": False,
        "implementation_type": "python_class",
        "implementation_path": "nexus.tools.communication.user_calendar_manager.UserCalendarManager",
        "tags": ["communication", "calendar", "user", "oauth", "scheduling"],
        "author": "System",
        "status": "active",
        "example_usage": "Read and create calendar events in user's Google Calendar account. Requires OAuth authorization."
    },
    # Utility Tools
    {
        "name": "google_search",
        "display_name": "Google Search",
        "description": "Performs a web search using Google Search. Returns search results with titles, URLs, and snippets.",
        "category": "utility",
        "version": "1.0.0",
        "schema_definition": {
            "name": "google_search",
            "description": "Performs a web search using Google Search. Returns search results with titles, URLs, and snippets.",
            "parameters": {
                "query": "str (Search query string)",
                "num_results": "Optional[int] (Number of results to return, default: 10, max: 100)",
                "search_type": "Optional[str] (Search type: 'web', 'images', 'videos', default: 'web')"
            }
        },
        "parameters": [
            {
                "parameter_name": "query",
                "parameter_type": "string",
                "description": "Search query string",
                "is_required": True,
                "order_index": 0
            },
            {
                "parameter_name": "num_results",
                "parameter_type": "integer",
                "description": "Number of results to return",
                "is_required": False,
                "default_value": "10",
                "validation_rules": {"min": 1, "max": 100},
                "order_index": 1
            },
            {
                "parameter_name": "search_type",
                "parameter_type": "string",
                "description": "Search type",
                "is_required": False,
                "default_value": "web",
                "validation_rules": {"enum": ["web", "images", "videos"]},
                "order_index": 2
            }
        ],
        "requires_human_review": False,
        "is_batch_processable": True,
        "estimated_execution_time_ms": 1500,
        "is_deterministic": False,
        "is_stateless": True,
        "implementation_type": "python_class",
        "implementation_path": "nexus.tools.utilities.google_search_tool.GoogleSearchTool",
        "tags": ["utility", "search", "google", "web"],
        "author": "System",
        "status": "active",
        "example_usage": "Search for general information, documentation, or public data. Ready for Google Custom Search API integration."
    },
    {
        "name": "generic_llm_call",
        "display_name": "Generic LLM Call",
        "description": "Makes a generic LLM API call using the configured LLM gateway. Supports custom prompts, model selection, and temperature control.",
        "category": "utility",
        "version": "1.0.0",
        "schema_definition": {
            "name": "generic_llm_call",
            "description": "Makes a generic LLM API call using the configured LLM gateway. Supports custom prompts, model selection, and temperature control.",
            "parameters": {
                "prompt": "str (The prompt/message to send to the LLM)",
                "model_id": "Optional[str] (Specific model to use, defaults to configured model)",
                "temperature": "Optional[float] (Sampling temperature, 0.0-2.0, default: 0.7)",
                "max_tokens": "Optional[int] (Maximum tokens in response, default: 1000)"
            }
        },
        "parameters": [
            {
                "parameter_name": "prompt",
                "parameter_type": "string",
                "description": "The prompt/message to send to the LLM",
                "is_required": True,
                "order_index": 0
            },
            {
                "parameter_name": "model_id",
                "parameter_type": "string",
                "description": "Specific model to use (defaults to configured model)",
                "is_required": False,
                "order_index": 1
            },
            {
                "parameter_name": "temperature",
                "parameter_type": "float",
                "description": "Sampling temperature (0.0-2.0)",
                "is_required": False,
                "default_value": "0.7",
                "validation_rules": {"min": 0.0, "max": 2.0},
                "order_index": 2
            },
            {
                "parameter_name": "max_tokens",
                "parameter_type": "integer",
                "description": "Maximum tokens in response",
                "is_required": False,
                "default_value": "1000",
                "validation_rules": {"min": 1, "max": 100000},
                "order_index": 3
            }
        ],
        "requires_human_review": True,
        "is_batch_processable": False,
        "estimated_execution_time_ms": 3000,
        "is_deterministic": False,
        "is_stateless": True,
        "implementation_type": "python_class",
        "implementation_path": "nexus.tools.utilities.generic_llm_tool.GenericLLMCallTool",
        "tags": ["utility", "llm", "ai", "generative"],
        "author": "System",
        "status": "active",
        "example_usage": "Make generic LLM calls for text generation, analysis, or transformation. Uses existing LLM Gateway infrastructure for governance."
    },
    {
        "name": "maps_plotting",
        "display_name": "Maps Plotting",
        "description": "Generates maps with locations, routes, or markers. Returns map image URL or embedded map data.",
        "category": "utility",
        "version": "1.0.0",
        "schema_definition": {
            "name": "maps_plotting",
            "description": "Generates maps with locations, routes, or markers. Returns map image URL or embedded map data.",
            "parameters": {
                "locations": "List[str] (List of addresses or coordinates in 'lat,lng' format)",
                "plot_type": "str (Type of plot: 'route', 'markers', 'heatmap', default: 'markers')",
                "center_location": "Optional[str] (Center point address or 'lat,lng' coordinates, defaults to centroid of locations)"
            }
        },
        "parameters": [
            {
                "parameter_name": "locations",
                "parameter_type": "array",
                "description": "List of addresses or coordinates in 'lat,lng' format",
                "is_required": True,
                "order_index": 0
            },
            {
                "parameter_name": "plot_type",
                "parameter_type": "string",
                "description": "Type of plot",
                "is_required": False,
                "default_value": "markers",
                "validation_rules": {"enum": ["route", "markers", "heatmap"]},
                "order_index": 1
            },
            {
                "parameter_name": "center_location",
                "parameter_type": "string",
                "description": "Center point address or 'lat,lng' coordinates (defaults to centroid)",
                "is_required": False,
                "order_index": 2
            }
        ],
        "requires_human_review": False,
        "is_batch_processable": False,
        "estimated_execution_time_ms": 2000,
        "is_deterministic": False,
        "is_stateless": True,
        "implementation_type": "python_class",
        "implementation_path": "nexus.tools.utilities.maps_plotting_tool.MapsPlottingTool",
        "tags": ["utility", "maps", "geography", "visualization"],
        "author": "System",
        "status": "active",
        "example_usage": "Plot locations on a map, generate routes, or create heatmaps. Ready for Google Maps API integration."
    },
    # CRM Tools
    {
        "name": "schedule_scanner",
        "display_name": "Schedule Scanner",
        "description": "Fetches appointments for a given date range from the scheduling system.",
        "category": "crm",
        "version": "1.0.0",
        "schema_definition": {
            "name": "schedule_scanner",
            "description": "Fetches appointments for a given date range.",
            "parameters": {
                "days_out": "int (number of days into the future to scan)"
            }
        },
        "parameters": [
            {
                "parameter_name": "days_out",
                "parameter_type": "integer",
                "description": "Number of days into the future to scan",
                "is_required": False,
                "default_value": "14",
                "validation_rules": {"min": 1, "max": 365},
                "order_index": 0
            }
        ],
        "requires_human_review": False,
        "is_batch_processable": False,
        "estimated_execution_time_ms": 500,
        "is_deterministic": False,
        "is_stateless": True,
        "implementation_type": "python_class",
        "implementation_path": "nexus.tools.crm.schedule_scanner.ScheduleScannerTool",
        "tags": ["crm", "scheduling", "appointments", "workflow"],
        "author": "System",
        "status": "active",
        "example_usage": "Scan appointments for the next 14 days to analyze scheduling patterns and identify at-risk appointments."
    },
    {
        "name": "risk_calculator",
        "display_name": "Risk Calculator",
        "description": "Analyzes a list of appointments and calculates risk scores for no-show and denial risks.",
        "category": "crm",
        "version": "1.0.0",
        "schema_definition": {
            "name": "risk_calculator",
            "description": "Analyzes a list of appointments and calculates risk scores.",
            "parameters": {
                "appointments": "List[Dict] (The appointments to analyze)"
            }
        },
        "parameters": [
            {
                "parameter_name": "appointments",
                "parameter_type": "array",
                "description": "The appointments to analyze (list of appointment dictionaries)",
                "is_required": True,
                "order_index": 0
            }
        ],
        "requires_human_review": False,
        "is_batch_processable": True,
        "estimated_execution_time_ms": 1000,
        "is_deterministic": False,
        "is_stateless": True,
        "implementation_type": "python_class",
        "implementation_path": "nexus.tools.crm.risk_calculator.RiskCalculatorTool",
        "tags": ["crm", "risk", "analytics", "appointments", "workflow"],
        "author": "System",
        "status": "active",
        "example_usage": "Calculate no-show and denial risk scores for appointments to identify high-risk appointments requiring intervention."
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

