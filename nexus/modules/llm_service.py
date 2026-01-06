from typing import List, Dict, Any
from nexus.modules.database import database
from nexus.modules.config_manager import config_manager
import logging
import os
import json

logger = logging.getLogger("nexus.llm_service")

class LLMService:
    """
    Manages the Catalog of Available Models.
    - Syncs models from providers (or seeds defaults).
    - Returns organized catalog for UI.
    """

    def __init__(self):
        self.known_models = {
            "google_vertex": [
                {
                    "model_id": "gemini-2.0-flash", 
                    "display_name": "Gemini 2.0 Flash", 
                    "description": "Ultra-fast, low-cost multimodal model. Best for high-volume tasks.",
                    "latency_tier": "fast",
                    "input_cost": 0.075, "output_cost": 0.30,
                    "capabilities": ["vision", "audio", "json_mode"],
                    "is_recommended": True
                },
                {
                    "model_id": "gemini-2.5-flash", 
                    "display_name": "Gemini 2.5 Flash", 
                    "description": "Fast and efficient multimodal model with improved capabilities.",
                    "latency_tier": "fast",
                    "input_cost": 0.075, "output_cost": 0.30,
                    "capabilities": ["vision", "audio", "json_mode"],
                    "is_recommended": True
                },
                {
                    "model_id": "gemini-2.5-pro", 
                    "display_name": "Gemini 2.5 Pro", 
                    "description": "High reasoning capability. Best for complex instructions and coding.",
                    "latency_tier": "balanced",
                    "input_cost": 1.25, "output_cost": 5.00,
                    "capabilities": ["vision", "audio", "json_mode", "function_calling"],
                    "is_recommended": True
                }
            ],
            "openai": [
                {
                    "model_id": "gpt-4-turbo", 
                    "display_name": "GPT-4 Turbo", 
                    "description": "Powerful reasoning model with large context.",
                    "latency_tier": "balanced",
                    "input_cost": 10.00, "output_cost": 30.00,
                    "capabilities": ["vision", "json_mode", "function_calling"],
                    "is_recommended": True
                },
                {
                    "model_id": "gpt-3.5-turbo", 
                    "display_name": "GPT-3.5 Turbo", 
                    "description": "Fast and cheap legacy model.",
                    "latency_tier": "fast",
                    "input_cost": 0.50, "output_cost": 1.50,
                    "capabilities": ["json_mode", "function_calling"],
                    "is_recommended": True
                }
            ],
            "ollama": [
                {
                    "model_id": "llama3", 
                    "display_name": "Meta Llama 3 (Local)", 
                    "description": "State-of-the-art open model running locally.",
                    "latency_tier": "fast",
                    "input_cost": 0.00, "output_cost": 0.00,
                    "capabilities": ["json_mode"],
                    "is_recommended": True
                },
                {
                    "model_id": "mistral", 
                    "display_name": "Mistral 7B (Local)", 
                    "description": "Efficient open model.",
                    "latency_tier": "fast",
                    "input_cost": 0.00, "output_cost": 0.00,
                    "capabilities": [],
                    "is_recommended": True
                },
                {
                    "model_id": "gemma", 
                    "display_name": "Google Gemma (Local)", 
                    "description": "Lightweight open model by Google.",
                    "latency_tier": "fast",
                    "input_cost": 0.00, "output_cost": 0.00,
                    "capabilities": [],
                    "is_recommended": True
                }
            ]
        }

    async def sync_models(self):
        """
        Ensures the database has the latest known models for active providers.
        For now, we seed 'known good' models. In future, we can query provider APIs.
        """
        providers = await config_manager.list_providers()

        for p in providers:
            p_name = p['name']
            
            # 1. Seed Known Models (Static)
            if p_name in self.known_models:
                for m in self.known_models[p_name]:
                    await self._upsert_model(p['id'], m)
                    
            # 2. Dynamic Discovery (Vertex)
            if p['provider_type'] == 'vertex':
                try:
                    dynamic_models = await self._fetch_vertex_models(p['id'], p_name)
                    for m in dynamic_models:
                        await self._upsert_model(p['id'], m)
                except Exception as e:
                    logger.warning(f"Could not auto-sync Vertex models: {e}")
            
            # 3. Dynamic Discovery (OpenAI-compatible)
            if p['provider_type'] == 'openai_compatible':
                try:
                    dynamic_models = await self._fetch_dynamic_models(p['id'], p_name)
                    for m in dynamic_models:
                        await self._upsert_model(p['id'], m)
                except Exception as e:
                    logger.warning(f"Could not auto-sync OpenAI-compatible models for {p_name}: {e}")

    async def _fetch_vertex_models(self, provider_id: int, provider_name: str):
        """
        Dynamically probes Gemini models using a Fallback Strategy:
        1. Try AI Studio (API Key) if key exists.
        2. If that fails or no key, Try Vertex AI (GCP Project).
        """
        from nexus.modules.crypto import decrypt
        import time

        # Fetch Secrets
        s_query = "SELECT config_key, encrypted_value, is_secret FROM llm_config WHERE provider_id = :pid"
        s_rows = await database.fetch_all(s_query, {"pid": provider_id})
        secrets = {}
        for row in s_rows:
             try:
                 val = decrypt(row["encrypted_value"]) if row["is_secret"] else row["encrypted_value"]
             except: val = row["encrypted_value"]
             secrets[row["config_key"]] = val

        project_id = secrets.get("project_id")
        location = secrets.get("location", "us-central1")
        api_key = secrets.get("api_key")

        results = []
        studio_success = False

        # --- STRATEGY 1: AI STUDIO (API KEY) ---
        if api_key and len(api_key.strip()) > 10:
            masked = api_key[:4] + "..." + api_key[-4:]
            logger.info(f"Attempting AI Studio Auth for {provider_name} (Key: {masked})")
            
            try:
                import google.generativeai as genai
                genai.configure(api_key=api_key)
                
                # Discovery (List)
                print("DEBUG: Studio -> Listing Models...")
                found_models = []
                try:
                    for m in genai.list_models():
                        if "generateContent" in m.supported_generation_methods:
                            found_models.append(m.name.replace("models/", ""))
                    print(f"DEBUG: Found models: {found_models}")
                except Exception as e:
                    print(f"DEBUG: List Failed (Expected if key invalid/restricted): {e}")
                    # Don't abort yet, try fallback list
                
                candidates = set(found_models)
                manual_list = ["gemini-2.0-flash-exp", "gemini-1.5-pro", "gemini-1.5-flash", "gemini-1.5-pro-001"]
                for m in manual_list: candidates.add(m)
                
                # Probing
                for model_id in candidates:
                    print(f"DEBUG: Probing {model_id} (Studio)...")
                    start_t = time.time()
                    try:
                        model = genai.GenerativeModel(model_id)
                        await model.generate_content_async("hi")
                        
                        # Check success
                        duration = time.time() - start_t
                        latency_ms = int(duration * 1000)
                        print(f"DEBUG:   -> Success ({latency_ms}ms)")
                        
                        tier = "balanced"
                        if latency_ms < 500: tier = "fast"
                        
                        results.append({
                            "model_id": model_id,
                            "display_name": model_id.replace("-", " ").title().replace("Exp", "(Exp)"),
                            "description": f"Latency: {latency_ms}ms (Studio)",
                            "latency_tier": tier, 
                            "input_cost": 0.0, "output_cost": 0.0,
                            "capabilities": ["vision"],
                            "last_latency_ms": latency_ms,
                            "is_recommended": True
                        })
                        studio_success = True  # At least one worked
                    except Exception as e:
                        print(f"DEBUG:   -> Failed {model_id}: {e}")
            
            except Exception as e:
                logger.warning(f"AI Studio Auth Crashed: {e}")
        
        # Return if Studio worked well
        if studio_success and len(results) > 0:
            logger.info("Sync completed via AI Studio.")
            return results
            
        # --- STRATEGY 2: VERTEX AI (GCP) ---
        if project_id:
            logger.info(f"Falling back to Vertex AI (Project: {project_id}, Loc: {location})")
            try:
                import vertexai
                from vertexai.generative_models import GenerativeModel
                vertexai.init(project=project_id, location=location)
                
                # Vertex Candidates (Explicitly include 2.0-flash-exp which we know works)
                candidates = [
                    # User Requested (Future/Preview)
                    "gemini-3.0-pro",
                    "gemini-3.0-flash",
                    "gemini-2.5-pro",
                    "gemini-2.5-flash",
                    "gemini-2.5-flash-image",
                    "gemini-2.5-flash-lite",
                    "gemini-2.0-flash-lite",
                    
                    # Validated / Known
                    "gemini-2.0-flash-exp",
                    "gemini-exp-1206",
                    "gemini-exp-1121",
                    "gemini-exp-1114",
                    "gemini-1.5-pro-002",
                    "gemini-1.5-flash-002",
                    "gemini-1.5-flash-8b",
                    "learnlm-1.5-pro-experimental",
                    "gemini-1.5-pro-001",
                    "gemini-1.5-flash-001",
                    "gemini-1.5-pro",
                    "gemini-1.5-flash",
                    "gemini-1.0-pro-001"
                ]
                
                for model_id in candidates:
                    print(f"DEBUG: Probing {model_id} (Vertex)...")
                    start_t = time.time()
                    try:
                        model = GenerativeModel(model_id)
                        await model.generate_content_async("hi")
                        
                        duration = time.time() - start_t
                        latency_ms = int(duration * 1000)
                        print(f"DEBUG:   -> Success ({latency_ms}ms)")
                        
                        tier = "balanced"
                        if latency_ms < 500: tier = "fast"
                        
                        is_rec = any(k['model_id'] == model_id for k in self.known_models.get('google_vertex', []))
                        if "2.0" in model_id: is_rec = True # Recommend the new one

                        results.append({
                            "model_id": model_id,
                            "display_name": model_id.replace("-", " ").title(),
                            "description": f"Latency: {latency_ms}ms (Vertex)",
                            "latency_tier": tier, 
                            "input_cost": 0.0, "output_cost": 0.0,
                            "capabilities": ["vision"],
                            "last_latency_ms": latency_ms,
                            "is_recommended": is_rec
                        })
                    except Exception as e:
                        print(f"DEBUG:   -> Failed {model_id}: {e}")
            except Exception as e:
                logger.error(f"Vertex Auth Failed: {e}")

        return results

    async def _fetch_dynamic_models(self, provider_id: int, provider_name: str) -> List[Dict]:
        """
        Connects to the provider and lists available models.
        Uses OpenAI API: GET https://api.openai.com/v1/models
        """
        # 1. Fetch Config (Directly from DB to avoid circular dependency or missing methods)
        from nexus.modules.crypto import decrypt
        from openai import AsyncOpenAI
        
        query = "SELECT config_key, encrypted_value, is_secret FROM llm_config WHERE provider_id = :pid"
        rows = await database.fetch_all(query, {"pid": provider_id})
        
        secrets = {}
        for row in rows:
             try:
                 val = decrypt(row["encrypted_value"]) if row["is_secret"] else row["encrypted_value"]
             except Exception:
                 val = row["encrypted_value"] # Fallback if not encrypted or key issue
             secrets[row["config_key"]] = val
             
        # 2. Fetch Base URL
        p_row = await database.fetch_one("SELECT base_url FROM llm_providers WHERE id=:id", {"id": provider_id})
        base_url = p_row["base_url"]
        
        api_key = secrets.get("api_key", "missing")

        client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        
        # Call OpenAI API: GET /v1/models
        resp = await client.models.list()
        
        results = []
        import time
        
        # Filter for chat models only (exclude TTS, audio, image-only, etc.)
        # Common non-chat model patterns
        non_chat_patterns = [
            "tts", "audio", "realtime", "image", "whisper", 
            "dall-e", "embedding", "moderation", "babbage", "davinci", "ada", "curie"
        ]
        
        chat_models = []
        for model in resp.data:
            model_id_lower = model.id.lower()
            # Skip deprecated/non-chat models
            if any(pattern in model_id_lower for pattern in non_chat_patterns):
                continue
            # Focus on gpt-* models for OpenAI
            if model_id_lower.startswith("gpt-") or "chat" in model_id_lower:
                chat_models.append(model)
        
        # If no chat models found with filtering, use all models (fallback)
        if not chat_models:
            chat_models = resp.data
        
        logger.info(f"Found {len(chat_models)} chat models out of {len(resp.data)} total models for {provider_name}")
        
        # Process chat models (limit benchmarking for performance)
        recommended_model_ids = ["gpt-4", "gpt-3.5-turbo", "gpt-4-turbo", "gpt-4o", "o1"]
        
        for model in chat_models:
            model_id = model.id
            model_id_lower = model_id.lower()
            
            # Only benchmark a subset for performance (prioritize recommended models)
            should_benchmark = (
                any(rec in model_id_lower for rec in recommended_model_ids) or
                len(chat_models) <= 20  # Benchmark all if small list
            )
            
            latency_ms = None
            if should_benchmark:
                start_t = time.time()
                try:
                    # Simple ping: "hi" usually triggers a short response
                    await client.chat.completions.create(
                        model=model_id,
                        messages=[{"role": "user", "content": "hi"}],
                        max_tokens=1
                    )
                    duration = time.time() - start_t
                    latency_ms = int(duration * 1000)
                except Exception as e:
                    # Silent skip for non-chat models or errors
                    logger.debug(f"Benchmark skipped for {model_id}: {e}")
            
            # Determine Tier (default to balanced if not benchmarked)
            if latency_ms is None:
                tier = "balanced"
            elif latency_ms < 500:
                tier = "fast"
            elif latency_ms < 2000:
                tier = "balanced"
            else:
                tier = "complex"
            
            # Determine capabilities based on model name
            capabilities = []
            if "vision" in model_id_lower or "4o" in model_id_lower or "4-turbo" in model_id_lower:
                capabilities.append("vision")
            if "json" in model_id_lower or "turbo" in model_id_lower:
                capabilities.append("json_mode")
            if "4" in model_id_lower or "turbo" in model_id_lower:
                capabilities.append("function_calling")
            
            # Check if recommended
            is_recommended = any(rec in model_id_lower for rec in recommended_model_ids)
            
            # Create display name
            display_name = model_id.replace("-", " ").title()
            if "gpt-4o" in model_id_lower:
                display_name = "GPT-4o"
            elif "gpt-4-turbo" in model_id_lower:
                display_name = "GPT-4 Turbo"
            elif "gpt-3.5-turbo" in model_id_lower:
                display_name = "GPT-3.5 Turbo"
            
            model_data = {
                "model_id": model_id,
                "display_name": display_name,
                "description": f"OpenAI model (latency: {latency_ms}ms)" if latency_ms else "OpenAI model",
                "latency_tier": tier,
                "input_cost": 0.0,  # Costs can be updated separately
                "output_cost": 0.0,
                "capabilities": capabilities,
                "is_recommended": is_recommended
            }
            
            if latency_ms is not None:
                model_data["last_latency_ms"] = latency_ms
            
            results.append(model_data)
        
        return results

    async def _upsert_model(self, provider_id: int, model_data: Dict):
        logger.info(f"Upserting Model: {model_data['model_id']} (Provider: {provider_id})")
        check_query = "SELECT id FROM llm_models WHERE provider_id = :pid AND model_id = :mid"
        existing = await database.fetch_one(check_query, {"pid": provider_id, "mid": model_data["model_id"]})
        
        latency_val = model_data.get("last_latency_ms", None)
        is_rec = model_data.get("is_recommended", False)
        
        if existing:
            # Update
            query = """
                UPDATE llm_models 
                SET display_name = :dname, 
                    description = :desc,
                    latency_tier = :latency,
                    input_cost_per_1k = :icost,
                    output_cost_per_1k = :ocost,
                    capabilities = :caps,
                    last_latency_ms = COALESCE(:lat, last_latency_ms),
                    is_recommended = :rec,
                    last_verified_at = CURRENT_TIMESTAMP
                WHERE id = :id
            """
            values = {
                "id": existing["id"],
                "dname": model_data["display_name"],
                "desc": model_data["description"],
                "latency": model_data["latency_tier"],
                "icost": model_data["input_cost"],
                "ocost": model_data["output_cost"],
                "caps": str(model_data["capabilities"]).replace("'", '"'),
                "lat": latency_val,
                "rec": is_rec
            }
        else:
            # Insert - Set Active Default (Active if Recommended, otherwise Inactive)
            is_active_default = is_rec 
            
            query = """
                INSERT INTO llm_models (provider_id, model_id, display_name, description, latency_tier, input_cost_per_1k, output_cost_per_1k, capabilities, last_latency_ms, is_recommended, is_active, last_verified_at)
                VALUES (:pid, :mid, :dname, :desc, :latency, :icost, :ocost, :caps, :lat, :rec, :act, CURRENT_TIMESTAMP)
            """
            values = {
                "pid": provider_id,
                "mid": model_data["model_id"],
                "dname": model_data["display_name"],
                "desc": model_data["description"],
                "latency": model_data["latency_tier"],
                "icost": model_data["input_cost"],
                "ocost": model_data["output_cost"],
                "caps": str(model_data["capabilities"]).replace("'", '"'),
                "lat": latency_val,
                "rec": is_rec,
                "act": is_active_default
            }
        
        await database.execute(query, values)

    async def get_catalog(self) -> List[Dict]:
        """
        Returns a nested catalog: Provider -> Models
        """
        providers = await config_manager.list_providers()
        catalog = []
        
        for p in providers:
            # Order by Recommended, Active, then Latency
            # We return ALL models now so UI can show inactive ones
            models_query = """
                SELECT * FROM llm_models 
                WHERE provider_id = :pid
                ORDER BY is_active DESC, is_recommended DESC, latency_tier ASC
            """
            models = await database.fetch_all(models_query, {"pid": p["id"]})
            
            p_data = dict(p)
            p_data["models"] = [dict(m) for m in models]
            catalog.append(p_data)
            
        return catalog

    async def toggle_model_active(self, model_id: int, is_active: bool):
        query = "UPDATE llm_models SET is_active = :act WHERE id = :id"
        await database.execute(query, {"act": is_active, "id": model_id})

    async def benchmark_single_model(self, model_id: int) -> int:
        """
        Runs an on-demand benchmark for a specific model and updates DB.
        Returns latency in ms.
        """
        # 1. Get Model & Provider Info
        query = """
        SELECT m.model_id, p.id as provider_id, p.name as provider_name, p.provider_type
        FROM llm_models m
        JOIN llm_providers p ON m.provider_id = p.id
        WHERE m.id = :id
        """
        target = await database.fetch_one(query, {"id": model_id})
        if not target: raise ValueError("Model not found")
        
        # 2. Setup Client (Reuse logic from _fetch_dynamic - ideally refactor this commonality)
        # For now, fast inline setup to ensure robustness
        
        # ... (Client Setup Logic similar to sync)
        from nexus.modules.crypto import decrypt
        from openai import AsyncOpenAI
        import time
        from vertexai.generative_models import GenerativeModel
        import vertexai

        # Fetch Secrets
        s_query = "SELECT config_key, encrypted_value, is_secret FROM llm_config WHERE provider_id = :pid"
        s_rows = await database.fetch_all(s_query, {"pid": target["provider_id"]})
        secrets = {}
        for row in s_rows:
             try:
                 val = decrypt(row["encrypted_value"]) if row["is_secret"] else row["encrypted_value"]
             except: val = row["encrypted_value"]
             secrets[row["config_key"]] = val
        
        # Fetch Base URL
        p_row = await database.fetch_one("SELECT base_url FROM llm_providers WHERE id=:id", {"id": target["provider_id"]})
        base_url = p_row["base_url"]
        
        latency_ms = 9999
        start_t = time.time()
        
        try:
            if target["provider_type"] == "vertex":
                # Check for API Key first (Hybrid Auth)
                api_key = secrets.get("api_key")
                studio_tried = False
                
                # Try Studio
                if api_key and len(api_key.strip()) > 10:
                    try:
                        import google.generativeai as genai
                        genai.configure(api_key=api_key)
                        model = genai.GenerativeModel(target["model_id"])
                        await model.generate_content_async("hi")
                        studio_tried = True
                    except Exception:
                        pass # Fallback
                
                if not studio_tried:
                     # Fallback to Vertex GCP
                    try:
                        import vertexai
                        from vertexai.generative_models import GenerativeModel
                    except ImportError:
                        raise ImportError("vertexai.generative_models not found. Please upgrade google-cloud-aiplatform>=1.38.0")
    
                    project_id = secrets.get("project_id")
                    location = secrets.get("location", "us-central1")
                    
                    print(f"DEBUG: Benchmark Init -> Project: {project_id} | Location: {location}")
                    print(f"DEBUG: Benchmark Target -> {target['model_id']}")
                    
                    vertexai.init(project=project_id, location=location)
                    model = GenerativeModel(target["model_id"])
                    await model.generate_content_async("hi")
            else:
                # OpenAI / Ollama
                api_key = secrets.get("api_key", "missing")
                client = AsyncOpenAI(api_key=api_key, base_url=base_url)
                await client.chat.completions.create(
                    model=target["model_id"],
                    messages=[{"role": "user", "content": "hi"}],
                    max_tokens=1
                )
            
            duration = time.time() - start_t
            latency_ms = int(duration * 1000)
            
            # Update DB
            u_query = "UPDATE llm_models SET last_latency_ms = :lat, last_verified_at = CURRENT_TIMESTAMP WHERE id = :id"
            await database.execute(u_query, {"lat": latency_ms, "id": model_id})
            
            return latency_ms
            
        except Exception as e:
            logger.error(f"Benchmark failed for {target['model_id']}: {e}")
            
            # Graceful Deprecation / Error Handling
            # If 404/NotFound or generic failure, mark as Inactive and append error to description
            msg = str(e)
            is_deprecated = "not found" in msg.lower() or "404" in msg
            err_tag = " [DEPRECATED]" if is_deprecated else " [ERROR]"
            
            error_query = """
                UPDATE llm_models 
                SET is_active = false,
                is_recommended = false,
                description = CASE 
                    WHEN description LIKE :tag_pattern THEN description 
                    ELSE description || :err_tag 
                END,
                last_verified_at = CURRENT_TIMESTAMP
            WHERE id = :id
            """
            await database.execute(error_query, {
                "id": model_id, 
                "tag_pattern": f"%{err_tag}%", 
                "err_tag": err_tag
            })
            
            return -1

    async def generate_text(
        self, 
        prompt: str, 
        system_instruction: str = None, 
        model_context: Dict = None,
        generation_config: Dict = None,
        return_metadata: bool = False
    ) -> str | tuple[str, Dict[str, Any]]:
        """
        Unified generation method.
        NOW REAL EXECUTION via Google Gemini (Studio or Vertex).
        
        Args:
            prompt: The user query or compiled prompt.
            system_instruction: Optional system role (if not already baked into prompt).
            model_context: Dict containing resolved model info {model_id, api_key, project_id, location, etc.}
            generation_config: Optional dict with temperature, max_output_tokens, top_p, top_k, etc.
                              If None, uses defaults or prompt-specific config.
            return_metadata: If True, returns tuple (text, metadata). If False, returns just text.
        
        Returns:
            If return_metadata=False: str (text response)
            If return_metadata=True: tuple[str, Dict] (text, metadata dict with tokens, finish_reason, etc.)
        """
        if not model_context:
            # Fallback for legacy calls (should be avoided)
            logger.warning("generate_text called without model_context! Using fallback.")
            model_context = {"model_id": "gemini-2.5-flash", "source": "legacy_fallback"}

        model_id = model_context.get("model_id", "gemini-2.5-flash")
        source = model_context.get("source", "unknown")
        
        # Use provided generation_config, or fallback to defaults
        if not generation_config:
            generation_config = {
                "temperature": 0.4 if "plan" in str(system_instruction).lower() else 0.7,
                "max_output_tokens": 8192,
                "top_p": 0.95,
                "top_k": 40,
                "frequency_penalty": 0.0,
                "presence_penalty": 0.0
            }
        
        logger.debug(f"🤖 [LLM_SERVICE] Execution | Model: {model_id} | Source: {source}")
        logger.debug(f"   📥 Prompt Length: {len(prompt)} chars")
        logger.debug(f"   ⚙️  Generation Config: temp={generation_config.get('temperature')}, max_tokens={generation_config.get('max_output_tokens')}")

        try:
            # --- PATH A: AI STUDIO (API KEY) ---
            api_key = model_context.get("api_key")
            provider_name = model_context.get("provider_name", "").lower()
            base_url = model_context.get("base_url")

            # 1. GOOGLE (Vertex or Studio)
            if "google" in provider_name or "vertex" in provider_name:
                provider_type = model_context.get("provider_type")
                
                # VERTEX AI: Use service account credentials (ADC) - no API keys
                if provider_type == "vertex":
                    if not model_context.get("project_id"):
                        raise ValueError("Vertex AI requires 'project_id' in configuration. API keys are not supported for Vertex AI.")
                    
                    import vertexai
                    from vertexai.generative_models import GenerativeModel
                    
                    location = model_context.get("location", "us-central1")
                    vertexai.init(project=model_context.get("project_id"), location=location)
                    
                    model = GenerativeModel(model_id)
                    
                    # For Vertex AI, prepend system_instruction to prompt if provided
                    full_prompt = prompt
                    if system_instruction:
                        full_prompt = f"{system_instruction}\n\n{prompt}"
                    
                    vertex_config = {
                        "temperature": generation_config.get("temperature", 0.4),
                        "max_output_tokens": generation_config.get("max_output_tokens") or generation_config.get("max_tokens", 8192)
                    }
                    response = await model.generate_content_async(full_prompt, generation_config=vertex_config)
                    text = response.text
                    
                    # Log the actual prompt and response for debugging
                    logger.debug(f"   📤 [LLM_SERVICE] Full prompt sent ({len(full_prompt)} chars)")
                    if len(full_prompt) > 1000:
                        logger.debug(f"   📤 [LLM_SERVICE] Prompt preview (first 1000 chars):\n{full_prompt[:1000]}...")
                    else:
                        logger.debug(f"   📤 [LLM_SERVICE] Full prompt:\n{full_prompt}")
                    
                    logger.debug(f"   📥 [LLM_SERVICE] Response received ({len(text)} chars)")
                    if len(text) > 1000:
                        logger.debug(f"   📥 [LLM_SERVICE] Response preview (first 1000 chars):\n{text[:1000]}...")
                    else:
                        logger.debug(f"   📥 [LLM_SERVICE] Full response:\n{text}")
                    
                    # Extract metadata
                    metadata = {}
                    max_output_tokens = vertex_config.get("max_output_tokens", 8192)
                    
                    # Try multiple ways to get usage metadata from Vertex AI
                    usage_metadata = None
                    if hasattr(response, 'usage_metadata'):
                        usage_metadata = response.usage_metadata
                    elif hasattr(response, 'candidates') and len(response.candidates) > 0:
                        # Sometimes usage_metadata is on the candidate
                        candidate = response.candidates[0]
                        if hasattr(candidate, 'usage_metadata'):
                            usage_metadata = candidate.usage_metadata
                    
                    if usage_metadata:
                        # Try different attribute names for token counts
                        prompt_tokens = (
                            getattr(usage_metadata, 'prompt_token_count', None) or
                            getattr(usage_metadata, 'prompt_tokens', None) or
                            0
                        )
                        completion_tokens = (
                            getattr(usage_metadata, 'candidates_token_count', None) or
                            getattr(usage_metadata, 'completion_tokens', None) or
                            0
                        )
                        total_tokens = (
                            getattr(usage_metadata, 'total_token_count', None) or
                            getattr(usage_metadata, 'total_tokens', None) or
                            (prompt_tokens + completion_tokens if prompt_tokens and completion_tokens else 0)
                        )
                        
                        metadata = {
                            "prompt_tokens": prompt_tokens,
                            "completion_tokens": completion_tokens,
                            "total_tokens": total_tokens if total_tokens else (prompt_tokens + completion_tokens),
                            "completion_percent": round((completion_tokens / max_output_tokens) * 100, 1) if max_output_tokens > 0 and completion_tokens > 0 else 0
                        }
                    else:
                        # Fallback: estimate tokens (rough approximation: 1 token ≈ 4 characters)
                        estimated_prompt_tokens = len(full_prompt) // 4
                        estimated_completion_tokens = len(text) // 4
                        metadata = {
                            "prompt_tokens": estimated_prompt_tokens,
                            "completion_tokens": estimated_completion_tokens,
                            "total_tokens": estimated_prompt_tokens + estimated_completion_tokens,
                            "completion_percent": round((estimated_completion_tokens / max_output_tokens) * 100, 1) if max_output_tokens > 0 else 0,
                            "estimated": True  # Flag to indicate this is an estimate
                        }
                    
                    if hasattr(response, 'candidates') and len(response.candidates) > 0:
                        candidate = response.candidates[0]
                        finish_reason_raw = getattr(candidate, 'finish_reason', None)
                        
                        # Convert enum to readable string
                        if finish_reason_raw is not None:
                            if hasattr(finish_reason_raw, 'name'):
                                # It's an enum with .name attribute
                                metadata["finish_reason"] = finish_reason_raw.name
                            elif isinstance(finish_reason_raw, int):
                                # Map enum integer values to names
                                finish_reason_map = {
                                    0: "FINISH_REASON_UNSPECIFIED",
                                    1: "STOP",
                                    2: "MAX_TOKENS",
                                    3: "SAFETY",
                                    4: "RECITATION",
                                    5: "OTHER"
                                }
                                metadata["finish_reason"] = finish_reason_map.get(finish_reason_raw, f"UNKNOWN({finish_reason_raw})")
                            else:
                                metadata["finish_reason"] = str(finish_reason_raw)
                        else:
                            metadata["finish_reason"] = "UNKNOWN"
                        
                        if hasattr(candidate, 'safety_ratings'):
                            metadata["safety_ratings"] = [r.rating.name if hasattr(r.rating, 'name') else str(r.rating) for r in candidate.safety_ratings]
                    
                    if return_metadata:
                        return text, metadata
                    return text
                
                # AI STUDIO: Use API key (google.generativeai SDK)
                elif api_key and len(api_key) > 10:
                    import google.generativeai as genai
                    genai.configure(api_key=api_key)
                    
                    # Use generation_config from parameter (already set above)
                    google_config = {
                        "temperature": generation_config.get("temperature", 0.7),
                        "top_p": generation_config.get("top_p", 0.95),
                        "top_k": generation_config.get("top_k", 40),
                        "max_output_tokens": generation_config.get("max_output_tokens") or generation_config.get("max_tokens", 8192),
                    }
                    
                    model = genai.GenerativeModel(
                        model_name=model_id,
                        system_instruction=system_instruction,
                        generation_config=google_config
                    )
                    
                    response = await model.generate_content_async(full_prompt)
                    text = response.text
                    # Response will be printed in gate_engine instead
                    # logger.debug(f"   ⚡️ Studio Response: {text[:100]}...")
                    
                    # Extract metadata (same logic as Vertex AI)
                    metadata = {}
                    max_output_tokens = google_config.get("max_output_tokens", 8192)
                    
                    # Try multiple ways to get usage metadata
                    usage_metadata = None
                    if hasattr(response, 'usage_metadata'):
                        usage_metadata = response.usage_metadata
                    elif hasattr(response, 'candidates') and len(response.candidates) > 0:
                        candidate = response.candidates[0]
                        if hasattr(candidate, 'usage_metadata'):
                            usage_metadata = candidate.usage_metadata
                    
                    if usage_metadata:
                        prompt_tokens = (
                            getattr(usage_metadata, 'prompt_token_count', None) or
                            getattr(usage_metadata, 'prompt_tokens', None) or
                            0
                        )
                        completion_tokens = (
                            getattr(usage_metadata, 'candidates_token_count', None) or
                            getattr(usage_metadata, 'completion_tokens', None) or
                            0
                        )
                        total_tokens = (
                            getattr(usage_metadata, 'total_token_count', None) or
                            getattr(usage_metadata, 'total_tokens', None) or
                            (prompt_tokens + completion_tokens if prompt_tokens and completion_tokens else 0)
                        )
                        
                        metadata = {
                            "prompt_tokens": prompt_tokens,
                            "completion_tokens": completion_tokens,
                            "total_tokens": total_tokens if total_tokens else (prompt_tokens + completion_tokens),
                            "completion_percent": round((completion_tokens / max_output_tokens) * 100, 1) if max_output_tokens > 0 and completion_tokens > 0 else 0
                        }
                    else:
                        # Fallback: estimate tokens
                        estimated_prompt_tokens = len(full_prompt) // 4
                        estimated_completion_tokens = len(text) // 4
                        metadata = {
                            "prompt_tokens": estimated_prompt_tokens,
                            "completion_tokens": estimated_completion_tokens,
                            "total_tokens": estimated_prompt_tokens + estimated_completion_tokens,
                            "completion_percent": round((estimated_completion_tokens / max_output_tokens) * 100, 1) if max_output_tokens > 0 else 0,
                            "estimated": True
                        }
                    
                    if hasattr(response, 'candidates') and len(response.candidates) > 0:
                        candidate = response.candidates[0]
                        finish_reason_raw = getattr(candidate, 'finish_reason', None)
                        
                        # Convert enum to readable string
                        if finish_reason_raw is not None:
                            if hasattr(finish_reason_raw, 'name'):
                                metadata["finish_reason"] = finish_reason_raw.name
                            elif isinstance(finish_reason_raw, int):
                                finish_reason_map = {
                                    0: "FINISH_REASON_UNSPECIFIED",
                                    1: "STOP",
                                    2: "MAX_TOKENS",
                                    3: "SAFETY",
                                    4: "RECITATION",
                                    5: "OTHER"
                                }
                                metadata["finish_reason"] = finish_reason_map.get(finish_reason_raw, f"UNKNOWN({finish_reason_raw})")
                            else:
                                metadata["finish_reason"] = str(finish_reason_raw)
                        else:
                            metadata["finish_reason"] = "UNKNOWN"
                        
                        if hasattr(candidate, 'safety_ratings'):
                            metadata["safety_ratings"] = [r.rating.name if hasattr(r.rating, 'name') else str(r.rating) for r in candidate.safety_ratings]
                    
                    if return_metadata:
                        return text, metadata
                    return text

            # 2. OPENAI COMPATIBLE (Ollama, OpenAI, DeepSeek, etc.)
            # This covers the local llama3.1 case
            from openai import AsyncOpenAI
            
            # Default to local ollama if no URL provided but provider is generic
            if not base_url and "ollama" in provider_name:
                base_url = "http://localhost:11434/v1"
            
            client = AsyncOpenAI(
                api_key=api_key or "ollama", # Ollama doesn't care, but SDK needs non-empty
                base_url=base_url
            )
            
            messages = []
            if system_instruction:
                messages.append({"role": "system", "content": system_instruction})
            messages.append({"role": "user", "content": prompt})
            
            openai_config = {
                "model": model_id,
                "messages": messages,
                "temperature": generation_config.get("temperature", 0.7),
            }
            # Add optional parameters if provided
            if generation_config.get("max_output_tokens") or generation_config.get("max_tokens"):
                openai_config["max_tokens"] = generation_config.get("max_output_tokens") or generation_config.get("max_tokens")
            if generation_config.get("top_p"):
                openai_config["top_p"] = generation_config["top_p"]
            if generation_config.get("frequency_penalty") is not None:
                openai_config["frequency_penalty"] = generation_config["frequency_penalty"]
            if generation_config.get("presence_penalty") is not None:
                openai_config["presence_penalty"] = generation_config["presence_penalty"]
            
            response = await client.chat.completions.create(**openai_config)
            
            text = response.choices[0].message.content
            # Response will be printed in gate_engine instead
            # logger.debug(f"   ⚡️ Generic/Ollama Response: {text[:100]}...")
            
            # Extract metadata
            metadata = {}
            max_output_tokens = generation_config.get("max_output_tokens") or generation_config.get("max_tokens", 8192)
            if hasattr(response, 'usage'):
                usage = response.usage
                prompt_tokens = getattr(usage, 'prompt_tokens', 0)
                completion_tokens = getattr(usage, 'completion_tokens', 0)
                total_tokens = getattr(usage, 'total_tokens', 0)
                metadata = {
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "total_tokens": total_tokens,
                    "completion_percent": round((completion_tokens / max_output_tokens) * 100, 1) if max_output_tokens > 0 and completion_tokens > 0 else 0
                }
            else:
                # Fallback: estimate tokens
                estimated_prompt_tokens = len(prompt) // 4
                if system_instruction:
                    estimated_prompt_tokens += len(system_instruction) // 4
                estimated_completion_tokens = len(text) // 4
                metadata = {
                    "prompt_tokens": estimated_prompt_tokens,
                    "completion_tokens": estimated_completion_tokens,
                    "total_tokens": estimated_prompt_tokens + estimated_completion_tokens,
                    "completion_percent": round((estimated_completion_tokens / max_output_tokens) * 100, 1) if max_output_tokens > 0 else 0,
                    "estimated": True
                }
            
            if hasattr(response, 'choices') and len(response.choices) > 0:
                finish_reason = getattr(response.choices[0], 'finish_reason', None)
                # OpenAI finish_reason is usually already a string, but handle enum case
                if finish_reason:
                    if hasattr(finish_reason, 'value'):
                        metadata["finish_reason"] = finish_reason.value
                    elif isinstance(finish_reason, str):
                        metadata["finish_reason"] = finish_reason
                    else:
                        metadata["finish_reason"] = str(finish_reason)
                else:
                    metadata["finish_reason"] = "UNKNOWN"
            
            if return_metadata:
                return text, metadata
            return text

        except Exception as e:
            logger.error(f"❌ LLM Execution Failed: {e}")
            error_text = f"Error: {str(e)}"
            if return_metadata:
                return error_text, {"error": str(e)}
            return error_text

llm_service = LLMService()
