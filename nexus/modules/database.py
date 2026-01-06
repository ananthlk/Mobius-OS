"""
Database Module

Provides database connection and initialization.
Refactored to use service layer for connection management and migrations.
"""
import os
import json
import logging
from typing import Any
from dotenv import load_dotenv

load_dotenv()

from nexus.services.database.connection_manager import ConnectionManager
from nexus.services.database.database_creator import DatabaseCreator

# Suppress databases library DEBUG logging (queries)
# This prevents database INSERT/UPDATE/SELECT queries from cluttering server logs
logging.getLogger("databases").setLevel(logging.WARNING)
# Also suppress SQLAlchemy if used
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

# Create connection manager instance
DATABASE_URL = os.getenv("DATABASE_URL")
_connection_manager = ConnectionManager(DATABASE_URL)

# Expose database instance for backward compatibility
database = _connection_manager.database

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
    Delegates to DatabaseCreator service.
    """
    if not DATABASE_URL:
        logging.warning("DATABASE_URL not set, skipping database creation check")
        return
    
    creator = DatabaseCreator(DATABASE_URL)
    await creator.ensure_exists()

async def connect_to_db():
    """
    Establish database connection.
    Ensures database exists first, then connects.
    """
    # Ensure the database exists before attempting to connect
    await ensure_database_exists()
    await _connection_manager.connect()

async def disconnect_from_db():
    """
    Close database connection.
    """
    await _connection_manager.disconnect()

async def init_db():
    """
    Initialize database by running all pending migrations.
    Uses the new migration system to auto-discover and execute migrations.
    """
    from nexus.services.database.migration_runner import MigrationRunner
    
    # Create migration runner
    runner = MigrationRunner(database)
    
    # Run all pending migrations
    await runner.run_migrations()
