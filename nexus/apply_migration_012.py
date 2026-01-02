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
        print("📄 Reading migration file 012_fix_trace_logs_fk.sql...")
        with open("nexus/migrations/012_fix_trace_logs_fk.sql", "r") as f:
            sql = f.read()
            
        print("🚀 Executing migration...")
        # Split by command if necessary
        commands = sql.split(";")
        for cmd in commands:
            if cmd.strip():
                print(f"Executing: {cmd[:50]}...")
                await database.execute(cmd)
        print("✅ Migration applied successfully.")
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
    finally:
        await database.disconnect()

if __name__ == "__main__":
    asyncio.run(apply_migration())
