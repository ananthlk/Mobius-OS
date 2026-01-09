"""Check migration 011 status"""
import asyncio
from nexus.modules.database import database, connect_to_db, disconnect_from_db


async def check():
    await connect_to_db()
    try:
        row = await database.fetch_one(
            "SELECT migration_number, filename, error_message, applied_at FROM schema_migrations WHERE migration_number = 11"
        )
        if row:
            print(f"Migration 011 status:")
            print(f"  Number: {row['migration_number']}")
            print(f"  Filename: {row['filename']}")
            print(f"  Error: {row['error_message'] or 'None (success)'}")
            print(f"  Applied at: {row['applied_at']}")
        else:
            print("Migration 011 not found in tracking table")
    finally:
        await disconnect_from_db()


if __name__ == "__main__":
    asyncio.run(check())
