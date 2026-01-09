"""
Probabilistic Combiner

Combines base probabilities with risk probabilities probabilistically.
Example:
- Base: ELIGIBLE = 100%, NOT_ELIGIBLE = 0%
- Risk: coverage_loss = 15%
- Result: ELIGIBLE = 85%, NOT_ELIGIBLE = 15%
"""
import logging
import asyncio
from typing import Dict, Optional, Callable, Any
from nexus.agents.eligibility_v2.models import EligibilityStatus, EventTense

logger = logging.getLogger("nexus.eligibility_v2.probabilistic_combiner")


class ProbabilisticCombiner:
    """Combines base probabilities with risk probabilities"""
    
    async def combine_probabilistically(
        self,
        base_probs: Dict[EligibilityStatus, float],
        risk_probs: Dict[str, float],
        event_tense: EventTense,
        emit_step: Optional[Callable[[str, Dict[str, Any]], None]] = None
    ) -> Dict[EligibilityStatus, float]:
        """
        Combine base probabilities with risk probabilities.
        
        Args:
            base_probs: Base probabilities for each state
            risk_probs: Risk probabilities (coverage_loss, payer_error, etc.)
            event_tense: FUTURE or PAST
            emit_step: Optional callback to emit calculation steps
        
        Returns:
            Final probabilities for each state (normalized to sum to 1.0)
        """
        final_probs = {
            EligibilityStatus.YES: base_probs.get(EligibilityStatus.YES, 0.0),
            EligibilityStatus.NO: base_probs.get(EligibilityStatus.NO, 0.0),
            EligibilityStatus.NOT_ESTABLISHED: base_probs.get(EligibilityStatus.NOT_ESTABLISHED, 0.0),
            EligibilityStatus.UNKNOWN: base_probs.get(EligibilityStatus.UNKNOWN, 0.0)
        }
        
        if emit_step:
            try:
                if asyncio.iscoroutinefunction(emit_step):
                    await emit_step("combination_start", {
                        "base_probabilities": {k.value: v for k, v in final_probs.items()},
                        "risk_probabilities": risk_probs
                    })
                else:
                    emit_step("combination_start", {
                        "base_probabilities": {k.value: v for k, v in final_probs.items()},
                        "risk_probabilities": risk_probs
                    })
            except Exception as e:
                logger.debug(f"Error emitting combination_start: {e}")
        
        # Apply coverage loss risk (moves probability from ELIGIBLE to NOT_ELIGIBLE)
        if "coverage_loss" in risk_probs:
            loss_prob = risk_probs["coverage_loss"]
            eligible_prob = final_probs[EligibilityStatus.YES]
            reduction = eligible_prob * loss_prob
            
            final_probs[EligibilityStatus.YES] = eligible_prob * (1 - loss_prob)
            final_probs[EligibilityStatus.NO] += reduction
            
            if emit_step:
                try:
                    step_data = {
                        "step": "coverage_loss",
                        "risk_probability": loss_prob,
                        "eligible_before": eligible_prob,
                        "eligible_after": final_probs[EligibilityStatus.YES],
                        "not_eligible_increase": reduction,
                        "formula": f"P(ELIGIBLE) × (1 - P_loss) → P(NOT_ELIGIBLE) += P(ELIGIBLE) × P_loss"
                    }
                    if asyncio.iscoroutinefunction(emit_step):
                        await emit_step("combination_step", step_data)
                    else:
                        emit_step("combination_step", step_data)
                except Exception as e:
                    logger.debug(f"Error emitting combination_step: {e}")
        
        # Apply retrospective denial risk (moves probability from ELIGIBLE to NOT_ELIGIBLE)
        if "retrospective_denial" in risk_probs:
            denial_prob = risk_probs["retrospective_denial"]
            eligible_prob = final_probs[EligibilityStatus.YES]
            reduction = eligible_prob * denial_prob
            
            final_probs[EligibilityStatus.YES] = eligible_prob * (1 - denial_prob)
            final_probs[EligibilityStatus.NO] += reduction
            
            if emit_step:
                try:
                    step_data = {
                        "step": "retrospective_denial",
                        "risk_probability": denial_prob,
                        "eligible_before": eligible_prob,
                        "eligible_after": final_probs[EligibilityStatus.YES],
                        "not_eligible_increase": reduction,
                        "formula": f"P(ELIGIBLE) × (1 - P_denial) → P(NOT_ELIGIBLE) += P(ELIGIBLE) × P_denial"
                    }
                    if asyncio.iscoroutinefunction(emit_step):
                        await emit_step("combination_step", step_data)
                    else:
                        emit_step("combination_step", step_data)
                except Exception as e:
                    logger.debug(f"Error emitting combination_step: {e}")
        
        # Apply payer/provider errors (moves probability to UNESTABLISHED)
        error_risks = risk_probs.get("payer_error", 0.0) + risk_probs.get("provider_error", 0.0)
        if error_risks > 0:
            # Distribute error probability proportionally from all states
            total_prob = sum(final_probs.values())
            if total_prob > 0:
                error_prob = total_prob * error_risks
                reductions = {}
                for state in final_probs:
                    reduction = final_probs[state] * (error_prob / total_prob)
                    reductions[state.value] = reduction
                    final_probs[state] -= reduction
                final_probs[EligibilityStatus.UNKNOWN] += error_prob
                
                if emit_step:
                    try:
                        step_data = {
                            "step": "payer_provider_errors",
                            "error_risk": error_risks,
                            "error_probability": error_prob,
                            "reductions": reductions,
                            "unestablished_increase": error_prob,
                            "formula": f"P(all) × P_error → P(UNESTABLISHED) += error_prob"
                        }
                        if asyncio.iscoroutinefunction(emit_step):
                            await emit_step("combination_step", step_data)
                        else:
                            emit_step("combination_step", step_data)
                    except Exception as e:
                        logger.debug(f"Error emitting combination_step: {e}")
        
        # Normalize to sum to 1.0
        total = sum(final_probs.values())
        if total > 0:
            final_probs = {k: v / total for k, v in final_probs.items()}
        
        if emit_step:
            try:
                if asyncio.iscoroutinefunction(emit_step):
                    await emit_step("combination_complete", {
                        "final_probabilities": {k.value: v for k, v in final_probs.items()},
                        "normalized": True
                    })
                else:
                    emit_step("combination_complete", {
                        "final_probabilities": {k.value: v for k, v in final_probs.items()},
                        "normalized": True
                    })
            except Exception as e:
                logger.debug(f"Error emitting combination_complete: {e}")
        
        return final_probs
