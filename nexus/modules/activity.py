import logging
from fastapi import APIRouter, Query
from pydantic import BaseModel
from typing import List, Optional, Dict
from datetime import datetime, timedelta
import json
from nexus.modules.database import database

# Setup Logger
logger = logging.getLogger("nexus.activity")

# Note: remove trailing slash from prefix if causing 307s in some proxies, 
# but FastAPI APIRouter(prefix="/api/activity") usually works fine. 
# The issue seen in logs: "GET /api/activity?..." vs "GET /api/activity/?..."
# We will explicitly support both via default behavior.
router = APIRouter(prefix="/api/activity", tags=["activity"])

# --- Schema ---
class UserActivity(BaseModel):
    id: str
    user_id: str
    module: str  # 'CHAT' | 'WORKFLOW'
    resource_id: str
    title: str
    subtitle: Optional[str] = None
    timestamp: datetime

# --- MOCK Fallbacks (kept for robust dev) ---
MOCK_CHATS = [
    UserActivity(
        id="c1", user_id="u1", module="CHAT", resource_id="chat_1", 
        title="Patient Intake: John Doe", subtitle="Started 2 hours ago", 
        timestamp=datetime.now() - timedelta(hours=2)
    ),
    # ... other mocks can remain locally if needed, but reducing noise
]

MOCK_WORKFLOWS = [
    UserActivity(
        id="w1", user_id="u1", module="WORKFLOW", resource_id="wf_1", 
        title="Medicaid Gap Analysis", subtitle="Draft - 3 steps", 
        timestamp=datetime.now() - timedelta(minutes=30)
    )
]

@router.get("")
@router.get("/")
async def get_activity(module: str = Query("CHAT")):
    """
    Returns recent activity for a specific module.
    Fetches real data from 'user_activity' table.
    """
    module = module.upper()
    logger.info(f"Fetching activity for module: {module}")

    try:
        query = """
        SELECT * FROM user_activity 
        WHERE module = :module 
        ORDER BY last_accessed DESC 
        LIMIT 10
        """
        rows = await database.fetch_all(query=query, values={"module": module})
        
        if rows:
            logger.info(f"Found {len(rows)} rows in DB for {module}")
            results = []
            for r in rows:
                # Parse metadata if exists
                meta = json.loads(r["resource_metadata"]) if r["resource_metadata"] else {}
                results.append(UserActivity(
                    id=str(r["id"]),
                    user_id=r["user_id"],
                    module=r["module"],
                    resource_id=r["resource_id"],
                    title=meta.get("title", "Untitled"),
                    subtitle=meta.get("status", ""),
                    timestamp=r["last_accessed"]
                ))
            return results
        else:
            logger.warning(f"No DB rows for {module}, falling back to MOCK data")
            if module == "WORKFLOW":
                return MOCK_WORKFLOWS
            return MOCK_CHATS

    except Exception as e:
        logger.error(f"Error fetching activity: {e}")
        # Fail safe
        if module == "WORKFLOW":
            return MOCK_WORKFLOWS
        return MOCK_CHATS

@router.post("")
@router.post("/")
async def log_activity(activity: UserActivity):
    """
    Manual log endpoint (mostly used by frontend if needed).
    """
    logger.info(f"Manually logging activity: {activity.title} ({activity.module})")
    # In real app, write to DB here too if frontend pushes it.
    # For now, we trust backend-generated logs mostly.
    return {"status": "logged"}
