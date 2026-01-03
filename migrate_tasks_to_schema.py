#!/usr/bin/env python3
"""
Migration Script: Update all tasks in task_catalog to conform to task_master_schema.json

This script:
1. Loads the task master schema
2. Fetches all tasks from the database
3. For each task, applies schema defaults to missing fields
4. Updates tasks in the database with the enriched data
"""

import asyncio
import sys
import os
import json
from typing import Dict, Any, Optional

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from nexus.modules.database import database
from nexus.modules.task_registry import task_registry

# Load schema
SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "nexus", "configs", "task_master_schema.json")

def load_schema() -> Dict[str, Any]:
    """Load the task master schema."""
    with open(SCHEMA_PATH, "r") as f:
        return json.load(f)

def apply_schema_defaults(data: Dict[str, Any], schema: Dict[str, Any], path: list = []) -> Dict[str, Any]:
    """
    Recursively apply schema defaults to a data structure.
    
    Args:
        data: The current data (task field value)
        schema: The schema definition for this field
        path: Current path in the schema (for debugging)
    
    Returns:
        Updated data with defaults applied
    """
    if not isinstance(schema, dict):
        return data
    
    result = data.copy() if isinstance(data, dict) else {}
    
    # Iterate through schema fields
    for key, field_schema in schema.items():
        # Skip metadata fields
        if key in ["schema_name", "schema_version", "audit"]:
            continue
        
        # Skip example arrays (intent_examples, question_intent_examples)
        if key in ["intent_examples", "question_intent_examples"]:
            continue
        
        current_path = path + [key]
        current_value = result.get(key)
        
        # If field_schema has a "default" key, it's a leaf field
        if isinstance(field_schema, dict) and "default" in field_schema:
            default_value = field_schema["default"]
            
            # Apply default if value is missing or None
            if current_value is None or current_value == "":
                result[key] = default_value
            # Handle arrays - ensure they're arrays
            elif field_schema.get("allowed") == "array[string]":
                if not isinstance(current_value, list):
                    # Try to parse if it's a string
                    if isinstance(current_value, str):
                        result[key] = [v.strip() for v in current_value.split(",") if v.strip()]
                    else:
                        result[key] = default_value if isinstance(default_value, list) else []
                # Ensure array items are strings
                elif current_value and not all(isinstance(v, str) for v in current_value):
                    result[key] = [str(v) for v in current_value]
            # Handle boolean fields - ensure they're booleans
            elif isinstance(default_value, bool) and not isinstance(current_value, bool):
                if isinstance(current_value, str):
                    result[key] = current_value.lower() in ("true", "1", "yes")
                elif isinstance(current_value, (int, float)):
                    result[key] = bool(current_value)
                else:
                    result[key] = default_value
            # Handle numeric fields - ensure they're numbers
            elif isinstance(default_value, (int, float)) and not isinstance(current_value, (int, float)):
                if isinstance(current_value, str):
                    try:
                        if isinstance(default_value, float):
                            result[key] = float(current_value)
                        else:
                            result[key] = int(current_value)
                    except (ValueError, TypeError):
                        result[key] = default_value
                else:
                    result[key] = default_value
            # Handle enum fields - validate against allowed values
            elif "allowed" in field_schema and isinstance(field_schema["allowed"], list):
                allowed_values = field_schema["allowed"]
                # Skip validation if it's an array default (multi-select)
                if not isinstance(default_value, list):
                    if current_value not in allowed_values:
                        result[key] = default_value
                else:
                    # Multi-select: ensure all values are in allowed list
                    if isinstance(current_value, list):
                        result[key] = [v for v in current_value if v in allowed_values]
                    else:
                        result[key] = default_value
        
        # If field_schema is a nested object (no "default" key), recurse
        elif isinstance(field_schema, dict):
            nested_value = current_value if isinstance(current_value, dict) else {}
            result[key] = apply_schema_defaults(nested_value, field_schema, current_path)
    
    return result

