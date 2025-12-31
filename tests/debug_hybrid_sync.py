import asyncio
import os
from dotenv import load_dotenv

# Load Env (for MOBIUS_MASTER_KEY and DATABASE_URL)
load_dotenv()

# Mocking the minimal environment to run the logic without full App context
from nexus.modules.database import database
from nexus.modules.crypto import decrypt
import google.generativeai as genai
import time

async def test_hybrid_sync():
    print("🚀 Starting Hybrid Sync Debugger...")
    
    # 1. Connect DB
    await database.connect()
    print("✅ Database Connected.")
    
    # 2. Get Vertex Provider ID
    p_row = await database.fetch_one("SELECT id, name FROM llm_providers WHERE provider_type = 'vertex'")
    if not p_row:
        print("❌ No Vertex provider found in DB.")
        return
    
    provider_id = p_row["id"]
    provider_name = p_row["name"]
    print(f"👉 Testing Provider: {provider_name} (ID: {provider_id})")
    
    # 3. Fetch & Decrypt Secrets
    s_query = "SELECT config_key, encrypted_value, is_secret FROM llm_config WHERE provider_id = :pid"
    s_rows = await database.fetch_all(s_query, {"pid": provider_id})
    secrets = {}
    for row in s_rows:
            try:
                val = decrypt(row["encrypted_value"]) if row["is_secret"] else row["encrypted_value"]
            except Exception as e:
                val = f"[Decrypt Error: {e}]"
            secrets[row["config_key"]] = val

    api_key = secrets.get("api_key", "")
    project_id = secrets.get("project_id", "")
    
    print("\n🔑 Credentials Found:")
    print(f"   - Project ID: {project_id}")
    if len(api_key) > 10:
        masked = api_key[:4] + "..." + api_key[-4:]
        print(f"   - API Key:    {masked} (Valid Length)")
    else:
        print(f"   - API Key:    (Missing or Short) -> '{api_key}'")

    # 4. Run Logic
    if len(api_key) > 10:
        print("\n⚡️ Mode: AI Studio (API Key)")
        try:
            genai.configure(api_key=api_key)
            
            print("   👉 Listing Models (genai.list_models)...")
            found = []
            for m in genai.list_models():
                if "generateContent" in m.supported_generation_methods:
                    found.append(m.name)
            
            print(f"   ✅ Found {len(found)} models: {found}")
            
            target = "gemini-1.5-flash"
            print(f"   👉 Probing {target}...")
            model = genai.GenerativeModel(target)
            resp = await model.generate_content_async("Hello")
            print(f"   ✅ Response: {resp.text.strip()}")
            
        except Exception as e:
            print(f"   ❌ API Failure: {e}")
            
    elif project_id:
        print("\n☁️ Mode: Vertex AI (GCP)")
        # ... (Vertex Logic omitted for brevity as we focus on Key)
        print("   (Skipping Vertex Test - User wants API Key)")
    else:
        print("❌ No valid credentials.")

    await database.disconnect()

if __name__ == "__main__":
    asyncio.run(test_hybrid_sync())
