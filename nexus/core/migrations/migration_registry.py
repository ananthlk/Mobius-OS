"""
Migration Registry

Auto-discovers migrations from the migrations directory.
"""
import os
import re
import logging
from pathlib import Path
from typing import List, Dict
from nexus.core.migrations.migration_models import Migration, MigrationStatus

logger = logging.getLogger("nexus.migrations.registry")


class MigrationRegistry:
    """
    Discovers and manages migration files.
    """
    
    # Pattern to match migration filenames: 001_name.sql or 015_name.sql
    MIGRATION_PATTERN = re.compile(r'^(\d+)_(.+)\.sql$')
    
    def __init__(self, migrations_dir: str = None):
        """
        Initialize migration registry.
        
        Args:
            migrations_dir: Path to migrations directory. Defaults to nexus/migrations
        """
        if migrations_dir is None:
            # Default to nexus/migrations relative to this file
            base_dir = Path(__file__).parent.parent.parent
            migrations_dir = str(base_dir / "migrations")
        
        self.migrations_dir = migrations_dir
    
    def discover_migrations(self) -> List[Migration]:
        """
        Discover all migration files in the migrations directory.
        
        Returns:
            List of Migration objects, sorted by migration number.
            
        Raises:
            ValueError: If duplicate migration numbers are found.
        """
        if not os.path.exists(self.migrations_dir):
            logger.warning(f"Migrations directory not found: {self.migrations_dir}")
            return []
        
        migrations: Dict[int, List[Migration]] = {}
        
        # Scan directory for migration files
        for filename in sorted(os.listdir(self.migrations_dir)):
            if not filename.endswith('.sql'):
                continue
            
            match = self.MIGRATION_PATTERN.match(filename)
            if not match:
                logger.warning(f"Skipping file with invalid migration name format: {filename}")
                continue
            
            migration_number = int(match.group(1))
            migration_name = match.group(2)
            filepath = os.path.join(self.migrations_dir, filename)
            
            migration = Migration(
                number=migration_number,
                filename=migration_name,
                filepath=filepath
            )
            
            # Track duplicates
            if migration_number not in migrations:
                migrations[migration_number] = []
            migrations[migration_number].append(migration)
        
        # Check for duplicates
        duplicates = {num: migs for num, migs in migrations.items() if len(migs) > 1}
        if duplicates:
            error_msg = "Duplicate migration numbers found:\n"
            for num, migs in duplicates.items():
                error_msg += f"  {num:03d}: {', '.join(m.filename for m in migs)}\n"
            logger.error(error_msg)
            # For now, warn but continue - use the first one alphabetically
            # In the future, this could be an error
            for num, migs in duplicates.items():
                migrations[num] = [sorted(migs, key=lambda m: m.filename)[0]]
                logger.warning(f"Using first migration for {num:03d}: {migrations[num][0].filename}")
        
        # Flatten and sort by number
        result = []
        for num in sorted(migrations.keys()):
            result.extend(migrations[num])
        
        logger.info(f"Discovered {len(result)} migrations from {self.migrations_dir}")
        return result
    
    def get_migration_by_number(self, number: int) -> Migration:
        """
        Get a specific migration by number.
        
        Args:
            number: Migration number
            
        Returns:
            Migration object
            
        Raises:
            ValueError: If migration not found
        """
        migrations = self.discover_migrations()
        for migration in migrations:
            if migration.number == number:
                return migration
        
        raise ValueError(f"Migration {number:03d} not found")


