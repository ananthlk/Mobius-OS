"""
Seed script to load Conversational Agent prompt into database.
Run this after migration 014_prompt_management.sql

This creates the prompt with key: conversational:formatting:default:response
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

async def seed_conversational_agent_prompt():
    """Load Conversational Agent prompt from JSON file into database."""
    
    # Load the prompt config
    config_path = os.path.join(os.path.dirname(__file__), "..", "configs", "conversational_agent_prompt.json")
    
    with open(config_path, 'r') as f:
        prompt_config = json.load(f)
    
    # Connect to database
    await database.connect()
    
    try:
        # Create the prompt using new API signature: module_name, domain, mode, step
        print(f"Creating prompt with:")
        print(f"  module_name: conversational")
        print(f"  domain: formatting")
        print(f"  mode: default")
        print(f"  step: response")
        print(f"  prompt_key will be: conversational:formatting:default:response")
        
        prompt_id = await prompt_manager.create_prompt(
            module_name="conversational",
            domain="formatting",
            mode="default",
            step="response",
            prompt_config=prompt_config,
            description="Conversational agent prompt for formatting raw LLM responses into user-friendly, well-formatted responses with markdown support",
            user_context={"user_id": "system"}
        )
        
        print(f"✅ Successfully seeded Conversational Agent prompt (ID: {prompt_id})")
        print(f"   Key: conversational:formatting:default:response")
        
        # Verify it was created
        verify = await prompt_manager.get_prompt(
            module_name="conversational",
            domain="formatting",
            mode="default",
            step="response"
        )
        if verify:
            print(f"✅ Verification: Prompt found in database")
        else:
            print(f"⚠️  Verification: Prompt NOT found in database (but create_prompt returned ID: {prompt_id})")
        
    except ValueError as e:
        if "already exists" in str(e):
            print(f"⚠️  Prompt already exists. Use update_prompt() to update it.")
            print(f"   To update, use the API: PUT /api/prompts/conversational:formatting:default:response")
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
    asyncio.run(seed_conversational_agent_prompt())





