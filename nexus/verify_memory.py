import asyncio
import logging
import sys
import os

# Ensure we can import nexus
sys.path.append(os.getcwd())

from nexus.modules.shaping_manager import shaping_manager
from nexus.modules.database import database

# Configure logging to stdout so we can capture it in the tool output
root = logging.getLogger()
root.setLevel(logging.DEBUG)
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s :: %(message)s"))
root.addHandler(handler)

async def main():
    print(">>> STARTING MEMORY ARCHITECTURE VERIFICATION <<<")
    
    # Ensure DB is connected (assumes DATABASE_URL is set in env)
    # If not, we might fail, but let's try.
    try:
        await database.connect()
    except Exception as e:
        print(f"DB Connect Error: {e}")
        # Build might fail if no DB, but we want to test logic. 
        # Ideally we mock DB if no env, but let's assume env is ok as server was running.
        return

    try:
        # 1. Create Session (Should trigger THINKING, ARTIFACTS, PERSISTENCE)
        print("\n[ACTION] Creating Session...")
        session_id = await shaping_manager.create_session("test_user", "find eligibility for medicaid")
        
        # 2. Append Message (Should trigger OUTPUT, PERSISTENCE, THINKING, ARTIFACTS)
        print("\n[ACTION] Appending Chat...")
        await shaping_manager.append_message(session_id, "user", "yes, please use the evidence based plan")
        
    except Exception as e:
        print(f"Execution Error: {e}")
    finally:
        await database.disconnect()
        print("\n>>> VERIFICATION COMPLETE <<<")

if __name__ == "__main__":
    asyncio.run(main())
