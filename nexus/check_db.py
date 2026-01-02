from nexus.modules.database import database, init_db, connect_to_db, disconnect_from_db
import asyncio

async def check():
    await connect_to_db()
    try:
        # Check if table exists
        query = "SELECT to_regclass('public.shaping_sessions');"
        result = await database.fetch_val(query)
        print(f"Table 'shaping_sessions' exists: {result}")
        if result:
            # Check columns
            cols = await database.fetch_all("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'shaping_sessions'")
            for c in cols:
                print(f" - {c['column_name']}: {c['data_type']}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await disconnect_from_db()

if __name__ == "__main__":
    asyncio.run(check())
