from databases import Database
import os
import json
import logging
from typing import Any, Dict
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

# Suppress databases library DEBUG logging (queries)
# This prevents database INSERT/UPDATE/SELECT queries from cluttering server logs
logging.getLogger("databases").setLevel(logging.WARNING)
# Also suppress SQLAlchemy if used
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

# Create the database instance
database = Database(DATABASE_URL)

def parse_jsonb(value: Any) -> Any:
    """
    Helper to parse JSONB values from PostgreSQL.
    PostgreSQL returns JSONB as strings, so we need to parse them.
    Returns the value as-is if it's already a dict/list, or parses it if it's a string.
    """
    if isinstance(value, str):
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return value
    return value

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

    # 010: Workflow Rich Logging
    try:
        sql = read_migration("010_workflow_rich_logging.sql")
        # Split by ; to run multiple statements
        for stmt in sql.split(";"):
            if stmt.strip():
                await database.execute(stmt)
        print("Migration 010 (Rich Logs) applied.")
    except Exception as e:
         print(f"Migration 010 Error: {e}")

    # 011: Memory Events
    try:
        sql = read_migration("011_memory_events.sql")
        for stmt in sql.split(";"):
            if stmt.strip():
                await database.execute(stmt)
        print("Migration 011 (Memory Events) applied.")
    except Exception as e:
         print(f"Migration 011 Error: {e}")

    # 012: Fix Trace Logs FK
    try:
        sql = read_migration("012_fix_trace_logs_fk.sql")
        for stmt in sql.split(";"):
            if stmt.strip():
                await database.execute(stmt)
        print("Migration 012 (Fix Trace Logs FK) applied.")
    except Exception as e:
         print(f"Migration 012 Error: {e}")

    # 013: Session State Table
    try:
        sql = read_migration("013_session_state.sql")
        for stmt in sql.split(";"):
            if stmt.strip():
                await database.execute(stmt)
        print("Migration 013 (Session State) applied.")
    except Exception as e:
         print(f"Migration 013 Error: {e}")

    # 014: Prompt Management
    try:
        sql = read_migration("014_prompt_management.sql")
        for stmt in sql.split(";"):
            if stmt.strip():
                await database.execute(stmt)
        print("Migration 014 (Prompt Management) applied.")
    except Exception as e:
         print(f"Migration 014 Error: {e}")

    # 015: Restructure Prompt Keys
    try:
        sql = read_migration("015_restructure_prompt_keys.sql")
        for stmt in sql.split(";"):
            if stmt.strip():
                await database.execute(stmt)
        print("Migration 015 (Restructure Prompt Keys) applied.")
    except Exception as e:
        print(f"Migration 015 Error: {e}")

    # 016: Gate State (if exists)
    try:
        sql = read_migration("015_gate_state.sql")
        for stmt in sql.split(";"):
            if stmt.strip():
                await database.execute(stmt)
        print("Migration 015 (Gate State) applied.")
    except Exception as e:
        print(f"Migration 015 (Gate State) Error: {e}")

    # 017: Journey State
    try:
        sql = read_migration("017_journey_state.sql")
        for stmt in sql.split(";"):
            if stmt.strip():
                await database.execute(stmt)
        print("Migration 017 (Journey State) applied.")
    except Exception as e:
        print(f"Migration 017 Error: {e}")

    # 018: Tool Library
    try:
        sql = read_migration("018_tool_library.sql")
        for stmt in sql.split(";"):
            if stmt.strip():
                await database.execute(stmt)
        print("Migration 018 (Tool Library) applied.")
    except Exception as e:
        print(f"Migration 018 Error: {e}")

    # 019: Tool Conditional Execution
    try:
        sql = read_migration("019_tool_conditional_execution.sql")
        for stmt in sql.split(";"):
            if stmt.strip():
                await database.execute(stmt)
        print("Migration 019 (Tool Conditional Execution) applied.")
    except Exception as e:
        print(f"Migration 019 Error: {e}")

    # 021: Eligibility Plan Templates
    try:
        sql = read_migration("021_eligibility_plan_templates.sql")
        for stmt in sql.split(";"):
            if stmt.strip():
                await database.execute(stmt)
        print("Migration 021 (Eligibility Plan Templates) applied.")
    except Exception as e:
        print(f"Migration 021 Error: {e}")

    # 022: Workflow Plan State
    try:
        sql = read_migration("022_workflow_plan_state.sql")
        for stmt in sql.split(";"):
            if stmt.strip():
                await database.execute(stmt)
        print("Migration 022 (Workflow Plan State) applied.")
    except Exception as e:
        print(f"Migration 022 Error: {e}")

    # 023: Active Agent State
    try:
        sql = read_migration("023_active_agent_state.sql")
        for stmt in sql.split(";"):
            if stmt.strip():
                await database.execute(stmt)
        print("Migration 023 (Active Agent State) applied.")
    except Exception as e:
        print(f"Migration 023 Error: {e}")

    # 025: Task Catalog
    try:
        sql = read_migration("025_task_catalog.sql")
        for stmt in sql.split(";"):
            if stmt.strip():
                await database.execute(stmt)
        print("Migration 025 (Task Catalog) applied.")
    except Exception as e:
        print(f"Migration 025 Error: {e}")

    # 030: Gmail OAuth Tokens
    try:
        sql = read_migration("030_gmail_oauth_tokens.sql")
        for stmt in sql.split(";"):
            if stmt.strip():
                await database.execute(stmt)
        print("Migration 030 (Gmail OAuth Tokens) applied.")
    except Exception as e:
        print(f"Migration 030 Error: {e}")

    # 032: Message Feedback
    try:
        sql = read_migration("032_message_feedback.sql")
        for stmt in sql.split(";"):
            if stmt.strip():
                await database.execute(stmt)
        print("Migration 032 (Message Feedback) applied.")
    except Exception as e:
        print(f"Migration 032 Error: {e}")
