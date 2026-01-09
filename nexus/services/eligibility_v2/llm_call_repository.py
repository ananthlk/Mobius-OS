"""
LLM Call Repository - Manages eligibility_llm_calls
"""
import logging
from typing import Optional, Dict, Any
from nexus.modules.database import database

logger = logging.getLogger("nexus.eligibility_v2.llm_call_repository")


class LLMCallRepository:
    """Repository for eligibility_llm_calls operations"""
    
    async def log_call(
        self,
        case_pk: int,
        call_type: str,
        prompt_hash: str,
        response_data: dict,
        turn_id: Optional[int] = None
    ):
        """Log an LLM call"""
        try:
            import json
            query = """
                INSERT INTO eligibility_llm_calls (case_pk, turn_id, call_type, prompt_hash, response_json)
                VALUES (:case_pk, :turn_id, :call_type, :prompt_hash, CAST(:response_json AS jsonb))
            """
            await database.execute(
                query=query,
                values={
                    "case_pk": case_pk,
                    "turn_id": turn_id,
                    "call_type": call_type,
                    "prompt_hash": prompt_hash,
                    "response_json": json.dumps(response_data)
                }
            )
        except Exception as e:
            logger.warning(f"Failed to log LLM call: {e}")
