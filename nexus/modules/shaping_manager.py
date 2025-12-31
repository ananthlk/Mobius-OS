import logging

logger = logging.getLogger("nexus.shaping")

class ShapingManager:
    """
    Manages the 'Workflow Shaping' chat sessions.
    """

    async def create_session(self, user_id: str, initial_query: str) -> int:
        """
        Starts a new shaping session.
        """
        logger.info(f"Creating session for {user_id}")
        # Initial transcript with user's first query
        transcript = [
            {"role": "user", "content": initial_query, "timestamp": "now"} # simplified timestamp for JSON
        ]
        
        query = """
        INSERT INTO workflow_problem_identification 
        (user_id, status, transcript, draft_plan)
        VALUES (:user_id, 'IDENTIFYING', :transcript, '{}')
        RETURNING id
        """
        session_id = await database.fetch_val(query=query, values={
            "user_id": user_id,
            "transcript": json.dumps(transcript)
        })
        
        logger.info(f"Session persisted. ID: {session_id}")
        
        # Also log to User Activity
        await self._log_activity(user_id, session_id, initial_query)
        
        return session_id
    
    # ... append_message (no changes needed, inferred from workflow logs) ...

    async def _log_activity(self, user_id: str, session_id: int, query: str):
        # ... logic ...
        logger.debug(f"Logged user activity for session {session_id}")
        # ... db insert ...

    async def append_message(self, session_id: int, role: str, content: str) -> None:
        """
        Appends a message to the session transcript.
        """
        # 1. Fetch current transcript
        select_query = "SELECT transcript FROM workflow_problem_identification WHERE id = :id"
        current_json = await database.fetch_val(query=select_query, values={"id": session_id})
        
        transcript = json.loads(current_json) if current_json else []
        
        # 2. Append new message
        transcript.append({
            "role": role,
            "content": content,
            "timestamp": "now" # In real app, use datetime
        })
        
        # 3. Update DB
        update_query = """
        UPDATE workflow_problem_identification
        SET transcript = :transcript, updated_at = CURRENT_TIMESTAMP
        WHERE id = :id
        """
        await database.execute(query=update_query, values={
            "id": session_id,
            "transcript": json.dumps(transcript)
        })

    async def get_session(self, session_id: int) -> Dict[str, Any]:
        query = "SELECT * FROM workflow_problem_identification WHERE id = :id"
        row = await database.fetch_one(query=query, values={"id": session_id})
        return dict(row) if row else None

    async def _log_activity(self, user_id: str, session_id: int, query: str):
        """
        Logs this as a 'WORKFLOW' activity in the sidebar.
        """
        # Truncate title
        title = (query[:30] + '...') if len(query) > 30 else query
        
        query = """
        INSERT INTO user_activity (user_id, module, resource_id, resource_metadata)
        VALUES (:user_id, 'WORKFLOW', :rid, :meta)
        """
        await database.execute(query=query, values={
            "user_id": user_id,
            "rid": str(session_id),
            "meta": json.dumps({"title": title, "status": "Drafting"})
        })

shaping_manager = ShapingManager()
