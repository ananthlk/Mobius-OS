"""
Test script for Data Retrieval Tools
Tests: patient_demographics_retriever, insurance_info_retriever, historical_insurance_lookup
"""
import sys
import os
import json

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nexus.tools.eligibility.gate1_data_retrieval import (
    PatientDemographicsRetriever,
    InsuranceInfoRetriever,
    HistoricalInsuranceLookup
)


def test_patient_demographics_retriever():
    """Test PatientDemographicsRetriever tool"""
    print("\n" + "=" * 80)
    print("Testing: PatientDemographicsRetriever")
    print("=" * 80)
    
    try:
        tool = PatientDemographicsRetriever()
        
        # Test schema
        schema = tool.define_schema()
        print(f"✅ Schema defined: {schema.name}")
        
        # Test run
        result = tool.run(
            patient_id="PATIENT_001",
            appointment_id="APPT_12345"
        )
        
        print(f"✅ Patient Demographics Retriever executed successfully")
        print(f"   Patient ID: {result.get('patient_id')}")
        print(f"   Name: {result.get('name')}")
        print(f"   DOB: {result.get('date_of_birth')}")
        
        print(f"\n   Full Result:")
        print(json.dumps(result, indent=2))
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_insurance_info_retriever():
    """Test InsuranceInfoRetriever tool"""
    print("\n" + "=" * 80)
    print("Testing: InsuranceInfoRetriever")
    print("=" * 80)
    
    try:
        tool = InsuranceInfoRetriever()
        
        # Test schema
        schema = tool.define_schema()
        print(f"✅ Schema defined: {schema.name}")
        
        # Test run
        result = tool.run(patient_id="PATIENT_001")
        
        print(f"✅ Insurance Info Retriever executed successfully")
        print(f"   Patient ID: {result.get('patient_id')}")
        print(f"   Payer Name: {result.get('payer_name')}")
        print(f"   Member ID: {result.get('member_id')}")
        print(f"   Effective Date: {result.get('effective_date')}")
        
        print(f"\n   Full Result:")
        print(json.dumps(result, indent=2))
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_historical_insurance_lookup():
    """Test HistoricalInsuranceLookup tool"""
    print("\n" + "=" * 80)
    print("Testing: HistoricalInsuranceLookup")
    print("=" * 80)
    
    try:
        tool = HistoricalInsuranceLookup()
        
        # Test schema
        schema = tool.define_schema()
        print(f"✅ Schema defined: {schema.name}")
        
        # Test run
        result = tool.run(
            patient_id="PATIENT_001",
            lookback_days=365
        )
        
        print(f"✅ Historical Insurance Lookup executed successfully")
        print(f"   Records found: {len(result)}")
        
        if result:
            print(f"   Sample Record:")
            print(json.dumps(result[0], indent=2))
        
        print(f"\n   Full Result:")
        print(json.dumps(result, indent=2))
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_all_tests():
    """Run all data retrieval tool tests"""
    print("=" * 80)
    print("DATA RETRIEVAL TOOLS TEST SUITE")
    print("=" * 80)
    
    tests = [
        test_patient_demographics_retriever,
        test_insurance_info_retriever,
        test_historical_insurance_lookup,
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






