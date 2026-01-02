import asyncio
import os
import sys

# Add project root to path
sys.path.append(os.getcwd())

from nexus.modules.database import database

async def check_rules():
    print("🔌 Connecting to DB...")
    await database.connect()
    
    try:
        print("\n🔍 Checking llm_system_rules:")
        rules = await database.fetch_all("SELECT * FROM llm_system_rules")
        for r in rules:
            print(dict(r))
            
        print("\n🔍 Checking referenced models:")
        if rules:
            model_ids = [r["model_id"] for r in rules]
            # Handle single item tuple syntax for SQL IN clause
            if len(model_ids) == 1:
                query = f"SELECT * FROM llm_models WHERE id = {model_ids[0]}"
            else:
                query = f"SELECT * FROM llm_models WHERE id IN {tuple(model_ids)}"
                
            models = await database.fetch_all(query)
            for m in models:
                print(dict(m))
        else:
            print("No system rules found.")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        await database.disconnect()

if __name__ == "__main__":
    asyncio.run(check_rules())
