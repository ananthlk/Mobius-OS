import os
import logging
from databases import Database

logger = logging.getLogger("MigrationRunner")

async def run_migrations(database: Database):
    """
    Scans nexus/migrations for .sql files and executes them.
    A simple forward-only migration runner.
    """
    migration_dir = "nexus/migrations"
    
    # 0. Ensure connected (caller responsible, or we check)
    if not database.is_connected:
        await database.connect()

    files = sorted([f for f in os.listdir(migration_dir) if f.endswith(".sql")])
    
    logger.info(f"🔎 Found {len(files)} migration files.")
    
    for filename in files:
        filepath = os.path.join(migration_dir, filename)
        logger.info(f"▶️ Applying migration: {filename}")
        
        with open(filepath, "r") as f:
            sql = f.read()
            
        # Split by ';' if multiple statements exist, roughly
        statements = [s.strip() for s in sql.split(";") if s.strip()]
        
        async with database.transaction():
            for stmt in statements:
                await database.execute(stmt)
                
    logger.info("✅ All migrations applied successfully.")
