"""
Test script for Eligibility Tools
Tests: billing_eligibility_verifier, clinical_eligibility_checker, financial_eligibility_verifier
"""
import sys
import os
import json

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nexus.tools.eligibility.gate2_use_case import (
    BillingEligibilityVerifier,
    ClinicalEligibilityChecker,
    FinancialEligibilityVerifier
)


def test_billing_eligibility_verifier():
    """Test BillingEligibilityVerifier tool"""
    print("\n" + "=" * 80)
    print("Testing: BillingEligibilityVerifier")
    print("=" * 80)
    
    try:
        tool = BillingEligibilityVerifier()
        
        # Test schema
        schema = tool.define_schema()
        print(f"✅ Schema defined: {schema.name}")
        
        # Test run
        result = tool.run(
            member_id="M123456789",
            date_of_birth="1980-01-15",
            service_date="2024-02-15",
            procedure_codes=["99213", "36415"],
            payer_id="87726"
        )
        
        print(f"✅ Billing Eligibility Verifier executed successfully")
        print(f"   Member ID: {result.get('member_id')}")
        print(f"   Eligibility Status: {result.get('eligibility_status')}")
        print(f"   Copay Amount: ${result.get('copay_amount')}")
        print(f"   Deductible Remaining: ${result.get('deductible_remaining')}")
        
        print(f"\n   Full Result:")
        print(json.dumps(result, indent=2))
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_clinical_eligibility_checker():
    """Test ClinicalEligibilityChecker tool"""
    print("\n" + "=" * 80)
    print("Testing: ClinicalEligibilityChecker")
    print("=" * 80)
    
    try:
        tool = ClinicalEligibilityChecker()
        
        # Test schema
        schema = tool.define_schema()
        print(f"✅ Schema defined: {schema.name}")
        
        # Test run
        result = tool.run(
            member_id="M123456789",
            date_of_birth="1980-01-15",
            service_type="preventive",
            clinical_indication="Annual Wellness Visit",
            payer_id="87726"
        )
        
        print(f"✅ Clinical Eligibility Checker executed successfully")
        print(f"   Member ID: {result.get('member_id')}")
        print(f"   Service Type: {result.get('service_type')}")
        print(f"   Coverage Status: {result.get('coverage_status')}")
        
        print(f"\n   Full Result:")
        print(json.dumps(result, indent=2))
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_financial_eligibility_verifier():
    """Test FinancialEligibilityVerifier tool"""
    print("\n" + "=" * 80)
    print("Testing: FinancialEligibilityVerifier")
    print("=" * 80)
    
    try:
        tool = FinancialEligibilityVerifier()
        
        # Test schema
        schema = tool.define_schema()
        print(f"✅ Schema defined: {schema.name}")
        
        # Test run
        result = tool.run(
            member_id="M123456789",
            date_of_birth="1980-01-15",
            service_date="2024-02-15",
            payer_id="87726"
        )
        
        print(f"✅ Financial Eligibility Verifier executed successfully")
        print(f"   Member ID: {result.get('member_id')}")
        print(f"   Eligibility Status: {result.get('eligibility_status')}")
        print(f"   Use Case: {result.get('use_case')}")
        
        print(f"\n   Full Result:")
        print(json.dumps(result, indent=2))
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_all_tests():
    """Run all eligibility tool tests"""
    print("=" * 80)
    print("ELIGIBILITY TOOLS TEST SUITE")
    print("=" * 80)
    
    tests = [
        test_billing_eligibility_verifier,
        test_clinical_eligibility_checker,
        test_financial_eligibility_verifier,
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



