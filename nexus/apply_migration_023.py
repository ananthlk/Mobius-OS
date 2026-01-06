"""
Apply Migration 023: Active Agent State Machine
Adds active_agent column to shaping_sessions table.
"""
import asyncio
import os
from nexus.modules.database import database

async def apply_migration():
    print("🚀 Connecting to database...")
    await database.connect()
    
    try:
        migration_file = "nexus/migrations/023_active_agent_state.sql"
        print(f"▶️ Applying migration: {migration_file}")
        
        with open(migration_file, "r") as f:
            sql = f.read()
        
        # Split by ';' if multiple statements exist
        statements = [s.strip() for s in sql.split(";") if s.strip()]
        
        async with database.transaction():
            for stmt in statements:
                if stmt.strip():
                    try:
                        await database.execute(stmt)
                        print(f"✅ Executed: {stmt[:50]}...")
                    except Exception as e:
                        # Check if it's a "column already exists" error - that's OK
                        if "already exists" in str(e).lower() or "duplicate" in str(e).lower():
                            print(f"⚠️  Column/object already exists (skipping): {e}")
                        else:
                            raise
        
        print("✅ Migration 023 applied successfully!")
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        raise
    finally:
        await database.disconnect()
        print("🔌 Disconnected from database")

if __name__ == "__main__":
    asyncio.run(apply_migration())




