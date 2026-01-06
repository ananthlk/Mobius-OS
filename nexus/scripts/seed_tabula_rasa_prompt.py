"""
Seed script to load TABULA_RASA prompt into database.
Run this after migration 014_prompt_management.sql
"""
import asyncio
import json
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nexus.modules.database import database
from nexus.modules.prompt_manager import prompt_manager

async def seed_prompt():
    """Load TABULA_RASA prompt from JSON file into database."""
    
    # Load the prompt config
    config_path = os.path.join(os.path.dirname(__file__), "..", "configs", "tabula_rasa_prompt_example.json")
    
    with open(config_path, 'r') as f:
        prompt_config = json.load(f)
    
    # Connect to database
    await database.connect()
    
    try:
        # Create the prompt using new API: module_name, domain, mode, step
        prompt_id = await prompt_manager.create_prompt(
            module_name="workflow",
            domain="eligibility",
            mode="TABULA_RASA",
            step="clarification",  # Main TABULA_RASA prompt is for initial clarification
            prompt_config=prompt_config,
            description="TABULA_RASA strategy prompt for building workflows from scratch",
            user_context={"user_id": "system"}
        )
        
        print(f"✅ Successfully seeded TABULA_RASA prompt (ID: {prompt_id})")
        print(f"   Key: workflow:eligibility:TABULA_RASA:clarification")
        
    except ValueError as e:
        if "already exists" in str(e):
            print(f"⚠️  Prompt already exists. Use update_prompt() to update it.")
        else:
            raise
    except Exception as e:
        print(f"❌ Error seeding prompt: {e}")
        raise
    finally:
        await database.disconnect()

if __name__ == "__main__":
    asyncio.run(seed_prompt())





