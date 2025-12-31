import asyncio
import sys
import os
from dotenv import load_dotenv

sys.path.append(os.getcwd())
load_dotenv()

from nexus.modules.database import database
from nexus.modules.llm_service import llm_service
# Set DB for service
llm_service.db = database

async def debug_vertex_discovery():
    print("🔬 Debugging Vertex Discovery...")
    
    # 1. Connect
    await database.connect()
    
    # 2. Get Vertex Provider
    provider = await database.fetch_one("SELECT * FROM llm_providers WHERE provider_type='vertex'")
    if not provider:
        print("❌ No Vertex provider found.")
        return

    print(f"   Provider: {provider['name']} (ID: {provider['id']})")
    
    # Decrypt Manually
    s_query = "SELECT config_key, encrypted_value, is_secret FROM llm_config WHERE provider_id = :pid"
    s_rows = await database.fetch_all(s_query, {"pid": provider['id']})
    
    try:
        from nexus.modules.crypto import decrypt
        s_map = {}
        for row in s_rows:
             if row['is_secret']:
                  try:
                      s_map[row['config_key']] = decrypt(row['encrypted_value'])
                      print(f"   🔓 {row['config_key']} decrypted.")
                  except Exception as e:
                      print(f"   ❌ {row['config_key']} decryption FAILED: {e}")
             else:
                  s_map[row['config_key']] = row['encrypted_value']
    except Exception as e:
        print(f"   ❌ Decryption Setup Failed: {e}")
        return

    project_id = s_map.get("project_id")
    location = s_map.get("location", "us-central1")
    
    print(f"   Project: {project_id}")
    print(f"   Location: {location}")

    if not project_id:
        print("   ❌ Project ID missing.")
        return

    import vertexai
    from vertexai.generative_models import GenerativeModel
    
    try:
        vertexai.init(project=project_id, location=location)
        print("   ✅ vertexai.init() success")
    except Exception as e:
        print(f"   ❌ vertexai.init() failed: {e}")
        return

    candidates = [
        "gemini-1.5-pro-001",
        "gemini-1.5-flash-001",
        "gemini-1.0-pro-001",
        "gemini-1.5-pro", # Legacy
        "gemini-1.5-flash" 
    ]
    
    print("\n   🔍 Probing Candidates:")
    for model_id in candidates:
        print(f"   👉 Testing {model_id}...", end=" ")
        try:
            model = GenerativeModel(model_id)
            # Use generation to truly test (checking object creation isn't enough usually, as it's lazy)
            # Just ping
            resp = await model.generate_content_async("ping")
            print(f"✅ OK")
        except Exception as e:
            err = str(e).replace("\n", " ")
            if "404" in err:
                print(f"❌ 404 Not Found")
            elif "403" in err:
                print(f"❌ 403 Permission Denied")
            else:
                print(f"❌ FAILED: {err[:100]}...")

    await database.disconnect()

if __name__ == "__main__":
    asyncio.run(debug_vertex_discovery())
