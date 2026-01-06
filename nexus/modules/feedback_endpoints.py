"""
Feedback Endpoints - API for submitting and retrieving message feedback.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from nexus.modules.database import database

router = APIRouter()

# --- Data Models ---
class FeedbackSubmitRequest(BaseModel):
    memory_event_id: int
    user_id: str
    rating: str  # 'thumbs_up' or 'thumbs_down'
    comment: Optional[str] = None

class FeedbackResponse(BaseModel):
    id: int
    memory_event_id: int
    user_id: str
    rating: str
    comment: Optional[str]
    created_at: str

# --- Endpoints ---

@router.post("/submit", response_model=FeedbackResponse)
async def submit_feedback(request: FeedbackSubmitRequest):
    """
    Submit feedback for a memory event (OUTPUT message).
    
    Validates rating is 'thumbs_up' or 'thumbs_down'.
    Uses INSERT ... ON CONFLICT to update if feedback already exists.
    """
    if request.rating not in ['thumbs_up', 'thumbs_down']:
        raise HTTPException(status_code=400, detail="Rating must be 'thumbs_up' or 'thumbs_down'")
    
    try:
        # Check if memory_event exists
        check_query = "SELECT id FROM memory_events WHERE id = :meid"
        event_check = await database.fetch_one(check_query, {"meid": request.memory_event_id})
        if not event_check:
            raise HTTPException(status_code=404, detail="Memory event not found")
        
        # Insert or update feedback (UPSERT)
        query = """
            INSERT INTO message_feedback (memory_event_id, user_id, rating, comment)
            VALUES (:meid, :uid, :rating, :comment)
            ON CONFLICT (memory_event_id, user_id)
            DO UPDATE SET
                rating = EXCLUDED.rating,
                comment = EXCLUDED.comment,
                created_at = CURRENT_TIMESTAMP
            RETURNING id, memory_event_id, user_id, rating, comment, created_at
        """
        
        result = await database.fetch_one(query, {
            "meid": request.memory_event_id,
            "uid": request.user_id,
            "rating": request.rating,
            "comment": request.comment
        })
        
        if not result:
            raise HTTPException(status_code=500, detail="Failed to save feedback")
        
        return FeedbackResponse(
            id=result["id"],
            memory_event_id=result["memory_event_id"],
            user_id=result["user_id"],
            rating=result["rating"],
            comment=result["comment"],
            created_at=result["created_at"].isoformat() if result["created_at"] else ""
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error submitting feedback: {str(e)}")

@router.get("/{memory_event_id}", response_model=Optional[FeedbackResponse])
async def get_feedback(memory_event_id: int, user_id: str):
    """
    Get existing feedback for a memory event by a specific user.
    
    Returns None if no feedback exists.
    """
    try:
        query = """
            SELECT id, memory_event_id, user_id, rating, comment, created_at
            FROM message_feedback
            WHERE memory_event_id = :meid AND user_id = :uid
            LIMIT 1
        """
        
        result = await database.fetch_one(query, {
            "meid": memory_event_id,
            "uid": user_id
        })
        
        if not result:
            return None
        
        return FeedbackResponse(
            id=result["id"],
            memory_event_id=result["memory_event_id"],
            user_id=result["user_id"],
            rating=result["rating"],
            comment=result["comment"],
            created_at=result["created_at"].isoformat() if result["created_at"] else ""
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving feedback: {str(e)}")

@router.get("/event/{memory_event_id}/all")
async def get_all_feedback_for_event(memory_event_id: int):
    """
    Get all feedback for a memory event (all users).
    Useful for analytics.
    """
    try:
        query = """
            SELECT id, memory_event_id, user_id, rating, comment, created_at
            FROM message_feedback
            WHERE memory_event_id = :meid
            ORDER BY created_at DESC
        """
        
        results = await database.fetch_all(query, {"meid": memory_event_id})
        
        return [
            FeedbackResponse(
                id=row["id"],
                memory_event_id=row["memory_event_id"],
                user_id=row["user_id"],
                rating=row["rating"],
                comment=row["comment"],
                created_at=row["created_at"].isoformat() if row["created_at"] else ""
            )
            for row in results
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving feedback: {str(e)}")



