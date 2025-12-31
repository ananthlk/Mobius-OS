from typing import List, Dict, Any
from nexus.modules.database import database
from nexus.modules.config_manager import config_manager
import logging
import os

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
                    "model_id": "gemini-1.5-flash", 
                    "display_name": "Gemini 1.5 Flash", 
                    "description": "Ultra-fast, low-cost multimodal model. Best for high-volume tasks.",
                    "latency_tier": "fast",
                    "input_cost": 0.075, "output_cost": 0.30,
                    "capabilities": ["vision", "audio", "json_mode"],
                    "is_recommended": True
                },
                {
                    "model_id": "gemini-1.5-pro", 
                    "display_name": "Gemini 1.5 Pro", 
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
                    
            # 3. Dynamic Discovery (Vertex)
            if p['provider_type'] == 'vertex':
                try:
                    dynamic_models = await self._fetch_vertex_models(p['id'], p_name)
                    for m in dynamic_models:
                        await self._upsert_model(p['id'], m)
                except Exception as e:
                    logger.warning(f"Could not auto-sync Vertex models: {e}")

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
        resp = await client.models.list()
        
        results = []
        import time
        
        # Limit to 10 for performance if list is huge
        models_to_check = resp.data[:10]
        
        for model in models_to_check:
            # Benchmark
            start_t = time.time()
            try:
                # Simple ping: "hi" usually triggers a short response
                await client.chat.completions.create(
                    model=model.id,
                    messages=[{"role": "user", "content": "hi"}],
                    max_tokens=1
                )
                duration = time.time() - start_t
                latency_ms = int(duration * 1000)
            except Exception as e:
                logger.warning(f"Benchmark failed for {model.id}: {e}")
                latency_ms = 9999
            
            # Determine Tier
            if latency_ms < 500: tier = "fast"
            elif latency_ms < 2000: tier = "balanced"
            else: tier = "complex"
            
            results.append({
                "model_id": model.id,
                "display_name": model.id.replace("-", " ").title(),
                "description": f"Latency: {latency_ms}ms",
                "latency_tier": tier, 
                "input_cost": 0.0,
                "output_cost": 0.0,
                "capabilities": ["json_mode"] if "llama" in model.id.lower() else [],
                "last_latency_ms": latency_ms,
                "is_recommended": any(x in model.id.lower() for x in ["llama3", "mistral", "gemma", "phi", "mixtral"])
            })
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

llm_service = LLMService()
