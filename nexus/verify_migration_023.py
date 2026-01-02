"""
Verify Migration 023: Check if active_agent column exists
"""
import asyncio
from nexus.modules.database import database

async def verify():
    print("🚀 Connecting to database...")
    await database.connect()
    
    try:
        # Check if column exists
        query = """
        SELECT column_name, data_type 
        FROM information_schema.columns 
        WHERE table_name = 'shaping_sessions' AND column_name = 'active_agent'
        """
        result = await database.fetch_one(query)
        
        if result:
            print(f"✅ Column 'active_agent' exists: {dict(result)}")
        else:
            print("❌ Column 'active_agent' does NOT exist")
        
        # Check if index exists
        index_query = """
        SELECT indexname 
        FROM pg_indexes 
        WHERE tablename = 'shaping_sessions' AND indexname = 'idx_shaping_sessions_active_agent'
        """
        index_result = await database.fetch_one(index_query)
        
        if index_result:
            print(f"✅ Index 'idx_shaping_sessions_active_agent' exists")
        else:
            print("⚠️  Index 'idx_shaping_sessions_active_agent' does NOT exist")
        
        # Check sample data
        sample_query = "SELECT id, active_agent, status FROM shaping_sessions LIMIT 5"
        samples = await database.fetch_all(sample_query)
        if samples:
            print(f"\n📊 Sample data (first 5 sessions):")
            for row in samples:
                row_dict = dict(row)
                print(f"  Session {row_dict.get('id')}: active_agent={row_dict.get('active_agent')}, status={row_dict.get('status')}")
        
    except Exception as e:
        print(f"❌ Verification failed: {e}")
        raise
    finally:
        await database.disconnect()
        print("🔌 Disconnected from database")

if __name__ == "__main__":
    asyncio.run(verify())

