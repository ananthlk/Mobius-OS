"""
Seed script to load GATE prompt for TABULA_RASA strategy into database.
Run this after migration 014_prompt_management.sql

This creates the prompt with key: workflow:eligibility:TABULA_RASA:gate
"""
import asyncio
import json
import sys
import os

# Add parent directory to path
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)
# Also set PYTHONPATH for subprocess calls
os.environ['PYTHONPATH'] = parent_dir

from nexus.modules.database import database
from nexus.modules.prompt_manager import prompt_manager

async def seed_gate_prompt():
    """Load GATE prompt from JSON file into database."""
    
    # Load the gate prompt config
    config_path = os.path.join(os.path.dirname(__file__), "..", "configs", "gate_prompt_tabula_rasa.json")
    
    with open(config_path, 'r') as f:
        prompt_config = json.load(f)
    
    # Connect to database
    await database.connect()
    
    try:
        # Create the prompt using new API signature: module_name, domain, mode, step
        print(f"Creating prompt with:")
        print(f"  module_name: workflow")
        print(f"  domain: eligibility")
        print(f"  mode: TABULA_RASA")
        print(f"  step: gate")
        print(f"  prompt_key will be: workflow:eligibility:TABULA_RASA:gate")
        
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
        print(f"   Key: workflow:eligibility:TABULA_RASA:gate")
        
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
        
    except ValueError as e:
        if "already exists" in str(e):
            print(f"⚠️  Prompt already exists. Use update_prompt() to update it.")
            print(f"   To update, use the API: PUT /api/prompts/workflow:eligibility:TABULA_RASA:gate")
        else:
            raise
    except Exception as e:
        print(f"❌ Error seeding prompt: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        await database.disconnect()

if __name__ == "__main__":
    asyncio.run(seed_gate_prompt())

