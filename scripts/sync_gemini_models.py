#!/usr/bin/env python3
"""
Sync Gemini models to update database with the three correct models.
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

async def sync_gemini_models():
    """Sync Gemini models to update database."""
    print("🔄 Syncing Gemini Models...")
    print("=" * 60)
    
    await connect_to_db()
    
    try:
        # 1. Check if google_vertex provider exists
        providers = await config_manager.list_providers()
        vertex_provider = None
        
        for provider in providers:
            if provider["name"].lower() == "google_vertex":
                vertex_provider = provider
                break
        
        if not vertex_provider:
            print("❌ Google Vertex provider not found!")
            return
        
        print(f"✅ Google Vertex provider found (ID: {vertex_provider['id']})")
        
        # 2. List current models
        from nexus.modules.database import database
        query = """
            SELECT m.id, m.model_id, m.display_name, m.is_active
            FROM llm_models m
            JOIN llm_providers p ON m.provider_id = p.id
            WHERE p.name = 'google_vertex'
            ORDER BY m.model_id
        """
        current_models = await database.fetch_all(query)
        print(f"\n📋 Current models in database: {len(current_models)}")
        for model in current_models[:10]:  # Show first 10
            status = "✅" if model["is_active"] else "❌"
            print(f"   {status} {model['model_id']} ({model['display_name']})")
        if len(current_models) > 10:
            print(f"   ... and {len(current_models) - 10} more")
        
        # 3. Sync models (this will upsert the new known_models)
        print("\n🔄 Running model sync...")
        await llm_service.sync_models()
        print("✅ Model sync completed!")
        
        # 4. List updated models
        print("\n📋 Updated models after sync:")
        updated_models = await database.fetch_all(query)
        print(f"   Total models: {len(updated_models)}")
        
        # Show the three expected models
        expected_models = ["gemini-2.0-flash", "gemini-2.5-flash", "gemini-2.5-pro"]
        print("\n✅ Expected models (from known_models):")
        for expected_id in expected_models:
            found = [m for m in updated_models if m["model_id"] == expected_id]
            if found:
                model = found[0]
                status = "✅" if model["is_active"] else "❌"
                print(f"   {status} {model['model_id']} ({model['display_name']}) - Active: {model['is_active']}")
            else:
                print(f"   ❌ {expected_id} - NOT FOUND")
        
        print("\n💡 Note: Old models may still exist in the database.")
        print("   They won't be removed by sync, but new models should be present.")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        await disconnect_from_db()

if __name__ == "__main__":
    asyncio.run(sync_gemini_models())




