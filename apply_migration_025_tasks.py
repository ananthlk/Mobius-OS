#!/usr/bin/env python3
"""
Migration: Extract tasks from existing draft_plans and populate task_catalog

This script:
1. Reads all draft_plans from shaping_sessions
2. Extracts step descriptions from gates->steps
3. Creates task catalog entries (with minimal metadata, leaving most fields open)
4. Maintains data integrity so existing plans can reference tasks in catalog
"""
import asyncio
import sys
import os
import json

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from nexus.modules.database import database, parse_jsonb
from nexus.modules.task_registry import task_registry

async def migrate_tasks_from_draft_plans():
    print("🚀 Connecting to DB...")
    await database.connect()
    try:
        print("▶️ Extracting tasks from existing draft_plans...")
        print("")
        
        # Get all shaping_sessions with draft_plans
        query = """
            SELECT id, user_id, draft_plan, consultant_strategy
            FROM shaping_sessions
            WHERE draft_plan IS NOT NULL 
            AND draft_plan::text != '{}'
            AND draft_plan::text != 'null'
        """
        
        sessions = await database.fetch_all(query=query)
        print(f"  📊 Found {len(sessions)} sessions with draft_plans")
        print("")
        
        tasks_created = 0
        tasks_found = 0
        tasks_skipped = 0
        step_descriptions_seen = set()
        
        for idx, session in enumerate(sessions, 1):
            session_dict = dict(session)
            draft_plan_raw = session_dict.get("draft_plan")
            if not draft_plan_raw:
                continue
            
            draft_plan = parse_jsonb(draft_plan_raw)
            if not draft_plan:
                continue
            
            session_id = session_dict.get("id")
            user_id = session_dict.get("user_id", "system")
            strategy = session_dict.get("consultant_strategy", "TABULA_RASA")
            
            print(f"  📝 Processing session {idx}/{len(sessions)} (ID: {session_id})...")
            
            # Extract steps from gates
            gates = draft_plan.get("gates", [])
            if not gates:
                # Also check for old "phases" structure for backward compatibility
                gates = draft_plan.get("phases", [])
            
            session_step_count = 0
            for gate in gates:
                steps = gate.get("steps", [])
                for step in steps:
                    # Get step description
                    step_description = step.get("description") or step.get("name")
                    if not step_description:
                        continue
                    
                    session_step_count += 1
                    
                    # Skip if we've already processed this description (deduplicate)
                    step_description_lower = step_description.lower().strip()
                    if step_description_lower in step_descriptions_seen:
                        tasks_skipped += 1
                        continue
                    
                    step_descriptions_seen.add(step_description_lower)
                    
                    # Infer domain from draft_plan or use default
                    domain = "eligibility"  # Default
                    # Could extract from problem_statement or other fields if available
                    
                    try:
                        # Check if task already exists first
                        existing_tasks = await task_registry.search_tasks(
                            query_text=step_description,
                            filters={"status": "active"}
                        )
                        
                        # Look for exact or close match
                        task_key = None
                        for task in existing_tasks:
                            if task.get("description", "").lower().strip() == step_description_lower:
                                task_key = task["task_key"]
                                tasks_found += 1
                                print(f"    ✓ Found existing: {task_key[:60]}...")
                                break
                        
                        if not task_key:
                            # Use find_or_create_task to create if it doesn't exist
                            task_key = await task_registry.find_or_create_task(
                                task_description=step_description,
                                context={
                                    "domain": domain,
                                    "strategy": strategy
                                },
                                created_by=user_id
                            )
                            tasks_created += 1
                            print(f"    ➕ Created: {task_key[:60]}...")
                    
                    except Exception as e:
                        print(f"    ✗ Failed to create task for '{step_description[:50]}...': {e}")
                        tasks_skipped += 1
            
            if session_step_count > 0:
                print(f"    Processed {session_step_count} steps from this session")
            print("")
        
        print("=" * 60)
        print(f"✅ Migration complete!")
        print(f"   📦 Tasks created: {tasks_created}")
        print(f"   🔍 Tasks found (existing): {tasks_found}")
        print(f"   ⏭️  Tasks skipped (duplicates): {tasks_skipped}")
        print(f"   📊 Total unique step descriptions: {len(step_descriptions_seen)}")
        print("=" * 60)
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        await database.disconnect()

if __name__ == "__main__":
    asyncio.run(migrate_tasks_from_draft_plans())

