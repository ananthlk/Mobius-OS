"""
Test script for Integration Tools
Tests: hie_insurance_query
"""
import sys
import os
import json

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nexus.tools.eligibility.gate1_data_retrieval import HIEInsuranceQuery


def test_hie_insurance_query():
    """Test HIEInsuranceQuery tool"""
    print("\n" + "=" * 80)
    print("Testing: HIEInsuranceQuery")
    print("=" * 80)
    
    try:
        tool = HIEInsuranceQuery()
        
        # Test schema
        schema = tool.define_schema()
        print(f"✅ Schema defined: {schema.name}")
        print(f"   Description: {schema.description[:80]}...")
        
        # Test run
        result = tool.run(
            patient_id="PATIENT_001",
            hie_network_id="HIE_NETWORK_001",
            query_type="insurance"
        )
        
        print(f"✅ HIE Insurance Query executed successfully")
        print(f"   Patient ID: {result.get('patient_id')}")
        print(f"   HIE Network ID: {result.get('hie_network_id')}")
        print(f"   Source: {result.get('source')}")
        
        if result.get('insurance_info'):
            print(f"   Insurance Info:")
            print(json.dumps(result.get('insurance_info'), indent=4))
        
        print(f"\n   Full Result:")
        print(json.dumps(result, indent=2))
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_all_tests():
    """Run all integration tool tests"""
    print("=" * 80)
    print("INTEGRATION TOOLS TEST SUITE")
    print("=" * 80)
    
    tests = [
        test_hie_insurance_query,
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






