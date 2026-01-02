#!/usr/bin/env python3
import asyncio
from nexus.modules.database import database

async def main():
    await database.connect()
    
    # Run migration 015
    sql1 = "ALTER TABLE shaping_sessions ADD COLUMN IF NOT EXISTS gate_state JSONB DEFAULT '{}'::jsonb;"
    await database.execute(sql1)
    print("✓ Added gate_state column")
    
    sql2 = "CREATE INDEX IF NOT EXISTS idx_shaping_sessions_gate_state ON shaping_sessions USING GIN (gate_state);"
    await database.execute(sql2)
    print("✓ Created index")
    
    await database.disconnect()
    print("✓ Migration 015 complete")

if __name__ == "__main__":
    asyncio.run(main())


