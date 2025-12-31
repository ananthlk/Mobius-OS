import os
import vertexai
from vertexai.generative_models import GenerativeModel
import google.auth

# Configuration
PROJECT_ID = "mobiusos-482817"
LOCATION = "us-central1"
MODEL_ID = "gemini-1.5-pro-001"

def verify_vertex():
    print("☁️  Verifying Vertex AI (GCP Auth)...")
    
    # 1. Check Credentials
    try:
        creds, project = google.auth.default()
        print(f"   ✅ Credentials found: {type(creds)}")
        print(f"   ✅ Default Project: {project}")
        print(f"   ℹ️  Quota Project: {getattr(creds, 'quota_project_id', 'N/A')}")
    except Exception as e:
        print(f"   ❌ ADC Error: {e}")
        return

    # 2. Iterate Regions & Models
    # 2. Iterate Regions & Models
    regions = ["us-central1", "us-east4", "northamerica-northeast1"]
    models = [
        "gemini-2.0-flash-exp", 
        "gemini-exp-1206",
        "chat-bison", 
        "text-bison", 
        "chat-bison@002",
        "gemini-1.0-pro-002"
    ]
    
    for loc in regions:
        print(f"\n🌍 Testing Region: {loc}")
        try:
            vertexai.init(project=PROJECT_ID, location=loc)
        except Exception as e:
            print(f"   ❌ Init Failed: {e}")
            continue
            
        for m in models:
            print(f"   👉 Probing {m}...", end=" ")
            try:
                model = GenerativeModel(m)
                resp = model.generate_content("hi")
                print(f"✅ SUCCESS!")
                print(f"      Response: {resp.text.strip()[:50]}...")
                return # Stop on first success
            except Exception as e:
                # Shorten error
                err = str(e).split('\n')[0]
                if "404" in err: print("❌ 404 (Not Found)")
                else: print(f"❌ Error: {err}")
        
    # 4. List Models (to see what IS available)
    print(f"\n👉 Listing Available Models (Model Garden)...")
    try:
        from google.cloud import aiplatform
        aiplatform.init(project=PROJECT_ID, location=LOCATION)
        # listing is complex in Vertex SDK, relying on probe is better, but let's try
        print("   (Skipping complex list, relying on direct probe)")
    except:
        pass

if __name__ == "__main__":
    verify_vertex()
