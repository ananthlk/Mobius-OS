"""
Reset Migration 011

Removes the failed migration record for 011 so it can be rerun.
Since we fixed the SQL to use IF NOT EXISTS, it should now succeed.
"""
import asyncio
from nexus.modules.database import database, connect_to_db, disconnect_from_db
from nexus.services.database.migration_runner import MigrationRunner


async def reset_and_rerun():
    """Reset migration 011 and rerun all pending migrations"""
    print("🔌 Connecting to database...")
    await connect_to_db()
    
    try:
        # Delete the failed migration record for 011
        print("🗑️  Removing failed migration record for 011...")
        await database.execute(
            "DELETE FROM schema_migrations WHERE migration_number = 11"
        )
        print("✅ Migration 011 record removed")
        
        # Now rerun migrations
        print("▶️  Running migrations...")
        runner = MigrationRunner(database)
        await runner.run_migrations()
        
        print("✅ Migration rerun complete!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await disconnect_from_db()


if __name__ == "__main__":
    asyncio.run(reset_and_rerun())
