import asyncio
from nexus.modules.database import database
from nexus.modules.migration_runner import run_migrations

async def main():
    print("🚀 Connecting to DB...")
    await database.connect()
    try:
        print("▶️ Running Migrations...")
        await run_migrations(database)
    finally:
        await database.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
