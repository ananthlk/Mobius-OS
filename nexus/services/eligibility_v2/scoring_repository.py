"""
Scoring Repository - Manages eligibility_score_runs
"""
import logging
import json
from typing import Optional
from nexus.agents.eligibility_v2.models import ScoreState
from nexus.modules.database import database

logger = logging.getLogger("nexus.eligibility_v2.scoring_repository")


class ScoringRepository:
    """Repository for eligibility_score_runs operations"""
    
    async def create_score_run(
        self,
        case_pk: int,
        turn_id: Optional[int],
        score_state: ScoreState,
        scoring_version: str,
        inputs_used: Optional[dict] = None
    ) -> int:
        """Create a new score run"""
        query = """
            INSERT INTO eligibility_score_runs (case_pk, turn_id, scoring_version, score_state, inputs_used)
            VALUES (:case_pk, :turn_id, :version, CAST(:score_state AS jsonb), CAST(:inputs_used AS jsonb))
            RETURNING id
        """
        result = await database.fetch_one(
            query=query,
            values={
                "case_pk": case_pk,
                "turn_id": turn_id,
                "version": scoring_version,
                "score_state": json.dumps(score_state.model_dump()),
                "inputs_used": json.dumps(inputs_used or {})
            }
        )
        return result["id"]
    
    async def get_latest_score(self, case_pk: int) -> Optional[ScoreState]:
        """Get the latest score for a case"""
        query = """
            SELECT score_state FROM eligibility_score_runs
            WHERE case_pk = :case_pk
            ORDER BY created_at DESC
            LIMIT 1
        """
        row = await database.fetch_one(query=query, values={"case_pk": case_pk})
        if row and row["score_state"]:
            score_dict = row["score_state"] if isinstance(row["score_state"], dict) else json.loads(row["score_state"])
            return ScoreState(**score_dict)
        return None