def apply_defaults_to_task(task: Dict[str, Any], schema: Dict[str, Any]) -> Dict[str, Any]:
    """
    Apply schema defaults to a task.
    
    Args:
        task: Task data from database
        schema: Full schema definition
    
    Returns:
        Updated task with defaults applied
    """
    updated_task = task.copy()
    
    # Apply defaults to each section in the schema
    for section_key, section_schema in schema.items():
        # Skip metadata fields
        if section_key in ["schema_name", "schema_version", "audit"]:
            continue
        
        # Get current section data (default to empty dict)
        current_section = updated_task.get(section_key, {})
        if not isinstance(current_section, dict):
            current_section = {}
        
        # Apply schema defaults to this section
        updated_section = apply_schema_defaults(current_section, section_schema, [section_key])
        updated_task[section_key] = updated_section
    
    # Ensure status is set (from governance section or default)
    if "status" not in updated_task or not updated_task["status"]:
        gov_status = updated_task.get("governance", {}).get("status")
        if gov_status:
            updated_task["status"] = gov_status
        else:
            updated_task["status"] = schema.get("governance", {}).get("status", {}).get("default", "draft")
    
    # Ensure version is set
    if "version" not in updated_task or updated_task["version"] is None:
        gov_version = updated_task.get("governance", {}).get("version")
        if gov_version:
            updated_task["version"] = gov_version
        else:
            updated_task["version"] = schema.get("governance", {}).get("version", {}).get("default", 1)
    
    # Ensure schema_version is set
    if "schema_version" not in updated_task or not updated_task["schema_version"]:
        updated_task["schema_version"] = schema.get("schema_version", "v1.0")
    
    return updated_task

async def migrate_tasks():
    """Main migration function."""
    print("🚀 Starting task migration to schema defaults...")
    print(f"📋 Loading schema from: {SCHEMA_PATH}")
    
    # Load schema
    try:
        schema = load_schema()
        print(f"✅ Schema loaded: {schema.get('schema_name')} v{schema.get('schema_version')}")
    except Exception as e:
        print(f"❌ Failed to load schema: {e}")
        return
    
    # Connect to database
    print("\n🔌 Connecting to database...")
    await database.connect()
    
    try:
        # Fetch all tasks
        print("📊 Fetching all tasks...")
        all_tasks = await task_registry.list_tasks(filters={})
        print(f"   Found {len(all_tasks)} tasks")
        
        if not all_tasks:
            print("   No tasks to migrate.")
            return
        
        updated_count = 0
        error_count = 0
        
        print("\n🔄 Processing tasks...")
        for idx, task in enumerate(all_tasks, 1):
            task_key = task.get("task_key", "unknown")
            task_name = task.get("name", "Unknown")
            
            try:
                print(f"\n  [{idx}/{len(all_tasks)}] Processing: {task_name[:50]}... (key: {task_key[:40]}...)")
                
                # Apply schema defaults
                updated_task = apply_defaults_to_task(task, schema)
                
                # Always update to ensure all schema fields are present
                # (Deep comparison would be expensive, so we just update all)
                changed = True  # Force update to ensure all schema fields are present
                
                # Update task in database
                # Prepare update data (only JSONB fields - update_task handles version/status separately)
                update_data = {
                    "classification": updated_task.get("classification", {}),
                    "automation": updated_task.get("automation", {}),
                    "tool_binding_defaults": updated_task.get("tool_binding_defaults", {}),
                    "information": updated_task.get("information", {}),
                    "policy": updated_task.get("policy", {}),
                    "temporal": updated_task.get("temporal", {}),
                    "escalation": updated_task.get("escalation", {}),
                    "dependencies": updated_task.get("dependencies", {}),
                    "failure": updated_task.get("failure", {}),
                    "ui": updated_task.get("ui", {}),
                    "governance": updated_task.get("governance", {}),
                    "contract": updated_task.get("contract", {}),
                    "status": updated_task.get("status"),
                    "schema_version": updated_task.get("schema_version"),
                }
                
                await task_registry.update_task(task_key, update_data, updated_by="system")
                print(f"    ✅ Updated successfully")
                updated_count += 1
                
            except Exception as e:
                print(f"    ❌ Error updating task: {e}")
                import traceback
                traceback.print_exc()
                error_count += 1
        
        print(f"\n{'='*60}")
        print(f"✅ Migration complete!")
        print(f"   📦 Tasks updated: {updated_count}")
        print(f"   ❌ Errors: {error_count}")
        print(f"   📊 Total processed: {len(all_tasks)}")
        print(f"{'='*60}")
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        await database.disconnect()

if __name__ == "__main__":
    asyncio.run(migrate_tasks())

