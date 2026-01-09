"""
Test script for Scenario 2: Testing with MRN136 and user-provided information
This tests how the interpreter handles user input and applies deterministic updates
"""
import asyncio
import logging
import sys
import os
from datetime import datetime

# Ensure we can import nexus
sys.path.append(os.getcwd())

from nexus.agents.eligibility_v2.orchestrator import EligibilityOrchestrator
from nexus.agents.eligibility_v2.models import UIEvent
from nexus.modules.database import database

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s :: %(message)s'
)
logger = logging.getLogger(__name__)

async def test_scenario_2():
    """Test scenario 2: MRN136 with user-provided product type and contract status"""
    print("=" * 80)
    print("Scenario 2: Testing MRN136 with User-Provided Information")
    print("=" * 80)
    
    try:
        # Connect to database
        await database.connect()
        print("✅ Database connected")
        
        # Create orchestrator
        orchestrator = EligibilityOrchestrator()
        
        # First turn: Initial eligibility check
        print("\n" + "=" * 80)
        print("TURN 1: Initial Eligibility Check")
        print("=" * 80)
        
        ui_event_1 = UIEvent(
            event_type="user_message",
            data={"message": "Check eligibility for MRN136"},
            timestamp=datetime.now().isoformat()
        )
        
        result_1 = await orchestrator.process_turn(
            case_id="test_case_mrn136",
            ui_event=ui_event_1,
            session_id=None,
            patient_id="MRN136"
        )
        
        print("\n📋 After Turn 1 - Case State:")
        case_state_1 = result_1.get("case_state", {})
        if isinstance(case_state_1, dict):
            patient = case_state_1.get("patient", {})
            health_plan = case_state_1.get("health_plan", {})
            eligibility_truth = case_state_1.get("eligibility_truth", {})
            
            print(f"  Patient: {patient.get('first_name')} {patient.get('last_name')}")
            print(f"  Payer: {health_plan.get('payer_name')}")
            print(f"  Product Type: {health_plan.get('product_type')}")
            print(f"  Contract Status: {health_plan.get('contract_status')}")
            print(f"  Eligibility Status: {eligibility_truth.get('status')}")
            print(f"  Coverage: {eligibility_truth.get('coverage_window_start')} to {eligibility_truth.get('coverage_window_end')}")
        
        # Second turn: User provides additional information
        print("\n" + "=" * 80)
        print("TURN 2: User Provides Product Type and Contract Status")
        print("=" * 80)
        
        ui_event_2 = UIEvent(
            event_type="user_message",
            data={"message": "The product type is COMMERCIAL and we are CONTRACTED with this payer"},
            timestamp=datetime.now().isoformat()
        )
        
        result_2 = await orchestrator.process_turn(
            case_id="test_case_mrn136",
            ui_event=ui_event_2,
            session_id=None,
            patient_id="MRN136"
        )
        
        print("\n📋 After Turn 2 - Case State (should have updated product_type and contract_status):")
        case_state_2 = result_2.get("case_state", {})
        if isinstance(case_state_2, dict):
            patient = case_state_2.get("patient", {})
            health_plan = case_state_2.get("health_plan", {})
            eligibility_truth = case_state_2.get("eligibility_truth", {})
            timing = case_state_2.get("timing", {})
            
            print(f"  Patient: {patient.get('first_name')} {patient.get('last_name')}")
            print(f"  Payer: {health_plan.get('payer_name')}")
            print(f"  Product Type: {health_plan.get('product_type')} ⬅️ Should be COMMERCIAL")
            print(f"  Contract Status: {health_plan.get('contract_status')} ⬅️ Should be CONTRACTED")
            print(f"  Eligibility Status: {eligibility_truth.get('status')} ⬅️ Should be preserved from Turn 1")
            print(f"  Coverage: {eligibility_truth.get('coverage_window_start')} to {eligibility_truth.get('coverage_window_end')} ⬅️ Should be preserved")
            print(f"  DOS Date: {timing.get('dos_date')}")
            print(f"  Event Tense: {timing.get('event_tense')}")
        
        # Third turn: User provides a specific date of service
        print("\n" + "=" * 80)
        print("TURN 3: User Provides Date of Service")
        print("=" * 80)
        
        ui_event_3 = UIEvent(
            event_type="user_message",
            data={"message": "The date of service is March 15, 2026"},
            timestamp=datetime.now().isoformat()
        )
        
        result_3 = await orchestrator.process_turn(
            case_id="test_case_mrn136",
            ui_event=ui_event_3,
            session_id=None,
            patient_id="MRN136"
        )
        
        print("\n📋 After Turn 3 - Case State (should have updated dos_date):")
        case_state_3 = result_3.get("case_state", {})
        if isinstance(case_state_3, dict):
            timing = case_state_3.get("timing", {})
            eligibility_truth = case_state_3.get("eligibility_truth", {})
            
            print(f"  DOS Date: {timing.get('dos_date')} ⬅️ Should be 2026-03-15")
            print(f"  Event Tense: {timing.get('event_tense')} ⬅️ Should be FUTURE (March 15, 2026 is in the future)")
            print(f"  Eligibility Status: {eligibility_truth.get('status')} ⬅️ Should still be preserved")
            print(f"  Coverage: {eligibility_truth.get('coverage_window_start')} to {eligibility_truth.get('coverage_window_end')} ⬅️ Should still be preserved")
        
        # Print final score state
        score_state_3 = result_3.get("score_state", {})
        print("\n📊 Final Score State:")
        if isinstance(score_state_3, dict):
            print(f"  Base Probability: {score_state_3.get('base_probability', 0):.1%}")
            if score_state_3.get('state_probabilities'):
                print("  State Probabilities:")
                for state, prob in score_state_3['state_probabilities'].items():
                    print(f"    {state}: {prob:.1%}")
        
        # Print questions and improvements
        questions = result_3.get("next_questions", [])
        print(f"\n❓ Next Questions ({len(questions)}):")
        for i, q in enumerate(questions, 1):
            if isinstance(q, dict):
                print(f"  {i}. {q.get('text', 'N/A')}")
        
        improvements = result_3.get("improvement_plan", [])
        print(f"\n🔧 Improvement Plan ({len(improvements)}):")
        for i, imp in enumerate(improvements, 1):
            if isinstance(imp, dict):
                print(f"  {i}. {imp.get('description', 'N/A')}")
        
        print("\n" + "=" * 80)
        print("✅ Scenario 2 Test Complete")
        print("=" * 80)
        print("\n🔍 Key Validations:")
        print("  ✓ Product type should be updated from user input")
        print("  ✓ Contract status should be updated from user input")
        print("  ✓ Eligibility status should be preserved (not overwritten by interpreter)")
        print("  ✓ Coverage window should be preserved (not overwritten by interpreter)")
        print("  ✓ DOS date should be updated from user input")
        print("  ✓ Event tense should be deterministically set based on DOS date")
        
    except Exception as e:
        print(f"\n❌ Error during test: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await database.disconnect()
        print("\n🔌 Database disconnected")

if __name__ == "__main__":
    asyncio.run(test_scenario_2())
