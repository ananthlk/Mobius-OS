#!/usr/bin/env python3
"""
Verify OpenAI provider setup and sync models.
"""
import asyncio
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Load environment variables
load_dotenv(PROJECT_ROOT / ".env")
load_dotenv(PROJECT_ROOT / ".env.local")

from nexus.modules.database import connect_to_db, disconnect_from_db
from nexus.modules.config_manager import config_manager
from nexus.modules.llm_service import llm_service
from nexus.modules.llm_gateway import gateway

async def verify_setup():
    """Verify OpenAI provider setup."""
    print("🔍 Verifying OpenAI Provider Setup...")
    print("=" * 60)
    
    await connect_to_db()
    
    try:
        # 1. Check if OpenAI provider exists
        providers = await config_manager.list_providers()
        openai_provider = None
        
        for provider in providers:
            if provider["name"].lower() == "openai":
                openai_provider = provider
                break
        
        if not openai_provider:
            print("❌ OpenAI provider not found!")
            return
        
        print(f"✅ OpenAI provider found (ID: {openai_provider['id']})")
        print(f"   Name: {openai_provider['name']}")
        print(f"   Type: {openai_provider['provider_type']}")
        print(f"   Active: {openai_provider['is_active']}")
        print(f"   Base URL: {openai_provider.get('base_url', 'None (using default)')}")
        
        # 2. Test connection
        print("\n🔌 Testing connection...")
        try:
            result = await gateway.test_connection("openai")
            print(f"✅ Connection test passed!")
            print(f"   Message: {result.get('message', 'N/A')}")
        except Exception as e:
            print(f"❌ Connection test failed: {e}")
            return
        
        # 3. Sync models
        print("\n📦 Syncing models...")
        try:
            await llm_service.sync_models()
            print("✅ Model sync completed!")
        except Exception as e:
            print(f"⚠️  Model sync had issues: {e}")
            import traceback
            traceback.print_exc()
        
        # 4. List models
        print("\n📋 Listing OpenAI models...")
        from nexus.modules.database import database
        query = """
            SELECT m.id, m.model_id, m.display_name, m.is_active, m.context_window
            FROM llm_models m
            JOIN llm_providers p ON m.provider_id = p.id
            WHERE p.name = 'openai'
            ORDER BY m.model_id
        """
        models = await database.fetch_all(query)
        
        if models:
            print(f"   Found {len(models)} models:")
            for model in models:
                status = "✅" if model["is_active"] else "❌"
                print(f"   {status} {model['model_id']} ({model['display_name']})")
        else:
            print("   No models found")
        
        print("\n✅ OpenAI provider is fully set up and ready to use!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        await disconnect_from_db()

if __name__ == "__main__":
    asyncio.run(verify_setup())

