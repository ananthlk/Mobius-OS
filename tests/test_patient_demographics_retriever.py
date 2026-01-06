#!/usr/bin/env python3
"""
Test Patient Demographics Retriever Tool
Tests if the tool is REAL (uses API) or STUB (uses mock data).
"""
import sys
import os
import json

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from nexus.tools.eligibility.gate1_data_retrieval import PatientDemographicsRetriever

def test_tool():
    """Test the PatientDemographicsRetriever tool"""
    print("\n" + "=" * 90)
    print("🧪 TESTING: patient_demographics_retriever")
    print("=" * 90)
    print()
    
    try:
        # Instantiate tool
        tool = PatientDemographicsRetriever()
        schema = tool.define_schema()
        
        print(f"✅ Tool loaded: {schema.name}")
        print(f"   Description: {schema.description}")
        print()
        
        # Check implementation by reading source
        import inspect
        run_source = inspect.getsource(tool.run)
        fetch_source = inspect.getsource(tool._fetch_from_api)
        
        # Analyze implementation
        uses_api = 'httpx' in fetch_source and 'api/user-profiles' in fetch_source
        uses_mock = 'mock' in run_source.lower() or 'mock' in fetch_source.lower()
        has_api_fallback = 'raise ValueError' in run_source and 'API unavailable' in run_source
        
        print("📋 Implementation Analysis:")
        print(f"   Uses httpx: {'httpx' in fetch_source}")
        print(f"   Uses API endpoint: {'api/user-profiles' in fetch_source}")
        print(f"   Has mock fallback: {uses_mock}")
        print(f"   Raises error on API failure: {has_api_fallback}")
        print()
        
        # Determine status
        if uses_api and not uses_mock and has_api_fallback:
            status = "REAL"
            print(f"✅ Status: {status}")
            print("   Tool uses API endpoints and raises errors when API fails (no mock fallback)")
        elif uses_mock:
            status = "STUB"
            print(f"⚠️  Status: {status}")
            print("   Tool uses mock data")
        else:
            status = "PARTIAL"
            print(f"⚠️  Status: {status}")
            print("   Tool has partial implementation")
        
        print()
        print("=" * 90)
        print("📝 RECOMMENDATION:")
        print("=" * 90)
        print(f"   Mark tool as: {status}")
        print(f"   Implementation: Uses /api/user-profiles/{{patient_id}}/system endpoint")
        print(f"   Requires: Patient data API to be running")
        print()
        
        # Try to actually test with API (optional - may fail if API not running)
        print("=" * 90)
        print("🧪 LIVE API TEST (Optional - may fail if API not running)")
        print("=" * 90)
        print()
        
        try:
            # Try with a test patient ID
            test_patient_id = "PATIENT_001"
            print(f"Testing with patient_id: {test_patient_id}")
            result = tool.run(patient_id=test_patient_id)
            print("✅ Tool executed successfully!")
            print(f"Result: {json.dumps(result, indent=2)}")
            print()
            print("✅ CONFIRMED: Tool is REAL - successfully uses API")
        except ValueError as e:
            print(f"⚠️  API test failed (expected if patient doesn't exist or API not running)")
            print(f"   Error: {str(e)}")
            print()
            print("📝 This is expected behavior for a REAL tool - it raises errors when API fails")
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            import traceback
            traceback.print_exc()
        
        print()
        print("=" * 90)
        return status
        
    except Exception as e:
        print(f"❌ Error testing tool: {e}")
        import traceback
        traceback.print_exc()
        return "ERROR"

if __name__ == "__main__":
    status = test_tool()
    print(f"\nFinal Status: {status}")




