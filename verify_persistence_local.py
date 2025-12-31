import asyncio
import os
import json
from nexus.modules.database import database
from nexus.modules.shaping_manager import shaping_manager
from nexus.modules.trace_manager import trace_manager

async def verify():
    print("--- Starting Local Persistence Verification ---")
    
    # 1. Connect and Init
    try:
        await database.connect()
        from nexus.modules.database import init_db
        await init_db()
        print("[OK] Connected and Migrations Applied")
    except Exception as e:
        print(f"[FAIL] Could not connect to DB: {e}")
        return

    # 2. Test Shaping Manager
    print("\n--- Testing Shaping Session ---")
    try:
        session_id = await shaping_manager.create_session("test_user_local", "Local Test Query")
        print(f"[OK] Created Session ID: {session_id}")
        
        await shaping_manager.append_message(session_id, "system", "System Reply Local")
        print(f"[OK] Appended Message to Session {session_id}")
        
        # Verify Read
        session = await shaping_manager.get_session(session_id)
        transcript = json.loads(session["transcript"])
        print(f"[INFO] Transcript Length: {len(transcript)}")
        assert len(transcript) == 2
    except Exception as e:
        print(f"[FAIL] Shaping Manager Error: {e}")

    # 3. Test Trace Manager
    print("\n--- Testing LLM Trace ---")
    try:
        trace_id = await trace_manager.log_trace(
            session_id=session_id,
            step_name="LOCAL_TEST",
            prompt_snapshot="TEST PROMPT",
            raw_completion={"text": "TEST OUTPUT"},
            model_metadata={"env": "local"}
        )
        print(f"[OK] Created Trace ID: {trace_id}")
    except Exception as e:
        print(f"[FAIL] Trace Manager Error: {e}")

    # 4. Disconnect
    await database.disconnect()
    print("\n--- Verification Complete ---")

if __name__ == "__main__":
    asyncio.run(verify())
