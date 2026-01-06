"""
Migration Script: Populate Users Table from Existing User IDs

This script extracts unique user_ids from existing tables and creates user records
for each unique auth_id. This is a one-time data migration script.
"""
import asyncio
import logging
from nexus.modules.database import connect_to_db, disconnect_from_db, database
from nexus.modules.user_manager import user_manager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def extract_unique_user_ids() -> set:
    """Extract unique user_id values from all tables that have user_id columns."""
    logger.info("Extracting unique user_ids from database tables...")
    
    unique_user_ids = set()
    
    # Tables with user_id columns
    tables_with_user_id = [
        "interactions",
        "shaping_sessions",
        "workflow_executions",
        "user_activity",
        "audit_logs",
        "user_llm_preferences",
        "user_communication_preferences",
        "prompt_usage",
        # Tables that might have user_id after migration 029
        "llm_providers",
        "agent_recipes",
        "prompt_templates",
        "prompt_history",
        "llm_trace_logs"
    ]
    
    for table in tables_with_user_id:
        try:
            # Try to get user_id column (some tables might not have it yet)
            query = f"SELECT DISTINCT user_id FROM {table} WHERE user_id IS NOT NULL"
            rows = await database.fetch_all(query)
            
            for row in rows:
                user_id = row.get("user_id") or row[0] if isinstance(row, tuple) else None
                if user_id and isinstance(user_id, str):
                    unique_user_ids.add(user_id)
            
            logger.info(f"  {table}: Found user_ids")
        except Exception as e:
            logger.warning(f"  {table}: Could not extract user_ids ({e})")
            continue
    
    logger.info(f"Found {len(unique_user_ids)} unique user_ids")
    return unique_user_ids


async def create_user_records(user_ids: set):
    """Create user records for each unique user_id (auth_id)."""
    logger.info(f"Creating user records for {len(user_ids)} users...")
    
    created_count = 0
    skipped_count = 0
    error_count = 0
    
    for auth_id in user_ids:
        try:
            # Check if user already exists
            existing = await user_manager.get_user_by_auth_id(auth_id)
            if existing:
                logger.debug(f"  User {auth_id} already exists, skipping")
                skipped_count += 1
                continue
            
            # Try to extract email from auth_id (if it's an email)
            email = auth_id if "@" in auth_id else f"{auth_id}@migrated.local"
            name = None
            
            # Create user with default role 'user'
            user_id = await user_manager.create_user(
                auth_id=auth_id,
                email=email,
                name=name,
                role="user",
                user_context={"user_id": "system", "session_id": None}
            )
            
            logger.info(f"  Created user {user_id} for auth_id {auth_id}")
            created_count += 1
            
        except Exception as e:
            logger.error(f"  Failed to create user for {auth_id}: {e}")
            error_count += 1
            continue
    
    logger.info(f"Migration complete: {created_count} created, {skipped_count} skipped, {error_count} errors")
    return created_count, skipped_count, error_count


async def main():
    """Main migration function."""
    logger.info("Starting user migration...")
    
    try:
        await connect_to_db()
        logger.info("Connected to database")
        
        # Extract unique user_ids
        user_ids = await extract_unique_user_ids()
        
        if not user_ids:
            logger.info("No user_ids found to migrate")
            return
        
        # Create user records
        created, skipped, errors = await create_user_records(user_ids)
        
        logger.info(f"Migration summary:")
        logger.info(f"  Total unique user_ids: {len(user_ids)}")
        logger.info(f"  Created: {created}")
        logger.info(f"  Skipped (already exist): {skipped}")
        logger.info(f"  Errors: {errors}")
        
    except Exception as e:
        logger.error(f"Migration failed: {e}", exc_info=True)
        raise
    finally:
        await disconnect_from_db()
        logger.info("Disconnected from database")


if __name__ == "__main__":
    asyncio.run(main())



