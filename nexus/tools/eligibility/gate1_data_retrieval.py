"""
Gate 1 Tools: Patient/Insurance Info Availability
"""
from typing import Any, Dict, List, Optional
from nexus.core.base_tool import NexusTool, ToolSchema

class PatientDemographicsRetriever(NexusTool):
    """Retrieves existing patient demographics from EHR/EMR."""
    def define_schema(self) -> ToolSchema:
        return ToolSchema(
            name="patient_demographics_retriever",
            description="Retrieves patient demographics (name, DOB, address, contact info) from EHR/EMR system.",
            parameters={
                "patient_id": "str (Patient identifier)",
                "appointment_id": "Optional[str] (Appointment identifier if available)"
            }
        )
    
    def run(self, patient_id: str, appointment_id: Optional[str] = None) -> Dict[str, Any]:
        # Mock implementation
        return {
            "patient_id": patient_id,
            "name": "John Doe",
            "date_of_birth": "1980-01-15",
            "address": "123 Main St, City, State 12345",
            "phone": "555-0100",
            "email": "john.doe@email.com"
        }

class InsuranceInfoRetriever(NexusTool):
    """Gets insurance information from patient record."""
    def define_schema(self) -> ToolSchema:
        return ToolSchema(
            name="insurance_info_retriever",
            description="Retrieves insurance information from patient record (payer ID, member ID, group number, policy number).",
            parameters={
                "patient_id": "str (Patient identifier)"
            }
        )
    
    def run(self, patient_id: str) -> Dict[str, Any]:
        # Mock implementation
        return {
            "patient_id": patient_id,
            "payer_id": "87726",
            "payer_name": "UnitedHealthcare",
            "member_id": "M123456789",
            "group_number": "GRP001",
            "policy_number": "POL123456",
            "effective_date": "2024-01-01",
            "expiration_date": "2024-12-31"
        }

class HistoricalInsuranceLookup(NexusTool):
    """Searches historical records for past insurance information."""
    def define_schema(self) -> ToolSchema:
        return ToolSchema(
            name="historical_insurance_lookup",
            description="Searches historical records for past insurance information when current info is missing.",
            parameters={
                "patient_id": "str (Patient identifier)",
                "lookback_days": "int (Number of days to look back, default 365)"
            }
        )
    
    def run(self, patient_id: str, lookback_days: int = 365) -> List[Dict[str, Any]]:
        # Mock implementation
        return [
            {
                "patient_id": patient_id,
                "insurance_record": {
                    "payer_id": "87726",
                    "member_id": "M123456789",
                    "effective_date": "2023-01-01",
                    "expiration_date": "2023-12-31"
                },
                "source": "historical_record",
                "record_date": "2023-06-15"
            }
        ]

class HIEInsuranceQuery(NexusTool):
    """Queries Health Information Exchange for insurance data."""
    def define_schema(self) -> ToolSchema:
        return ToolSchema(
            name="hie_insurance_query",
            description="Queries Health Information Exchange (HIE) for insurance data when local records are incomplete.",
            parameters={
                "patient_id": "str (Patient identifier)",
                "hie_network_id": "str (HIE network identifier)",
                "query_type": "str (Type of query: 'insurance', 'demographics', 'both')"
            }
        )
    
    def run(self, patient_id: str, hie_network_id: str, query_type: str = "insurance") -> Dict[str, Any]:
        # Mock implementation
        return {
            "patient_id": patient_id,
            "hie_network_id": hie_network_id,
            "insurance_info": {
                "payer_id": "87726",
                "member_id": "M123456789",
                "payer_name": "UnitedHealthcare"
            },
            "source": "hie",
            "query_timestamp": "2024-01-15T10:30:00Z"
        }

class PatientInsuranceCollector(NexusTool):
    """Initiates patient communication to collect insurance information."""
    def define_schema(self) -> ToolSchema:
        return ToolSchema(
            name="patient_insurance_collector",
            description="Initiates patient communication to collect insurance information when it must come from patient directly.",
            parameters={
                "patient_id": "str (Patient identifier)",
                "communication_method": "str (Method: 'portal', 'sms', 'email', 'phone')",
                "urgency": "str (Urgency level: 'low', 'medium', 'high')"
            }
        )
    
    def run(self, patient_id: str, communication_method: str = "portal", urgency: str = "medium") -> Dict[str, Any]:
        # Mock implementation - this would trigger actual communication
        return {
            "patient_id": patient_id,
            "communication_sent": True,
            "method": communication_method,
            "urgency": urgency,
            "message_id": "MSG123456",
            "status": "pending_response"
        }


