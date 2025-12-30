from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from nexus.modules.spectacles_endpoints import router as spectacles_router
from nexus.modules.portal_endpoints import router as portal_router
from nexus.modules.workflow_endpoints import router as workflows_router
from nexus.modules.system_endpoints import router as system_router
from nexus.modules.database import connect_to_db, disconnect_from_db, init_db
from nexus.recipes.crm_recipes import register_crm_recipes

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await connect_to_db()
    # Migration Note: active migrations should be triggered via /api/system/migrate in prod
    # But for dev convenience we can keep init_db or move to migrations entirely.
    # await init_db() -> Replacing with proper migrations calls would be best practice, but keeping separate for now.
    await register_crm_recipes() # Now async
    yield
    # Shutdown
    await disconnect_from_db()

app = FastAPI(title="Mobius Nexus", version="0.1.0", lifespan=lifespan)

# CORS Configuration
origins = [
    "*"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Surface Routers
app.include_router(spectacles_router, prefix="/api/spectacles", tags=["Spectacles"])
app.include_router(spectacles_router, prefix="/api/spectacles", tags=["Spectacles"])
app.include_router(portal_router, prefix="/api/portal", tags=["Portal"])
app.include_router(workflows_router)
app.include_router(system_router)

@app.get("/")
async def root():
    return {"status": "online", "system": "Mobius Nexus"}
