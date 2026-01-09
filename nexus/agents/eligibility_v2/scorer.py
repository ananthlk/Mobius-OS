"""
Eligibility Scorer

Deterministic scoring logic for eligibility probability using purist approach.
"""
import logging
import asyncio
from datetime import date
from typing import Optional, Callable, Any, Dict
from nexus.agents.eligibility_v2.models import (
    CaseState, ScoreState, EligibilityStatus, EventTense
)
from nexus.agents.eligibility_v2.base_probability_calculator import BaseProbabilityCalculator
from nexus.agents.eligibility_v2.risk_probability_calculator import RiskProbabilityCalculator
from nexus.agents.eligibility_v2.time_function import TimeFunction
from nexus.agents.eligibility_v2.probabilistic_combiner import ProbabilisticCombiner
from nexus.agents.eligibility_v2.calculation_explainer import CalculationExplainer

logger = logging.getLogger("nexus.eligibility_v2.scorer")


class EligibilityScorer:
    """Scorer for eligibility probability using purist approach"""
    
    def __init__(self):
        self.base_calculator = BaseProbabilityCalculator()
        self.risk_calculator = RiskProbabilityCalculator()
        self.time_function = TimeFunction()
        self.combiner = ProbabilisticCombiner()
        self.explainer = CalculationExplainer()
    
    async def score(
        self,
        case_state: CaseState,
        emit_calculation: Optional[Callable[[str, Dict[str, Any]], None]] = None
    ) -> ScoreState:
        """
        Compute eligibility score using purist approach.
        
        Args:
            case_state: Current case state
            emit_calculation: Optional callback to emit calculation steps as process events
        
        Returns:
            ScoreState with multi-state probabilities and calculation explanation
        """
        logger.debug("Computing score for case using purist approach")
        
        # Emit: Starting calculation
        if emit_calculation:
            try:
                if asyncio.iscoroutinefunction(emit_calculation):
                    await emit_calculation("calculation_start", {
                        "message": "Starting probability calculation",
                        "case_state_summary": self._summarize_case_state(case_state)
                    })
                else:
                    emit_calculation("calculation_start", {
                        "message": "Starting probability calculation",
                        "case_state_summary": self._summarize_case_state(case_state)
                    })
            except Exception as e:
                logger.debug(f"Error emitting calculation_start: {e}")
        
        # 1. Compute base probabilities (purist)
        base_probs, base_source = await self.base_calculator.compute_base_probability(
            case_state, emit_step=emit_calculation
        )
        
        # Emit: Base probabilities computed
        if emit_calculation:
            try:
                if asyncio.iscoroutinefunction(emit_calculation):
                    await emit_calculation("base_probabilities", {
                        "probabilities": {k.value: v for k, v in base_probs.items()},
                        "source": base_source,
                        "explanation": self._explain_base_probabilities(base_probs, base_source)
                    })
                else:
                    emit_calculation("base_probabilities", {
                        "probabilities": {k.value: v for k, v in base_probs.items()},
                        "source": base_source,
                        "explanation": self._explain_base_probabilities(base_probs, base_source)
                    })
            except Exception as e:
                logger.debug(f"Error emitting base_probabilities: {e}")
        
        # 2. Compute risk probabilities
        risk_probs = await self.risk_calculator.compute_risk_probabilities(
            case_state, emit_step=emit_calculation
        )
        
        # Emit: Risk probabilities computed
        if emit_calculation:
            try:
                if asyncio.iscoroutinefunction(emit_calculation):
                    await emit_calculation("risk_probabilities", {
                        "risks": risk_probs,
                        "explanation": self._explain_risks(risk_probs)
                    })
                else:
                    emit_calculation("risk_probabilities", {
                        "risks": risk_probs,
                        "explanation": self._explain_risks(risk_probs)
                    })
            except Exception as e:
                logger.debug(f"Error emitting risk_probabilities: {e}")
        
        # 3. Apply time function to risks
        time_gap = self._compute_time_gap(case_state)
        adjusted_risks = await self.time_function.apply_time_function(
            risk_probs, case_state.timing.event_tense, time_gap, emit_step=emit_calculation
        )
        
        # Emit: Time adjustment applied
        if emit_calculation:
            try:
                formula = f"P_risk_adjusted = P_risk_base × exp(α × {time_gap})" if case_state.timing.event_tense == EventTense.FUTURE else f"P_risk_adjusted = P_risk_base × exp(-α × {time_gap})"
                if asyncio.iscoroutinefunction(emit_calculation):
                    await emit_calculation("time_adjustment", {
                        "time_gap_days": time_gap,
                        "event_tense": case_state.timing.event_tense.value,
                        "base_risks": risk_probs,
                        "adjusted_risks": adjusted_risks,
                        "formula": formula
                    })
                else:
                    emit_calculation("time_adjustment", {
                        "time_gap_days": time_gap,
                        "event_tense": case_state.timing.event_tense.value,
                        "base_risks": risk_probs,
                        "adjusted_risks": adjusted_risks,
                        "formula": formula
                    })
            except Exception as e:
                logger.debug(f"Error emitting time_adjustment: {e}")
        
        # 4. Combine probabilistically
        final_probs = await self.combiner.combine_probabilistically(
            base_probs, adjusted_risks, case_state.timing.event_tense,
            emit_step=emit_calculation
        )
        
        # 5. Generate explanation
        explanation = self.explainer.generate_explanation(
            base_probs, base_source, risk_probs, adjusted_risks,
            time_gap, case_state.timing.event_tense, final_probs
        )
        
        # Emit: Final probabilities
        if emit_calculation:
            try:
                if asyncio.iscoroutinefunction(emit_calculation):
                    await emit_calculation("calculation_complete", {
                        "final_probabilities": {k.value: v for k, v in final_probs.items()},
                        "calculation_explanation": explanation.model_dump(),
                        "human_readable": explanation.human_readable
                    })
                else:
                    emit_calculation("calculation_complete", {
                        "final_probabilities": {k.value: v for k, v in final_probs.items()},
                        "calculation_explanation": explanation.model_dump(),
                        "human_readable": explanation.human_readable
                    })
            except Exception as e:
                logger.debug(f"Error emitting calculation_complete: {e}")
        
        # 6. Create ScoreState with multi-state probabilities
        base_confidence = self._compute_confidence(case_state, base_source)
        
        score_state = ScoreState(
            base_probability=final_probs[EligibilityStatus.YES],  # For backward compatibility
            base_confidence=base_confidence,
            state_probabilities={
                "eligible": final_probs[EligibilityStatus.YES],
                "not_eligible": final_probs[EligibilityStatus.NO],
                "no_info": final_probs[EligibilityStatus.NOT_ESTABLISHED],
                "unestablished": final_probs[EligibilityStatus.UNKNOWN]
            },
            risk_probabilities=adjusted_risks,
            base_probability_source=base_source,
            calculation_explanation=explanation.model_dump(),
            calculation_human_readable=explanation.human_readable,
            scoring_version="v2"  # Updated version
        )
        
        logger.info(
            f"Computed score: eligible={final_probs[EligibilityStatus.YES]:.2f}, "
            f"not_eligible={final_probs[EligibilityStatus.NO]:.2f}, "
            f"no_info={final_probs[EligibilityStatus.NOT_ESTABLISHED]:.2f}, "
            f"unestablished={final_probs[EligibilityStatus.UNKNOWN]:.2f}"
        )
        
        return score_state
    
    def _compute_time_gap(self, case_state: CaseState) -> int:
        """Compute time gap in days"""
        if not case_state.timing.dos_date:
            return 0
        
        today = date.today()
        
        if case_state.timing.event_tense == EventTense.FUTURE:
            # Days until DOS
            return max(0, (case_state.timing.dos_date - today).days)
        elif case_state.timing.event_tense == EventTense.PAST:
            # Days since visit
            return max(0, (today - case_state.timing.dos_date).days)
        else:
            return 0
    
    def _compute_confidence(self, case_state: CaseState, base_source: str) -> float:
        """Compute confidence in the score"""
        if base_source == "direct_evidence":
            # High confidence if we have direct evidence
            evidence_strength = case_state.eligibility_truth.evidence_strength
            strength_map = {
                "HIGH": 0.95,
                "MEDIUM": 0.85,
                "LOW": 0.70,
                "NONE": 0.50
            }
            return strength_map.get(evidence_strength.value if evidence_strength else "NONE", 0.50)
        else:
            # Lower confidence for historical fallback
            return 0.60
    
    def _summarize_case_state(self, case_state: CaseState) -> Dict[str, Any]:
        """Summarize case state for logging"""
        return {
            "has_eligibility_check": case_state.eligibility_check.checked,
            "eligibility_status": case_state.eligibility_truth.status.value if case_state.eligibility_truth.status else None,
            "event_tense": case_state.timing.event_tense.value,
            "dos_date": str(case_state.timing.dos_date) if case_state.timing.dos_date else None,
            "product_type": case_state.health_plan.product_type.value if case_state.health_plan.product_type else None
        }
    
    def _explain_base_probabilities(
        self, base_probs: Dict[EligibilityStatus, float], base_source: str
    ) -> str:
        """Generate explanation for base probabilities"""
        if base_source == "direct_evidence":
            eligible_prob = base_probs.get(EligibilityStatus.YES, 0.0)
            if eligible_prob >= 0.9:
                return f"Direct eligibility check shows patient is eligible (confidence: {eligible_prob:.0%})."
            elif eligible_prob <= 0.1:
                return f"Direct eligibility check shows patient is not eligible."
            else:
                return f"Direct eligibility check with {eligible_prob:.0%} confidence."
        else:
            return "Using historical propensity data as fallback."
    
    def _explain_risks(self, risk_probs: Dict[str, float]) -> str:
        """Generate explanation for risks"""
        if not risk_probs:
            return "No risks identified."
        
        lines = ["Risk factors:"]
        risk_descriptions = {
            "coverage_loss": "Coverage loss",
            "payer_error": "Payer error",
            "provider_error": "Provider error",
            "retrospective_denial": "Retrospective denial"
        }
        
        for risk_name, risk_prob in risk_probs.items():
            if risk_prob > 0.01:
                desc = risk_descriptions.get(risk_name, risk_name.replace("_", " ").title())
                lines.append(f"  - {desc}: {risk_prob:.1%}")
        
        return "\n".join(lines)
