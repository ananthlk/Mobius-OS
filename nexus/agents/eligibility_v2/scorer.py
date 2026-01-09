"""
Eligibility Scorer

Deterministic scoring logic for eligibility probability.
"""
import logging
from nexus.agents.eligibility_v2.models import (
    CaseState, ScoreState, ProductType, ContractStatus, Sex, EventTense
)
from nexus.services.eligibility_v2.propensity_repository import PropensityRepository

logger = logging.getLogger("nexus.eligibility_v2.scorer")


class EligibilityScorer:
    """Scorer for eligibility probability"""
    
    def __init__(self):
        self.propensity_repo = PropensityRepository()
    
    async def score(self, case_state: CaseState) -> ScoreState:
        """Compute eligibility score"""
        logger.debug("Computing score for case")
        
        # Get propensity data
        propensity_data = await self._get_propensity_data(case_state)
        
        # Compute base probability
        base_probability = propensity_data.get("probability", 0.5)
        base_confidence = propensity_data.get("combined_confidence", 0.5)
        
        # Create ScoreState
        score_state = ScoreState(
            base_probability=base_probability,
            base_confidence=base_confidence,
            probability_interval=propensity_data.get("probability_interval"),
            volatility=propensity_data.get("volatility"),
            sample_size=propensity_data.get("sample_size"),
            sample_confidence=propensity_data.get("sample_confidence"),
            backoff_path=propensity_data.get("backoff_path", []),
            backoff_level=propensity_data.get("backoff_level"),
            backoff_dims=propensity_data.get("backoff_dims"),
            drivers=[],
            missing_inputs=[],
            scoring_version="v1"
        )
        
        logger.info(f"Computed score: probability={base_probability:.2f}, confidence={base_confidence:.2f}")
        return score_state
    
    async def _get_propensity_data(self, case_state: CaseState) -> dict:
        """Get propensity data from repository"""
        # Extract dimensions
        product_type = case_state.health_plan.product_type.value if case_state.health_plan.product_type != ProductType.UNKNOWN else None
        contract_status = case_state.health_plan.contract_status.value if case_state.health_plan.contract_status != ContractStatus.UNKNOWN else None
        event_tense = case_state.timing.event_tense.value if case_state.timing.event_tense != EventTense.UNKNOWN else None
        payer_id = case_state.health_plan.payer_id
        sex = case_state.patient.sex.value if case_state.patient.sex and case_state.patient.sex != Sex.UNKNOWN else None
        
        # Age bucket
        age_bucket = None
        if case_state.patient.date_of_birth and case_state.timing.dos_date:
            from datetime import date
            age = (case_state.timing.dos_date - case_state.patient.date_of_birth).days // 365
            if age < 18:
                age_bucket = "0-17"
            elif age < 26:
                age_bucket = "18-25"
            elif age < 36:
                age_bucket = "26-35"
            elif age < 46:
                age_bucket = "36-45"
            elif age < 56:
                age_bucket = "46-55"
            elif age < 66:
                age_bucket = "56-65"
            else:
                age_bucket = "66+"
        
        return await self.propensity_repo.get_propensity_with_volatility(
            product_type=product_type,
            contract_status=contract_status,
            event_tense=event_tense,
            payer_id=payer_id,
            sex=sex,
            age_bucket=age_bucket
        )
