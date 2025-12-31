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
