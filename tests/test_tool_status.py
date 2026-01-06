#!/usr/bin/env python3
"""
Tool Status Testing Framework
Tests tools and marks them as STUB or REAL based on implementation.
"""
import sys
import os
import json
import inspect
from typing import Dict, Any

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def analyze_tool_implementation(tool_instance) -> Dict[str, Any]:
    """
    Analyze a tool instance to determine if it's STUB or REAL.
    
    Returns:
        Dict with:
        - status: "REAL", "STUB", or "PARTIAL"
        - uses_api: bool
        - uses_mock: bool
        - api_endpoints: List[str]
        - notes: str
    """
    try:
        source = inspect.getsource(tool_instance.run)
        source_lower = source.lower()
        
        # Check for API usage
        uses_api = any(keyword in source for keyword in [
            'httpx', 'requests.get', 'requests.post',
            'api/user-profiles', 'user_profile_endpoints',
            'user_profile_manager', 'API_BASE_URL'
        ])
        
        # Check for mock/stub indicators
        uses_mock = any(indicator in source_lower for indicator in [
            'mock implementation',
            'mock data',
            '# mock',
            'return {',  # Simple dict return (may be mock)
            'stub',
            'todo',
            'fixme'
        ])
        
        # Extract API endpoints if any
        api_endpoints = []
        if 'api/user-profiles' in source:
            import re
            endpoints = re.findall(r'/api/[^\s\'"]+', source)
            api_endpoints = list(set(endpoints))
        
        # Determine status
        if uses_api and not uses_mock:
            status = "REAL"
            notes = "Uses API endpoints - real implementation"
        elif uses_mock or (not uses_api and 'return {' in source_lower):
            status = "STUB"
            notes = "Uses mock data or stub implementation"
        elif uses_api and uses_mock:
            status = "PARTIAL"
            notes = "Uses API but has mock fallback or partial implementation"
        else:
            status = "UNKNOWN"
            notes = "Could not determine implementation type"
        
        return {
            "status": status,
            "uses_api": uses_api,
            "uses_mock": uses_mock,
            "api_endpoints": api_endpoints,
            "notes": notes
        }
    except Exception as e:
        return {
            "status": "ERROR",
            "uses_api": False,
            "uses_mock": False,
            "api_endpoints": [],
            "notes": f"Error analyzing: {str(e)}"
        }


def test_tool(tool_name: str, tool_class_path: str) -> Dict[str, Any]:
    """
    Test a single tool and return status information.
    
    Args:
        tool_name: Name of the tool
        tool_class_path: Full Python path to tool class (e.g., "nexus.tools.eligibility.gate1_data_retrieval.PatientDemographicsRetriever")
    
    Returns:
        Dict with test results
    """
    print(f"\n{'='*90}")
    print(f"Testing: {tool_name}")
    print(f"{'='*90}\n")
    
    try:
        # Import tool class
        module_path, class_name = tool_class_path.rsplit('.', 1)
        module = __import__(module_path, fromlist=[class_name])
        tool_class = getattr(module, class_name)
        
        # Instantiate tool
        tool = tool_class()
        
        # Get schema
        schema = tool.define_schema()
        
        print(f"✅ Tool loaded: {schema.name}")
        print(f"   Description: {schema.description[:80]}...")
        print()
        
        # Analyze implementation
        analysis = analyze_tool_implementation(tool)
        
        print(f"📋 Implementation Analysis:")
        print(f"   Status: {analysis['status']}")
        print(f"   Uses API: {analysis['uses_api']}")
        print(f"   Uses Mock: {analysis['uses_mock']}")
        if analysis['api_endpoints']:
            print(f"   API Endpoints: {', '.join(analysis['api_endpoints'])}")
        print(f"   Notes: {analysis['notes']}")
        print()
        
        return {
            "tool_name": tool_name,
            "tool_class_path": tool_class_path,
            "schema_name": schema.name,
            "description": schema.description,
            "status": analysis['status'],
            "uses_api": analysis['uses_api'],
            "uses_mock": analysis['uses_mock'],
            "api_endpoints": analysis['api_endpoints'],
            "notes": analysis['notes'],
            "success": True
        }
        
    except Exception as e:
        print(f"❌ Error testing tool: {e}")
        import traceback
        traceback.print_exc()
        return {
            "tool_name": tool_name,
            "tool_class_path": tool_class_path,
            "status": "ERROR",
            "error": str(e),
            "success": False
        }


if __name__ == "__main__":
    # Test first tool: patient_demographics_retriever
    result = test_tool(
        "patient_demographics_retriever",
        "nexus.tools.eligibility.gate1_data_retrieval.PatientDemographicsRetriever"
    )
    
    print(f"\n{'='*90}")
    print("TEST RESULT")
    print(f"{'='*90}\n")
    print(json.dumps(result, indent=2))




