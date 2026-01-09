"""
Test script to run all failure scenarios and verify deterministic behavior
"""
import asyncio
import logging
import sys
import os
from datetime import datetime
import json

sys.path.append(os.getcwd())

from nexus.agents.eligibility_v2.orchestrator import EligibilityOrchestrator
from nexus.agents.eligibility_v2.models import UIEvent, EligibilityStatus
from nexus.modules.database import database
from nexus.tools.eligibility.test_scenarios import list_test_scenarios

# Configure logging - reduce noise for cleaner output
logging.basicConfig(
    level=logging.WARNING,
    format='%(asctime)s [%(levelname)s] %(name)s :: %(message)s'
)
logger = logging.getLogger(__name__)

async def test_scenario(mrn: str, description: str, expected_status: str = None):
    """Test a single scenario and return results"""
    orchestrator = EligibilityOrchestrator()
    
    ui_event = UIEvent(
        event_type="user_message",
        data={"message": f"Check eligibility for {mrn}"},
        timestamp=datetime.now().isoformat()
    )
    
    try:
        result = await orchestrator.process_turn(
            case_id=f"test_{mrn.lower()}",
            ui_event=ui_event,
            session_id=None,
            patient_id=mrn
        )
        
        case_state = result.get("case_state", {})
        eligibility_truth = case_state.get("eligibility_truth", {})
        patient = case_state.get("patient", {})
        health_plan = case_state.get("health_plan", {})
        timing = case_state.get("timing", {})
        eligibility_check = case_state.get("eligibility_check", {})
        
        status = eligibility_truth.get("status")
        status_str = str(status) if status else "None"
        
        has_demographics = patient is not None and patient.get("first_name") is not None
        has_insurance = health_plan is not None and health_plan.get("payer_name") is not None
        has_visits = len(timing.get("related_visits", [])) > 0
        has_coverage_window = (
            eligibility_truth.get("coverage_window_start") is not None and
            eligibility_truth.get("coverage_window_end") is not None
        )
        check_performed = eligibility_check.get("checked", False)
        
        # Build result
        scenario_result = {
            "mrn": mrn,
            "description": description,
            "status": status_str,
            "has_demographics": has_demographics,
            "has_insurance": has_insurance,
            "has_visits": has_visits,
            "has_coverage_window": has_coverage_window,
            "check_performed": check_performed,
            "patient_name": f"{patient.get('first_name', '')} {patient.get('last_name', '')}".strip() if patient else "N/A",
            "payer": health_plan.get("payer_name") if health_plan else "N/A",
            "coverage_start": eligibility_truth.get("coverage_window_start"),
            "coverage_end": eligibility_truth.get("coverage_window_end"),
            "expected_status": expected_status
        }
        
        return scenario_result
    except Exception as e:
        logger.error(f"Error testing {mrn}: {e}", exc_info=True)
        return {
            "mrn": mrn,
            "description": description,
            "error": str(e),
            "status": "ERROR"
        }

async def test_determinism(mrn: str, iterations: int = 3):
    """Test that the same MRN returns the same data across multiple calls"""
    print(f"\n{'='*80}")
    print(f"Testing Determinism for {mrn} ({iterations} iterations)")
    print(f"{'='*80}")
    
    results = []
    for i in range(iterations):
        result = await test_scenario(mrn, f"Iteration {i+1}")
        results.append(result)
        await asyncio.sleep(0.1)  # Small delay between calls
    
    # Check if all results are identical
    first_result = results[0]
    all_same = all(
        r.get("status") == first_result.get("status") and
        r.get("patient_name") == first_result.get("patient_name") and
        r.get("payer") == first_result.get("payer") and
        r.get("has_demographics") == first_result.get("has_demographics") and
        r.get("has_insurance") == first_result.get("has_insurance") and
        r.get("has_visits") == first_result.get("has_visits")
        for r in results
    )
    
    print(f"\nResults:")
    for i, r in enumerate(results, 1):
        print(f"  Iteration {i}:")
        print(f"    Status: {r.get('status')}")
        print(f"    Patient: {r.get('patient_name')}")
        print(f"    Payer: {r.get('payer')}")
        print(f"    Has Demographics: {r.get('has_demographics')}")
        print(f"    Has Insurance: {r.get('has_insurance')}")
        print(f"    Has Visits: {r.get('has_visits')}")
    
    print(f"\n✓ Deterministic: {all_same}")
    if not all_same:
        print("  ⚠️  WARNING: Results are not identical across iterations!")
    
    return all_same

