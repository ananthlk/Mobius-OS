import asyncio
import os
import sys
from dotenv import load_dotenv

# Add project root to path
sys.path.append(os.getcwd())

# Load environment variables (DATABASE_URL)
load_dotenv()

async def run_test():
    print("🏥 Starting Healthcare Audit & Soft Delete Validation...")
    
    # Imports inside async to allow env loading first if needed, 
    # but mainly to ensure modules leverage the env vars.
    from nexus.modules.database import database, init_db
    from nexus.modules.config_manager import config_manager
    
    # 1. Start DB & Migrate
    await database.connect()
    await init_db()
    
    # Context (Simulating an Admin User)
    ctx = {
        "user_id": "dr_strange_001", 
        "session_id": "sess_time_stone_v1"
    }
    
    provider_name = "audit_test_provider_v1"
    
    try:
        # ---------------------------------------------------------
        # Step 1: Create Provider
        # ---------------------------------------------------------
        print(f"\n[Step 1] Creating Provider '{provider_name}' as {ctx['user_id']}...")
        pid = await config_manager.create_provider(
            name=provider_name, 
            provider_type="vertex", 
            user_context=ctx
        )
        print(f"   ✅ Created Provider ID: {pid}")

        # Verify it shows up in list
        print("   🔍 Verifying visibility in active list...")
        all_providers = await config_manager.list_providers()
        found = any(p['id'] == pid for p in all_providers)
        if found:
            print("   ✅ Provider is visible.")
        else:
            print("   ❌ ERROR: Provider not found in list!")
            return

        # ---------------------------------------------------------
        # Step 2: Soft Delete
        # ---------------------------------------------------------
        print(f"\n[Step 2] Soft Deleting Provider ID {pid}...")
        await config_manager.delete_provider(pid, ctx)
        print("   ✅ Delete command executed.")

        # Verify it is GONE from list (Soft Delete check)
        print("   🔍 Verifying removal from active list...")
        all_providers_after = await config_manager.list_providers()
        still_there = any(p['id'] == pid for p in all_providers_after)
        if not still_there:
            print("   ✅ Provider is succcessfully hidden (Soft Deleted).")
        else:
            print("   ❌ ERROR: Provider is still visible! Soft Delete failed.")
            return

        # ---------------------------------------------------------
        # Step 3: Verify Persistence (DB Check)
        # ---------------------------------------------------------
        print("\n[Step 3] Checking Database directly for 'Ghost' record...")
        db_row = await database.fetch_one("SELECT * FROM llm_providers WHERE id = :id", {"id": pid})
        if db_row and db_row['deleted_at']:
            print(f"   ✅ Database Record Exists. Deleted At: {db_row['deleted_at']}")
        else:
             print("   ❌ ERROR: Record missing or deleted_at is NULL!")

        # ---------------------------------------------------------
        # Step 4: Verify Audit Logs
        # ---------------------------------------------------------
        print("\n[Step 4] Auditing the Auditor...")
        logs = await database.fetch_all(
            "SELECT * FROM audit_logs WHERE resource_id = :rid ORDER BY id ASC", 
            {"rid": str(pid)}
        )
        
        if len(logs) >= 2:
            print(f"   ✅ Found {len(logs)} Audit Entries:")
            for log in logs:
                print(f"      - [{log['created_at']}] ACTION: {log['action']} | BY: {log['user_id']} | RES: {log['resource_type']}")
        else:
             print(f"   ❌ ERROR: Expected at least 2 logs (CREATE, DELETE), found {len(logs)}")

    except Exception as e:
        print(f"\n❌ Test Failed with Exception: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Cleanup (Optional: Hard delete the test data to keep DB clean)
        # print("\n[Cleanup] Removing test artifacts...")
        # await database.execute("DELETE FROM audit_logs WHERE resource_id = :rid", {"rid": str(pid)})
        # await database.execute("DELETE FROM llm_providers WHERE id = :pid", {"pid": pid})
        
        await database.disconnect()
        print("\n🏥 Test Complete.")

if __name__ == "__main__":
    asyncio.run(run_test())
