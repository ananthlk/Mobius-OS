#!/usr/bin/env python3
"""
Clean up irrelevant models from the database.
- Gemini: Keep only gemini-2.0-flash, gemini-2.5-flash, gemini-2.5-pro
- OpenAI: Keep only commonly used models (gpt-4-turbo, gpt-4o, gpt-3.5-turbo variants)
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

from nexus.modules.database import connect_to_db, disconnect_from_db, database

# Valid Gemini models
VALID_GEMINI_MODELS = ["gemini-2.0-flash", "gemini-2.5-flash", "gemini-2.5-pro"]

# Valid OpenAI models - keep only the most commonly used
VALID_OPENAI_MODELS = [
    # GPT-4 variants
    "gpt-4-turbo",
    "gpt-4-turbo-preview",
    "gpt-4-turbo-2024-04-09",
    "gpt-4o",
    "gpt-4o-2024-05-13",
    "gpt-4o-2024-08-06",
    "gpt-4o-2024-11-20",
    "gpt-4o-mini",
    "gpt-4o-mini-2024-07-18",
    # GPT-3.5 variants
    "gpt-3.5-turbo",
    "gpt-3.5-turbo-1106",
    "gpt-3.5-turbo-0125",
    "gpt-3.5-turbo-16k",
    # o1 models
    "o1-preview",
    "o1-mini",
]

async def cleanup_models():
    """Delete irrelevant models from the database."""
    print("🧹 Cleaning up irrelevant models...")
    print("=" * 60)
    
    await connect_to_db()
    
    try:
        # 1. Get provider IDs
        providers_query = "SELECT id, name FROM llm_providers WHERE name IN ('google_vertex', 'openai')"
        providers = await database.fetch_all(providers_query)
        provider_map = {p["name"]: p["id"] for p in providers}
        
        vertex_id = provider_map.get("google_vertex")
        openai_id = provider_map.get("openai")
        
        if not vertex_id:
            print("❌ Google Vertex provider not found!")
        if not openai_id:
            print("❌ OpenAI provider not found!")
        
        total_deleted = 0
        
        # 2. Clean up Gemini models
        if vertex_id:
            print("\n🔍 Checking Gemini models...")
            gemini_query = """
                SELECT id, model_id, display_name, is_active
                FROM llm_models
                WHERE provider_id = :pid
                ORDER BY model_id
            """
            gemini_models = await database.fetch_all(gemini_query, {"pid": vertex_id})
            
            models_to_delete = [m for m in gemini_models if m["model_id"] not in VALID_GEMINI_MODELS]
            models_to_keep = [m for m in gemini_models if m["model_id"] in VALID_GEMINI_MODELS]
            
            print(f"   Found {len(gemini_models)} total Gemini models")
            print(f"   Keeping {len(models_to_keep)} valid models:")
            for m in models_to_keep:
                print(f"      ✅ {m['model_id']} ({m['display_name']})")
            
            print(f"   Deleting {len(models_to_delete)} invalid models...")
            if models_to_delete:
                for m in models_to_delete[:5]:  # Show first 5
                    print(f"      ❌ {m['model_id']} ({m['display_name']})")
                if len(models_to_delete) > 5:
                    print(f"      ... and {len(models_to_delete) - 5} more")
                
                # Delete models (CASCADE will handle related records)
                ids_to_delete = [m["id"] for m in models_to_delete]
                placeholders = ",".join([f":id{i}" for i in range(len(ids_to_delete))])
                delete_query = f"""
                    DELETE FROM llm_models 
                    WHERE id IN ({placeholders})
                """
                params = {f"id{i}": id_val for i, id_val in enumerate(ids_to_delete)}
                await database.execute(delete_query, params)
                deleted_count = len(ids_to_delete)
                total_deleted += deleted_count
                print(f"   ✅ Deleted {deleted_count} Gemini models")
        
        # 3. Clean up OpenAI models
        if openai_id:
            print("\n🔍 Checking OpenAI models...")
            openai_query = """
                SELECT id, model_id, display_name, is_active
                FROM llm_models
                WHERE provider_id = :pid
                ORDER BY model_id
            """
            openai_models = await database.fetch_all(openai_query, {"pid": openai_id})
            
            models_to_delete = [m for m in openai_models if m["model_id"] not in VALID_OPENAI_MODELS]
            models_to_keep = [m for m in openai_models if m["model_id"] in VALID_OPENAI_MODELS]
            
            print(f"   Found {len(openai_models)} total OpenAI models")
            print(f"   Keeping {len(models_to_keep)} valid models:")
            for m in models_to_keep[:10]:  # Show first 10
                print(f"      ✅ {m['model_id']} ({m['display_name']})")
            if len(models_to_keep) > 10:
                print(f"      ... and {len(models_to_keep) - 10} more")
            
            print(f"   Deleting {len(models_to_delete)} invalid models...")
            if models_to_delete:
                for m in models_to_delete[:10]:  # Show first 10
                    print(f"      ❌ {m['model_id']} ({m['display_name']})")
                if len(models_to_delete) > 10:
                    print(f"      ... and {len(models_to_delete) - 10} more")
                
                # Delete models
                ids_to_delete = [m["id"] for m in models_to_delete]
                placeholders = ",".join([f":id{i}" for i in range(len(ids_to_delete))])
                delete_query = f"""
                    DELETE FROM llm_models 
                    WHERE id IN ({placeholders})
                """
                params = {f"id{i}": id_val for i, id_val in enumerate(ids_to_delete)}
                await database.execute(delete_query, params)
                deleted_count = len(ids_to_delete)
                total_deleted += deleted_count
                print(f"   ✅ Deleted {deleted_count} OpenAI models")
        
        # 4. Show final summary
        print("\n📊 Final Summary:")
        if vertex_id:
            gemini_final = await database.fetch_all(gemini_query, {"pid": vertex_id})
            print(f"   Gemini: {len(gemini_final)} models remaining")
            for m in gemini_final:
                print(f"      ✅ {m['model_id']} ({m['display_name']})")
        
        if openai_id:
            openai_final = await database.fetch_all(openai_query, {"pid": openai_id})
            print(f"\n   OpenAI: {len(openai_final)} models remaining")
            for m in openai_final[:15]:  # Show first 15
                print(f"      ✅ {m['model_id']} ({m['display_name']})")
            if len(openai_final) > 15:
                print(f"      ... and {len(openai_final) - 15} more")
        
        print(f"\n✅ Cleanup complete! Deleted {total_deleted} models total.")
        print("   Refresh your frontend to see the changes.")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        await disconnect_from_db()

if __name__ == "__main__":
    asyncio.run(cleanup_models())




