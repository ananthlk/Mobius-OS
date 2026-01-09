"""
Migration Runner

Executes database migrations in order.
"""
import logging
import os
from typing import List
from databases import Database
from nexus.core.migrations.migration_registry import MigrationRegistry
from nexus.core.migrations.migration_tracker import MigrationTracker
from nexus.core.migrations.migration_models import Migration, MigrationStatus

logger = logging.getLogger("nexus.database.migrations")


class MigrationRunner:
    """
    Discovers and executes pending database migrations.
    """
    
    def __init__(self, database: Database, migrations_dir: str = None):
        """
        Initialize migration runner.
        
        Args:
            database: Database instance
            migrations_dir: Optional path to migrations directory
        """
        self.database = database
        self.registry = MigrationRegistry(migrations_dir)
        self.tracker = MigrationTracker(database)
    
    def _read_migration_file(self, migration: Migration) -> str:
        """
        Read SQL content from migration file.
        
        Args:
            migration: Migration object
            
        Returns:
            SQL content as string
        """
        with open(migration.filepath, 'r') as f:
            return f.read()
    
    async def _execute_migration(self, migration: Migration) -> None:
        """
        Execute a single migration.
        
        Args:
            migration: Migration to execute
            
        Raises:
            Exception: If migration execution fails
        """
        logger.info(f"Executing migration {migration.number:03d}: {migration.filename}")
        
        sql_content = self._read_migration_file(migration)
        
        # Split by semicolon and execute each statement
        # This handles migrations with multiple statements
        statements = [stmt.strip() for stmt in sql_content.split(';') if stmt.strip()]
        
        for i, statement in enumerate(statements, 1):
            try:
                await self.database.execute(statement)
                logger.debug(f"  Executed statement {i}/{len(statements)}")
            except Exception as e:
                error_msg = f"Failed to execute statement {i}/{len(statements)}: {str(e)}"
                logger.error(f"Migration {migration.number:03d} error: {error_msg}")
                await self.tracker.mark_failed(migration, error_msg)
                raise
    
    async def run_migrations(self) -> None:
        """
        Discover and run all pending migrations.
        
        This method:
        1. Creates the tracking table if needed
        2. Discovers all migrations
        3. Filters to pending migrations
        4. Executes them in order
        5. Records success/failure
        """
        # Ensure tracking table exists
        await self.tracker.create_tracking_table()
        
        # Discover all migrations
        all_migrations = self.registry.discover_migrations()
        
        if not all_migrations:
            logger.info("No migrations found")
            return
        
        # Get already applied migrations
        applied_numbers = await self.tracker.get_applied_migrations()
        
        # Filter to pending migrations
        pending_migrations = [
            m for m in all_migrations 
            if m.number not in applied_numbers
        ]
        
        if not pending_migrations:
            logger.info(f"All {len(all_migrations)} migrations are already applied")
            return
        
        logger.info(f"Found {len(pending_migrations)} pending migrations out of {len(all_migrations)} total")
        
        # Execute pending migrations in order
        for migration in pending_migrations:
            try:
                await self._execute_migration(migration)
                await self.tracker.mark_applied(migration)
                logger.info(f"✅ Migration {migration.number:03d} applied successfully: {migration.filename}")
            except Exception as e:
                error_msg = f"Migration {migration.number:03d} failed: {str(e)}"
                logger.error(error_msg)
                await self.tracker.mark_failed(migration, str(e))
                # Continue with next migration instead of stopping
                # This allows partial migration progress
                logger.warning(f"Continuing with remaining migrations after failure...")
        
        # Summary
        applied_count = len(await self.tracker.get_applied_migrations())
        logger.info(f"Migration run complete. {applied_count}/{len(all_migrations)} migrations applied.")




