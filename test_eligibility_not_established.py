"""
Test script for Scenario 3: Testing when eligibility is NOT established
This tests how the deterministic update handles cases with NO eligibility status
"""
import asyncio
import logging
import sys
import os
from datetime import datetime

# Ensure we can import nexus
sys.path.append(os.getcwd())

from nexus.agents.eligibility_v2.orchestrator import EligibilityOrchestrator
from nexus.agents.eligibility_v2.models import UIEvent, EligibilityStatus
from nexus.modules.database import database

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s :: %(message)s'
)
logger = logging.getLogger(__name__)

async def test_not_established():
    """Test scenario where eligibility is NOT established"""
    print("=" * 80)
    print("Scenario 3: Testing When Eligibility is NOT Established")
    print("=" * 80)
    
    try:
        # Connect to database
        await database.connect()
        print("✅ Database connected")
        
        # Create orchestrator
        orchestrator = EligibilityOrchestrator()
        
        # Test with MRN137 (or another MRN that might not have active coverage)
        # The eligibility tool simulator should handle this
        print("\n" + "=" * 80)
        print("Testing MRN137 - Checking if eligibility is established")
        print("=" * 80)
        
        ui_event = UIEvent(
            event_type="user_message",
            data={"message": "Check eligibility for MRN137"},
            timestamp=datetime.now().isoformat()
        )
        
        result = await orchestrator.process_turn(
            case_id="test_case_mrn137_not_established",
            ui_event=ui_event,
            session_id=None,
            patient_id="MRN137"
        )
        
        print("\n📋 Case State After Eligibility Check:")
        case_state = result.get("case_state", {})
        if isinstance(case_state, dict):
            patient = case_state.get("patient", {})
            health_plan = case_state.get("health_plan", {})
            eligibility_truth = case_state.get("eligibility_truth", {})
            eligibility_check = case_state.get("eligibility_check", {})
            timing = case_state.get("timing", {})
            
            print(f"  Patient: {patient.get('first_name')} {patient.get('last_name')}")
            print(f"  Member ID: {patient.get('member_id')}")
            print(f"  Payer: {health_plan.get('payer_name')}")
            print(f"  Plan: {health_plan.get('plan_name')}")
            print(f"  Product Type: {health_plan.get('product_type')}")
            print(f"\n  Eligibility Check Performed: {eligibility_check.get('checked')}")
            print(f"  Eligibility Status: {eligibility_truth.get('status')}")
            print(f"  Evidence Strength: {eligibility_truth.get('evidence_strength')}")
            print(f"  Coverage Window Start: {eligibility_truth.get('coverage_window_start')}")
            print(f"  Coverage Window End: {eligibility_truth.get('coverage_window_end')}")
            print(f"\n  DOS Date: {timing.get('dos_date')}")
            print(f"  Event Tense: {timing.get('event_tense')}")
        
        # Check the eligibility status
        eligibility_status = case_state.get("eligibility_truth", {}).get("status")
        is_established = eligibility_status in [EligibilityStatus.YES, EligibilityStatus.NO]
        is_not_established = eligibility_status == EligibilityStatus.NOT_ESTABLISHED
        
        print("\n" + "=" * 80)
        print("Eligibility Status Analysis")
        print("=" * 80)
        
        if eligibility_status == EligibilityStatus.YES:
            print("✅ Eligibility Status: YES (Active coverage found)")
            print("   This means the patient has active coverage.")
        elif eligibility_status == EligibilityStatus.NO:
            print("❌ Eligibility Status: NO (No active coverage)")
            print("   This means the patient does NOT have active coverage.")
        elif eligibility_status == EligibilityStatus.NOT_ESTABLISHED:
            print("⚠️  Eligibility Status: NOT_ESTABLISHED")
            print("   This means eligibility could not be determined.")
        elif eligibility_status == EligibilityStatus.UNKNOWN:
            print("❓ Eligibility Status: UNKNOWN")
            print("   This means eligibility status is unknown.")
        else:
            print(f"❓ Eligibility Status: {eligibility_status}")
        
        # Print score state
        score_state = result.get("score_state", {})
        print("\n📊 Score State:")
        if isinstance(score_state, dict):
            base_prob = score_state.get('base_probability', 0)
            print(f"  Base Probability: {base_prob:.1%}")
            
            if score_state.get('base_probability_source'):
                print(f"  Base Probability Source: {score_state.get('base_probability_source')}")
                if score_state.get('base_probability_source') == 'direct_evidence':
                    print("    → Using direct evidence from 270 transaction")
                else:
                    print("    → Using historical propensity fallback")
            
            if score_state.get('state_probabilities'):
                print("  State Probabilities:")
                for state, prob in score_state['state_probabilities'].items():
                    print(f"    {state}: {prob:.1%}")
            
            if score_state.get('risk_probabilities'):
                print("  Risk Probabilities:")
                for risk, prob in score_state['risk_probabilities'].items():
                    if prob > 0:
                        print(f"    {risk}: {prob:.1%}")
        
        # Print questions and improvements
        questions = result.get("next_questions", [])
        print(f"\n❓ Next Questions ({len(questions)}):")
        for i, q in enumerate(questions, 1):
            if isinstance(q, dict):
                print(f"  {i}. {q.get('text', 'N/A')}")
        
        improvements = result.get("improvement_plan", [])
        print(f"\n🔧 Improvement Plan ({len(improvements)}):")
        for i, imp in enumerate(improvements, 1):
            if isinstance(imp, dict):
                print(f"  {i}. {imp.get('description', 'N/A')}")
        
        # Test preservation: Try to update with user input
        print("\n" + "=" * 80)
        print("Testing Preservation: User Provides Additional Info")
        print("=" * 80)
        
        ui_event_2 = UIEvent(
            event_type="user_message",
            data={"message": "The date of service is January 10, 2025"},
            timestamp=datetime.now().isoformat()
        )
        
        result_2 = await orchestrator.process_turn(
            case_id="test_case_mrn137_not_established",
            ui_event=ui_event_2,
            session_id=None,
            patient_id="MRN137"
        )
        
        case_state_2 = result_2.get("case_state", {})
        eligibility_truth_2 = case_state_2.get("eligibility_truth", {})
        timing_2 = case_state_2.get("timing", {})
        
        print("\n📋 After User Input - Case State:")
        print(f"  Eligibility Status: {eligibility_truth_2.get('status')} ⬅️ Should be preserved")
        print(f"  Coverage Window: {eligibility_truth_2.get('coverage_window_start')} to {eligibility_truth_2.get('coverage_window_end')} ⬅️ Should be preserved")
        print(f"  DOS Date: {timing_2.get('dos_date')} ⬅️ Should be updated to 2025-01-10")
        print(f"  Event Tense: {timing_2.get('event_tense')} ⬅️ Should be PAST (Jan 10, 2025 is in the past)")
        
        # Validation
        print("\n" + "=" * 80)
        print("Validation Results")
        print("=" * 80)
        
        preserved_status = eligibility_truth_2.get('status') == eligibility_truth.get('status')
        preserved_coverage = (
            eligibility_truth_2.get('coverage_window_start') == eligibility_truth.get('coverage_window_start') and
            eligibility_truth_2.get('coverage_window_end') == eligibility_truth.get('coverage_window_end')
        )
        dos_updated = timing_2.get('dos_date') == '2025-01-10' or str(timing_2.get('dos_date')) == '2025-01-10'
        
        print(f"  ✓ Eligibility Status Preserved: {preserved_status}")
        print(f"  ✓ Coverage Window Preserved: {preserved_coverage}")
        print(f"  ✓ DOS Date Updated: {dos_updated}")
        
        if preserved_status and preserved_coverage and dos_updated:
            print("\n✅ All validations passed!")
        else:
            print("\n⚠️  Some validations failed")
        
        print("\n" + "=" * 80)
        print("✅ Scenario 3 Test Complete")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n❌ Error during test: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await database.disconnect()
        print("\n🔌 Database disconnected")

if __name__ == "__main__":
    asyncio.run(test_not_established())
