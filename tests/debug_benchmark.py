import asyncio
import httpx
import sys
import os
from dotenv import load_dotenv

sys.path.append(os.getcwd())
load_dotenv()

from nexus.modules.database import database
from nexus.modules.llm_service import llm_service

async def test_endpoint():
    print("🔬 Debugging Benchmark Endpoint...")
    
    # 1. Connect DB to find a valid model ID
    await database.connect()
    row = await database.fetch_one("SELECT id, model_id FROM llm_models LIMIT 1")
    if not row:
        print("❌ No models found in DB.")
        return
    
    model_id = row['id']
    model_name = row['model_id']
    print(f"   Targeting Model ID: {model_id} ({model_name})")
    
    # 2. Test Function Call Directly (verify internal logic)
    print("   Running llm_service.benchmark_single_model() directly...")
    try:
        latency = await llm_service.benchmark_single_model(model_id)
        print(f"   ✅ Direct Call Success: {latency} ms")
    except Exception as e:
        print(f"   ❌ Direct Call Failed: {e}")
        import traceback
        traceback.print_exc()

    # 3. Test API Endpoint (verify Router/HTTP)
    print("\n   Testing API Endpoint (POST)...")
    url = f"http://localhost:8000/api/admin/ai/models/{model_id}/benchmark"
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(url, timeout=10.0)
            print(f"   Status Code: {resp.status_code}")
            print(f"   Response: {resp.text}")
        except Exception as e:
            print(f"   ❌ HTTP Request Failed: {e}")

    await database.disconnect()

if __name__ == "__main__":
    asyncio.run(test_endpoint())
