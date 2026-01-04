"""
Test script for Financial Tools
Tests: copay_deductible_calculator
"""
import sys
import os
import json

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nexus.tools.eligibility.gate2_use_case import CopayDeductibleCalculator


def test_copay_deductible_calculator():
    """Test CopayDeductibleCalculator tool"""
    print("\n" + "=" * 80)
    print("Testing: CopayDeductibleCalculator")
    print("=" * 80)
    
    try:
        tool = CopayDeductibleCalculator()
        
        # Test schema
        schema = tool.define_schema()
        print(f"✅ Schema defined: {schema.name}")
        print(f"   Description: {schema.description}")
        
        # Test run
        result = tool.run(
            member_id="M123456789",
            service_type="office_visit",
            procedure_code="99213",
            payer_id="87726"
        )
        
        print(f"✅ Copay Deductible Calculator executed successfully")
        print(f"   Member ID: {result.get('member_id')}")
        print(f"   Procedure Code: {result.get('procedure_code')}")
        print(f"   Copay Amount: ${result.get('copay_amount')}")
        print(f"   Deductible Amount: ${result.get('deductible_amount')}")
        print(f"   Remaining Deductible: ${result.get('remaining_deductible')}")
        print(f"   Coinsurance Percentage: {result.get('coinsurance_percentage')}")
        print(f"   Out of Pocket Max: ${result.get('out_of_pocket_max')}")
        
        print(f"\n   Full Result:")
        print(json.dumps(result, indent=2))
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_all_tests():
    """Run all financial tool tests"""
    print("=" * 80)
    print("FINANCIAL TOOLS TEST SUITE")
    print("=" * 80)
    
    tests = [
        test_copay_deductible_calculator,
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

