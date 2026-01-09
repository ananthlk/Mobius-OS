"""
Fix Migration 033 - Reset tracking so it re-runs with new file
"""
import asyncio
import os
import sys

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)

from dotenv import load_dotenv
load_dotenv()

from nexus.modules.database import database, connect_to_db, disconnect_from_db

async def fix_migration():
    await connect_to_db()
    try:
        # Delete the old migration 033 record
        await database.execute(
            "DELETE FROM schema_migrations WHERE migration_number = 33"
        )
        print("✅ Deleted migration 033 tracking record")
        print("🔄 Migration 033 will re-run on next server restart")
    finally:
        await disconnect_from_db()

if __name__ == "__main__":
    asyncio.run(fix_migration())
