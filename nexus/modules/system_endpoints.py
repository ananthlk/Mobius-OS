from fastapi import APIRouter, HTTPException
from nexus.modules.database import database
from nexus.modules.migration_runner import run_migrations

router = APIRouter(prefix="/api/system", tags=["System"])

@router.post("/migrate")
async def trigger_migrations():
    """
    Manually checks and runs pending database migrations.
    Useful for production hooks (Cloud Run jobs).
    """
    try:
        await run_migrations(database)
        return {"status": "success", "message": "Database migrations applied."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/db_dump")
async def dump_debug_tables():
    """
    DEBUG: Returns the last 5 rows of key tables to verify persistence.
    """
    sessions = await database.fetch_all("SELECT * FROM workflow_problem_identification ORDER BY id DESC LIMIT 5")
    traces = await database.fetch_all("SELECT * FROM llm_trace_logs ORDER BY created_at DESC LIMIT 5")
    activity = await database.fetch_all("SELECT * FROM user_activity ORDER BY id DESC LIMIT 5")
    
    return {
        "sessions": [dict(r) for r in sessions],
        "traces": [dict(r) for r in traces],
        "activity": [dict(r) for r in activity]
    }
