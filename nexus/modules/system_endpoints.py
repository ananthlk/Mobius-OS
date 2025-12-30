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
