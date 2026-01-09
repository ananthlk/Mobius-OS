import asyncio
import os
import sys

# Add project root to path
sys.path.append(os.getcwd())

from nexus.modules.database import database

async def apply_migration():
    print("🔌 Connecting to DB...")
    await database.connect()
    
    try:
        print("📄 Reading migration file 014_prompt_management.sql...")
        with open("nexus/migrations/014_prompt_management.sql", "r") as f:
            sql = f.read()
            
        print("🚀 Executing migration...")
        # Split by command if necessary
        commands = sql.split(";")
        for cmd in commands:
            if cmd.strip():
                print(f"Executing: {cmd[:80]}...")
                await database.execute(cmd)
        print("✅ Migration 014 applied successfully.")
        print("   - Created prompt_templates table")
        print("   - Created prompt_history table")
        print("   - Created prompt_usage table")
        print("   - Added iteration tracking columns to shaping_sessions")
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await database.disconnect()

if __name__ == "__main__":
    asyncio.run(apply_migration())








