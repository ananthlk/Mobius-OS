from typing import Optional, Dict, Tuple
from nexus.modules.database import database
import logging

logger = logging.getLogger("nexus.governance")

class LLMGovernance:
    """
    Implements the 4-Tier Model Selection Hierarchy:
    1. Runtime Override (Client sends specific model_id)
    2. User Preference (User selects override for Module or Global)
    3. Module Default (System admin sets default for 'Chat', 'Workflow')
    4. Global Default (System fallback)
    """

    async def resolve_model(
        self, 
        module_id: str, 
        user_id: str, 
        runtime_model_id: Optional[str] = None
    ) -> Dict:
        """
        Returns full context: { "model_id": str, "provider_name": str, "source": str }
        """

        # 1. Runtime Override
        if runtime_model_id:
            # We need to find the provider for this model_id
            query = """
                SELECT m.model_id, p.name as provider_name 
                FROM llm_models m 
                JOIN llm_providers p ON m.provider_id = p.id
                WHERE m.model_id = :mid
            """
            row = await database.fetch_one(query, {"mid": runtime_model_id})
            if row:
                return {**dict(row), "source": "runtime_override"}
            # If unknown model, we can't route it easily without assuming a default provider.
            # For now, if runtime override is unknown, we fail or assume Vertex/OpenAI? 
            # Better to require it exists in catalog. 
            pass 

        # 2-4. Parallelize all preference/rule queries for better performance
        import asyncio
        
        query_user_module = """
            SELECT m.model_id, p.name as provider_name
            FROM user_llm_preferences pref
            JOIN llm_models m ON pref.model_id = m.id
            JOIN llm_providers p ON m.provider_id = p.id
            WHERE pref.user_id = :uid AND pref.module_id = :mid
        """
        query_user_global = """
            SELECT m.model_id, p.name as provider_name
            FROM user_llm_preferences pref
            JOIN llm_models m ON pref.model_id = m.id
            JOIN llm_providers p ON m.provider_id = p.id
            WHERE pref.user_id = :uid AND pref.module_id = 'all'
        """
        query_system_module = """
            SELECT m.model_id, p.name as provider_name
            FROM llm_system_rules r
            JOIN llm_models m ON r.model_id = m.id
            JOIN llm_providers p ON m.provider_id = p.id
            WHERE r.rule_type = 'MODULE' AND r.module_id = :mid
        """
        query_system_global = """
            SELECT m.model_id, p.name as provider_name
            FROM llm_system_rules r
            JOIN llm_models m ON r.model_id = m.id
            JOIN llm_providers p ON m.provider_id = p.id
            WHERE r.rule_type = 'GLOBAL'
        """
        
        # Execute all queries in parallel
        user_module_row, user_global_row, system_module_row, system_global_row = await asyncio.gather(
            database.fetch_one(query_user_module, {"uid": user_id, "mid": module_id}),
            database.fetch_one(query_user_global, {"uid": user_id}),
            database.fetch_one(query_system_module, {"mid": module_id}),
            database.fetch_one(query_system_global),
            return_exceptions=True
        )
        
        # Check results in priority order
        if user_module_row and not isinstance(user_module_row, Exception):
            return {**dict(user_module_row), "source": "user_module_pref"}
        
        if user_global_row and not isinstance(user_global_row, Exception):
            return {**dict(user_global_row), "source": "user_global_pref"}
        
        if system_module_row and not isinstance(system_module_row, Exception):
            return {**dict(system_module_row), "source": "system_module_default"}
        
        if system_global_row and not isinstance(system_global_row, Exception):
            return {**dict(system_global_row), "source": "system_global_default"}
        
        # 5. Fail Safe
        return {
            "model_id": "gemini-2.5-flash", 
            "provider_name": "google_vertex", 
            "source": "fail_safe"
        }

    async def set_system_rule(self, rule_type: str, module_id: str, model_pk: int):
        """
        Sets a system rule.
        """
        # Upsert logic
        check = "SELECT id FROM llm_system_rules WHERE rule_type = :rt AND module_id = :mid"
        existing = await database.fetch_one(check, {"rt": rule_type, "mid": module_id})
        
        if existing:
            query = "UPDATE llm_system_rules SET model_id = :pid, updated_at = CURRENT_TIMESTAMP WHERE id = :id"
            await database.execute(query, {"pid": model_pk, "id": existing["id"]})
        else:
            query = "INSERT INTO llm_system_rules (rule_type, module_id, model_id) VALUES (:rt, :mid, :pid)"
            await database.execute(query, {"rt": rule_type, "mid": module_id, "pid": model_pk})

    async def set_user_preference(self, user_id: str, module_id: str, model_pk: int):
        """
        Sets a user preference.
        """
        check = "SELECT id FROM user_llm_preferences WHERE user_id = :uid AND module_id = :mid"
        existing = await database.fetch_one(check, {"uid": user_id, "mid": module_id})
        
        if existing:
            query = "UPDATE user_llm_preferences SET model_id = :pid, updated_at = CURRENT_TIMESTAMP WHERE id = :id"
            await database.execute(query, {"pid": model_pk, "id": existing["id"]})
        else:
            await database.execute(query, {"uid": user_id, "mid": module_id, "pid": model_pk})

    async def get_all_rules(self) -> Dict[str, Dict]:
        """
        Returns the current configuration for the UI Matrix.
        Result: { "GLOBAL": {model_id, provider_name}, "chat": {...}, ... }
        """
        rules = {}
        
        # 1. Get Global
        global_res = await self.resolve_model(module_id="all", user_id="system_check")
        rules["GLOBAL"] = {
            "model_id": global_res["model_id"],
            "provider_name": global_res["provider_name"]
        }

        # 2. Get Modules (Hardcoded list for now, or fetch distinct)
        modules = ["chat", "workflow", "coding"]
        for m in modules:
            # We want the *System Default* specifically for the UI, 
            # but resolve_model gives us the final resolved value.
            # For the "Governance Board", we want to see what is set in `llm_system_rules`.
            
            query = """
                SELECT m.model_id, p.name as provider_name
                FROM llm_system_rules r
                JOIN llm_models m ON r.model_id = m.id
                JOIN llm_providers p ON m.provider_id = p.id
                WHERE r.rule_type = 'MODULE' AND r.module_id = :mid
            """
            row = await database.fetch_one(query, {"mid": m})
            if row:
                rules[m] = dict(row)
            else:
                rules[m] = None # Not set, falls back to Global
                
        return rules

llm_governance = LLMGovernance()
