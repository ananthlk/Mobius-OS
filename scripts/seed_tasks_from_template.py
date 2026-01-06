#!/usr/bin/env python3
"""
Seed tasks from the hierarchical eligibility template into task_catalog.
Extracts all tasks from gates/sub_levels and registers them in task_catalog.
"""
import asyncio
import json
import sys
import os
from pathlib import Path
from typing import Dict, Any, List

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from nexus.modules.database import connect_to_db, disconnect_from_db, database
from nexus.modules.task_registry import task_registry

async def extract_tasks_from_template(template_path: str) -> List[Dict[str, Any]]:
    """Extract all tasks from the hierarchical template."""
    with open(template_path, 'r') as f:
        template_data = json.load(f)
    
    tasks = []
    template_config = template_data.get('template_config', {})
    gates = template_config.get('gates', [])
    
    for gate in gates:
        gate_key = gate.get('gate_key', '')
        gate_name = gate.get('name', '')
        sub_levels = gate.get('sub_levels', {})
        
        for sub_level_key, sub_level_data in sub_levels.items():
            sub_level_tasks = sub_level_data.get('tasks', [])
            
            for task in sub_level_tasks:
                task_id = task.get('id', '')
                description = task.get('description', '')
                tool_hint = task.get('tool_hint', '')
                
                # Create task_key from gate, sub_level, and task id
                task_key = f"{gate_key}:{sub_level_key}:{task_id}"
                
                # Infer category from task description
                desc_lower = description.lower()
                if any(word in desc_lower for word in ['collect', 'gather', 'retrieve', 'get', 'fetch']):
                    category = "collect"
                elif any(word in desc_lower for word in ['check', 'verify', 'validate', 'confirm', 'assess']):
                    category = "verify"
                elif any(word in desc_lower for word in ['parse', 'extract', 'analyze', 'interpret', 'compute', 'calculate']):
                    category = "interpret"
                elif any(word in desc_lower for word in ['notify', 'inform', 'send', 'communicate']):
                    category = "notify"
                elif any(word in desc_lower for word in ['escalate', 'refer', 'transfer']):
                    category = "escalate"
                elif any(word in desc_lower for word in ['decide', 'determine', 'choose', 'select']):
                    category = "decide"
                elif any(word in desc_lower for word in ['wait', 'pause', 'delay']):
                    category = "wait"
                elif task.get('requires_human_action', False) or task.get('requires_human_review', False):
                    category = "manual"
                else:
                    # Default based on tool_hint or description
                    category = "verify"  # Safe default
                
                # Build task data for task_catalog
                task_data = {
                    "task_key": task_key,
                    "name": description[:255],  # Truncate if needed
                    "description": description,
                    "classification": {
                        "domain": "eligibility",
                        "category": category,  # Use inferred category
                        "sub_category": sub_level_key,
                        "gate": gate_key,
                        "sub_level": sub_level_key
                    },
                    "contract": {
                        "inputs": task.get('inputs', []),
                        "outputs": task.get('outputs', []),
                        "preconditions": task.get('preconditions', [])
                    },
                    "automation": {
                        "tool_hint": tool_hint,
                        "requires_human_action": task.get('requires_human_action', False),
                        "requires_human_review": task.get('requires_human_review', False),
                        "human_action_description": task.get('human_action_description', ''),
                        "is_automated": not task.get('requires_human_action', False)
                    },
                    "temporal": {
                        "timeline_estimate": task.get('timeline_estimate', ''),
                        "depends_on": task.get('depends_on', [])
                    },
                    "information": {
                        "gate_context": gate_name,
                        "sub_level_context": sub_level_data.get('name', ''),
                        "template_source": "hierarchical_eligibility_template"
                    },
                    "status": "active",
                    "version": 1,
                    "schema_version": "1.0"
                }
                
                tasks.append(task_data)
    
    return tasks

async def seed_tasks():
    """Seed tasks from template into task_catalog."""
    print("🌱 Seeding tasks from hierarchical eligibility template...")
    print("=" * 60)
    
    await connect_to_db()
    
    try:
        # Load template
        template_path = PROJECT_ROOT / "nexus" / "configs" / "hierarchical_eligibility_template.json"
        
        if not template_path.exists():
            print(f"❌ Template file not found: {template_path}")
            return
        
        print(f"📄 Loading template from: {template_path}")
        tasks = await extract_tasks_from_template(str(template_path))
        print(f"   Found {len(tasks)} tasks in template")
        
        # Register each task
        registered_count = 0
        skipped_count = 0
        error_count = 0
        
        for task_data in tasks:
            try:
                # Check if task already exists
                existing = await task_registry.get_task_by_key(task_data['task_key'])
                
                if existing:
                    print(f"   ⏭️  Skipping existing task: {task_data['task_key']}")
                    skipped_count += 1
                    continue
                
                # Create task using create_task method
                result = await task_registry.create_task(
                    task_data=task_data,
                    created_by="system"
                )
                
                print(f"   ✅ Registered: {task_data['task_key']}")
                registered_count += 1
                
            except Exception as e:
                print(f"   ❌ Error registering task {task_data.get('task_key', 'unknown')}: {e}")
                error_count += 1
        
        print("\n" + "=" * 60)
        print(f"🎉 Task seeding complete!")
        print(f"   ✅ Registered: {registered_count} new tasks")
        print(f"   ⏭️  Skipped: {skipped_count} existing tasks")
        print(f"   ❌ Errors: {error_count} tasks")
        
        # Verify
        total_tasks = await database.fetch_val(query="SELECT COUNT(*) FROM task_catalog")
        print(f"\n📊 Total tasks in catalog: {total_tasks}")
        
    except Exception as e:
        print(f"\n❌ Error during task seeding: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        await disconnect_from_db()

if __name__ == "__main__":
    asyncio.run(seed_tasks())

