"""
Seed script to load/update GATE prompt for TABULA_RASA strategy into database.
Run this after migration 014_prompt_management.sql

This creates or updates the prompt with key: workflow:eligibility:TABULA_RASA:gate
"""
import asyncio
import json
import sys
import os

# Add parent directory to path (nexus/scripts -> nexus -> project root)
script_dir = os.path.dirname(os.path.abspath(__file__))
nexus_dir = os.path.dirname(script_dir)
project_root = os.path.dirname(nexus_dir)

# Add project root to path
sys.path.insert(0, project_root)
# Also set PYTHONPATH
os.environ['PYTHONPATH'] = project_root

from nexus.modules.database import database
from nexus.modules.prompt_manager import prompt_manager

async def seed_gate_prompt():
    """Load/Update GATE prompt from JSON file into database."""
    
    # Load the gate prompt config
    config_path = os.path.join(os.path.dirname(__file__), "..", "configs", "gate_prompt_tabula_rasa.json")
    
    with open(config_path, 'r') as f:
        prompt_config = json.load(f)
    
    # Connect to database
    await database.connect()
    
    try:
        prompt_key = "workflow:eligibility:TABULA_RASA:gate"
        
        # Check if prompt exists
        existing = await prompt_manager.get_prompt(
            module_name="workflow",
            domain="eligibility",
            mode="TABULA_RASA",
            step="gate"
        )
        
        if existing:
            # Update existing prompt
            print(f"📝 Updating existing prompt: {prompt_key}")
            print(f"   Current version: {existing.get('version', 'unknown')}")
            
            prompt_id = await prompt_manager.update_prompt(
                prompt_key=prompt_key,
                prompt_config=prompt_config,
                change_reason="Updated to 5 gates: added 2_insurance_history and renumbered gates",
                user_context={"user_id": "system"}
            )
            
            print(f"✅ Successfully updated GATE prompt (ID: {prompt_id})")
            print(f"   Key: {prompt_key}")
            
            # Verify it was updated
            verify = await prompt_manager.get_prompt(
                module_name="workflow",
                domain="eligibility",
                mode="TABULA_RASA",
                step="gate"
            )
            if verify:
                print(f"✅ Verification: Prompt updated in database (version: {verify.get('version', 'unknown')})")
                # Show gate count
                gates = verify.get('config', {}).get('GATES', {})
                gate_order = verify.get('config', {}).get('GATE_ORDER', [])
                print(f"   Gates in config: {len(gate_order)} gates")
                print(f"   Gate order: {', '.join(gate_order)}")
            else:
                print(f"⚠️  Verification: Prompt NOT found after update")
        else:
            # Create new prompt
            print(f"Creating new prompt: {prompt_key}")
            
            prompt_id = await prompt_manager.create_prompt(
                module_name="workflow",
                domain="eligibility",
                mode="TABULA_RASA",
                step="gate",
                prompt_config=prompt_config,
                description="Gate-based data collection prompt for TABULA_RASA eligibility workflows",
                user_context={"user_id": "system"}
            )
            
            print(f"✅ Successfully seeded GATE prompt (ID: {prompt_id})")
            print(f"   Key: {prompt_key}")
            
            # Verify it was created
            verify = await prompt_manager.get_prompt(
                module_name="workflow",
                domain="eligibility",
                mode="TABULA_RASA",
                step="gate"
            )
            if verify:
                print(f"✅ Verification: Prompt found in database")
            else:
                print(f"⚠️  Verification: Prompt NOT found in database (but create_prompt returned ID: {prompt_id})")
        
    except Exception as e:
        print(f"❌ Error seeding/updating prompt: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        await database.disconnect()

if __name__ == "__main__":
    asyncio.run(seed_gate_prompt())

