#!/usr/bin/env python3
"""
Set the workflow module to use OpenAI (gpt-3.5-turbo) as the default model.
"""
import asyncio
import sys
import os
sys.path.append(os.getcwd())

from nexus.modules.database import database
from nexus.modules.llm_governance import llm_governance

async def set_workflow_to_openai():
    print("🔌 Connecting to database...")
    await database.connect()
    
    try:
        # Find OpenAI provider
        print("\n🔍 Checking OpenAI provider...")
        provider_query = "SELECT id, name, provider_type, is_active FROM llm_providers WHERE name = 'openai'"
        provider = await database.fetch_one(provider_query)
        
        if not provider:
            print("❌ OpenAI provider not found!")
            print("   Please create it via Admin UI at /dashboard/admin/llms")
            return
        
        if not provider["is_active"]:
            print("⚠️  OpenAI provider exists but is not active!")
            print("   Activating it...")
            await database.execute(
                "UPDATE llm_providers SET is_active = true WHERE id = :id",
                {"id": provider["id"]}
            )
        
        print(f"✅ OpenAI provider found (ID: {provider['id']}, Type: {provider['provider_type']})")
        
        # Check if API key is configured
        print("\n🔍 Checking API key configuration...")
        api_key_query = """
            SELECT config_key, is_secret 
            FROM llm_config 
            WHERE provider_id = :pid AND config_key = 'api_key'
        """
        api_key = await database.fetch_one(api_key_query, {"pid": provider["id"]})
        
        if not api_key:
            print("⚠️  OpenAI API key not configured!")
            print("   Please configure it via Admin UI at /dashboard/admin/llms")
            print("   Or use: scripts/store_openai_key.py")
        else:
            print("✅ OpenAI API key is configured")
        
        # Find OpenAI models
        print("\n🔍 Finding OpenAI models...")
        models_query = """
            SELECT m.id, m.model_id, m.display_name, m.is_active
            FROM llm_models m
            JOIN llm_providers p ON m.provider_id = p.id
            WHERE p.name = 'openai' AND m.is_active = true
            ORDER BY m.id
        """
        models = await database.fetch_all(models_query)
        
        if not models:
            print("❌ No active OpenAI models found!")
            print("   Please sync models by running llm_service.sync_models()")
            return
        
        print(f"✅ Found {len(models)} OpenAI model(s):")
        for model in models:
            print(f"   - {model['model_id']} (ID: {model['id']}, Display: {model['display_name']})")
        
        # Prefer gpt-3.5-turbo, fallback to first available
        target_model = None
        for model in models:
            if model['model_id'] == 'gpt-3.5-turbo':
                target_model = model
                break
        
        if not target_model:
            target_model = models[0]
            print(f"\n⚠️  gpt-3.5-turbo not found, using {target_model['model_id']} instead")
        
        print(f"\n✅ Using model: {target_model['model_id']} (ID: {target_model['id']})")
        
        # Set workflow module default
        print("\n🛠️  Setting workflow module default...")
        await llm_governance.set_system_rule('MODULE', 'workflow', target_model['id'])
        print("✅ Set workflow module default to OpenAI")
        
        # Verify
        print("\n🔍 Verifying configuration...")
        resolution = await llm_governance.resolve_model('workflow', 'system')
        print(f"✅ Verification: workflow module will use:")
        print(f"   Model: {resolution['model_id']}")
        print(f"   Provider: {resolution['provider_name']}")
        print(f"   Source: {resolution['source']}")
        
        if resolution['provider_name'] != 'openai':
            print("\n⚠️  Warning: Resolution returned different provider!")
            print("   This might be due to user preferences or other rules.")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await database.disconnect()
        print("\n✅ Done!")

if __name__ == "__main__":
    asyncio.run(set_workflow_to_openai())

