#!/usr/bin/env python3
"""
Show Input/Output Fields for All Tools
"""
import sys
import json
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from nexus.tools.library.seed_tools import TOOLS_TO_SEED

def get_tool_input_output(tool_name: str):
    """Get input/output fields for a specific tool by importing and inspecting it"""
    try:
        # Find tool in registry
        tool_def = next((t for t in TOOLS_TO_SEED if t['name'] == tool_name), None)
        if not tool_def:
            return None, "Tool not found in registry"
        
        # Try to import the tool class
        impl_path = tool_def.get('implementation_path', '')
        if not impl_path:
            return tool_def, "No implementation path"
        
        try:
            module_path, class_name = impl_path.rsplit('.', 1)
            module = __import__(module_path, fromlist=[class_name])
            tool_class = getattr(module, class_name)
            tool_instance = tool_class()
            schema = tool_instance.define_schema()
            
            # Get output structure by checking the run method
            import inspect
            run_source = inspect.getsource(tool_class.run)
            
            # Try to extract return structure from source (basic parsing)
            output_fields = []
            if 'return {' in run_source or "return {" in run_source:
                # Try to find return dictionary structure
                # This is a simple heuristic - could be improved
                output_fields = ["(See implementation for exact structure)"]
            
            return {
                'tool_def': tool_def,
                'schema': schema,
                'output_fields': output_fields,
                'has_implementation': True
            }, None
        except Exception as e:
            return tool_def, f"Could not import tool: {str(e)}"
    except Exception as e:
        return None, f"Error: {str(e)}"

def format_tool_io(tool_data, error=None):
    """Format tool input/output information"""
    if error:
        tool_def = tool_data
        print(f"\n{'='*90}")
        print(f"❌ {tool_def.get('name', 'Unknown')} - {error}")
        print(f"{'='*90}")
        return
    
    if isinstance(tool_data, dict) and 'tool_def' in tool_data:
        tool_def = tool_data['tool_def']
        schema = tool_data.get('schema')
    else:
        tool_def = tool_data
        schema = None
    
    print(f"\n{'='*90}")
    print(f"{tool_def.get('name', 'Unknown')} ({tool_def.get('display_name', 'N/A')})")
    print(f"{'='*90}")
    print(f"Category: {tool_def.get('category', 'N/A')}")
    print(f"Status: {tool_def.get('status', 'N/A')}")
    if 'implementation_status' in tool_def:
        print(f"Implementation: {tool_def['implementation_status']}")
    print()
    
    # INPUT FIELDS
    print("📥 INPUT FIELDS:")
    if schema:
        for param_name, param_desc in schema.parameters.items():
            print(f"   • {param_name}: {param_desc}")
    else:
        params = tool_def.get('parameters', [])
        if params:
            for param in sorted(params, key=lambda x: x.get('order_index', 999)):
                required = "REQUIRED" if param.get('is_required', False) else "OPTIONAL"
                param_type = param.get('parameter_type', 'N/A')
                default = f" (default: {param.get('default_value')})" if param.get('default_value') else ""
                print(f"   • {param.get('parameter_name', 'N/A'):30} [{param_type:10}] {required}{default}")
                desc = param.get('description', '')
                if desc:
                    print(f"     {desc}")
        else:
            print("   (No parameters defined)")
    
    print()
    print("📤 OUTPUT FIELDS:")
    print("   Returns: Dict[str, Any]")
    print("   (Check tool implementation for exact structure)")

if __name__ == "__main__":
    print("=" * 90)
    print("📋 ALL TOOLS - INPUT & OUTPUT FIELDS")
    print("=" * 90)
    
    sorted_tools = sorted(TOOLS_TO_SEED, key=lambda x: x['name'])
    
    for i, tool_def in enumerate(sorted_tools, 1):
        tool_name = tool_def['name']
        tool_data, error = get_tool_input_output(tool_name)
        format_tool_io(tool_data, error)
        
        if i < len(sorted_tools):
            print()
    
    print("\n" + "=" * 90)
    print(f"TOTAL: {len(sorted_tools)} tools")
    print("=" * 90)




