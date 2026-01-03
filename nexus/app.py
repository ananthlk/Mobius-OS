from fastapi import FastAPI
from dotenv import load_dotenv
import logging

# --- VERBOSE LOGGING CONFIGURATION ---
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s :: %(message)s",
    datefmt="%H:%M:%S"
)

# Hide uvicorn access logs (GET/POST requests) to reduce noise
logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

load_dotenv() # Load env vars immediately

from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from nexus.modules.spectacles_endpoints import router as spectacles_router
from nexus.modules.portal_endpoints import router as portal_router
from nexus.modules.workflow_endpoints import router as workflows_router
from nexus.modules.system_endpoints import router as system_router
from nexus.modules.admin_endpoints import router as admin_router
from nexus.modules.external_logging import router as external_router
from nexus.modules.prompt_endpoints import router as prompt_router
from nexus.modules.gate_endpoints import router as gate_router
from nexus.modules.task_catalog_endpoints import router as task_catalog_router
from nexus.modules.database import connect_to_db, disconnect_from_db, init_db
from nexus.recipes.crm_recipes import register_crm_recipes

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await connect_to_db()
    # Migration Note: active migrations should be triggered via /api/system/migrate in prod
    # But for dev convenience we can keep init_db or move to migrations entirely.
    await init_db()
    await register_crm_recipes() # Now async
    
    # Seed tool library if empty
    try:
        from nexus.tools.library.seed_tools import seed_tools
        await seed_tools()
    except Exception as e:
        # Log but don't fail startup if seeding fails
        import logging
        logger = logging.getLogger("nexus.app")
        logger.warning(f"Tool library seeding failed (non-fatal): {e}")
    
    # Seed planner prompt if it doesn't exist
    try:
        from nexus.modules.prompt_manager import prompt_manager
        from nexus.scripts.seed_planner_prompt import seed_planner_prompt
        # Check if planner prompt exists
        planner_prompt = await prompt_manager.get_prompt(
            module_name="workflow",
            domain="eligibility",
            mode="TABULA_RASA",
            step="planner"
        )
        if not planner_prompt:
            # Import the async function directly (seed_planner_prompt connects/disconnects internally)
            await seed_planner_prompt()
    except Exception as e:
        # Log but don't fail startup if seeding fails
        import logging
        logger = logging.getLogger("nexus.app")
        logger.warning(f"Planner prompt seeding failed (non-fatal): {e}")
    
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
app.include_router(gate_router)  # Gate state management
app.include_router(task_catalog_router)  # Task catalog management
app.include_router(system_router)
app.include_router(admin_router)
app.include_router(external_router)  # External conversation logging
app.include_router(prompt_router)  # Prompt management
from nexus.modules.activity import router as activity_router
app.include_router(activity_router)

@app.get("/")
async def root():
    return {"status": "online", "system": "Mobius Nexus"}
