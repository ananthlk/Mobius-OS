#!/usr/bin/env python3
"""
Test Patient Insurance Collector Tool
Tests the tool and shows input/output.
"""
import sys
import os
import json

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from nexus.tools.eligibility.gate1_data_retrieval import PatientInsuranceCollector

def test_tool():
    """Test the PatientInsuranceCollector tool"""
    print("\n" + "=" * 90)
    print("🧪 TESTING: patient_insurance_collector")
    print("=" * 90)
    print()
    
    try:
        # Instantiate tool
        tool = PatientInsuranceCollector()
        schema = tool.define_schema()
        
        print(f"✅ Tool loaded: {schema.name}")
        print(f"   Description: {schema.description}")
        print()
        
        # Check implementation
        import inspect
        run_source = inspect.getsource(tool.run)
        
        # Analyze implementation
        uses_api = 'httpx' in run_source or 'api/' in run_source or 'user_profile' in run_source
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
            print("   Tool uses mock/hardcoded data - no real communication integration")
        elif uses_api:
            status = "REAL"
            print(f"✅ Status: {status}")
        else:
            status = "UNKNOWN"
        
        print()
        print("=" * 90)
        print("🧪 TEST EXECUTION")
        print("=" * 90)
        print()
        
        # Test inputs
        test_inputs = {
            "patient_id": "PATIENT_001",
            "communication_method": "portal",
            "urgency": "medium"
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
                if 'communication_sent' in result:
                    print(f"   ✅ Communication sent: {result.get('communication_sent')}")
                if 'method' in result:
                    print(f"   ✅ Method: {result.get('method')}")
            print()
            
            if status == "STUB":
                print("⚠️  NOTE: Tool returns hardcoded mock data")
                print("   (No real communication integration - this is a stub)")
            
            print("✅ CONFIRMED: Tool executed and returned data")
            
        except Exception as e:
            print(f"❌ Error executing tool: {e}")
            import traceback
            traceback.print_exc()
        
        print()
        print("=" * 90)
        print("📝 RECOMMENDATION:")
        print("=" * 90)
        print(f"   Mark tool as: {status}")
        print(f"   Implementation: Mock/hardcoded data - no real communication integration")
        print()
        print("💡 NAMING:")
        print("   This is a communication/action tool (not a query tool)")
        print("   Suggested name: patient_insurance_collector (keep as is)")
        print("   OR: communication_patient_insurance_collector")
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




