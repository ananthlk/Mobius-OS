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
        provider_name: str = None, 
        model_id: str = None
    ) -> Dict[str, Any]:
        """
        Generic chat completion.
        If provider_name is None, uses the system default (active) provider.
        """
        config = await self._get_provider_config(provider_name)
        if not config:
            raise ValueError(f"Provider '{provider_name}' not configured or active.")

        provider_type = config["provider_type"]
        
        if provider_type == "vertex":
            return await self._call_vertex(config, model_id, messages)
        elif provider_type == "openai_compatible":
            return await self._call_openai_compatible(config, model_id, messages)
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
        target_model = model_id or "gemini-1.5-pro" 
        model = GenerativeModel(target_model)
        
        # Convert Messages (OpenAI format -> Vertex format)
        # Simple/Naive conversion for now
        history = []
        last_user_msg = ""
        
        for m in messages:
            role = "user" if m["role"] == "user" else "model"
            if role == "user":
                last_user_msg = m["content"]
            else:
                history.append({"role": role, "parts": [Part.from_text(m["content"])]})
                
        # Generate
        chat = model.start_chat(history=[]) # Stateless for simplicity here, or map history
        response = await chat.send_message_async(last_user_msg)
        
        return {
            "content": response.text,
            "raw": response.to_dict(),
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

gateway = LLMGateway()
