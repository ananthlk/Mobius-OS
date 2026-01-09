#!/usr/bin/env python3
"""
Apply migration 020_planning_phase.sql
Run this to add planning phase columns to shaping_sessions table.
"""
import asyncio
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from nexus.modules.database import database

async def apply_migration():
    print("🚀 Connecting to DB...")
    await database.connect()
    try:
        print("▶️ Applying migration 020_planning_phase.sql...")
        
        migration_file = "nexus/migrations/020_planning_phase.sql"
        with open(migration_file, "r") as f:
            sql = f.read()
        
        # Split by ';' if multiple statements exist
        statements = [s.strip() for s in sql.split(";") if s.strip()]
        
        async with database.transaction():
            for stmt in statements:
                if stmt.strip():
                    print(f"  Executing: {stmt[:50]}...")
                    await database.execute(stmt)
        
        print("✅ Migration 020 applied successfully.")
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        raise
    finally:
        await database.disconnect()

if __name__ == "__main__":
    asyncio.run(apply_migration())







