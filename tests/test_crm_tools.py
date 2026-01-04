"""
Test script for CRM Tools
Tests: schedule_scanner, risk_calculator
"""
import sys
import os
import json

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nexus.tools.crm.schedule_scanner import ScheduleScannerTool
from nexus.tools.crm.risk_calculator import RiskCalculatorTool


def test_schedule_scanner():
    """Test ScheduleScannerTool"""
    print("\n" + "=" * 80)
    print("Testing: ScheduleScannerTool")
    print("=" * 80)
    
    try:
        tool = ScheduleScannerTool()
        
        # Test schema
        schema = tool.define_schema()
        print(f"✅ Schema defined: {schema.name}")
        print(f"   Description: {schema.description}")
        
        # Test run
        result = tool.run(days_out=14)
        
        print(f"✅ Schedule Scanner executed successfully")
        print(f"   Appointments found: {len(result)}")
        
        if result:
            print(f"\n   Sample Appointment:")
            print(json.dumps(result[0], indent=2))
        
        print(f"\n   All Appointments:")
        print(json.dumps(result, indent=2))
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_risk_calculator():
    """Test RiskCalculatorTool"""
    print("\n" + "=" * 80)
    print("Testing: RiskCalculatorTool")
    print("=" * 80)
    
    try:
        tool = RiskCalculatorTool()
        
        # Test schema
        schema = tool.define_schema()
        print(f"✅ Schema defined: {schema.name}")
        
        # Test run with sample appointments
        sample_appointments = [
            {
                "id": "appt_101",
                "patient_name": "John Doe",
                "time": "2024-02-15 09:00",
                "type": "New Patient",
                "insurance_status": "Unknown"
            },
            {
                "id": "appt_102",
                "patient_name": "Jane Smith",
                "time": "2024-02-15 10:30",
                "type": "Follow Up",
                "insurance_status": "Verified"
            },
            {
                "id": "appt_103",
                "patient_name": "Robert Brown",
                "time": "2024-02-15 14:00",
                "type": "Procedure",
                "insurance_status": "Pending Auth"
            }
        ]
        
        result = tool.run(appointments=sample_appointments)
        
        print(f"✅ Risk Calculator executed successfully")
        print(f"   Total Appointments: {result.get('summary', {}).get('total_appointments')}")
        print(f"   High Risk Count: {result.get('summary', {}).get('high_risk_count')}")
        print(f"   Overall Health Score: {result.get('summary', {}).get('overall_health_score')}")
        
        print(f"\n   Summary:")
        print(json.dumps(result.get('summary', {}), indent=2))
        
        print(f"\n   Analyzed Appointments:")
        for appt in result.get('appointments', [])[:2]:  # Show first 2
            print(f"   - {appt.get('patient_name')}: No-Show Risk={appt.get('risk_scores', {}).get('no_show')}, Denial Risk={appt.get('risk_scores', {}).get('denial')}")
        
        print(f"\n   Full Result:")
        print(json.dumps(result, indent=2))
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_all_tests():
    """Run all CRM tool tests"""
    print("=" * 80)
    print("CRM TOOLS TEST SUITE")
    print("=" * 80)
    
    tests = [
        test_schedule_scanner,
        test_risk_calculator,
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"❌ Test {test.__name__} crashed: {e}")
            results.append(False)
    
    print("\n" + "=" * 80)
    passed = sum(results)
    total = len(results)
    print(f"Results: {passed}/{total} tests passed")
    print("=" * 80)
    
    return 0 if passed == total else 1


if __name__ == "__main__":
    exit_code = run_all_tests()
    sys.exit(exit_code)

