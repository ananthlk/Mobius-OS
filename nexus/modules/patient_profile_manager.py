"""
Patient Profile Manager

Manages patient profiles and synthetic patient data generation.
"""
import logging
from typing import Dict, Any, Optional
from nexus.modules.database import database
from nexus.tools.eligibility.patient_simulator import PatientSimulator

logger = logging.getLogger("nexus.patient_profile_manager")


class PatientProfileManager:
    """Manages patient profile operations"""
    
    def __init__(self):
        self.patient_simulator = PatientSimulator()
    
    async def generate_synthetic_patient(self, patient_id: str, seed_data: Optional[Dict] = None) -> Dict[str, Any]:
        """Generate synthetic patient data"""
        try:
            patient_data = self.patient_simulator.generate_synthetic_patient(
                patient_id=patient_id,
                seed_data=seed_data
            )
            
            # Store in database
            import json
            query = """
                INSERT INTO patient_profiles (patient_id, profile_data, created_at, updated_at)
                VALUES (:patient_id, :profile_data::jsonb, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                ON CONFLICT (patient_id) 
                DO UPDATE SET 
                    profile_data = :profile_data::jsonb,
                    updated_at = CURRENT_TIMESTAMP
            """
            await database.execute(
                query=query,
                values={
                    "patient_id": patient_id,
                    "profile_data": json.dumps(patient_data)
                }
            )
            
            logger.info(f"Generated synthetic patient for {patient_id}")
            return patient_data
        except Exception as e:
            logger.error(f"Failed to generate synthetic patient: {e}")
            raise
    
    async def get_patient_system_view(self, patient_id: str) -> Optional[Dict[str, Any]]:
        """Get patient system view (demographics)"""
        try:
            import asyncio
            import json
            
            query = "SELECT profile_data FROM patient_profiles WHERE patient_id = :patient_id"
            row = await asyncio.wait_for(
                database.fetch_one(query=query, values={"patient_id": patient_id}),
                timeout=2.0
            )
            
            if row and row.get("profile_data"):
                profile_data = row["profile_data"] if isinstance(row["profile_data"], dict) else json.loads(row["profile_data"])
                return {
                    "demographics": profile_data.get("demographics", {})
                }
            
            # If not found, generate
            await self.generate_synthetic_patient(patient_id)
            row = await database.fetch_one(query=query, values={"patient_id": patient_id})
            if row and row.get("profile_data"):
                profile_data = row["profile_data"] if isinstance(row["profile_data"], dict) else json.loads(row["profile_data"])
                return {
                    "demographics": profile_data.get("demographics", {})
                }
            
            return None
        except asyncio.TimeoutError:
            logger.warning(f"Timeout fetching patient {patient_id}, attempting to generate")
            try:
                await self.generate_synthetic_patient(patient_id)
                return await self.get_patient_system_view(patient_id)
            except Exception as e:
                logger.error(f"Failed to generate patient after timeout: {e}")
                return None
        except Exception as e:
            logger.error(f"Failed to get patient system view: {e}")
            return None
    
    async def get_patient_health_plan_view(self, patient_id: str) -> Optional[Dict[str, Any]]:
        """Get patient health plan view"""
        try:
            import asyncio
            import json
            
            query = "SELECT profile_data FROM patient_profiles WHERE patient_id = :patient_id"
            row = await asyncio.wait_for(
                database.fetch_one(query=query, values={"patient_id": patient_id}),
                timeout=2.0
            )
            
            if row and row.get("profile_data"):
                profile_data = row["profile_data"] if isinstance(row["profile_data"], dict) else json.loads(row["profile_data"])
                return {
                    "health_plan": profile_data.get("health_plan", {})
                }
            
            # If not found, generate
            await self.generate_synthetic_patient(patient_id)
            row = await database.fetch_one(query=query, values={"patient_id": patient_id})
            if row and row.get("profile_data"):
                profile_data = row["profile_data"] if isinstance(row["profile_data"], dict) else json.loads(row["profile_data"])
                return {
                    "health_plan": profile_data.get("health_plan", {})
                }
            
            return None
        except asyncio.TimeoutError:
            logger.warning(f"Timeout fetching patient {patient_id}, attempting to generate")
            try:
                await self.generate_synthetic_patient(patient_id)
                return await self.get_patient_health_plan_view(patient_id)
            except Exception as e:
                logger.error(f"Failed to generate patient after timeout: {e}")
                return None
        except Exception as e:
            logger.error(f"Failed to get patient health plan view: {e}")
            return None
    
    async def get_patient_emr_view(self, patient_id: str) -> Optional[Dict[str, Any]]:
        """Get patient EMR view (includes visits)"""
        try:
            import json
            
            query = "SELECT profile_data FROM patient_profiles WHERE patient_id = :patient_id"
            row = await database.fetch_one(query=query, values={"patient_id": patient_id})
            
            if row and row.get("profile_data"):
                profile_data = row["profile_data"] if isinstance(row["profile_data"], dict) else json.loads(row["profile_data"])
                return {
                    "visits": profile_data.get("visits", [])
                }
            
            return None
        except Exception as e:
            logger.error(f"Failed to get patient EMR view: {e}")
            return None


# Singleton instance
patient_profile_manager = PatientProfileManager()
