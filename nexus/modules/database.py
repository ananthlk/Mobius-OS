from databases import Database
import os
import json
import logging
from typing import Any, Dict
from urllib.parse import urlparse
import asyncpg
from dotenv import load_dotenv
import time

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

# #region agent log
def _log_debug(session_id, run_id, hypothesis_id, location, message, data):
    try:
        log_path = "/Users/ananth/Personal AI Projects/Mobius OS/.cursor/debug.log"
        with open(log_path, "a") as f:
            f.write(json.dumps({
                "sessionId": session_id,
                "runId": run_id,
                "hypothesisId": hypothesis_id,
                "location": location,
                "message": message,
                "data": data,
                "timestamp": int(time.time() * 1000)
            }) + "\n")
    except:
        pass
# #endregion

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

async def ensure_database_exists():
    """
    Ensure the target database exists by creating it if it doesn't.
    Connects to the default 'postgres' database to check/create the target database.
    """
    # #region agent log
    _log_debug("debug-session", "run1", "A", "database.py:36", "ensure_database_exists entry", {"DATABASE_URL_set": DATABASE_URL is not None, "DATABASE_URL_preview": DATABASE_URL[:50] + "..." if DATABASE_URL and len(DATABASE_URL) > 50 else DATABASE_URL})
    # #endregion
    
    if not DATABASE_URL:
        logging.warning("DATABASE_URL not set, skipping database creation check")
        # #region agent log
        _log_debug("debug-session", "run1", "A", "database.py:42", "DATABASE_URL not set", {})
        # #endregion
        return
    
    try:
        # Parse the DATABASE_URL
        parsed = urlparse(DATABASE_URL)
        db_name = parsed.path.lstrip('/')
        
        # #region agent log
        _log_debug("debug-session", "run1", "A", "database.py:48", "Parsed DATABASE_URL", {"db_name": db_name, "host": parsed.hostname, "port": parsed.port, "user": parsed.username})
        # #endregion
        
        if not db_name:
            logging.warning("No database name found in DATABASE_URL, skipping database creation check")
            # #region agent log
            _log_debug("debug-session", "run1", "A", "database.py:51", "No database name in URL", {})
            # #endregion
            return
        
        # Extract connection parameters
        host = parsed.hostname or 'localhost'
        port = parsed.port or 5432
        user = parsed.username or 'postgres'
        password = parsed.password or ''
        
        # Connect to 'postgres' database to check/create target database
        # Use keyword arguments for safer connection (handles special characters in password)
        conn = None
        try:
            # #region agent log
            _log_debug("debug-session", "run1", "A", "database.py:64", "Connecting to postgres DB to check existence", {"target_db": db_name, "host": host, "port": port})
            # #endregion
            
            conn = await asyncpg.connect(
                host=host,
                port=port,
                user=user,
                password=password,
                database='postgres'  # Connect to default 'postgres' database
            )
            
            # Check if database exists
            exists = await conn.fetchval(
                "SELECT 1 FROM pg_database WHERE datname = $1",
                db_name
            )
            
            # #region agent log
            # List all databases to see if data might be in another database
            all_dbs = await conn.fetch("SELECT datname, pg_database_size(datname) as size FROM pg_database WHERE datistemplate = false ORDER BY size DESC")
            db_list = [{"name": db["datname"], "size_bytes": db["size"]} for db in all_dbs]
            _log_debug("debug-session", "run1", "A", "database.py:110", "Database existence check result", {"db_name": db_name, "exists": exists is not None, "all_databases": db_list})
            # #endregion
            
            if not exists:
                # SAFEGUARD: Check if this is a production database name that should not be auto-created
                production_db_names = ['mobius_db', 'mobius_prod', 'mobius_production']
                is_production_db = db_name.lower() in [name.lower() for name in production_db_names]
                
                if is_production_db:
                    # CRITICAL: Production database missing - this could indicate data loss
                    error_msg = (
                        f"⚠️ CRITICAL: Production database '{db_name}' does not exist!\n"
                        f"This could indicate data loss. The application will NOT auto-create this database.\n"
                        f"Please check:\n"
                        f"  1. PostgreSQL backups\n"
                        f"  2. Database dumps\n"
                        f"  3. If this is a new setup, manually create the database first\n"
                        f"  4. Check if data exists in another database or PostgreSQL instance"
                    )
                    logging.critical(error_msg)
                    # #region agent log
                    _log_debug("debug-session", "run1", "A", "database.py:122", "PRODUCTION DATABASE MISSING - NOT CREATING", {
                        "db_name": db_name,
                        "action": "REFUSED_CREATE",
                        "reason": "production_database_safeguard"
                    })
                    # #endregion
                    raise RuntimeError(f"Production database '{db_name}' does not exist. Auto-creation refused to prevent data loss. {error_msg}")
                
                # For non-production databases, allow creation but log a warning
                logging.warning(f"Database '{db_name}' does not exist, creating it...")
                logging.warning(f"⚠️ Auto-creating database '{db_name}'. If this database previously existed with data, that data may be lost.")
                # #region agent log
                _log_debug("debug-session", "run1", "A", "database.py:135", "DATABASE CREATION TRIGGERED", {
                    "db_name": db_name,
                    "action": "CREATE_DATABASE",
                    "warning": "non_production_auto_create"
                })
                # #endregion
                # Create the database (must use string formatting as database name can't be parameterized)
                # Escape the database name to prevent SQL injection
                escaped_db_name = db_name.replace('"', '""')
                await conn.execute(f'CREATE DATABASE "{escaped_db_name}"')
                logging.info(f"Database '{db_name}' created successfully")
                # #region agent log
                _log_debug("debug-session", "run1", "A", "database.py:143", "Database created successfully", {"db_name": db_name})
                # #endregion
            else:
                logging.debug(f"Database '{db_name}' already exists")
                # #region agent log
                _log_debug("debug-session", "run1", "A", "database.py:86", "Database already exists", {"db_name": db_name})
                # #endregion
                
        finally:
            if conn:
                await conn.close()
                
    except RuntimeError as e:
        # Re-raise RuntimeError (production database missing) - this is critical
        raise
    except Exception as e:
        # Log the error but don't fail - the connection attempt will show the real error
        logging.warning(f"Could not ensure database exists (non-fatal): {e}")
        # #region agent log
        _log_debug("debug-session", "run1", "A", "database.py:176", "ensure_database_exists error", {"error": str(e)})
        # #endregion
        # Don't raise - let the actual connection attempt show the real error

