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

    # Run Migrations
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) # nexus/
    MIGRATIONS_DIR = os.path.join(BASE_DIR, "migrations")

    # Helper to read SQL
    def read_migration(filename):
        path = os.path.join(MIGRATIONS_DIR, filename)
        with open(path, "r") as f:
            return f.read()

    # 001: Initial Interactions
    await database.execute(read_migration("001_create_interactions.sql"))
        
    # 002: Recipes Table
    seed_sql = read_migration("002_create_recipes.sql")
    for stmt in seed_sql.split(";"):
        if stmt.strip():
            await database.execute(stmt)

    # 003: Advanced Schema
    try:
        sql = read_migration("003_advanced_schema.sql")
        for stmt in sql.split(";"):
            if stmt.strip():
                await database.execute(stmt)
    except Exception as e:
        print(f"Migration 003 Warning: {e}")

    # 004: AI Gateway
    try:
        sql = read_migration("004_ai_gateway.sql")
        for stmt in sql.split(";"):
            if stmt.strip():
                await database.execute(stmt)
        print("Migration 004 (AI Gateway) applied.")
    except Exception as e:
         print(f"Migration 004 Error: {e}")
        # Non-critical for dev if tables exist, but good to log.
