import google.auth
import os

def check_auth():
    print("🔐 Checking Google Auth (ADC)...")
    try:
        creds, project = google.auth.default()
        print(f"   ✅ Credentials Found: {type(creds)}")
        print(f"   ✅ Default Project: {project}")
        print(f"   ℹ️  Service Account Email (if available): {getattr(creds, 'service_account_email', 'N/A')}")
        print(f"   ℹ️  Quota Project: {getattr(creds, 'quota_project_id', 'N/A')}")
        
    except Exception as e:
        print(f"   ❌ ADC Error: {e}")
        print("   👉 Run: `gcloud auth application-default login`")

if __name__ == "__main__":
    check_auth()
