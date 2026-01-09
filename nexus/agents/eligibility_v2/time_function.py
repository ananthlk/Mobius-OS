"""
Time Function

Amplifies or deteriorates risk probabilities based on time gap and event tense.
- FUTURE events: risks amplify over time (longer gap = higher risk)
- PAST events: risks deteriorate over time (longer gap = lower risk if not yet occurred)
"""
import logging
import math
import asyncio
from typing import Dict, Optional, Callable, Any
from nexus.agents.eligibility_v2.models import EventTense

logger = logging.getLogger("nexus.eligibility_v2.time_function")


class TimeFunction:
    """Applies time-based amplification/deterioration to risk probabilities"""
    
    async def apply_time_function(
        self,
        risk_probabilities: Dict[str, float],
        event_tense: EventTense,
        time_gap_days: int,
        emit_step: Optional[Callable[[str, Dict[str, Any]], None]] = None
    ) -> Dict[str, float]:
        """
        Apply time-based amplification/deterioration to risk probabilities.
        
        Args:
            risk_probabilities: Base risk probabilities
            event_tense: FUTURE or PAST
            time_gap_days: Time gap in days (positive)
            emit_step: Optional callback to emit calculation steps
        
        Returns:
            Adjusted risk probabilities
        """
        adjusted_risks = {}
        
        if emit_step:
            try:
                if asyncio.iscoroutinefunction(emit_step):
                    await emit_step("time_adjustment_start", {
                        "event_tense": event_tense.value,
                        "time_gap_days": time_gap_days,
                        "base_risks": risk_probabilities
                    })
                else:
                    emit_step("time_adjustment_start", {
                        "event_tense": event_tense.value,
                        "time_gap_days": time_gap_days,
                        "base_risks": risk_probabilities
                    })
            except Exception as e:
                logger.debug(f"Error emitting time_adjustment_start: {e}")
        
        for risk_name, base_prob in risk_probabilities.items():
            if event_tense == EventTense.FUTURE:
                # Amplify: exp(α * t) where α > 0
                adjusted_prob = self._amplify_risk(risk_name, base_prob, time_gap_days)
            elif event_tense == EventTense.PAST:
                # Deteriorate: exp(-α * t) where α > 0
                adjusted_prob = self._deteriorate_risk(risk_name, base_prob, time_gap_days)
            else:
                # UNKNOWN: no adjustment
                adjusted_prob = base_prob
            
            adjusted_risks[risk_name] = adjusted_prob
            
            if emit_step and abs(adjusted_prob - base_prob) > 0.001:
                try:
                    if asyncio.iscoroutinefunction(emit_step):
                        await emit_step("time_adjustment_risk", {
                            "risk_name": risk_name,
                            "base_probability": base_prob,
                            "adjusted_probability": adjusted_prob,
                            "time_gap_days": time_gap_days,
                            "formula": self._get_formula(risk_name, event_tense, time_gap_days),
                            "explanation": self._get_explanation(risk_name, base_prob, adjusted_prob, time_gap_days, event_tense)
                        })
                    else:
                        emit_step("time_adjustment_risk", {
                            "risk_name": risk_name,
                            "base_probability": base_prob,
                            "adjusted_probability": adjusted_prob,
                            "time_gap_days": time_gap_days,
                            "formula": self._get_formula(risk_name, event_tense, time_gap_days),
                            "explanation": self._get_explanation(risk_name, base_prob, adjusted_prob, time_gap_days, event_tense)
                        })
                except Exception as e:
                    logger.debug(f"Error emitting time_adjustment_risk: {e}")
        
        if emit_step:
            try:
                if asyncio.iscoroutinefunction(emit_step):
                    await emit_step("time_adjustment_complete", {
                        "adjusted_risks": adjusted_risks,
                        "explanation": f"Applied time-based adjustments for {event_tense.value} event with {time_gap_days}-day gap"
                    })
                else:
                    emit_step("time_adjustment_complete", {
                        "adjusted_risks": adjusted_risks,
                        "explanation": f"Applied time-based adjustments for {event_tense.value} event with {time_gap_days}-day gap"
                    })
            except Exception as e:
                logger.debug(f"Error emitting time_adjustment_complete: {e}")
        
        return adjusted_risks
    
    def _amplify_risk(self, risk_name: str, base_prob: float, time_gap_days: int) -> float:
        """Amplify risk for future events"""
        # Get amplification factor α based on risk type
        alpha = self._get_alpha(risk_name, is_future=True)
        
        # Apply exponential amplification: P_adjusted = P_base * exp(α * t)
        amplification = math.exp(alpha * time_gap_days)
        adjusted = base_prob * amplification
        
        # Cap at 1.0
        return min(1.0, adjusted)
    
    def _deteriorate_risk(self, risk_name: str, base_prob: float, time_gap_days: int) -> float:
        """Deteriorate risk for past events"""
        # Special handling for retrospective_denial: linear decrease for 60 days, then 0
        if risk_name == "retrospective_denial":
            if time_gap_days <= 60:
                # Linear decrease: P_adjusted = P_base * (1 - t/60)
                # Goes from P_base at t=0 to 0 at t=60
                linear_factor = 1.0 - (time_gap_days / 60.0)
                adjusted = base_prob * linear_factor
            else:
                # After 60 days, risk is 0
                adjusted = 0.0
            return max(0.0, adjusted)
        
        # For other risks, use exponential deterioration
        # Get deterioration factor α based on risk type
        alpha = self._get_alpha(risk_name, is_future=False)
        
        # Apply exponential deterioration: P_adjusted = P_base * exp(-α * t)
        deterioration = math.exp(-alpha * time_gap_days)
        adjusted = base_prob * deterioration
        
        # Don't go below 0
        return max(0.0, adjusted)
    
    def _get_alpha(self, risk_name: str, is_future: bool) -> float:
        """Get time factor α for specific risk type"""
        if is_future:
            # Future amplification factors
            factors = {
                "coverage_loss": 0.001,      # 0.1% per day
                "payer_error": 0.0005,        # 0.05% per day
                "provider_error": 0.0005,     # 0.05% per day
            }
        else:
            # Past deterioration factors
            factors = {
                "retrospective_denial": 0.0005,  # 0.05% per day decay
                "payer_error": 0.001,            # 0.1% per day decay
                "provider_error": 0.001,          # 0.1% per day decay
            }
        
        return factors.get(risk_name, 0.0005)  # Default
    
    def _get_formula(self, risk_name: str, event_tense: EventTense, time_gap_days: int) -> str:
        """Get formula string for this adjustment"""
        if event_tense == EventTense.FUTURE:
            alpha = self._get_alpha(risk_name, is_future=True)
            return f"P_adjusted = P_base × exp({alpha} × {time_gap_days})"
        else:
            # Past events
            if risk_name == "retrospective_denial":
                if time_gap_days <= 60:
                    return f"P_adjusted = P_base × (1 - {time_gap_days}/60)  [linear decrease]"
                else:
                    return f"P_adjusted = 0.0  [after 60 days]"
            else:
                alpha = self._get_alpha(risk_name, is_future=False)
                return f"P_adjusted = P_base × exp(-{alpha} × {time_gap_days})"
    
    def _get_explanation(
        self, risk_name: str, base_prob: float, adjusted_prob: float,
        time_gap_days: int, event_tense: EventTense
    ) -> str:
        """Get human-readable explanation"""
        risk_descriptions = {
            "coverage_loss": "Coverage loss",
            "payer_error": "Payer error",
            "provider_error": "Provider error",
            "retrospective_denial": "Retrospective denial"
        }
        desc = risk_descriptions.get(risk_name, risk_name.replace("_", " ").title())
        
        if event_tense == EventTense.FUTURE:
            if adjusted_prob > base_prob:
                return f"{desc} risk amplified from {base_prob:.1%} to {adjusted_prob:.1%} due to {time_gap_days}-day time gap"
            else:
                return f"{desc} risk: {adjusted_prob:.1%} (no significant change)"
        else:
            # Past events
            if risk_name == "retrospective_denial":
                if time_gap_days <= 60:
                    return f"{desc} risk linearly reduced from {base_prob:.1%} to {adjusted_prob:.1%} ({time_gap_days} days since DOS, linear decrease over 60 days)"
                else:
                    return f"{desc} risk is 0% (more than 60 days since DOS)"
            else:
                if adjusted_prob < base_prob:
                    return f"{desc} risk reduced from {base_prob:.1%} to {adjusted_prob:.1%} due to {time_gap_days}-day time gap"
                else:
                    return f"{desc} risk: {adjusted_prob:.1%} (no significant change)"
