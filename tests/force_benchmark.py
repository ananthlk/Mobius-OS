import asyncio
import sys
import os
import logging
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO)
sys.path.append(os.getcwd())
load_dotenv()

from nexus.modules.database import database, init_db
from nexus.modules.llm_service import llm_service

async def force_sync():
    print("🚀 Forcing Sync & Benchmark...")
    await database.connect()
    
    # Ensure migration 007 runs
    print("   Running Migrations...")
    await init_db()
    
    # Run Sync (+ Benchmark)
    print("   Benchmarking Providers...")
    await llm_service.sync_models()
    
    # Check Result
    print("   Checking Latency Stats...")
    rows = await database.fetch_all("SELECT model_id, last_latency_ms FROM llm_models WHERE last_latency_ms IS NOT NULL")
    for r in rows:
        print(f"   ✅ {r['model_id']}: {r['last_latency_ms']} ms")
        
    await database.disconnect()

if __name__ == "__main__":
    asyncio.run(force_sync())
