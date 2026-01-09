"""
Test script to check eligibility for MRN135 using the new deterministic update architecture
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

async def test_eligibility_mrn135():
    """Test eligibility check for MRN135"""
    print("=" * 80)
    print("Testing Eligibility Check for MRN135")
    print("=" * 80)
    
    try:
        # Connect to database
        await database.connect()
        print("✅ Database connected")
        
        # Create orchestrator
        orchestrator = EligibilityOrchestrator()
        
        # Create a UI event for the user message
        ui_event = UIEvent(
            event_type="user_message",
            data={"message": "Check eligibility for MRN135"},
            timestamp=datetime.now().isoformat()
        )
        
        # Process the turn
        print("\n📝 Processing turn...")
        result = await orchestrator.process_turn(
            case_id="test_case_mrn135",
            ui_event=ui_event,
            session_id=None,
            patient_id="MRN135"
        )
        
        print("\n" + "=" * 80)
        print("RESULTS")
        print("=" * 80)
        
        # Print case state summary
        case_state = result.get("case_state", {})
        print("\n📋 Case State Summary:")
        if isinstance(case_state, dict):
            patient = case_state.get("patient", {})
            health_plan = case_state.get("health_plan", {})
            eligibility_truth = case_state.get("eligibility_truth", {})
            timing = case_state.get("timing", {})
            
            print(f"  Patient: {patient.get('first_name')} {patient.get('last_name')}")
            print(f"  DOB: {patient.get('date_of_birth')}")
            print(f"  Member ID: {patient.get('member_id')}")
            print(f"  Payer: {health_plan.get('payer_name')}")
            print(f"  Plan: {health_plan.get('plan_name')}")
            print(f"  Product Type: {health_plan.get('product_type')}")
            print(f"  Eligibility Status: {eligibility_truth.get('status')}")
            print(f"  Coverage Window: {eligibility_truth.get('coverage_window_start')} to {eligibility_truth.get('coverage_window_end')}")
            print(f"  DOS Date: {timing.get('dos_date')}")
            print(f"  Event Tense: {timing.get('event_tense')}")
            print(f"  Eligibility Check Performed: {case_state.get('eligibility_check', {}).get('checked')}")
        
        # Print score state
        score_state = result.get("score_state", {})
        print("\n📊 Score State:")
        if isinstance(score_state, dict):
            print(f"  Base Probability: {score_state.get('base_probability', 0):.1%}")
            if score_state.get('state_probabilities'):
                print("  State Probabilities:")
                for state, prob in score_state['state_probabilities'].items():
                    print(f"    {state}: {prob:.1%}")
            if score_state.get('risk_probabilities'):
                print("  Risk Probabilities:")
                for risk, prob in score_state['risk_probabilities'].items():
                    print(f"    {risk}: {prob:.1%}")
        
        # Print questions
        questions = result.get("next_questions", [])
        print(f"\n❓ Next Questions ({len(questions)}):")
        for i, q in enumerate(questions, 1):
            if isinstance(q, dict):
                print(f"  {i}. {q.get('text', 'N/A')}")
            else:
                print(f"  {i}. {q}")
        
        # Print improvement plan
        improvements = result.get("improvement_plan", [])
        print(f"\n🔧 Improvement Plan ({len(improvements)}):")
        for i, imp in enumerate(improvements, 1):
            if isinstance(imp, dict):
                print(f"  {i}. {imp.get('description', 'N/A')}")
            else:
                print(f"  {i}. {imp}")
        
        # Print presentation summary
        summary = result.get("presentation_summary", "")
        if summary:
            print(f"\n💬 Presentation Summary:")
            print(f"  {summary[:200]}..." if len(summary) > 200 else f"  {summary}")
        
        print("\n" + "=" * 80)
        print("✅ Test Complete")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n❌ Error during test: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await database.disconnect()
        print("\n🔌 Database disconnected")

if __name__ == "__main__":
    asyncio.run(test_eligibility_mrn135())
