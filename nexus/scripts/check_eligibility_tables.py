"""Check if eligibility_v2 tables exist"""
import asyncio
from nexus.modules.database import database, connect_to_db, disconnect_from_db


async def check():
    await connect_to_db()
    try:
        result = await database.fetch_all(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' AND table_name LIKE 'eligibility%'"
        )
        tables = [r["table_name"] for r in result] if result else []
        print(f"Found {len(tables)} eligibility tables: {tables}")
        
        # Check specific columns
        for table in ["eligibility_cases", "eligibility_score_runs", "eligibility_llm_calls"]:
            if table in tables:
                result = await database.fetch_all(
                    f"SELECT column_name, data_type FROM information_schema.columns WHERE table_name = '{table}' ORDER BY ordinal_position"
                )
                print(f"\n{table} columns:")
                for r in result:
                    print(f"  - {r['column_name']}: {r['data_type']}")
            else:
                print(f"\n{table}: NOT FOUND")
    finally:
        await disconnect_from_db()


if __name__ == "__main__":
    asyncio.run(check())
