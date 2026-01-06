"""
Database Creator

Handles database existence checking and creation with safeguards.
"""
import logging
import asyncpg
from urllib.parse import urlparse
from typing import Optional

logger = logging.getLogger("nexus.database.creator")

class DatabaseCreator:
    """
    Manages database creation with production safeguards.
    """
    
    # Production database names that should not be auto-created
    PRODUCTION_DB_NAMES = ['mobius_db', 'mobius_prod', 'mobius_production']
    
    def __init__(self, database_url: str):
        """
        Initialize database creator.
        
        Args:
            database_url: Full database connection URL
        """
        self.database_url = database_url
        self._parsed_url = urlparse(database_url)
    
    async def ensure_exists(self) -> None:
        """
        Ensure the target database exists by creating it if it doesn't.
        Connects to the default 'postgres' database to check/create the target database.
        
        Raises:
            RuntimeError: If attempting to auto-create a production database
        """
        if not self.database_url:
            logger.warning("DATABASE_URL not set, skipping database creation check")
            return
        
        db_name = self._parsed_url.path.lstrip('/')
        
        if not db_name:
            logger.warning("No database name found in DATABASE_URL, skipping database creation check")
            return
        
        # Extract connection parameters
        host = self._parsed_url.hostname or 'localhost'
        port = self._parsed_url.port or 5432
        user = self._parsed_url.username or 'postgres'
        password = self._parsed_url.password or ''
        
        # Connect to 'postgres' database to check/create target database
        conn = None
        try:
            logger.debug(f"Connecting to postgres DB to check existence of '{db_name}'")
            
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
            
            if not exists:
                # SAFEGUARD: Check if this is a production database
                is_production_db = db_name.lower() in [name.lower() for name in self.PRODUCTION_DB_NAMES]
                
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
                    logger.critical(error_msg)
                    raise RuntimeError(
                        f"Production database '{db_name}' does not exist. "
                        f"Auto-creation refused to prevent data loss. {error_msg}"
                    )
                
                # For non-production databases, allow creation but log a warning
                logger.warning(f"Database '{db_name}' does not exist, creating it...")
                logger.warning(
                    f"⚠️ Auto-creating database '{db_name}'. "
                    f"If this database previously existed with data, that data may be lost."
                )
                
                # Create the database (must use string formatting as database name can't be parameterized)
                # Escape the database name to prevent SQL injection
                escaped_db_name = db_name.replace('"', '""')
                await conn.execute(f'CREATE DATABASE "{escaped_db_name}"')
                logger.info(f"Database '{db_name}' created successfully")
            else:
                logger.debug(f"Database '{db_name}' already exists")
                
        except RuntimeError:
            # Re-raise RuntimeError (production database missing) - this is critical
            raise
        except Exception as e:
            # Log the error but don't fail - the connection attempt will show the real error
            logger.warning(f"Could not ensure database exists (non-fatal): {e}")
            # Don't raise - let the actual connection attempt show the real error
        finally:
            if conn:
                await conn.close()


