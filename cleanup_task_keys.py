#!/usr/bin/env python3
"""
Cleanup Task Keys: Remove timestamps and merge duplicate tasks

This script:
1. Finds all tasks with timestamped keys (ending in _YYYYMMDDHHMMSS)
2. Groups them by their base key (description-based)
3. Keeps the oldest task for each base key
4. Updates/deprecates duplicates
5. Rekeys tasks to use stable keys without timestamps
"""
import asyncio
import sys
import os
import re

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from nexus.modules.database import database, parse_jsonb
from nexus.modules.task_registry import task_registry

async def cleanup_task_keys():
    print("🚀 Connecting to DB...")
    await database.connect()
    try:
        print("▶️ Cleaning up task keys - removing timestamps...")
        print("")
        
        # Get all tasks
        query = "SELECT task_key, name, description, created_at_utc FROM task_catalog ORDER BY created_at_utc"
        all_tasks = await database.fetch_all(query=query)
        
        print(f"  📊 Found {len(all_tasks)} total tasks")
        
        # Group tasks by their stable key (generated from description)
        tasks_by_stable_key = {}
        timestamp_pattern = re.compile(r'_\d{14}$')  # Pattern: _YYYYMMDDHHMMSS
        
        for task_row in all_tasks:
            task_dict = dict(task_row)
            current_key = task_dict["task_key"]
            description = task_dict.get("description") or task_dict.get("name", "")
            
            # Generate stable key from description
            stable_key = task_registry._generate_task_key(description)
            
            # Check if current key has timestamp
            has_timestamp = bool(timestamp_pattern.search(current_key))
            
            if stable_key not in tasks_by_stable_key:
                tasks_by_stable_key[stable_key] = []
            
            tasks_by_stable_key[stable_key].append({
                "current_key": current_key,
                "stable_key": stable_key,
                "description": description,
                "has_timestamp": has_timestamp,
                "created_at": task_dict.get("created_at_utc")
            })
        
        # Process each group
        tasks_to_update = []
        tasks_to_deprecate = []
        keys_to_update = {}  # Map old_key -> new_key
        
        for stable_key, task_list in tasks_by_stable_key.items():
            if len(task_list) == 1:
                # Single task - just rekey if it has timestamp
                task = task_list[0]
                if task["has_timestamp"]:
                    # Need to rekey to stable key
                    if task["current_key"] != stable_key:
                        keys_to_update[task["current_key"]] = stable_key
                        tasks_to_update.append(task)
                # Otherwise, key is already correct
            else:
                # Multiple tasks with same stable key - merge them
                # Sort by creation date (oldest first)
                sorted_tasks = sorted(task_list, key=lambda t: t["created_at"] or datetime.min)
                
                # Keep the oldest one, deprecate the rest
                primary_task = sorted_tasks[0]
                duplicates = sorted_tasks[1:]
                
                # If primary has timestamp, rekey it
                if primary_task["has_timestamp"] and primary_task["current_key"] != stable_key:
                    keys_to_update[primary_task["current_key"]] = stable_key
                    tasks_to_update.append(primary_task)
                
                # Mark duplicates for deprecation
                for dup in duplicates:
                    tasks_to_deprecate.append(dup)
                    # Also map their keys to the stable key (for reference)
                    keys_to_update[dup["current_key"]] = stable_key
        
        print(f"  🔑 Tasks to rekey: {len(tasks_to_update)}")
        print(f"  🗑️  Duplicate tasks to deprecate: {len(tasks_to_deprecate)}")
        print("")
        
        # Update task keys (rekey tasks)
        updated_count = 0
        for task in tasks_to_update:
            old_key = task["current_key"]
            new_key = keys_to_update[old_key]
            
            # Check if new_key already exists (might happen if we already have a task with stable key)
            existing = await task_registry.get_task_by_key(new_key)
            if existing:
                # New key already exists - deprecate the timestamped one instead
                print(f"    ⚠️  Key '{new_key}' already exists, deprecating '{old_key}' instead")
                await task_registry.delete_task(old_key, soft_delete=True)
                tasks_to_deprecate.append(task)
            else:
                # Update the task_key
                try:
                    query = "UPDATE task_catalog SET task_key = :new_key WHERE task_key = :old_key"
                    await database.execute(query=query, values={"new_key": new_key, "old_key": old_key})
                    
                    # Also update task_group_memberships if any
                    query_memberships = "UPDATE task_group_memberships SET task_key = :new_key WHERE task_key = :old_key"
                    await database.execute(query=query_memberships, values={"new_key": new_key, "old_key": old_key})
                    
                    # Also update task_catalog_history if any
                    query_history = "UPDATE task_catalog_history SET task_key = :new_key WHERE task_key = :old_key"
                    await database.execute(query=query_history, values={"new_key": new_key, "old_key": old_key})
                    
                    updated_count += 1
                    print(f"    ✓ Rekeyed: {old_key[:50]}... → {new_key[:50]}...")
                except Exception as e:
                    print(f"    ✗ Failed to rekey '{old_key}': {e}")
        
        # Deprecate duplicate tasks
        deprecated_count = 0
        for task in tasks_to_deprecate:
            try:
                await task_registry.delete_task(task["current_key"], soft_delete=True)
                deprecated_count += 1
                print(f"    🗑️  Deprecated: {task['current_key'][:60]}...")
            except Exception as e:
                print(f"    ✗ Failed to deprecate '{task['current_key']}': {e}")
        
        print("")
        print("=" * 60)
        print(f"✅ Cleanup complete!")
        print(f"   🔑 Tasks rekeyed: {updated_count}")
        print(f"   🗑️  Tasks deprecated: {deprecated_count}")
        print(f"   📊 Total stable keys: {len(tasks_by_stable_key)}")
        print("=" * 60)
        
    except Exception as e:
        print(f"❌ Cleanup failed: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        await database.disconnect()

if __name__ == "__main__":
    from datetime import datetime
    asyncio.run(cleanup_task_keys())


