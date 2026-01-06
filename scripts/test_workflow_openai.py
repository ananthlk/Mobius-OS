#!/usr/bin/env python3
"""
Test that the workflow module is using OpenAI correctly.
"""
import asyncio
import sys
import os
sys.path.append(os.getcwd())

from nexus.modules.database import database
from nexus.modules.config_manager import config_manager
from nexus.modules.llm_service import llm_service

async def test_workflow_openai():
    print("🔌 Connecting to database...")
    await database.connect()
    
    try:
        # Step 1: Resolve app context for workflow module
        print("\n📋 Step 1: Resolving app context for 'workflow' module...")
        model_context = await config_manager.resolve_app_context("workflow", "test_user")
        
        print(f"   Provider: {model_context.get('provider_name')}")
        print(f"   Model: {model_context.get('model_id')}")
        print(f"   Source: {model_context.get('source')}")
        print(f"   Has API key: {bool(model_context.get('api_key'))}")
        
        if model_context.get('provider_name') != 'openai':
            print(f"\n⚠️  Warning: Expected 'openai' but got '{model_context.get('provider_name')}'")
            return
        
        # Step 2: Test a simple LLM call
        print("\n📋 Step 2: Testing LLM call with OpenAI...")
        prompt = "Say 'Hello, OpenAI is working!' in exactly 5 words."
        system_instruction = "You are a helpful assistant."
        generation_config = {"temperature": 0.7, "max_tokens": 50}
        
        print(f"   Prompt: {prompt}")
        print("   Calling OpenAI...")
        
        try:
            response_text = await llm_service.generate_text(
                prompt=prompt,
                system_instruction=system_instruction,
                model_context=model_context,
                generation_config=generation_config
            )
            
            print(f"\n✅ SUCCESS!")
            print(f"   Response: {response_text}")
            print(f"\n✅ OpenAI is working correctly for the workflow module!")
            
        except Exception as e:
            print(f"\n❌ LLM call failed: {e}")
            import traceback
            traceback.print_exc()
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await database.disconnect()
        print("\n✅ Test complete!")

if __name__ == "__main__":
    asyncio.run(test_workflow_openai())


