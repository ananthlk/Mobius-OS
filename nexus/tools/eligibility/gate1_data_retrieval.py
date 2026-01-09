"""
Gate 1 Data Retrieval Tools

Tools for retrieving patient and insurance data from EMR/internal systems.
"""
import logging
from typing import Dict, Any, Optional
from nexus.core.base_tool import NexusTool, ToolSchema

logger = logging.getLogger("nexus.tools.gate1")


class EMRPatientDemographicsRetriever(NexusTool):
    """Retrieves patient demographics from EMR"""
    
    def define_schema(self) -> ToolSchema:
        return ToolSchema(
            name="emr_patient_demographics",
            description="Retrieve patient demographics from EMR",
            parameters={"patient_id": "str"}
        )
    
    def run(self, patient_id: str) -> Dict[str, Any]:
        """Synchronous run method"""
        import asyncio
        return asyncio.run(self.run_async(patient_id))
    
    async def run_async(self, patient_id: str) -> Dict[str, Any]:
        """Async method to retrieve demographics directly"""
        try:
            # Use PatientSimulator directly to generate synthetic patient data
            from nexus.tools.eligibility.patient_simulator import PatientSimulator
            
            simulator = PatientSimulator()
            patient_data = simulator.generate_synthetic_patient(patient_id)
            demographics = patient_data.get("demographics")
            
            # Handle test scenario where demographics is None
            if demographics is None:
                logger.info(f"Test scenario: {patient_id} - demographics is None (missing data)")
                return {}
            
            logger.info(f"Successfully generated demographics for {patient_id}: {demographics.get('first_name', 'N/A')} {demographics.get('last_name', 'N/A')}")
            return {
                "member_id": demographics.get("member_id"),
                "first_name": demographics.get("first_name"),
                "last_name": demographics.get("last_name"),
                "date_of_birth": demographics.get("date_of_birth"),
                "sex": demographics.get("sex")
            }
        except Exception as e:
            logger.error(f"Failed to fetch demographics for {patient_id}: {e}")
            return {}


class EMRPatientInsuranceInfoRetriever(NexusTool):
    """Retrieves patient insurance information from EMR"""
    
    def define_schema(self) -> ToolSchema:
        return ToolSchema(
            name="emr_patient_insurance",
            description="Retrieve patient insurance information from EMR",
            parameters={"patient_id": "str"}
        )
    
    def run(self, patient_id: str) -> Dict[str, Any]:
        """Synchronous run method"""
        import asyncio
        return asyncio.run(self.run_async(patient_id))
    
    async def run_async(self, patient_id: str) -> Dict[str, Any]:
        """Async method to retrieve insurance directly"""
        try:
            # Use PatientSimulator directly to generate synthetic patient data
            from nexus.tools.eligibility.patient_simulator import PatientSimulator
            
            simulator = PatientSimulator()
            patient_data = simulator.generate_synthetic_patient(patient_id)
            health_plan = patient_data.get("health_plan")
            
            # Handle test scenario where health_plan is None
            if health_plan is None:
                logger.info(f"Test scenario: {patient_id} - health_plan is None (missing data)")
                return {}
            
            logger.info(f"Successfully generated insurance for {patient_id}: {health_plan.get('payer_name', 'N/A')}")
            return {
                "payer_name": health_plan.get("payer_name"),
                "payer_id": health_plan.get("payer_id"),
                "plan_name": health_plan.get("plan_name"),
                "member_id": health_plan.get("member_id")
            }
        except Exception as e:
            logger.error(f"Failed to fetch insurance for {patient_id}: {e}")
            return {}


class EMRPatientVisitsRetriever(NexusTool):
    """Retrieves patient visits/appointments from EMR"""
    
    def define_schema(self) -> ToolSchema:
        return ToolSchema(
            name="emr_patient_visits",
            description="Retrieve patient visits/appointments from EMR",
            parameters={"patient_id": "str", "lookback_days": "int", "lookahead_days": "int"}
        )
    
    def run(self, patient_id: str, lookback_days: int = 90, lookahead_days: int = 90) -> list:
        """Retrieve visits for patient (synchronous wrapper)"""
        import asyncio
        try:
            # Check if we're in an async context
            loop = None
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                pass
            
            if loop:
                # We're in an async context, can't use asyncio.run()
                # Return empty list - caller should use run_async instead
                logger.warning(f"Cannot use synchronous run() in async context for {patient_id}, use run_async() instead")
                return []
            else:
                # Not in async context, safe to use asyncio.run()
                return asyncio.run(self._fetch_visits(patient_id, lookback_days, lookahead_days))
        except Exception as e:
            logger.warning(f"Could not retrieve visits for patient {patient_id}, returning empty list: {e}")
            return []
    
    async def run_async(self, patient_id: str, lookback_days: int = 90, lookahead_days: int = 90) -> list:
        """Retrieve visits for patient (async method)"""
        return await self._fetch_visits(patient_id, lookback_days, lookahead_days)
    
    async def _fetch_visits(self, patient_id: str, lookback_days: int, lookahead_days: int) -> list:
        """Async method to fetch visits"""
        try:
            # Use PatientSimulator directly to generate synthetic patient data
            from nexus.tools.eligibility.patient_simulator import PatientSimulator
            from datetime import date, timedelta
            
            simulator = PatientSimulator()
            patient_data = simulator.generate_synthetic_patient(patient_id)
            visits = patient_data.get("visits", [])
            
            # Filter by date range
            today = date.today()
            cutoff_start = today - timedelta(days=lookback_days)
            cutoff_end = today + timedelta(days=lookahead_days)
            
            filtered_visits = []
            for visit in visits:
                visit_date_str = visit.get("visit_date")
                if visit_date_str:
                    try:
                        visit_date = date.fromisoformat(visit_date_str)
                        if cutoff_start <= visit_date <= cutoff_end:
                            filtered_visits.append(visit)
                    except (ValueError, TypeError):
                        # If date parsing fails, include the visit anyway
                        filtered_visits.append(visit)
            
            return filtered_visits[:10]  # Return first 10 for now
        except Exception as e:
            logger.warning(f"Failed to fetch visits for {patient_id}: {e}")
            return []
