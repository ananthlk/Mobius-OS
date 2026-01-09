"""
Calculation Explanation Generator

Generates both machine-readable and human-readable explanations of probability calculations.
"""
import logging
from typing import Dict, Any, List
from nexus.agents.eligibility_v2.models import EligibilityStatus, EventTense
from pydantic import BaseModel

logger = logging.getLogger("nexus.eligibility_v2.calculation_explainer")


class CalculationExplanation(BaseModel):
    """Structured explanation of probability calculation"""
    base_probabilities: Dict[str, float]
    base_source: str  # "direct_evidence" or "historical_fallback"
    risk_probabilities: Dict[str, float]
    time_adjusted_risks: Dict[str, float]
    time_gap_days: int
    event_tense: str
    combination_steps: List[Dict[str, Any]]  # Step-by-step combination
    final_probabilities: Dict[str, float]
    human_readable: str  # Natural language explanation


class CalculationExplainer:
    """Generate transparent calculation explanations"""
    
    def generate_explanation(
        self,
        base_probs: Dict[EligibilityStatus, float],
        base_source: str,
        risk_probs: Dict[str, float],
        adjusted_risks: Dict[str, float],
        time_gap: int,
        event_tense: EventTense,
        final_probs: Dict[EligibilityStatus, float]
    ) -> CalculationExplanation:
        """Generate both structured and human-readable explanation"""
        
        # Machine-readable structured data
        explanation = CalculationExplanation(
            base_probabilities={k.value: v for k, v in base_probs.items()},
            base_source=base_source,
            risk_probabilities=risk_probs,
            time_adjusted_risks=adjusted_risks,
            time_gap_days=time_gap,
            event_tense=event_tense.value,
            combination_steps=self._generate_combination_steps(
                base_probs, adjusted_risks, final_probs
            ),
            final_probabilities={k.value: v for k, v in final_probs.items()},
            human_readable=self._generate_human_readable(
                base_probs, base_source, risk_probs, adjusted_risks,
                time_gap, event_tense, final_probs
            )
        )
        return explanation
    
    def _generate_combination_steps(
        self, base_probs, adjusted_risks, final_probs
    ) -> List[Dict[str, Any]]:
        """Generate step-by-step combination logic"""
        steps = []
        
        # Step 1: Start with base
        steps.append({
            "step": 1,
            "description": "Start with base probabilities",
            "probabilities": {k.value: v for k, v in base_probs.items()},
            "formula": "P_base(state)"
        })
        
        # Step 2: Apply each risk
        step_num = 2
        for risk_name, risk_prob in adjusted_risks.items():
            steps.append({
                "step": step_num,
                "description": f"Apply {risk_name} risk ({risk_prob:.1%})",
                "risk": risk_name,
                "risk_probability": risk_prob,
                "formula": self._get_risk_formula(risk_name)
            })
            step_num += 1
        
        # Step 3: Final probabilities
        steps.append({
            "step": step_num,
            "description": "Final probabilities after normalization",
            "probabilities": {k.value: v for k, v in final_probs.items()},
            "formula": "P_final(state) = normalized(P_base ± risks)"
        })
        
        return steps
    
    def _generate_human_readable(
        self, base_probs, base_source, risk_probs, adjusted_risks,
        time_gap, event_tense, final_probs
    ) -> str:
        """Generate natural language explanation"""
        lines = []
        
        # Base probability explanation
        if base_source == "direct_evidence":
            eligible_prob = base_probs.get(EligibilityStatus.YES, 0.0)
            if eligible_prob >= 0.9:
                lines.append(f"Based on direct eligibility check, patient is eligible (confidence: {eligible_prob:.0%}).")
            elif eligible_prob <= 0.1:
                not_eligible_prob = base_probs.get(EligibilityStatus.NO, 0.0)
                if not_eligible_prob >= 0.9:
                    lines.append(f"Based on direct eligibility check, patient is not eligible (confidence: {not_eligible_prob:.0%}).")
                else:
                    lines.append(f"Based on eligibility check, patient has {eligible_prob:.0%} probability of being eligible.")
            else:
                lines.append(f"Based on eligibility check, patient has {eligible_prob:.0%} probability of being eligible.")
        else:
            lines.append("No direct eligibility evidence available. Using historical propensity data:")
            for status, prob in base_probs.items():
                if prob > 0.05:
                    lines.append(f"  - {status.value}: {prob:.1%}")
        
        # Risk explanation
        if adjusted_risks:
            lines.append("\nRisk factors identified:")
            for risk_name, risk_prob in adjusted_risks.items():
                if risk_prob > 0.01:
                    risk_desc = self._get_risk_description(risk_name)
                    time_effect = ""
                    if time_gap > 0:
                        base_risk = risk_probs.get(risk_name, risk_prob)
                        if abs(risk_prob - base_risk) > 0.001:
                            if risk_prob > base_risk:
                                time_effect = f" (amplified from {base_risk:.1%} due to {time_gap}-day time gap)"
                            else:
                                time_effect = f" (reduced from {base_risk:.1%} due to {time_gap}-day time gap)"
                    lines.append(f"  - {risk_desc}: {risk_prob:.1%}{time_effect}")
        
        # Final probability explanation
        lines.append("\nFinal probability distribution:")
        for status, prob in sorted(final_probs.items(), key=lambda x: x[1], reverse=True):
            if prob > 0.01:
                lines.append(f"  - {status.value}: {prob:.1%}")
        
        return "\n".join(lines)
    
    def _get_risk_formula(self, risk_name: str) -> str:
        """Get formula for specific risk"""
        formulas = {
            "coverage_loss": "P(ELIGIBLE) × (1 - P_loss) → P(NOT_ELIGIBLE) += P(ELIGIBLE) × P_loss",
            "payer_error": "P(all) × P_error → P(UNESTABLISHED) += error_prob",
            "provider_error": "P(all) × P_error → P(UNESTABLISHED) += error_prob",
            "retrospective_denial": "P(ELIGIBLE) × (1 - P_denial) → P(NOT_ELIGIBLE) += P(ELIGIBLE) × P_denial"
        }
        return formulas.get(risk_name, "P(state) adjusted by risk")
    
    def _get_risk_description(self, risk_name: str) -> str:
        """Get human-readable risk description"""
        descriptions = {
            "coverage_loss": "Coverage loss before DOS",
            "payer_error": "Payer system error",
            "provider_error": "Provider data error",
            "retrospective_denial": "Retrospective payment denial"
        }
        return descriptions.get(risk_name, risk_name.replace("_", " ").title())
