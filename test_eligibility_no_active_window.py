"""
Test script for Scenario 3b: Testing when eligibility check returns NO active window
This tests how the deterministic update handles cases with NO eligibility (no active coverage)
"""
import asyncio
import logging
import sys
import os
from datetime import datetime, date
from copy import deepcopy

# Ensure we can import nexus
sys.path.append(os.getcwd())

from nexus.agents.eligibility_v2.orchestrator import EligibilityOrchestrator
from nexus.agents.eligibility_v2.models import UIEvent, EligibilityStatus, CaseState
from nexus.modules.database import database

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s :: %(message)s'
)
logger = logging.getLogger(__name__)

async def test_no_active_window():
    """Test scenario where eligibility check returns NO active window"""
    print("=" * 80)
    print("Scenario 3b: Testing When Eligibility Check Returns NO Active Window")
    print("=" * 80)
    
    try:
        # Connect to database
        await database.connect()
        print("✅ Database connected")
        
        # Create orchestrator
        orchestrator = EligibilityOrchestrator()
        
        # First, get a normal case state with patient data
        print("\n" + "=" * 80)
        print("Step 1: Load Patient Data (MRN138)")
        print("=" * 80)
        
        ui_event_1 = UIEvent(
            event_type="user_message",
            data={"message": "Check eligibility for MRN138"},
            timestamp=datetime.now().isoformat()
        )
        
        result_1 = await orchestrator.process_turn(
            case_id="test_case_mrn138_no_coverage",
            ui_event=ui_event_1,
            session_id=None,
            patient_id="MRN138"
        )
        
        case_state_1 = result_1.get("case_state", {})
        print("\n📋 Initial Case State:")
        if isinstance(case_state_1, dict):
            patient = case_state_1.get("patient", {})
            health_plan = case_state_1.get("health_plan", {})
            eligibility_truth = case_state_1.get("eligibility_truth", {})
            
            print(f"  Patient: {patient.get('first_name')} {patient.get('last_name')}")
            print(f"  Member ID: {patient.get('member_id')}")
            print(f"  Payer: {health_plan.get('payer_name')}")
            print(f"  Eligibility Status: {eligibility_truth.get('status')}")
            print(f"  Coverage Window: {eligibility_truth.get('coverage_window_start')} to {eligibility_truth.get('coverage_window_end')}")
        
        # Now, manually test the deterministic update with a result that has NO active window
        print("\n" + "=" * 80)
        print("Step 2: Simulate Eligibility Check with NO Active Window")
        print("=" * 80)
        
        # Create a case state from the result
        case_state_obj = CaseState(**case_state_1) if isinstance(case_state_1, dict) else case_state_1
        
        # Simulate an eligibility check result with NO active window
        eligibility_result_no_active = {
            "insurance_id": case_state_obj.patient.member_id if hasattr(case_state_obj, 'patient') else case_state_1.get("patient", {}).get("member_id"),
            "insurance_name": case_state_obj.health_plan.payer_name if hasattr(case_state_obj, 'health_plan') else case_state_1.get("health_plan", {}).get("payer_name"),
            "eligibility_windows": [
                {
                    "effective_date": "2024-01-01",
                    "end_date": "2024-12-31",
                    "status": "inactive",  # Only inactive windows, no active
                    "coverage_type": "medical",
                    "plan_name": "Old Plan",
                    "member_id": case_state_obj.patient.member_id if hasattr(case_state_obj, 'patient') else case_state_1.get("patient", {}).get("member_id")
                },
                {
                    "effective_date": "2023-01-01",
                    "end_date": "2023-12-31",
                    "status": "inactive",  # Another inactive window
                    "coverage_type": "medical",
                    "plan_name": "Older Plan",
                    "member_id": case_state_obj.patient.member_id if hasattr(case_state_obj, 'patient') else case_state_1.get("patient", {}).get("member_id")
                }
            ],
            "queried_at": datetime.now().isoformat()
        }
        
        print("\n📋 Simulated Eligibility Result (NO active window):")
        print(f"  Windows: {len(eligibility_result_no_active['eligibility_windows'])}")
        for i, window in enumerate(eligibility_result_no_active['eligibility_windows'], 1):
            print(f"    Window {i}: {window['effective_date']} to {window['end_date']} - Status: {window['status']}")
        
        # Apply deterministic update with NO active window
        print("\n" + "=" * 80)
        print("Step 3: Apply Deterministic Update (should set status to NO)")
        print("=" * 80)
        
        updated_case_state = orchestrator._deterministically_update_case_state(
            case_state=case_state_obj,
            update_source="eligibility_check",
            updates={},
            eligibility_check_result=eligibility_result_no_active
        )
        
        print("\n📋 Case State After Deterministic Update:")
        print(f"  Eligibility Status: {updated_case_state.eligibility_truth.status}")
        print(f"  Evidence Strength: {updated_case_state.eligibility_truth.evidence_strength}")
        print(f"  Coverage Window Start: {updated_case_state.eligibility_truth.coverage_window_start}")
        print(f"  Coverage Window End: {updated_case_state.eligibility_truth.coverage_window_end}")
        print(f"  Eligibility Check Performed: {updated_case_state.eligibility_check.checked}")
        print(f"  Eligibility Check Source: {updated_case_state.eligibility_check.source}")
        
        # Validation
        print("\n" + "=" * 80)
        print("Validation Results")
        print("=" * 80)
        
        status_is_no = updated_case_state.eligibility_truth.status == EligibilityStatus.NO
        evidence_is_high = updated_case_state.eligibility_truth.evidence_strength.value == "HIGH"
        check_performed = updated_case_state.eligibility_check.checked == True
        no_coverage_window = (
            updated_case_state.eligibility_truth.coverage_window_start is None and
            updated_case_state.eligibility_truth.coverage_window_end is None
        )
        
        print(f"  ✓ Status is NO: {status_is_no}")
        print(f"  ✓ Evidence Strength is HIGH: {evidence_is_high}")
        print(f"  ✓ Eligibility Check Performed: {check_performed}")
        print(f"  ✓ No Coverage Window Set: {no_coverage_window}")
        
        if status_is_no and evidence_is_high and check_performed and no_coverage_window:
            print("\n✅ All validations passed! Deterministic update correctly handles NO active window.")
            print("   - Status correctly set to NO when no active window found")
            print("   - Coverage window correctly cleared (set to None)")
            print("   - Evidence strength correctly set to HIGH")
        else:
            print("\n⚠️  Some validations failed")
            if not status_is_no:
                print("   - Expected status NO, got:", updated_case_state.eligibility_truth.status)
            if not no_coverage_window:
                print("   - Expected coverage window to be None, got:", 
                      updated_case_state.eligibility_truth.coverage_window_start,
                      "to", updated_case_state.eligibility_truth.coverage_window_end)
        
        # Test that interpreter doesn't overwrite eligibility_truth when eligibility_check.checked is True
        print("\n" + "=" * 80)
        print("Step 4: Test Preservation - User Provides Additional Info")
        print("=" * 80)
        print("Note: The eligibility check will run again (since it's a new turn),")
        print("      but we're testing that the interpreter preserves eligibility_truth")
        print("      when eligibility_check.checked is True")
        
        ui_event_2 = UIEvent(
            event_type="user_message",
            data={"message": "The product type is MEDICARE"},
            timestamp=datetime.now().isoformat()
        )
        
        # Process turn - eligibility check will run again, but interpreter should preserve
        # eligibility_truth if it was already set
        result_2 = await orchestrator.process_turn(
            case_id="test_case_mrn138_no_coverage",
            ui_event=ui_event_2,
            session_id=None,
            patient_id="MRN138"
        )
        
        case_state_2 = result_2.get("case_state", {})
        eligibility_truth_2 = case_state_2.get("eligibility_truth", {})
        health_plan_2 = case_state_2.get("health_plan", {})
        eligibility_check_2 = case_state_2.get("eligibility_check", {})
        
        print("\n📋 After User Input - Case State:")
        print(f"  Eligibility Check Performed: {eligibility_check_2.get('checked')}")
        print(f"  Eligibility Status: {eligibility_truth_2.get('status')}")
        print(f"  Coverage Window: {eligibility_truth_2.get('coverage_window_start')} to {eligibility_truth_2.get('coverage_window_end')}")
        print(f"  Product Type: {health_plan_2.get('product_type')} ⬅️ Should be updated to MEDICARE")
        
        # Note: The eligibility check runs again and finds an active window (simulator always generates one)
        # So the status will be YES, not NO. This is expected behavior.
        # The key test is that the deterministic update correctly handled the NO case in Step 3.
        
        print("\n" + "=" * 80)
        print("Final Validation")
        print("=" * 80)
        print(f"  ✓ Product Type Updated: {health_plan_2.get('product_type') in ['MEDICARE', 'ProductType.MEDICARE']}")
        print(f"  ✓ Eligibility Check Performed: {eligibility_check_2.get('checked')}")
        print("\n  Note: Eligibility status may be YES because the eligibility check runs again")
        print("        and the simulator always generates an active window. The key validation")
        print("        is that Step 3 correctly set NO when there was no active window.")
        
        print("\n" + "=" * 80)
        print("✅ Scenario 3b Test Complete")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n❌ Error during test: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await database.disconnect()
        print("\n🔌 Database disconnected")

if __name__ == "__main__":
    asyncio.run(test_no_active_window())
