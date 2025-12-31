from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timedelta

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

# --- Mock Data Store ---
MOCK_CHATS = [
    UserActivity(
        id="c1", user_id="u1", module="CHAT", resource_id="chat_1", 
        title="Patient Intake: John Doe", subtitle="Started 2 hours ago", 
        timestamp=datetime.now() - timedelta(hours=2)
    ),
    UserActivity(
        id="c2", user_id="u1", module="CHAT", resource_id="chat_2", 
        title="Billing Inquiry #402", subtitle="Pending Review", 
        timestamp=datetime.now() - timedelta(days=1)
    ),
    UserActivity(
        id="c3", user_id="u1", module="CHAT", resource_id="chat_3", 
        title="Crisis Protocol Review", subtitle="Completed", 
        timestamp=datetime.now() - timedelta(days=2)
    )
]

MOCK_WORKFLOWS = [
    UserActivity(
        id="w1", user_id="u1", module="WORKFLOW", resource_id="wf_1", 
        title="Medicaid Gap Analysis", subtitle="Draft - 3 steps", 
        timestamp=datetime.now() - timedelta(minutes=30)
    ),
    UserActivity(
        id="w2", user_id="u1", module="WORKFLOW", resource_id="wf_2", 
        title="New Patient Protocol", subtitle="Active v2", 
        timestamp=datetime.now() - timedelta(days=1)
    ),
    UserActivity(
        id="w3", user_id="u1", module="WORKFLOW", resource_id="wf_3", 
        title="Daily Rounds Automation", subtitle="Paused", 
        timestamp=datetime.now() - timedelta(days=3)
    )
]

@router.get("/")
async def get_activity(module: str = "CHAT"):
    """
    Returns recent activity for a specific module.
    """
    module = module.upper()
    if module == "WORKFLOW":
        return MOCK_WORKFLOWS
    return MOCK_CHATS

@router.post("/")
async def log_activity(activity: UserActivity):
    """
    Logs a new activity (Mock: appends to list in-memory).
    """
    if activity.module == "WORKFLOW":
        MOCK_WORKFLOWS.insert(0, activity)
    else:
        MOCK_CHATS.insert(0, activity)
    return {"status": "logged"}