async def main():
    """Run all test scenarios"""
    await database.connect()
    
    # Get all test scenarios
    scenarios = list_test_scenarios()
    
    # Define expected results for each scenario type
    expected_results = {
        "NO_ACTIVE_WINDOW": "EligibilityStatus.NO",
        "EXPIRED": "EligibilityStatus.NO",
        "FUTURE": "EligibilityStatus.NO",
        "ACTIVE": "EligibilityStatus.YES"
    }
    
    print("=" * 80)
    print("Testing All Failure Scenarios")
    print("=" * 80)
    print(f"\nTotal test scenarios: {len(scenarios)}")
    
    # Test each scenario
    results = []
    for mrn, config in sorted(scenarios.items()):
        desc_parts = []
        if config.get("eligibility_result") != "ACTIVE":
            desc_parts.append(config.get("eligibility_result", "ACTIVE"))
        if config.get("demographics") != "FULL":
            desc_parts.append(f"demographics={config.get('demographics')}")
        if config.get("insurance") != "FULL":
            desc_parts.append(f"insurance={config.get('insurance')}")
        if config.get("visits") != "FULL":
            desc_parts.append(f"visits={config.get('visits')}")
        
        description = ", ".join(desc_parts) if desc_parts else "Normal case"
        expected_status = expected_results.get(config.get("eligibility_result", "ACTIVE"))
        
        result = await test_scenario(mrn, description, expected_status)
        results.append(result)
    
    # Print summary
    print("\n" + "=" * 80)
    print("Test Results Summary")
    print("=" * 80)
    
    for r in results:
        status_icon = "✅" if r.get("status") == r.get("expected_status") else "❌"
        print(f"\n{status_icon} {r['mrn']}: {r['description']}")
        print(f"   Status: {r.get('status')} (expected: {r.get('expected_status')})")
        print(f"   Demographics: {'✓' if r.get('has_demographics') else '✗'}")
        print(f"   Insurance: {'✓' if r.get('has_insurance') else '✗'}")
        print(f"   Visits: {'✓' if r.get('has_visits') else '✗'}")
        print(f"   Coverage Window: {'✓' if r.get('has_coverage_window') else '✗'}")
        if r.get('error'):
            print(f"   ERROR: {r.get('error')}")
    
    # Statistics
    print("\n" + "=" * 80)
    print("Statistics")
    print("=" * 80)
    print(f"Total scenarios tested: {len(results)}")
    print(f"Scenarios with NO status: {sum(1 for r in results if 'NO' in str(r.get('status', '')))}")
    print(f"Scenarios with missing demographics: {sum(1 for r in results if not r.get('has_demographics'))}")
    print(f"Scenarios with missing insurance: {sum(1 for r in results if not r.get('has_insurance'))}")
    print(f"Scenarios with no visits: {sum(1 for r in results if not r.get('has_visits'))}")
    print(f"Scenarios with no coverage window: {sum(1 for r in results if not r.get('has_coverage_window'))}")
    print(f"Scenarios with errors: {sum(1 for r in results if r.get('error'))}")
    
    # Test determinism for a few key scenarios
    print("\n" + "=" * 80)
    print("Testing Determinism (Same MRN = Same Data)")
    print("=" * 80)
    
    test_mrns = ["MRN200", "MRN204", "MRN207", "MRN210"]
    determinism_results = []
    for mrn in test_mrns:
        is_deterministic = await test_determinism(mrn, iterations=3)
        determinism_results.append((mrn, is_deterministic))
    
    print("\n" + "=" * 80)
    print("Determinism Test Results")
    print("=" * 80)
    for mrn, is_det in determinism_results:
        status = "✅ PASS" if is_det else "❌ FAIL"
        print(f"  {status}: {mrn}")
    
    all_deterministic = all(is_det for _, is_det in determinism_results)
    print(f"\n{'✅ All determinism tests passed!' if all_deterministic else '⚠️  Some determinism tests failed'}")
    
    print("\n" + "=" * 80)
    print("✅ All Tests Complete")
    print("=" * 80)
    
    await database.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
