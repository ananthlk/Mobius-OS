import json
from uuid import uuid4
from typing import Dict, Any, Optional
from nexus.modules.database import database

class TraceManager:
    """
    Manages the 'Black Box' logging of LLM interactions.
    Stores raw prompts and completions for auditing and debugging.
    """

    async def log_trace(
        self, 
        session_id: int, 
        step_name: str, 
        prompt_snapshot: str, 
        raw_completion: Dict[str, Any], 
        model_metadata: Dict[str, Any]
    ) -> str:
        """
        Logs a single LLM execution trace.
        Returns the generated Trace UUID.
        """
        trace_id = str(uuid4())
        
        query = """
        INSERT INTO llm_trace_logs 
        (id, session_id, step_name, prompt_snapshot, raw_completion, model_metadata)
        VALUES (:id, :session_id, :step_name, :prompt, :completion, :meta)
        """
        
        await database.execute(query=query, values={
            "id": trace_id,
            "session_id": session_id,
            "step_name": step_name,
            "prompt": prompt_snapshot,
            "completion": json.dumps(raw_completion),
            "meta": json.dumps(model_metadata)
        })
        
        return trace_id

trace_manager = TraceManager()
