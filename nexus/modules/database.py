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

    # 005: LLM Governance
    try:
        sql = read_migration("005_llm_governance.sql")
        for stmt in sql.split(";"):
            if stmt.strip():
                await database.execute(stmt)
        print("Migration 005 (Governance) applied.")
    except Exception as e:
         print(f"Migration 005 Error: {e}")

    # 006: System Audit
    try:
        sql = read_migration("006_system_audit.sql")
        for stmt in sql.split(";"):
            if stmt.strip():
                await database.execute(stmt)
        print("Migration 006 (Audit) applied.")
    except Exception as e:
         print(f"Migration 006 Error: {e}")

    # 007: Latency Metrics
    try:
        sql = read_migration("007_model_latency.sql")
        for stmt in sql.split(";"):
            if stmt.strip():
                await database.execute(stmt)
        print("Migration 007 (Latency) applied.")
    except Exception as e:
         print(f"Migration 007 Error: {e}")

    # 008: Model Recommendation
    try:
        sql = read_migration("008_model_recommendation.sql")
        for stmt in sql.split(";"):
            if stmt.strip():
                await database.execute(stmt)
        print("Migration 008 (Recommendation) applied.")
    except Exception as e:
         print(f"Migration 008 Error: {e}")

    # 009: Fix Vertex IDs
    try:
        sql = read_migration("009_fix_vertex_ids.sql")
        for stmt in sql.split(";"):
            if stmt.strip():
                await database.execute(stmt)
        print("Migration 009 (Vertex Fix) applied.")
    except Exception as e:
         print(f"Migration 009 Error: {e}")
