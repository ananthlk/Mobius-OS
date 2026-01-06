#!/usr/bin/env python3
"""
Deactivate old Gemini models, keeping only the three specified models:
- gemini-2.0-flash
- gemini-2.5-flash
- gemini-2.5-pro
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

# The three valid models
VALID_MODELS = ["gemini-2.0-flash", "gemini-2.5-flash", "gemini-2.5-pro"]

async def cleanup_old_models():
    """Deactivate old Gemini models."""
    print("🧹 Cleaning up old Gemini models...")
    print("=" * 60)
    
    await connect_to_db()
    
    try:
        # 1. Get all Gemini models
        query = """
            SELECT m.id, m.model_id, m.display_name, m.is_active
            FROM llm_models m
            JOIN llm_providers p ON m.provider_id = p.id
            WHERE p.name = 'google_vertex'
            ORDER BY m.model_id
        """
        all_models = await database.fetch_all(query)
        
        print(f"📋 Found {len(all_models)} total Gemini models")
        
        # 2. Find models to deactivate
        models_to_deactivate = [m for m in all_models if m["model_id"] not in VALID_MODELS]
        models_to_keep = [m for m in all_models if m["model_id"] in VALID_MODELS]
        
        print(f"\n✅ Models to keep (active): {len(models_to_keep)}")
        for m in models_to_keep:
            print(f"   - {m['model_id']} ({m['display_name']})")
        
        print(f"\n❌ Models to deactivate: {len(models_to_deactivate)}")
        for m in models_to_deactivate[:10]:  # Show first 10
            status = "✅" if m["is_active"] else "❌"
            print(f"   {status} {m['model_id']} ({m['display_name']})")
        if len(models_to_deactivate) > 10:
            print(f"   ... and {len(models_to_deactivate) - 10} more")
        
        # 3. Deactivate old models
        if models_to_deactivate:
            print(f"\n🔧 Deactivating {len(models_to_deactivate)} old models...")
            ids_to_deactivate = [m["id"] for m in models_to_deactivate]
            
            # Build IN clause with individual IDs
            placeholders = ",".join([f":id{i}" for i in range(len(ids_to_deactivate))])
            deactivate_query = f"""
                UPDATE llm_models 
                SET is_active = false 
                WHERE id IN ({placeholders})
            """
            params = {f"id{i}": id_val for i, id_val in enumerate(ids_to_deactivate)}
            await database.execute(deactivate_query, params)
            print("✅ Old models deactivated!")
        else:
            print("\n✅ No old models to deactivate!")
        
        # 4. Ensure valid models are active
        print(f"\n🔧 Ensuring valid models are active...")
        ids_to_activate = [m["id"] for m in models_to_keep]
        if ids_to_activate:
            # Build IN clause with individual IDs
            placeholders = ",".join([f":id{i}" for i in range(len(ids_to_activate))])
            activate_query = f"""
                UPDATE llm_models 
                SET is_active = true 
                WHERE id IN ({placeholders})
            """
            params = {f"id{i}": id_val for i, id_val in enumerate(ids_to_activate)}
            await database.execute(activate_query, params)
            print("✅ Valid models activated!")
        
        # 5. Show final status
        print("\n📊 Final status:")
        final_models = await database.fetch_all(query)
        active_models = [m for m in final_models if m["is_active"]]
        inactive_models = [m for m in final_models if not m["is_active"]]
        
        print(f"   Active models: {len(active_models)}")
        for m in active_models:
            print(f"      ✅ {m['model_id']} ({m['display_name']})")
        
        print(f"\n   Inactive models: {len(inactive_models)}")
        if inactive_models:
            print(f"      (Hidden from UI)")
        
        print("\n✅ Cleanup complete! Refresh your frontend to see the changes.")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        await disconnect_from_db()

if __name__ == "__main__":
    asyncio.run(cleanup_old_models())

