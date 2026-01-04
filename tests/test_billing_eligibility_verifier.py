#!/usr/bin/env python3
"""
Test Billing Eligibility Verifier Tool
Tests the tool and shows input/output.
"""
import sys
import os
import json

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from nexus.tools.eligibility.gate2_use_case import BillingEligibilityVerifier

def test_tool():
    """Test the BillingEligibilityVerifier tool"""
    print("\n" + "=" * 90)
    print("🧪 TESTING: billing_eligibility_verifier")
    print("=" * 90)
    print()
    
    try:
        # Instantiate tool
        tool = BillingEligibilityVerifier()
        schema = tool.define_schema()
        
        print(f"✅ Tool loaded: {schema.name}")
        print(f"   Description: {schema.description}")
        print()
        
        # Check implementation
        import inspect
        run_source = inspect.getsource(tool.run)
        
        # Analyze implementation
        uses_api = 'httpx' in run_source or 'api/user-profiles' in run_source or 'user_profile' in run_source
        uses_mock = 'Mock implementation' in run_source or '# Mock' in run_source or 'mock' in run_source.lower()
        returns_dict = 'return {' in run_source
        
        print("📋 Implementation Analysis:")
        print(f"   Uses API: {uses_api}")
        print(f"   Uses Mock: {uses_mock}")
        print(f"   Returns hardcoded dict: {returns_dict}")
        print()
        
        # Determine status
        if uses_mock or (not uses_api and returns_dict):
            status = "STUB"
            print(f"❌ Status: {status}")
            print("   Tool uses mock/hardcoded data")
        elif uses_api:
            status = "REAL"
            print(f"✅ Status: {status}")
            print("   Tool uses API endpoints")
        else:
            status = "UNKNOWN"
        
        print()
        print("=" * 90)
        print("🧪 TEST EXECUTION")
        print("=" * 90)
        print()
        
        # Test inputs - check what parameters this tool expects
        test_inputs = {
            "member_id": "MEMBER_001",
            "date_of_birth": "1980-01-15",
            "service_date": "2024-01-15",
            "procedure_codes": ["99213", "D0150"],
            "payer_id": "PAYER_001"
        }
        
        print("📥 INPUT PROVIDED:")
        print(json.dumps(test_inputs, indent=2))
        print()
        
        # Execute tool
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
            if isinstance(result, dict):
                print(f"   Type: Dict")
                print(f"   Keys: {list(result.keys())}")
                if 'patient_id' in result:
                    print(f"   ✅ Patient ID: {result.get('patient_id')}")
                if 'eligible' in result or 'status' in result:
                    eligible = result.get('eligible', result.get('status', 'N/A'))
                    print(f"   ✅ Eligible: {eligible}")
            print()
            
            if status == "STUB":
                print("⚠️  NOTE: Tool returns mock data")
                print("   (No real eligibility verification - this is a stub)")
            elif status == "REAL":
                print("✅ NOTE: Tool uses real API")
                print("   (May fail if API not available)")
            
            print("✅ CONFIRMED: Tool executed and returned data")
            
        except TypeError as e:
            error_msg = str(e)
            if "missing" in error_msg.lower() or "required" in error_msg.lower():
                print(f"⚠️  Parameter mismatch: {error_msg}")
                print("   Checking tool schema for correct parameters...")
                # Try to get correct parameters from schema
                params = schema.parameters if hasattr(schema, 'parameters') else {}
                print(f"   Expected parameters: {list(params.keys()) if isinstance(params, dict) else 'N/A'}")
            else:
                print(f"❌ Error: {error_msg}")
                import traceback
                traceback.print_exc()
        except ValueError as e:
            error_msg = str(e)
            if "not found" in error_msg.lower() or "api" in error_msg.lower():
                print(f"⚠️  API/Patient lookup failed (expected if patient doesn't exist or API not running)")
                print(f"   Error: {error_msg}")
                print()
                print("📝 This is expected behavior for a REAL tool - it needs patient data from API")
            else:
                print(f"❌ Error: {error_msg}")
                import traceback
                traceback.print_exc()
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            import traceback
            traceback.print_exc()
        
        print()
        print("=" * 90)
        print("📝 RECOMMENDATION:")
        print("=" * 90)
        print(f"   Mark tool as: {status}")
        if status == "REAL":
            print(f"   Implementation: Uses real API endpoints")
        else:
            print(f"   Implementation: Mock/hardcoded data")
        print()
        
        return {
            "status": status,
            "test_inputs": test_inputs,
            "test_result": "success" if 'result' in locals() else "error",
            "output_keys": list(result.keys()) if 'result' in locals() and isinstance(result, dict) else []
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

