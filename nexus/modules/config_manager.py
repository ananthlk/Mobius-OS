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
        WHERE deleted_at IS NULL
        ORDER BY id
        """
        rows = await database.fetch_all(query)
        return [dict(r) for r in rows]

    async def create_provider(self, name: str, provider_type: str, user_context: Dict, base_url: str = None) -> int:
        from nexus.modules.audit_manager import audit_manager
        
        query = """
        INSERT INTO llm_providers (name, provider_type, base_url, created_by)
        VALUES (:name, :type, :url, :uid)
        RETURNING id
        """
        try:
            pid = await database.fetch_val(query, {
                "name": name, 
                "type": provider_type, 
                "url": base_url,
                "uid": user_context.get("user_id", "unknown")
            })
            
            await audit_manager.log_event(
                user_id=user_context.get("user_id", "unknown"),
                session_id=user_context.get("session_id"),
                action="CREATE",
                resource_type="PROVIDER",
                resource_id=str(pid),
                details={"name": name, "type": provider_type}
            )
            return pid
            
        except Exception as e:
            logger.error(f"Failed to create provider: {e}")
            raise ValueError(f"Provider '{name}' might already exist.")

    async def update_secret(self, provider_id: int, key: str, value: str, user_context: Dict, is_secret: bool = True):
        from nexus.modules.audit_manager import audit_manager
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
            
        await audit_manager.log_event(
            user_id=user_context.get("user_id", "unknown"),
            session_id=user_context.get("session_id"),
            action="UPDATE_SECRET",
            resource_type="PROVIDER",
            resource_id=str(provider_id),
            details={"key": key, "is_secret": is_secret}
        )

    async def get_provider_models(self, provider_id: int) -> List[Dict]:
        query = "SELECT * FROM llm_models WHERE provider_id = :pid"
        rows = await database.fetch_all(query, {"pid": provider_id})
        return [dict(r) for r in rows]

    async def delete_provider(self, provider_id: int, user_context: Dict):
        """
        Soft-deletes a provider.
        """
        from nexus.modules.audit_manager import audit_manager
        
        query = """
        UPDATE llm_providers 
        SET deleted_at = CURRENT_TIMESTAMP, updated_by = :uid
        WHERE id = :pid
        """
        await database.execute(query, {
            "pid": provider_id, 
            "uid": user_context.get("user_id", "unknown")
        })
        
        await audit_manager.log_event(
            user_id=user_context.get("user_id", "unknown"),
            session_id=user_context.get("session_id"),
            action="DELETE",
            resource_type="PROVIDER",
            resource_id=str(provider_id)
        )

    async def resolve_app_context(self, module_id: str, user_id: str, override_model: str = None) -> Dict:
        """
        Centralizes the logic for "Which model should be used?".
        Delegates to LLMGovernance but acts as the single point of contact for the App.
        Automatically enriches the context with provider secrets (api_key, project_id, location, base_url).
        """
        from nexus.modules.llm_governance import llm_governance
        model_context = await llm_governance.resolve_model(module_id, user_id, override_model)
        
        # Automatically enrich with provider secrets
        provider_name = model_context.get("provider_name")
        if provider_name:
            from nexus.modules.crypto import decrypt
            
            query = "SELECT id, provider_type, base_url FROM llm_providers WHERE name = :name AND is_active = true"
            provider_row = await database.fetch_one(query, {"name": provider_name})
            
            if provider_row:
                provider = dict(provider_row)  # Convert row to dict for .get() method
                
                # Fetch & decrypt configs
                config_query = "SELECT config_key, encrypted_value, is_secret FROM llm_config WHERE provider_id = :pid"
                rows = await database.fetch_all(config_query, {"pid": provider["id"]})
                
                secrets = {}
                for row in rows:
                    val = row["encrypted_value"]
                    if row["is_secret"]:
                        val = decrypt(val)
                    secrets[row["config_key"]] = val
                
                # Enrich model_context
                model_context.update({
                    "api_key": secrets.get("api_key"),
                    "project_id": secrets.get("project_id"),
                    "location": secrets.get("location", "us-central1"),
                    "base_url": provider.get("base_url"),
                    "provider_type": provider.get("provider_type")
                })
        
        return model_context
        
config_manager = ConfigManager()
