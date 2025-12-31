import asyncio
import sys
import os
import logging
from dotenv import load_dotenv

# Setup logging
logging.basicConfig(level=logging.INFO)
sys.path.append(os.getcwd())
load_dotenv()

from nexus.modules.database import database
from nexus.modules.config_manager import config_manager
from nexus.modules.llm_gateway import gateway

async def verify_gemma():
    print("🧪 Verifying Gemma Integration...")
    
    await database.connect()
    
    try:
        # 1. Check Governance Resolution
        print("\n[Step 1] Resolving Model for 'chat' module...")
        context = await config_manager.resolve_app_context("chat", "user_default")
        print(f"   ✅ Apps will use: {context['model_id']} (Provider: {context['provider_name']})")
        
        if "gemma" not in context['model_id'].lower():
            print("   ⚠️ WARNING: Resolved model is NOT Gemma. Did you set the rule in Governance?")
        
        # 2. End-to-End Generation
        print("\n[Step 2] Sending Prompt to Gateway...")
        response = await gateway.chat_completion(
            messages=[{"role": "user", "content": "Hello! Who are you?"}],
            module_id="chat",
            user_id="user_default"
        )
        
        print("\n   ✅ Response Received:")
        print(f"      Model: {response['model']}")
        print(f"      Content: {response['content']}")
        print(f"      Provider: {response['provider']}")
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await database.disconnect()

if __name__ == "__main__":
    asyncio.run(verify_gemma())
