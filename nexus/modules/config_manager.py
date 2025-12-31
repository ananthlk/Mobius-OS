import logging
from typing import List, Dict, Any
from nexus.modules.database import database
from nexus.modules.crypto import encrypt

logger = logging.getLogger("nexus.config")

class ConfigManager:
    """
    Manages System Configuration, specifically AI Providers.
    Handles encryption of secrets before writing to DB.
    """
    
    async def list_providers(self) -> List[Dict[str, Any]]:
        query = """
        SELECT id, name, provider_type, base_url, is_active, created_at 
        FROM llm_providers 
        ORDER BY id
        """
        rows = await database.fetch_all(query)
        return [dict(r) for r in rows]

    async def create_provider(self, name: str, provider_type: str, base_url: str = None) -> int:
        query = """
        INSERT INTO llm_providers (name, provider_type, base_url)
        VALUES (:name, :type, :url)
        RETURNING id
        """
        try:
            return await database.fetch_val(query, {"name": name, "type": provider_type, "url": base_url})
        except Exception as e:
            logger.error(f"Failed to create provider: {e}")
            raise ValueError(f"Provider '{name}' might already exist.")

    async def update_secret(self, provider_id: int, key: str, value: str, is_secret: bool = True):
        """
        Encrypts and stores a configuration value.
        """
        final_val = value
        if is_secret and value:
            final_val = encrypt(value)
            
        # Check if exists
        check_query = "SELECT id FROM llm_config WHERE provider_id = :pid AND config_key = :key"
        existing = await database.fetch_one(check_query, {"pid": provider_id, "key": key})
        
        if existing:
            query = """
            UPDATE llm_config 
            SET encrypted_value = :val, is_secret = :sec, updated_at = CURRENT_TIMESTAMP
            WHERE id = :id
            """
            await database.execute(query, {"val": final_val, "sec": is_secret, "id": existing["id"]})
        else:
            query = """
            INSERT INTO llm_config (provider_id, config_key, encrypted_value, is_secret)
            VALUES (:pid, :key, :val, :sec)
            """
            await database.execute(query, {"pid": provider_id, "key": key, "val": final_val, "sec": is_secret})

    async def get_provider_models(self, provider_id: int) -> List[Dict]:
        query = "SELECT * FROM llm_models WHERE provider_id = :pid"
        rows = await database.fetch_all(query, {"pid": provider_id})
        return [dict(r) for r in rows]
        
config_manager = ConfigManager()
