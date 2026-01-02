import asyncio
from nexus.modules.database import init_db, connect_to_db, disconnect_from_db

async def apply():
    print("Connecting...")
    await connect_to_db()
    print("Running init_db (applying migrations)...")
    await init_db()
    print("Done.")
    await disconnect_from_db()

if __name__ == "__main__":
    asyncio.run(apply())
