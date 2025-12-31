from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from typing import List, Optional
from nexus.modules.config_manager import config_manager
import logging

logger = logging.getLogger("nexus.admin")

router = APIRouter(prefix="/api/admin/ai", tags=["admin_ai"])

# --- Schemas ---

class ProviderCreate(BaseModel):
    name: str # e.g. "openai-corp"
    provider_type: str # "vertex", "openai_compatible"
    base_url: Optional[str] = None

class SecretUpdate(BaseModel):
    provider_id: int
    key: str # 'api_key', 'project_id'
    value: str
    is_secret: bool = True

class ProviderListResponse(BaseModel):
    id: int
    name: str
    provider_type: str
    base_url: Optional[str]
    is_active: bool

# --- Endpoints ---

@router.get("/providers", response_model=List[ProviderListResponse])
async def list_providers():
    return await config_manager.list_providers()

@router.post("/providers")
async def create_provider(
    provider: ProviderCreate, 
    x_user_id: str = Header("unknown", alias="X-User-ID"),
    x_session_id: str = Header(None, alias="X-Session-ID")
):
    context = {"user_id": x_user_id, "session_id": x_session_id}
    try:
        new_id = await config_manager.create_provider(provider.name, provider.provider_type, context, provider.base_url)
        return {"id": new_id, "status": "created"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/providers/{provider_id}")
async def delete_provider(
    provider_id: int,
    x_user_id: str = Header("unknown", alias="X-User-ID"),
    x_session_id: str = Header(None, alias="X-Session-ID")
):
    """
    Deletes a provider (Soft Delete).
    """
    context = {"user_id": x_user_id, "session_id": x_session_id}
    await config_manager.delete_provider(provider_id, context)
    return {"status": "deleted", "id": provider_id}

class TestConnectionRequest(BaseModel):
    provider_id: int
    
@router.post("/providers/test")
async def test_provider_connection(req: TestConnectionRequest):
    """
    Attempts to send a 'Hello' message to the provider to verify creds.
    """
    # 1. Get Provider Name
    providers = await config_manager.list_providers() # Naive, better to get by ID
    target = next((p for p in providers if p["id"] == req.provider_id), None)
    
    if not target:
        raise HTTPException(status_code=404, detail="Provider not found")
        
    from nexus.modules.llm_gateway import gateway
    
    try:
        # Verify Connectivity (List Models / Auth Check)
        result = await gateway.test_connection(target["name"])
        
        return {
            "status": "success", 
            "message": result["message"], 
            "reply": "Connection Verified", # UI expects this field
            "model": "system-check"
        }
    except Exception as e:
        logger.error(f"Test Connection Failed: {e}")
        return {"status": "error", "message": str(e)}

@router.post("/secrets")
async def update_secret(
    req: SecretUpdate,
    x_user_id: str = Header("unknown", alias="X-User-ID"),
    x_session_id: str = Header(None, alias="X-Session-ID")
):
    """
    Securely updates a configuration value (encrypts if is_secret=True).
    """
    context = {"user_id": x_user_id, "session_id": x_session_id}
    await config_manager.update_secret(req.provider_id, req.key, req.value, context, req.is_secret)
    return {"status": "updated", "key": req.key}

# --- Governance & Catalog ---

@router.get("/catalog")
async def get_model_catalog():
    """
    Returns the full hierarchy of Providers -> Models with metadata.
    """
    from nexus.modules.llm_service import llm_service
    return await llm_service.get_catalog()

@router.post("/catalog/sync")
async def sync_model_catalog():
    """
    Forces a sync of available models (seeds defaults).
    """
    from nexus.modules.llm_service import llm_service
    await llm_service.sync_models()
    return {"status": "synced"}

class SetRuleRequest(BaseModel):
    rule_type: str # 'GLOBAL', 'MODULE', 'USER'
    module_id: str # 'all', 'chat', ...
    model_id: int
    user_id: Optional[str] = None

@router.post("/defaults")
async def set_default_rule(req: SetRuleRequest):
    """
    Sets a governance rule (System Rule or User Preference).
    """
    from nexus.modules.llm_governance import llm_governance
    
    if req.rule_type == 'USER':
        if not req.user_id:
            raise HTTPException(400, "user_id required for USER rules")
        await llm_governance.set_user_preference(req.user_id, req.module_id, req.model_id)
    else:
        # System Rule (GLOBAL or MODULE)
        await llm_governance.set_system_rule(req.rule_type, req.module_id, req.model_id)
        
    return {"status": "success", "rule": req.model_dump()}

@router.get("/rules")
async def get_governance_rules():
    """
    Returns the current system governance configuration.
    """
    from nexus.modules.llm_governance import llm_governance
    return await llm_governance.get_all_rules()

@router.get("/resolve")
async def resolve_model(module: str, user_id: str = "user_default"):
    """
    Resolves the active model for a given context. Used by UI for badges.
    """
    from nexus.modules.llm_governance import llm_governance
    return await llm_governance.resolve_model(module_id=module, user_id=user_id)

# --- Granular Model Control ---

class ToggleModelRequest(BaseModel):
    is_active: bool

@router.post("/models/{model_id}/toggle")
async def toggle_model(model_id: int, req: ToggleModelRequest):
    """
    Enables/Disables a discovered model.
    """
    from nexus.modules.llm_service import llm_service
    await llm_service.toggle_model_active(model_id, req.is_active)
    return {"status": "updated", "model_id": model_id, "is_active": req.is_active}

@router.post("/models/{model_id}/benchmark")
async def benchmark_model(model_id: int):
    """
    Triggers an on-demand latency test for a specific model.
    """
    from nexus.modules.llm_service import llm_service
    latency = await llm_service.benchmark_single_model(model_id)
    
    if latency == -1:
        # Return success so UI refreshes and sees the new "Inactive/Unverified" state
        return {"status": "success", "latency_ms": -1, "message": "Model failed benchmark and has been decommissioned."}
        
    return {"status": "success", "latency_ms": latency}
