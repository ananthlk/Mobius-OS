"""
Test script for Utility Tools
Tests: google_search, generic_llm_call, maps_plotting
"""
import sys
import os
import json

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nexus.tools.utilities.google_search_tool import GoogleSearchTool
from nexus.tools.utilities.generic_llm_tool import GenericLLMCallTool
from nexus.tools.utilities.maps_plotting_tool import MapsPlottingTool


def test_google_search():
    """Test GoogleSearchTool"""
    print("\n" + "=" * 80)
    print("Testing: GoogleSearchTool")
    print("=" * 80)
    
    try:
        tool = GoogleSearchTool()
        
        # Test schema
        schema = tool.define_schema()
        print(f"✅ Schema defined: {schema.name}")
        print(f"   Description: {schema.description[:80]}...")
        
        # Test run
        result = tool.run(
            query="Python async programming",
            num_results=5,
            search_type="web"
        )
        
        print(f"✅ Google Search executed successfully")
        print(f"   Query: {result.get('query')}")
        print(f"   Search Type: {result.get('search_type')}")
        print(f"   Results Returned: {result.get('num_results')}")
        
        if result.get('results'):
            print(f"\n   Sample Result:")
            print(json.dumps(result.get('results')[0], indent=2))
        
        print(f"\n   Full Result:")
        print(json.dumps(result, indent=2))
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_generic_llm_call():
    """Test GenericLLMCallTool"""
    print("\n" + "=" * 80)
    print("Testing: GenericLLMCallTool")
    print("=" * 80)
    
    try:
        tool = GenericLLMCallTool()
        
        # Test schema
        schema = tool.define_schema()
        print(f"✅ Schema defined: {schema.name}")
        print(f"   Description: {schema.description[:80]}...")
        
        # Test run
        result = tool.run(
            prompt="What is the capital of France?",
            temperature=0.7,
            max_tokens=100
        )
        
        print(f"✅ Generic LLM Call executed successfully")
        print(f"   Prompt: {result.get('prompt')[:60]}...")
        print(f"   Model ID: {result.get('model_id')}")
        print(f"   Temperature: {result.get('temperature')}")
        print(f"   Response: {result.get('response')[:100]}...")
        
        if result.get('usage'):
            print(f"   Token Usage:")
            print(json.dumps(result.get('usage'), indent=4))
        
        print(f"\n   Full Result:")
        print(json.dumps(result, indent=2))
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_maps_plotting():
    """Test MapsPlottingTool"""
    print("\n" + "=" * 80)
    print("Testing: MapsPlottingTool")
    print("=" * 80)
    
    try:
        tool = MapsPlottingTool()
        
        # Test schema
        schema = tool.define_schema()
        print(f"✅ Schema defined: {schema.name}")
        print(f"   Description: {schema.description[:80]}...")
        
        # Test run
        result = tool.run(
            locations=[
                "1600 Amphitheatre Parkway, Mountain View, CA",
                "1 Infinite Loop, Cupertino, CA"
            ],
            plot_type="markers",
            center_location="San Francisco, CA"
        )
        
        print(f"✅ Maps Plotting executed successfully")
        print(f"   Map ID: {result.get('map_id')}")
        print(f"   Plot Type: {result.get('plot_type')}")
        print(f"   Number of Locations: {result.get('num_locations')}")
        print(f"   Map URL: {result.get('map_url')}")
        print(f"   Static Image URL: {result.get('static_image_url')}")
        
        print(f"\n   Full Result:")
        print(json.dumps(result, indent=2))
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_all_tests():
    """Run all utility tool tests"""
    print("=" * 80)
    print("UTILITY TOOLS TEST SUITE")
    print("=" * 80)
    
    tests = [
        test_google_search,
        test_generic_llm_call,
        test_maps_plotting,
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




