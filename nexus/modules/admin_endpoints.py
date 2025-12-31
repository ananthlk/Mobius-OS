from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from nexus.modules.config_manager import config_manager

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
async def create_provider(req: ProviderCreate):
    try:
        pid = await config_manager.create_provider(req.name, req.provider_type, req.base_url)
        return {"status": "created", "id": pid}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/secrets")
async def update_secret(req: SecretUpdate):
    """
    Securely updates a configuration value (encrypts if is_secret=True).
    """
    await config_manager.update_secret(req.provider_id, req.key, req.value, req.is_secret)
    return {"status": "updated", "key": req.key}
