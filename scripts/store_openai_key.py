#!/usr/bin/env python3
"""
Store OpenAI API key in the encrypted vault.
Creates the OpenAI provider if it doesn't exist, then stores the API key.

Usage:
    python scripts/store_openai_key.py <api_key>
    or
    OPENAI_API_KEY=<api_key> python scripts/store_openai_key.py
"""
import asyncio
import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Load environment variables
load_dotenv(PROJECT_ROOT / ".env")
load_dotenv(PROJECT_ROOT / ".env.local")

from nexus.modules.database import connect_to_db, disconnect_from_db, database
from nexus.modules.config_manager import config_manager

async def store_openai_key(api_key: str):
    """Store OpenAI API key in the encrypted vault."""
    print("🔑 Storing OpenAI API key...")
    print("=" * 60)
    
    await connect_to_db()
    
    try:
        # Check if OpenAI provider exists
        providers = await config_manager.list_providers()
        openai_provider = None
        
        for provider in providers:
            if provider["name"].lower() == "openai":
                openai_provider = provider
                break
        
        provider_id = None
        
        if openai_provider:
            print(f"✅ Found existing OpenAI provider (ID: {openai_provider['id']})")
            provider_id = openai_provider["id"]
        else:
            print("📝 Creating new OpenAI provider...")
            # Create OpenAI provider
            user_context = {"user_id": "system", "session_id": None}
            provider_id = await config_manager.create_provider(
                name="openai",
                provider_type="openai_compatible",
                user_context=user_context,
                base_url=None  # Uses default OpenAI API endpoint
            )
            print(f"✅ Created OpenAI provider (ID: {provider_id})")
        
        # Store the API key
        print("🔐 Storing API key (encrypted)...")
        user_context = {"user_id": "system", "session_id": None}
        await config_manager.update_secret(
            provider_id=provider_id,
            key="api_key",
            value=api_key,
            user_context=user_context,
            is_secret=True
        )
        print("✅ API key stored successfully!")
        print(f"\n📋 Summary:")
        print(f"   Provider: openai (ID: {provider_id})")
        print(f"   Key stored: api_key (encrypted)")
        print(f"   Provider type: openai_compatible")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        await disconnect_from_db()

if __name__ == "__main__":
    # Get API key from command line argument or environment variable
    api_key = None
    if len(sys.argv) > 1:
        api_key = sys.argv[1]
    else:
        api_key = os.getenv("OPENAI_API_KEY")
    
    if not api_key:
        print("❌ Error: OpenAI API key required")
        print("Usage: python scripts/store_openai_key.py <api_key>")
        print("   or: OPENAI_API_KEY=<api_key> python scripts/store_openai_key.py")
        sys.exit(1)
    
    asyncio.run(store_openai_key(api_key))