async def connect_to_db():
    # #region agent log
    _log_debug("debug-session", "run1", "B", "database.py:97", "connect_to_db entry", {})
    # #endregion
    # Ensure the database exists before attempting to connect
    await ensure_database_exists()
    # #region agent log
    _log_debug("debug-session", "run1", "B", "database.py:100", "About to connect to database", {})
    # #endregion
    await database.connect()
    # #region agent log
    _log_debug("debug-session", "run1", "B", "database.py:100", "Database connected successfully", {})
    # #endregion

async def disconnect_from_db():
    await database.disconnect()

async def init_db():
    # #region agent log
    _log_debug("debug-session", "run1", "C", "database.py:105", "init_db entry - checking existing data", {})
    # #endregion
    
    # Check existing data counts BEFORE running migrations
    try:
        # #region agent log
        table_counts = {}
        tables_to_check = ['interactions', 'shaping_sessions', 'memory_events', 'agent_recipes', 'session_state', 'gate_state', 'workflow_plan_state']
        for table in tables_to_check:
            try:
                count = await database.fetch_val(query=f"SELECT COUNT(*) FROM {table}")
                table_counts[table] = count
            except:
                table_counts[table] = "table_not_exists"
        _log_debug("debug-session", "run1", "C", "database.py:185", "Existing data counts BEFORE init_db", table_counts)
        
        # Check timestamps of existing records to see when they were created
        try:
            if table_counts.get('shaping_sessions', 0) > 0:
                sessions_info = await database.fetch_all(query="SELECT id, user_id, status, created_at, updated_at FROM shaping_sessions ORDER BY created_at DESC LIMIT 10")
                sessions_data = [{"id": s["id"], "user_id": s["user_id"], "status": s["status"], "created_at": str(s.get("created_at", "N/A")), "updated_at": str(s.get("updated_at", "N/A"))} for s in sessions_info]
                _log_debug("debug-session", "run1", "C", "database.py:194", "Existing shaping_sessions timestamps", {"sessions": sessions_data})
        except Exception as e:
            _log_debug("debug-session", "run1", "C", "database.py:197", "Error checking session timestamps", {"error": str(e)})
        # #endregion
    except Exception as e:
        # #region agent log
        _log_debug("debug-session", "run1", "C", "database.py:118", "Error checking existing data", {"error": str(e)})
        # #endregion
    
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

    # 015: Gate State (if exists)
    try:
        sql = read_migration("015_gate_state.sql")
        for stmt in sql.split(";"):
            if stmt.strip():
                await database.execute(stmt)
        print("Migration 015 (Gate State) applied.")
    except Exception as e:
        print(f"Migration 015 (Gate State) Error: {e}")

    # 016: User Communication Preferences
    try:
        sql = read_migration("016_user_communication_preferences.sql")
        for stmt in sql.split(";"):
            if stmt.strip():
                await database.execute(stmt)
        print("Migration 016 (User Communication Preferences) applied.")
    except Exception as e:
        print(f"Migration 016 Error: {e}")

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

    # 020: Planning Phase
    try:
        sql = read_migration("020_planning_phase.sql")
        for stmt in sql.split(";"):
            if stmt.strip():
                await database.execute(stmt)
        print("Migration 020 (Planning Phase) applied.")
    except Exception as e:
        print(f"Migration 020 Error: {e}")

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

    # 026: Bounded Plan and User Profiles
    try:
        sql = read_migration("026_bounded_plan_and_user_profiles.sql")
        for stmt in sql.split(";"):
            if stmt.strip():
                await database.execute(stmt)
        print("Migration 026 (Bounded Plan and User Profiles) applied.")
    except Exception as e:
        print(f"Migration 026 Error: {e}")

    # 027: Users Table
    try:
        sql = read_migration("027_users_table.sql")
        for stmt in sql.split(";"):
            if stmt.strip():
                await database.execute(stmt)
        print("Migration 027 (Users Table) applied.")
    except Exception as e:
        print(f"Migration 027 Error: {e}")

    # 028: User Account Profiles
    try:
        sql = read_migration("028_user_account_profiles.sql")
        for stmt in sql.split(";"):
            if stmt.strip():
                await database.execute(stmt)
        print("Migration 028 (User Account Profiles) applied.")
    except Exception as e:
        print(f"Migration 028 Error: {e}")

    # 029: Add User ID to Tables
    try:
        sql = read_migration("029_add_user_id_to_tables.sql")
        for stmt in sql.split(";"):
            if stmt.strip():
                await database.execute(stmt)
        print("Migration 029 (Add User ID to Tables) applied.")
    except Exception as e:
        print(f"Migration 029 Error: {e}")

    # 030: Gmail OAuth Tokens
    try:
        sql = read_migration("030_gmail_oauth_tokens.sql")
        for stmt in sql.split(";"):
            if stmt.strip():
                await database.execute(stmt)
        print("Migration 030 (Gmail OAuth Tokens) applied.")
    except Exception as e:
        print(f"Migration 030 Error: {e}")

    # 031: Comprehensive User Profiles
    try:
        sql = read_migration("031_comprehensive_user_profiles.sql")
        for stmt in sql.split(";"):
            if stmt.strip():
                await database.execute(stmt)
        print("Migration 031 (Comprehensive User Profiles) applied.")
    except Exception as e:
        print(f"Migration 031 Error: {e}")

    # 032: Message Feedback
    try:
        sql = read_migration("032_message_feedback.sql")
        for stmt in sql.split(";"):
            if stmt.strip():
                await database.execute(stmt)
        print("Migration 032 (Message Feedback) applied.")
    except Exception as e:
        print(f"Migration 032 Error: {e}")
    
    # #region agent log
    # Check existing data counts AFTER running migrations
    try:
        table_counts_after = {}
        tables_to_check = ['interactions', 'shaping_sessions', 'memory_events', 'agent_recipes', 'session_state', 'gate_state', 'workflow_plan_state']
        for table in tables_to_check:
            try:
                count = await database.fetch_val(query=f"SELECT COUNT(*) FROM {table}")
                table_counts_after[table] = count
            except:
                table_counts_after[table] = "table_not_exists"
        _log_debug("debug-session", "run1", "C", "database.py:490", "Existing data counts AFTER init_db", table_counts_after)
        
        # Check database info
        try:
            current_db = await database.fetch_val(query="SELECT current_database()")
            db_size = await database.fetch_val(query="SELECT pg_database_size(current_database())")
            _log_debug("debug-session", "run1", "C", "database.py:495", "Database info", {"current_db": current_db, "size_bytes": db_size})
        except Exception as e:
            _log_debug("debug-session", "run1", "C", "database.py:497", "Error getting database info", {"error": str(e)})
    except Exception as e:
        _log_debug("debug-session", "run1", "C", "database.py:390", "Error checking data after init", {"error": str(e)})
    # #endregion
