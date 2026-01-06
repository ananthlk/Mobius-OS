"""
Database Connection Manager

Handles database connection lifecycle, pooling, and health checks.
"""
import logging
from databases import Database
from typing import Optional
import os
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("nexus.database.connection")

class ConnectionManager:
    """
    Manages database connection lifecycle.
    """
    
    def __init__(self, database_url: Optional[str] = None):
        """
        Initialize connection manager.
        
        Args:
            database_url: Optional database URL. If not provided, uses DATABASE_URL env var.
        """
        self.database_url = database_url or os.getenv("DATABASE_URL")
        if not self.database_url:
            raise ValueError("DATABASE_URL must be set either as parameter or environment variable")
        
        self._database: Optional[Database] = None
    
    @property
    def database(self) -> Database:
        """
        Get the database instance. Creates it if it doesn't exist.
        """
        if self._database is None:
            self._database = Database(self.database_url)
        return self._database
    
    async def connect(self) -> None:
        """
        Establish database connection.
        """
        if self._database is None:
            self._database = Database(self.database_url)
        
        if not self._database.is_connected:
            await self._database.connect()
            logger.info("Database connection established")
    
    async def disconnect(self) -> None:
        """
        Close database connection.
        """
        if self._database and self._database.is_connected:
            await self._database.disconnect()
            logger.info("Database connection closed")
    
    async def health_check(self) -> bool:
        """
        Check if database connection is healthy.
        
        Returns:
            True if connection is healthy, False otherwise
        """
        try:
            if not self._database or not self._database.is_connected:
                return False
            # Simple query to verify connection
            await self._database.fetch_val("SELECT 1")
            return True
        except Exception as e:
            logger.warning(f"Database health check failed: {e}")
            return False
    
    def is_connected(self) -> bool:
        """
        Check if database is currently connected.
        
        Returns:
            True if connected, False otherwise
        """
        return self._database is not None and self._database.is_connected


