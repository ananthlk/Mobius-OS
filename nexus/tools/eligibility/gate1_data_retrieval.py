"""
Gate 1 Tools: Patient/Insurance Info Availability
"""
from typing import Any, Dict, List, Optional
from nexus.core.base_tool import NexusTool, ToolSchema
import os
import logging

logger = logging.getLogger("nexus.tools.gate1")

# API Configuration
API_BASE_URL = os.getenv("MOBIUS_API_URL", "http://localhost:8000")


class EMRPatientDemographicsRetriever(NexusTool):
    """Retrieves existing patient demographics from EHR/EMR system using patient_id."""
    def define_schema(self) -> ToolSchema:
        return ToolSchema(
            name="emr_patient_demographics_retriever",
            description="Retrieves patient demographics (name, DOB, address, contact info) from EMR system. Uses patient_id (EMR identifier).",
            parameters={
                "patient_id": "str (Patient identifier)",
                "appointment_id": "Optional[str] (Appointment identifier if available)"
            }
        )
    
    def _fetch_from_api(self, patient_id: str) -> Optional[Dict[str, Any]]:
        """Fetch demographics from user profile API."""
        try:
            import httpx
            
            url = f"{API_BASE_URL}/api/user-profiles/{patient_id}/system"
            with httpx.Client(timeout=5.0) as client:
                response = client.get(url)
                if response.status_code == 200:
                    system_data = response.json()
                    demographics = system_data.get("demographics", {})
                    return {
                        "patient_id": patient_id,
                        "name": demographics.get("name", ""),
                        "date_of_birth": demographics.get("dob", ""),
                        "address": demographics.get("address", ""),
                        "phone": demographics.get("phone", ""),
                        "email": demographics.get("email", "")
                    }
                else:
                    logger.debug(f"API returned status {response.status_code} for patient {patient_id}")
                    return None
        except Exception as e:
            logger.debug(f"Failed to fetch from API: {e}")
            return None
    
    def run(self, patient_id: str, appointment_id: Optional[str] = None) -> Dict[str, Any]:
        # Fetch from API only
        api_result = self._fetch_from_api(patient_id)
        if api_result:
            return api_result
        
        # If API fails, raise error
        raise ValueError(f"Failed to retrieve demographics for patient {patient_id}. Patient not found or API unavailable.")

class EMRPatientInsuranceInfoRetriever(NexusTool):
    """
    Gets insurance information from patient record stored in EMR/internal systems.
    
    Note: This tool retrieves insurance info FROM the patient's profile/record (EMR system).
    It uses patient_id (EMR identifier), NOT member_id (insurance identifier).
    For querying insurance systems directly (e.g., eligibility checks), use member_id.
    """
    def define_schema(self) -> ToolSchema:
        return ToolSchema(
            name="emr_patient_insurance_info_retriever",
            description="Retrieves insurance information FROM patient record/EMR system (payer ID, member ID, group number, policy number). Uses patient_id (EMR identifier).",
            parameters={
                "patient_id": "str (Patient identifier from EMR/internal system)"
            }
        )
    
    def _fetch_from_api(self, patient_id: str) -> Optional[Dict[str, Any]]:
        """Fetch insurance info from user profile API."""
        try:
            import httpx
            
            url = f"{API_BASE_URL}/api/user-profiles/{patient_id}/health-plan"
            with httpx.Client(timeout=5.0) as client:
                response = client.get(url)
                if response.status_code == 200:
                    health_plan_data = response.json()
                    coverage = health_plan_data.get("coverage", {})
                    return {
                        "patient_id": patient_id,
                        "payer_id": "87726",  # Could be derived from carrier mapping
                        "payer_name": health_plan_data.get("carrier", ""),
                        "member_id": health_plan_data.get("member_id", ""),
                        "group_number": health_plan_data.get("group", ""),
                        "policy_number": health_plan_data.get("member_id", ""),  # Using member_id as policy
                        "effective_date": coverage.get("effective_date", ""),
                        "expiration_date": coverage.get("termination_date", "")
                    }
                else:
                    logger.debug(f"API returned status {response.status_code} for patient {patient_id}")
                    return None
        except Exception as e:
            logger.debug(f"Failed to fetch from API: {e}")
            return None
    
    def run(self, patient_id: str) -> Dict[str, Any]:
        # Fetch from API only
        api_result = self._fetch_from_api(patient_id)
        if api_result:
            return api_result
        
        # If API fails, raise error
        raise ValueError(f"Failed to retrieve insurance information for patient {patient_id}. Patient not found or API unavailable.")

class EMRPatientHistoricalInsuranceLookup(NexusTool):
    """Searches historical records for past insurance information from EMR system using patient_id."""
    def define_schema(self) -> ToolSchema:
        return ToolSchema(
            name="emr_patient_historical_insurance_lookup",
            description="Searches historical insurance records from EMR system when current info is missing. Uses patient_id (EMR identifier).",
            parameters={
                "patient_id": "str (Patient identifier)",
                "lookback_days": "int (Number of days to look back, default 365)"
            }
        )
    
    def _fetch_from_api(self, patient_id: str, lookback_days: int) -> Optional[List[Dict[str, Any]]]:
        """Fetch historical insurance from user profile API."""
        try:
            import httpx
            from datetime import datetime, timedelta
            
            url = f"{API_BASE_URL}/api/user-profiles/{patient_id}/health-plan"
            with httpx.Client(timeout=5.0) as client:
                response = client.get(url)
                if response.status_code == 200:
                    health_plan_data = response.json()
                    coverage = health_plan_data.get("coverage", {})
                    effective_date = coverage.get("effective_date", "")
                    
                    # For now, return current coverage as historical record
                    # In a real system, this would query historical records
                    if effective_date:
                        return [
                            {
                                "patient_id": patient_id,
                                "insurance_record": {
                                    "payer_id": "87726",  # Could be derived from carrier
                                    "member_id": health_plan_data.get("member_id", ""),
                                    "effective_date": effective_date,
                                    "expiration_date": coverage.get("termination_date", "")
                                },
                                "source": "historical_record",
                                "record_date": effective_date
                            }
                        ]
                else:
                    logger.debug(f"API returned status {response.status_code} for patient {patient_id}")
                    return None
        except Exception as e:
            logger.debug(f"Failed to fetch from API: {e}")
            return None
    
    def run(self, patient_id: str, lookback_days: int = 365) -> List[Dict[str, Any]]:
        # Fetch from API only
        api_result = self._fetch_from_api(patient_id, lookback_days)
        if api_result:
            return api_result
        
        # If API fails, raise error
        raise ValueError(f"Failed to retrieve historical insurance data for patient {patient_id}. Patient not found or API unavailable.")

class HIEInsuranceQuery(NexusTool):
    """Queries Health Information Exchange (HIE) system for insurance data. Uses patient_id to query HIE network."""
    def define_schema(self) -> ToolSchema:
        return ToolSchema(
            name="hie_insurance_query",
            description="Queries Health Information Exchange (HIE) system for insurance data when local records are incomplete. Uses patient_id and hie_network_id.",
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



