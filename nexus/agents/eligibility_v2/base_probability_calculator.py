"""
Base Probability Calculator

Computes base probability for each eligibility state using purist approach:
- Direct evidence (270 transaction) → deterministic 100%/0%
- No direct evidence → historical propensity fallback
"""
import logging
import asyncio
from typing import Dict, Optional, Callable, Any, Tuple
from nexus.agents.eligibility_v2.models import (
    CaseState, EligibilityStatus, EvidenceStrength
)
from nexus.services.eligibility_v2.propensity_repository import PropensityRepository

logger = logging.getLogger("nexus.eligibility_v2.base_probability_calculator")


class BaseProbabilityCalculator:
    """Calculator for base probability using purist approach"""
    
    def __init__(self):
        self.propensity_repo = PropensityRepository()
    
    async def compute_base_probability(
        self,
        case_state: CaseState,
        emit_step: Optional[Callable[[str, Dict[str, Any]], None]] = None
    ) -> Tuple[Dict[EligibilityStatus, float], str]:
        """
        Compute base probability for each state based on current case state.
        
        Returns:
            Tuple of (probabilities dict, source string)
            - probabilities: {ELIGIBLE: p1, NOT_ELIGIBLE: p2, NO_INFO: p3, UNESTABLISHED: p4}
            - source: "direct_evidence" or "historical_fallback"
        """
        # Check for direct evidence (270 transaction result)
        # Purist approach: Direct evidence is deterministic (100% or 0%)
        if (case_state.eligibility_check.checked and 
            case_state.eligibility_truth.status != EligibilityStatus.NOT_ESTABLISHED):
            
            evidence_strength = case_state.eligibility_truth.evidence_strength
            
            if case_state.eligibility_truth.status == EligibilityStatus.YES:
                # Direct evidence shows eligible → 100% eligible, 0% not eligible
                # Uncertainty (if any) goes to NOT_ESTABLISHED
                result = {
                    EligibilityStatus.YES: 1.0,  # 100% eligible
                    EligibilityStatus.NO: 0.0,    # 0% not eligible
                    EligibilityStatus.NOT_ESTABLISHED: 0.0,
                    EligibilityStatus.UNKNOWN: 0.0
                }
                
                if emit_step:
                    try:
                        if asyncio.iscoroutinefunction(emit_step):
                            await emit_step("base_probability_direct_evidence", {
                                "status": "YES",
                                "evidence_strength": evidence_strength.value,
                                "probabilities": {k.value: v for k, v in result.items()},
                                "explanation": "Direct eligibility check shows patient is eligible (100% payment expected)."
                            })
                        else:
                            emit_step("base_probability_direct_evidence", {
                                "status": "YES",
                                "evidence_strength": evidence_strength.value,
                                "probabilities": {k.value: v for k, v in result.items()},
                                "explanation": "Direct eligibility check shows patient is eligible (100% payment expected)."
                            })
                    except Exception as e:
                        logger.debug(f"Error emitting base_probability_direct_evidence: {e}")
                
                return result, "direct_evidence"
                
            elif case_state.eligibility_truth.status == EligibilityStatus.NO:
                # Direct evidence shows not eligible → 0% eligible, 100% not eligible
                result = {
                    EligibilityStatus.YES: 0.0,    # 0% eligible
                    EligibilityStatus.NO: 1.0,      # 100% not eligible
                    EligibilityStatus.NOT_ESTABLISHED: 0.0,
                    EligibilityStatus.UNKNOWN: 0.0
                }
                
                if emit_step:
                    try:
                        if asyncio.iscoroutinefunction(emit_step):
                            await emit_step("base_probability_direct_evidence", {
                                "status": "NO",
                                "evidence_strength": evidence_strength.value,
                                "probabilities": {k.value: v for k, v in result.items()},
                                "explanation": "Direct eligibility check shows patient is not eligible (0% payment expected)."
                            })
                        else:
                            emit_step("base_probability_direct_evidence", {
                                "status": "NO",
                                "evidence_strength": evidence_strength.value,
                                "probabilities": {k.value: v for k, v in result.items()},
                                "explanation": "Direct eligibility check shows patient is not eligible (0% payment expected)."
                            })
                    except Exception as e:
                        logger.debug(f"Error emitting base_probability_direct_evidence: {e}")
                
                return result, "direct_evidence"
        
        # No direct evidence → use historical propensity as fallback
        if emit_step:
            try:
                if asyncio.iscoroutinefunction(emit_step):
                    await emit_step("base_probability_historical_fallback", {
                        "message": "No direct eligibility evidence available. Using historical propensity data."
                    })
                else:
                    emit_step("base_probability_historical_fallback", {
                        "message": "No direct eligibility evidence available. Using historical propensity data."
                    })
            except Exception as e:
                logger.debug(f"Error emitting base_probability_historical_fallback: {e}")
        
        historical_probs = await self.propensity_repo.get_historical_propensity_by_state(case_state)
        
        if emit_step:
            try:
                if asyncio.iscoroutinefunction(emit_step):
                    await emit_step("base_probability_historical_result", {
                        "probabilities": {k.value: v for k, v in historical_probs.items()},
                        "explanation": "Historical propensity data: " + ", ".join([
                            f"{k.value}: {v:.1%}" for k, v in historical_probs.items() if v > 0.05
                        ])
                    })
                else:
                    emit_step("base_probability_historical_result", {
                        "probabilities": {k.value: v for k, v in historical_probs.items()},
                        "explanation": "Historical propensity data: " + ", ".join([
                            f"{k.value}: {v:.1%}" for k, v in historical_probs.items() if v > 0.05
                        ])
                    })
            except Exception as e:
                logger.debug(f"Error emitting base_probability_historical_result: {e}")
        
        return historical_probs, "historical_fallback"
