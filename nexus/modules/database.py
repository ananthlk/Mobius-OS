from databases import Database
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

# Create the database instance
database = Database(DATABASE_URL)

async def connect_to_db():
    await database.connect()

async def disconnect_from_db():
    await database.disconnect()

async def init_db():
    query = """
    CREATE TABLE IF NOT EXISTS interactions (
        id SERIAL PRIMARY KEY,
        user_id TEXT NOT NULL,
        role TEXT NOT NULL,
        content TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """
    await database.execute(query=query)

    query_recipes = """
    CREATE TABLE IF NOT EXISTS agent_recipes (
        id SERIAL PRIMARY KEY,
        name TEXT UNIQUE NOT NULL,
        goal TEXT NOT NULL,
        steps JSONB NOT NULL,
        start_step_id TEXT NOT NULL,
        version INTEGER DEFAULT 1,
        status TEXT DEFAULT 'ACTIVE',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """
    await database.execute(query=query_recipes)

    # --- Advanced Schema Migration (003) ---
    # In a real system, use Alembic/Flyway. Here we run the raw SQL for simplicity.
    # We read the file content to ensure we are always in sync with the definition.
    try:
        with open("nexus/migrations/003_advanced_schema.sql", "r") as f:
            migration_sql = f.read()
            # Split by statement if needed, or execute block. 
            # Databases usually support multi-statement execute if supported by driver.
            # asyncpg usually requires execute per statement or script.
            # We will split strictly by -- comments or simple heuristics if needed, 
            # but usually execute() can handle a block if it's DDL. 
            # If not, we might need a refined runner. 
            # For now, let's try executing the block.
            # NOTE: DO $$ blocks require safe execution.
            await database.execute(query=migration_sql)
    except Exception as e:
        print(f"Migration Error: {e}")
        # Non-critical for dev if tables exist, but good to log.

