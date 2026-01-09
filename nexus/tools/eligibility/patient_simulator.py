"""
Patient Simulator

Generates synthetic patient data for testing.
"""
import logging
import random
from typing import Dict, Any, Optional
from datetime import date, timedelta

logger = logging.getLogger("nexus.tools.eligibility.patient_simulator")


class PatientSimulator:
    """Generates synthetic patient data"""
    
    def _get_seeded_random(self, patient_id: str):
        """Get seeded random generator for deterministic data"""
        # Use patient_id as seed
        seed = hash(patient_id) % (2**32)
        return random.Random(seed)
    
    def generate_synthetic_patient(
        self,
        patient_id: str,
        seed_data: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Generate synthetic patient profile"""
        rng = self._get_seeded_random(patient_id)
        
        # Generate demographics
        demographics = self._generate_demographics(patient_id, rng, seed_data)
        
        # Generate health plan
        health_plan = self._generate_health_plan(patient_id, rng, seed_data)
        
        # Generate EMR data (visits)
        emr_data = self._generate_emr_data(patient_id, rng, seed_data)
        
        logger.debug(f"Generated patient {patient_id}: {demographics.get('first_name')} {demographics.get('last_name')}")
        
        return {
            "demographics": demographics,
            "health_plan": health_plan,
            "visits": emr_data.get("visits", [])
        }
    
    def _generate_demographics(self, patient_id: str, rng: random.Random, seed_data: Optional[Dict]) -> Dict[str, Any]:
        """Generate patient demographics"""
        first_names = ["John", "Jane", "David", "Sarah", "Michael", "Emily", "Robert", "Jessica"]
        last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis"]
        
        first_name = rng.choice(first_names)
        last_name = rng.choice(last_names)
        
        # Generate DOB (age 25-75)
        age = rng.randint(25, 75)
        dob = date.today() - timedelta(days=age * 365 + rng.randint(0, 365))
        
        sex = rng.choice(["MALE", "FEMALE", "OTHER"])
        
        # Generate member ID
        member_id = f"{patient_id.replace('MRN', '')}123456789"
        
        return {
            "member_id": member_id,
            "first_name": first_name,
            "last_name": last_name,
            "date_of_birth": dob.isoformat(),
            "sex": sex
        }
    
    def _generate_health_plan(self, patient_id: str, rng: random.Random, seed_data: Optional[Dict]) -> Dict[str, Any]:
        """Generate health plan information"""
        payers = ["UnitedHealthcare", "Anthem", "Aetna", "Cigna", "Humana", "Blue Cross"]
        payer_name = rng.choice(payers)
        payer_id = "87726"  # Common payer ID
        
        plan_name = f"{patient_id.replace('MRN', '')}PLAN"
        
        return {
            "payer_name": payer_name,
            "payer_id": payer_id,
            "plan_name": plan_name,
            "member_id": f"{patient_id.replace('MRN', '')}123456789"
        }
    
    def _generate_emr_data(self, patient_id: str, rng: random.Random, seed_data: Optional[Dict]) -> Dict[str, Any]:
        """Generate EMR data (visits)"""
        visits = []
        today = date.today()
        
        # Generate 2-5 visits
        num_visits = rng.randint(2, 5)
        for i in range(num_visits):
            # Random date within ±6 months
            days_offset = rng.randint(-180, 180)
            visit_date = today + timedelta(days=days_offset)
            
            visit_types = ["appointment", "encounter", "procedure"]
            statuses = ["scheduled", "completed", "cancelled"]
            
            visits.append({
                "visit_id": f"VISIT{i+1:03d}",
                "visit_date": visit_date.isoformat(),
                "visit_type": rng.choice(visit_types),
                "status": rng.choice(statuses),
                "provider": f"Dr. {rng.choice(['Smith', 'Jones', 'Williams'])}",
                "location": rng.choice(["Main Clinic", "North Branch", "South Branch"])
            })
        
        return {"visits": visits}
