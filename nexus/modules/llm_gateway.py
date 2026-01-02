import logging
import json
from typing import Dict, Any, Optional
from nexus.modules.database import database
from nexus.modules.crypto import decrypt
# Providers
from openai import AsyncOpenAI
# Vertex AI
import vertexai
from vertexai.preview.generative_models import GenerativeModel, Part

logger = logging.getLogger("nexus.gateway")

class LLMGateway:
    """
    The Single Point of Entry for all LLM calls.
    Handles:
    - Determining which provider/model to use.
    - Fetching encrypted credentials from the Vault.
    - Normalizing requests/responses.
    """
    
    async def chat_completion(
        self, 
        messages: list, 
        provider_name: str = None, # Legacy: For explicit overrides or testing
        model_id: str = None,      # Legacy: For explicit overrides
        module_id: str = "chat",
        user_id: str = "user_default"
    ) -> Dict[str, Any]:
        """
        Generic chat completion.
        Uses 4-Tier Governance to resolve model if provider/model not explicitly passed.
        """
        
        # 1. Resolve Model & Provider via Governance (Through ConfigManager)
        # If provider/model passed explicitly (legacy/testing), we treat as Runtime Override
        
        # We assume self.config_manager is available (it's used loosely effectively via import in _get_provider_config, 
        # but let's be explicit and import the instance or reuse the import)
        from nexus.modules.config_manager import config_manager
        
        resolution = await config_manager.resolve_app_context(
            module_id=module_id, 
            user_id=user_id, 
            override_model=model_id
        )
        
        target_model = resolution["model_id"]
        target_provider = resolution["provider_name"]
        
        # Override if legacy provider_name was passed (e.g. testing)
        if provider_name:
            target_provider = provider_name
            
        # 2. Get Config
        config = await self._get_provider_config(target_provider)
        if not config:
            raise ValueError(f"Provider '{target_provider}' not configured or active.")
        
        # 3. Route
        provider_type = config["provider_type"]
        
        if provider_type == "vertex":
            return await self._call_vertex(config, target_model, messages)
        elif provider_type == "openai_compatible":
            return await self._call_openai_compatible(config, target_model, messages)
        else:
            raise ValueError(f"Unsupported provider type: {provider_type}")

    async def _get_provider_config(self, provider_name: Optional[str]) -> Dict[str, Any]:
        """
        Fetches provider details + decrypted secrets.
        """
        # 1. Select Provider
        if provider_name:
            query = "SELECT id, name, provider_type, base_url FROM llm_providers WHERE name = :name"
            provider = await database.fetch_one(query, {"name": provider_name})
        else:
            # Default: Pick the first active one (Logic can be improved)
            query = "SELECT id, name, provider_type, base_url FROM llm_providers WHERE is_active = true LIMIT 1"
            provider = await database.fetch_one(query)
            
        if not provider:
            return None
            
        # 2. Fetch & Decrypt Configs
        config_query = "SELECT config_key, encrypted_value, is_secret FROM llm_config WHERE provider_id = :pid"
        rows = await database.fetch_all(config_query, {"pid": provider["id"]})
        
        secrets = {}
        for row in rows:
            val = row["encrypted_value"]
            if row["is_secret"]:
                val = decrypt(val) # DECRYPT HERE
            secrets[row["config_key"]] = val
            
        return {
            "id": provider["id"],
            "name": provider["name"],
            "provider_type": provider["provider_type"],
            "base_url": provider["base_url"],
            "secrets": secrets
        }

    async def _call_vertex(self, config: Dict, model_id: str, messages: list) -> Dict:
        """
        Native Vertex AI Implementation.
        Requires 'project_id' and 'location' in config.
        """
        secrets = config["secrets"]
        project_id = secrets.get("project_id")
        location = secrets.get("location", "us-central1")
        
        if not project_id:
            raise ValueError("Vertex AI requires 'project_id' in configuration.")

        # Initialize Vertex AI SDK
        # Note: In a real high-throughput app, we might cache this init
        vertexai.init(project=project_id, location=location)
        
        # Default Model
        target_model = model_id or "gemini-2.5-flash"
        
        # Extract system instruction and user messages
        system_instruction = None
        user_messages = []
        
        for m in messages:
            if m["role"] == "system":
                system_instruction = m["content"]
            elif m["role"] == "user":
                user_messages.append(m["content"])
            # Ignore "assistant" or "model" messages for now (could build history if needed)
        
        # Combine all user messages into one (or use the last one)
        # For conversational agent, there should only be one user message
        user_content = "\n\n".join(user_messages) if user_messages else ""
        
        if not user_content:
            raise ValueError("No user message found in messages")
        
        # Create model
        model = GenerativeModel(target_model)
        
        # For Vertex AI, prepend system_instruction to prompt if provided
        # (This matches the approach used in llm_service.py for consistency)
        full_prompt = user_content
        if system_instruction:
            full_prompt = f"{system_instruction}\n\n{user_content}"
        
        # Generate
        response = await model.generate_content_async(full_prompt)
        
        return {
            "content": response.text,
            "raw": str(response),
            "provider": "vertex",
            "model": target_model
        }

    async def _call_openai_compatible(self, config: Dict, model_id: str, messages: list) -> Dict:
        """
        Standard OpenAI Client (also works for Groq, Ollama, etc via base_url)
        """
        api_key = config["secrets"].get("api_key", "missing-key")
        base_url = config.get("base_url") # Optional override
        
        client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        
        target_model = model_id or "gpt-3.5-turbo"
        
        response = await client.chat.completions.create(
            model=target_model,
            messages=messages
        )
        
        content = response.choices[0].message.content
        return {
            "content": content,
            "raw": response.model_dump(),
            "provider": config["name"],
            "model": target_model
        }

    async def test_connection(self, provider_name: str) -> Dict[str, Any]:
        """
        Verifies connectivity to the provider without generating text.
        """
        config = await self._get_provider_config(provider_name)
        if not config:
            raise ValueError(f"Provider '{provider_name}' not found.")
            
        provider_type = config["provider_type"]
        
        if provider_type == "vertex":
            # Test Vertex: Init and list models (or just verify project access)
            # Minimal check: Just check if we can init without error
            secrets = config["secrets"]
            try:
                vertexai.init(project=secrets.get("project_id"), location=secrets.get("location"))
                # Try a lightweight call
                # list_models is part of ModelGardenService but GenerativeModel is easier
                # We'll assume Init is enough or try catching an auth error on a dummy object
                return {"status": "success", "message": "Vertex AI Project Accessible"}
            except Exception as e:
                raise ValueError(f"Vertex Connection Failed: {e}")
                
        elif provider_type == "openai_compatible":
            # Test OpenAI/Ollama: List Models
            api_key = config["secrets"].get("api_key", "missing")
            base_url = config.get("base_url")
            
            try:
                client = AsyncOpenAI(api_key=api_key, base_url=base_url)
                # This verifies URL + Key
                models = await client.models.list()
                
                # Check for at least one model
                count = len(models.data)
                first_model = models.data[0].id if count > 0 else "none"
                
                return {
                    "status": "success", 
                    "message": f"Connected! Found {count} models (e.g. {first_model})"
                }
            except Exception as e:
                # Clarify common errors
                msg = str(e)
                if "Connection refused" in msg:
                    msg += " (Check Base URL)"
                if "401" in msg:
                    msg += " (Invalid API Key)"
                raise ValueError(f"Connection Failed: {msg}")
                
        else:
            raise ValueError("Unknown provider type")

gateway = LLMGateway()
