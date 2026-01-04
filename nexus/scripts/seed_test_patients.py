"""
Seed script to generate test patient profiles for bounded plan testing.

This creates a set of known test patients that can be used for testing
the eligibility check workflow.
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nexus.modules.database import database
from nexus.modules.user_profile_manager import user_profile_manager


# Pre-defined test patients for consistent testing
# Scenarios simulate real-world partial data availability
TEST_PATIENTS = [
    # Standard patients - all views available
    {
        "patient_id": "TEST001",
        "name": "John Doe",
        "seed_data": {"test_patient": True, "scenario": "standard"}
    },
    {
        "patient_id": "TEST002",
        "name": "Jane Smith",
        "seed_data": {"test_patient": True, "scenario": "standard"}
    },
    {
        "patient_id": "TEST003",
        "name": "Michael Johnson",
        "seed_data": {"test_patient": True, "scenario": "standard"}
    },
    {
        "patient_id": "TEST004",
        "name": "Sarah Williams",
        "seed_data": {"test_patient": True, "scenario": "standard"}
    },
    {
        "patient_id": "TEST005",
        "name": "Robert Brown",
        "seed_data": {"test_patient": True, "scenario": "standard"}
    },
    # Realistic scenarios: Patient exists in EMR but not in insurance
    {
        "patient_id": "TEST006",
        "name": "Emily Davis",
        "seed_data": {"test_patient": True, "scenario": "no_insurance"}
    },
    # Patient exists in EMR only (no system integration, no insurance)
    {
        "patient_id": "TEST007",
        "name": "David Miller",
        "seed_data": {"test_patient": True, "scenario": "emr_only"}
    },
    # Patient has insurance but no EMR records (new patient, just enrolled)
    {
        "patient_id": "TEST008",
        "name": "Jessica Garcia",
        "seed_data": {"test_patient": True, "scenario": "insurance_only"}
    },
    # Patient has EMR and insurance but system data not synced
    {
        "patient_id": "TEST009",
        "name": "William Taylor",
        "seed_data": {"test_patient": True, "scenario": "missing_system"}
    },
    # Patient has system and insurance but no EMR (never visited)
    {
        "patient_id": "TEST010",
        "name": "Amanda Martinez",
        "seed_data": {"test_patient": True, "scenario": "missing_emr"}
    },
    # Patient only in system (demographics only, no clinical or insurance)
    {
        "patient_id": "TEST011",
        "name": "Christopher Lee",
        "seed_data": {"test_patient": True, "scenario": "system_only"}
    },
    # Patient has EMR and system but insurance expired/terminated
    {
        "patient_id": "TEST012",
        "name": "Jennifer White",
        "seed_data": {"test_patient": True, "scenario": "emr_and_insurance"}
    }
]


async def seed_test_patients():
    """Generate test patient profiles."""
    await database.connect()
    
    try:
        print("🌱 Seeding test patient profiles...")
        print("")
        
        generated_patients = []
        
        for patient_config in TEST_PATIENTS:
            try:
                print(f"Generating patient: {patient_config['name']} (ID: {patient_config['patient_id']})")
                
                # Generate patient with scenario-based view availability
                # The generate_synthetic_patient method now handles scenarios natively
                profile = await user_profile_manager.generate_synthetic_patient(
                    patient_id=patient_config["patient_id"],
                    name=patient_config["name"],
                    seed_data=patient_config.get("seed_data")
                )
                
                # Log which views were generated
                scenario = patient_config.get("seed_data", {}).get("scenario", "standard")
                available_views = []
                if profile["availability_flags"]["emr"]:
                    available_views.append("EMR")
                if profile["availability_flags"]["system"]:
                    available_views.append("System")
                if profile["availability_flags"]["health_plan"]:
                    available_views.append("Health Plan")
                
                if len(available_views) < 3:
                    print(f"  ⚠️  Partial data scenario: {scenario}")
                    print(f"      Available views: {', '.join(available_views)}")
                else:
                    print(f"  ✅ All views available")
                
                # Get name from system_data or demographics
                name = "Unknown"
                if profile.get("system_data") and profile["system_data"].get("demographics"):
                    name = profile["system_data"]["demographics"].get("name", "Unknown")
                elif profile.get("system_data") and isinstance(profile["system_data"], dict) and "demographics" in profile["system_data"]:
                    name = profile["system_data"]["demographics"].get("name", "Unknown")
                
                generated_patients.append({
                    "patient_id": profile["patient_id"],
                    "name": name,
                    "scenario": scenario,
                    "has_emr": profile["availability_flags"]["emr"],
                    "has_system": profile["availability_flags"]["system"],
                    "has_health_plan": profile["availability_flags"]["health_plan"]
                })
                
                print(f"  ✅ Generated successfully")
                print("")
                
            except Exception as e:
                print(f"  ❌ Error generating patient {patient_config['name']}: {e}")
                print("")
        
        print("=" * 60)
        print("✅ Test Patients Seeded Successfully!")
        print("=" * 60)
        print("")
        print("Available Test Patients:")
        print("")
        for patient in generated_patients:
            views = []
            if patient["has_emr"]:
                views.append("EMR")
            if patient["has_system"]:
                views.append("System")
            if patient["has_health_plan"]:
                views.append("Health Plan")
            
            scenario_desc = {
                "standard": "All views available",
                "no_insurance": "EMR + System (no insurance)",
                "emr_only": "EMR only (not in other systems)",
                "insurance_only": "Insurance only (new patient)",
                "missing_system": "EMR + Insurance (system not synced)",
                "missing_emr": "System + Insurance (no EMR records)",
                "system_only": "System only (demographics only)",
                "emr_and_insurance": "EMR + Insurance (system missing)"
            }.get(patient["scenario"], patient["scenario"])
            
            print(f"  • {patient['name']} (ID: {patient['patient_id']})")
            print(f"    Scenario: {scenario_desc}")
            print(f"    Available views: {', '.join(views) if views else 'None'}")
            print("")
        
        print("=" * 60)
        print("Usage Examples:")
        print("=" * 60)
        print("")
        print("1. Search by name:")
        print('   curl "http://localhost:8000/api/user-profiles/search?name=John%20Doe"')
        print("")
        print("2. Get full profile:")
        print("   curl http://localhost:8000/api/user-profiles/TEST001")
        print("")
        print("3. Get EMR view:")
        print("   curl http://localhost:8000/api/user-profiles/TEST001/emr")
        print("")
        print("4. Get system view:")
        print("   curl http://localhost:8000/api/user-profiles/TEST001/system")
        print("")
        print("5. Get health plan view:")
        print("   curl http://localhost:8000/api/user-profiles/TEST001/health-plan")
        print("")
        print("6. Test in workflow:")
        print('   When asked for patient name, type: "John Doe"')
        print("   The system will automatically fetch the profile.")
        print("")
        
    except Exception as e:
        print(f"❌ Error seeding test patients: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        await database.disconnect()


if __name__ == "__main__":
    asyncio.run(seed_test_patients())

