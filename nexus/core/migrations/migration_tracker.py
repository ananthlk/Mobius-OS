"""
Migration Tracker

Tracks which migrations have been applied to the database.
"""
import logging
from typing import Set, Optional
from datetime import datetime
from databases import Database
from nexus.core.migrations.migration_models import Migration, MigrationStatus

logger = logging.getLogger("nexus.migrations.tracker")


class MigrationTracker:
    """
    Tracks applied migrations in the database.
    """
    
    def __init__(self, database: Database):
        """
        Initialize migration tracker.
        
        Args:
            database: Database instance
        """
        self.database = database
    
    async def create_tracking_table(self) -> None:
        """
        Create the schema_migrations table if it doesn't exist.
        """
        query = """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            id SERIAL PRIMARY KEY,
            migration_number INTEGER NOT NULL UNIQUE,
            filename VARCHAR(255) NOT NULL,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            error_message TEXT
        );
        
        CREATE INDEX IF NOT EXISTS idx_schema_migrations_number 
        ON schema_migrations(migration_number);
        """
        
        try:
            # Split by semicolon and execute each statement
            for stmt in query.split(';'):
                stmt = stmt.strip()
                if stmt:
                    await self.database.execute(stmt)
            logger.debug("Migration tracking table created/verified")
        except Exception as e:
            logger.error(f"Failed to create migration tracking table: {e}")
            raise
    
    async def get_applied_migrations(self) -> Set[int]:
        """
        Get set of applied migration numbers.
        
        Returns:
            Set of migration numbers that have been applied
        """
        try:
            query = "SELECT migration_number FROM schema_migrations WHERE error_message IS NULL"
            rows = await self.database.fetch_all(query)
            return {row["migration_number"] for row in rows}
        except Exception as e:
            # Table might not exist yet - return empty set
            logger.debug(f"Could not get applied migrations (table may not exist): {e}")
            return set()
    
    async def mark_applied(self, migration: Migration) -> None:
        """
        Record a migration as successfully applied.
        
        Args:
            migration: Migration object
        """
        query = """
        INSERT INTO schema_migrations (migration_number, filename, applied_at)
        VALUES (:number, :filename, :applied_at)
        ON CONFLICT (migration_number) 
        DO UPDATE SET 
            filename = EXCLUDED.filename,
            applied_at = EXCLUDED.applied_at,
            error_message = NULL
        """
        
        await self.database.execute(query, {
            "number": migration.number,
            "filename": migration.filename,
            "applied_at": datetime.now()
        })
        
        migration.status = MigrationStatus.APPLIED
        migration.applied_at = datetime.now()
        logger.info(f"Marked migration {migration.number:03d} as applied: {migration.filename}")
    
    async def mark_failed(self, migration: Migration, error_message: str) -> None:
        """
        Record a migration as failed.
        
        Args:
            migration: Migration object
            error_message: Error message describing the failure
        """
        query = """
        INSERT INTO schema_migrations (migration_number, filename, error_message)
        VALUES (:number, :filename, :error)
        ON CONFLICT (migration_number) 
        DO UPDATE SET error_message = EXCLUDED.error_message
        """
        
        await self.database.execute(query, {
            "number": migration.number,
            "filename": migration.filename,
            "error": error_message
        })
        
        migration.status = MigrationStatus.FAILED
        migration.error_message = error_message
        logger.error(f"Marked migration {migration.number:03d} as failed: {migration.filename} - {error_message}")
    
    async def get_migration_status(self, migration_number: int) -> Optional[MigrationStatus]:
        """
        Get the status of a specific migration.
        
        Args:
            migration_number: Migration number
            
        Returns:
            MigrationStatus or None if migration not found
        """
        query = """
        SELECT error_message FROM schema_migrations 
        WHERE migration_number = :number
        """
        
        row = await self.database.fetch_one(query, {"number": migration_number})
        if not row:
            return MigrationStatus.PENDING
        
        if row["error_message"]:
            return MigrationStatus.FAILED
        
        return MigrationStatus.APPLIED




