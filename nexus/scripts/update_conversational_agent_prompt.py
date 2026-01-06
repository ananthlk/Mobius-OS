"""
Update script to update Conversational Agent prompt in database.
Run this after modifying conversational_agent_prompt.json

This updates the prompt with key: conversational:formatting:default:response
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

async def update_conversational_agent_prompt():
    """Update Conversational Agent prompt from JSON file in database."""
    
    # Load the prompt config
    config_path = os.path.join(os.path.dirname(__file__), "..", "configs", "conversational_agent_prompt.json")
    
    with open(config_path, 'r') as f:
        prompt_config = json.load(f)
    
    # Connect to database
    await database.connect()
    
    try:
        prompt_key = "conversational:formatting:default:response"
        
        print(f"Updating prompt with key: {prompt_key}")
        print(f"  module_name: conversational")
        print(f"  domain: formatting")
        print(f"  mode: default")
        print(f"  step: response")
        
        new_id = await prompt_manager.update_prompt(
            prompt_key=prompt_key,
            prompt_config=prompt_config,
            change_reason="Updated to handle gate questions - extract and ask questions directly instead of reformatting",
            user_context={"user_id": "system"}
        )
        
        # Get the new version number
        version_query = "SELECT version FROM prompt_templates WHERE id = :id"
        version = await database.fetch_val(version_query, {"id": new_id})
        
        print(f"✅ Successfully updated Conversational Agent prompt (ID: {new_id}, Version: {version})")
        print(f"   Key: {prompt_key}")
        
        # Verify it was updated
        verify = await prompt_manager.get_prompt(
            module_name="conversational",
            domain="formatting",
            mode="default",
            step="response"
        )
        if verify:
            print(f"✅ Verification: Prompt found in database")
            print(f"   System instructions length: {len(verify['config'].get('SYSTEM_INSTRUCTIONS', ''))} chars")
        else:
            print(f"⚠️  Verification: Prompt NOT found in database (but update_prompt returned ID: {new_id})")
        
    except ValueError as e:
        if "not found" in str(e):
            print(f"❌ Prompt not found. Please create it first using seed_conversational_agent_prompt.py")
        else:
            print(f"❌ Error: {e}")
        raise
    except Exception as e:
        print(f"❌ Error updating prompt: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        await database.disconnect()

if __name__ == "__main__":
    asyncio.run(update_conversational_agent_prompt())

