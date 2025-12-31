import asyncio
import sys
import os
import logging
from dotenv import load_dotenv

# Setup logging to see warnings
logging.basicConfig(level=logging.INFO)
root = logging.getLogger()
root.setLevel(logging.INFO)

sys.path.append(os.getcwd())
load_dotenv()

from nexus.modules.database import database
from nexus.modules.llm_service import llm_service

async def run_debug():
    print("🔧 Debugging Sync Models...")
    try:
        await database.connect()
        
        # 1. Trigger Sync
        print("   Calling sync_models()...")
        await llm_service.sync_models()
        
        # 2. Check Results
        print("   Checking DB results...")
        rows = await database.fetch_all("SELECT * FROM llm_models")
        print(f"   found {len(rows)} total models in DB.")
        for r in rows:
            print(f"   - {r['model_id']} (Provider: {r['provider_id']})")
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await database.disconnect()

if __name__ == "__main__":
    asyncio.run(run_debug())
