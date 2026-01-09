#!/usr/bin/env python3
"""
Test Historical Insurance Lookup Tool
Tests the tool and shows input/output.
"""
import sys
import os
import json

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from nexus.tools.eligibility.gate1_data_retrieval import HistoricalInsuranceLookup

def test_tool():
    """Test the HistoricalInsuranceLookup tool"""
    print("\n" + "=" * 90)
    print("🧪 TESTING: historical_insurance_lookup")
    print("=" * 90)
    print()
    
    try:
        # Instantiate tool
        tool = HistoricalInsuranceLookup()
        schema = tool.define_schema()
        
        print(f"✅ Tool loaded: {schema.name}")
        print(f"   Description: {schema.description}")
        print()
        
        # Check implementation
        import inspect
        run_source = inspect.getsource(tool.run)
        fetch_source = inspect.getsource(tool._fetch_from_api)
        
        # Analyze implementation
        uses_api = 'httpx' in fetch_source and 'api/user-profiles' in fetch_source
        uses_mock = 'mock' in run_source.lower() or 'mock' in fetch_source.lower()
        has_api_fallback = 'raise ValueError' in run_source and 'API unavailable' in run_source
        has_comment = 'For now, return current coverage' in fetch_source or 'real system' in fetch_source.lower()
        
        print("📋 Implementation Analysis:")
        print(f"   Uses httpx: {'httpx' in fetch_source}")
        print(f"   Uses API endpoint: {'api/user-profiles' in fetch_source}")
        print(f"   Has mock fallback: {uses_mock}")
        print(f"   Raises error on API failure: {has_api_fallback}")
        if has_comment:
            print(f"   ⚠️  Has comment indicating partial implementation")
        print()
        
        # Determine status
        if uses_api and not uses_mock and has_api_fallback and not has_comment:
            status = "REAL"
        elif uses_api and has_comment:
            status = "PARTIAL"
            print(f"⚠️  Status: {status}")
            print("   Tool uses API but has comments indicating partial/limited implementation")
        elif uses_mock:
            status = "STUB"
        else:
            status = "PARTIAL"
        
        if status == "REAL":
            print(f"✅ Status: {status}")
        elif status == "PARTIAL":
            print(f"⚠️  Status: {status}")
        else:
            print(f"❌ Status: {status}")
        
        print()
        print("=" * 90)
        print("🧪 TEST EXECUTION")
        print("=" * 90)
        print()
        
        # Test inputs
        test_inputs = {
            "patient_id": "PATIENT_001",
            "lookback_days": 365
        }
        
        print("📥 INPUT PROVIDED:")
        print(json.dumps(test_inputs, indent=2))
        print()
        
        # Try to actually test with API
        try:
            print("🔄 Executing tool...")
            result = tool.run(**test_inputs)
            
            print("✅ Tool executed successfully!")
            print()
            print("📤 OUTPUT OBTAINED:")
            print(json.dumps(result, indent=2))
            print()
            
            # Analyze output structure
            print("📊 OUTPUT ANALYSIS:")
            if isinstance(result, list):
                print(f"   Type: List with {len(result)} items")
                if result:
                    print(f"   First item keys: {list(result[0].keys())}")
            elif isinstance(result, dict):
                print(f"   Type: Dict")
                print(f"   Keys: {list(result.keys())}")
            print()
            
            if status == "PARTIAL":
                print("⚠️  NOTE: Tool uses API but returns current coverage as historical record")
                print("   (In a real system, this would query actual historical records)")
            
            print("✅ CONFIRMED: Tool executed and returned data")
            
        except ValueError as e:
            print(f"⚠️  API test failed (expected if patient doesn't exist or API not running)")
            print(f"   Error: {str(e)}")
            print()
            print("📝 This is expected behavior - tool raises errors when API fails")
            print("   (No mock fallback = REAL implementation)")
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            import traceback
            traceback.print_exc()
        
        print()
        print("=" * 90)
        print("📝 RECOMMENDATION:")
        print("=" * 90)
        print(f"   Mark tool as: {status}")
        print(f"   Implementation: Uses /api/user-profiles/{{patient_id}}/health-plan endpoint")
        if status == "PARTIAL":
            print(f"   Note: Returns current coverage as historical (partial implementation)")
        print()
        
        return {
            "status": status,
            "test_inputs": test_inputs,
            "test_result": "success" if 'result' in locals() else "api_not_available"
        }
        
    except Exception as e:
        print(f"❌ Error testing tool: {e}")
        import traceback
        traceback.print_exc()
        return {"status": "ERROR", "error": str(e)}

if __name__ == "__main__":
    result = test_tool()
    print("\n" + "=" * 90)
    print("TEST SUMMARY")
    print("=" * 90)
    print(json.dumps(result, indent=2))






