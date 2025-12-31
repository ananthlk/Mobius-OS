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
    # Run Migrations
    
    # 001: Initial Schema
    with open("nexus/migrations/001_initial_schema.sql", "r") as f:
        await database.execute(f.read())
        
    # 002: Seed Data
    with open("nexus/migrations/002_seed_data.sql", "r") as f:
        # Simple split by statement (naive)
        sql = f.read()
        statements = sql.split(";")
        for stmt in statements:
            if stmt.strip():
                await database.execute(stmt)

    # 003: Advanced Schema (Split execution for DO blocks safety)
    try:
        with open("nexus/migrations/003_advanced_schema.sql", "r") as f:
            sql = f.read()
            statements = sql.split(";")
            for stmt in statements:
                if stmt.strip():
                    await database.execute(stmt)
    except Exception as e:
        print(f"Migration 003 Warning: {e}")

    # 004: AI Gateway (Split execution)
    try:
        with open("nexus/migrations/004_ai_gateway.sql", "r") as f:
            sql = f.read()
            statements = sql.split(";")
            for stmt in statements:
                if stmt.strip():
                    await database.execute(stmt)
        print("Migration 004 (AI Gateway) applied.")
    except Exception as e:
        print(f"Migration 004 Error: {e}")
        # Non-critical for dev if tables exist, but good to log.
