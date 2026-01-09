"""
Risk Probability Calculator

Computes separate risk probabilities (not adjustments, but actual probabilities):
- Coverage loss risk (for future events)
- Retrospective denial risk (for past events)
- Payer error risk
- Provider error risk
"""
import logging
import asyncio
from typing import Dict, Optional, Callable, Any
from nexus.agents.eligibility_v2.models import CaseState, EventTense
from nexus.modules.database import database

logger = logging.getLogger("nexus.eligibility_v2.risk_probability_calculator")


class RiskProbabilityCalculator:
    """Calculator for risk probabilities"""
    
    async def compute_risk_probabilities(
        self,
        case_state: CaseState,
        emit_step: Optional[Callable[[str, Dict[str, Any]], None]] = None
    ) -> Dict[str, float]:
        """
        Compute probability of each risk occurring.
        
        Returns:
            Dict mapping risk name to probability, e.g.:
            {
                "coverage_loss": 0.15,  # 15% chance of losing coverage
                "payer_error": 0.05,    # 5% chance of payer system error
                "provider_error": 0.03,  # 3% chance of provider data error
                "retrospective_denial": 0.10  # 10% chance of retrospective denial
            }
        """
        risks = {}
        
        if case_state.timing.event_tense == EventTense.FUTURE:
            # Future risks
            if emit_step:
                await emit_step("risk_calculation_start", {
                    "event_tense": "FUTURE",
                    "message": "Computing future event risks"
                })
            
            risks["coverage_loss"] = await self._compute_coverage_loss_risk(case_state, emit_step)
            risks["payer_error"] = await self._compute_payer_error_risk(case_state, emit_step)
            risks["provider_error"] = await self._compute_provider_error_risk(case_state, emit_step)
            
        elif case_state.timing.event_tense == EventTense.PAST:
            # Past risks
            if emit_step:
                try:
                    if asyncio.iscoroutinefunction(emit_step):
                        await emit_step("risk_calculation_start", {
                            "event_tense": "PAST",
                            "message": "Computing retrospective risks"
                        })
                    else:
                        emit_step("risk_calculation_start", {
                            "event_tense": "PAST",
                            "message": "Computing retrospective risks"
                        })
                except Exception as e:
                    logger.debug(f"Error emitting risk_calculation_start: {e}")
            
            risks["retrospective_denial"] = await self._compute_retrospective_denial_risk(case_state, emit_step)
            risks["payer_error"] = await self._compute_payer_error_risk(case_state, emit_step)
            risks["provider_error"] = await self._compute_provider_error_risk(case_state, emit_step)
        
        if emit_step:
            try:
                if asyncio.iscoroutinefunction(emit_step):
                    await emit_step("risk_calculation_complete", {
                        "risks": risks,
                        "explanation": self._explain_risks(risks, case_state.timing.event_tense)
                    })
                else:
                    emit_step("risk_calculation_complete", {
                        "risks": risks,
                        "explanation": self._explain_risks(risks, case_state.timing.event_tense)
                    })
            except Exception as e:
                logger.debug(f"Error emitting risk_calculation_complete: {e}")
        
        return risks
    
    async def _compute_coverage_loss_risk(
        self, case_state: CaseState, emit_step: Optional[Callable] = None
    ) -> float:
        """Compute probability of coverage loss before DOS"""
        # Query historical coverage loss patterns
        # For now, use simplified logic based on product type and time gap
        
        if not case_state.timing.dos_date:
            return 0.0
        
        from datetime import date
        today = date.today()
        days_until_dos = (case_state.timing.dos_date - today).days
        
        if days_until_dos <= 0:
            return 0.0
        
        # Base risk by product type
        product_type = case_state.health_plan.product_type
        base_risk = {
            "MEDICAID": 0.15,      # Higher volatility
            "MEDICARE": 0.08,
            "DSNP": 0.12,
            "COMMERCIAL": 0.05,    # Lower volatility
            "OTHER": 0.10,
            "UNKNOWN": 0.10
        }.get(product_type.value if product_type else "UNKNOWN", 0.10)
        
        # Query historical data if available
        try:
            query = """
                SELECT 
                    COUNT(*) FILTER (WHERE lost_coverage_before_dos = true)::float / COUNT(*) as loss_rate
                FROM eligibility_transactions
                WHERE eligibility_status = 'YES'
                    AND event_tense = 'FUTURE'
                    AND product_type = :product_type
                    AND days_until_dos BETWEEN :min_days AND :max_days
            """
            values = {
                "product_type": product_type.value if product_type else "UNKNOWN",
                "min_days": max(1, days_until_dos - 7),
                "max_days": days_until_dos + 7
            }
            row = await database.fetch_one(query=query, values=values)
            if row and row.get("loss_rate"):
                base_risk = float(row["loss_rate"])
        except Exception as e:
            logger.debug(f"Could not query historical coverage loss data: {e}")
        
        if emit_step:
            try:
                if asyncio.iscoroutinefunction(emit_step):
                    await emit_step("coverage_loss_risk", {
                        "risk": base_risk,
                        "days_until_dos": days_until_dos,
                        "product_type": product_type.value if product_type else "UNKNOWN",
                        "explanation": f"Coverage loss risk: {base_risk:.1%} based on product type and historical patterns"
                    })
                else:
                    emit_step("coverage_loss_risk", {
                        "risk": base_risk,
                        "days_until_dos": days_until_dos,
                        "product_type": product_type.value if product_type else "UNKNOWN",
                        "explanation": f"Coverage loss risk: {base_risk:.1%} based on product type and historical patterns"
                    })
            except Exception as e:
                logger.debug(f"Error emitting coverage_loss_risk: {e}")
        
        return base_risk
    
    async def _compute_retrospective_denial_risk(
        self, case_state: CaseState, emit_step: Optional[Callable] = None
    ) -> float:
        """Compute probability of retrospective payment denial"""
        # Query historical denial patterns
        # For now, use simplified logic
        
        if not case_state.timing.dos_date:
            return 0.0
        
        from datetime import date
        today = date.today()
        days_since_visit = (today - case_state.timing.dos_date).days
        
        if days_since_visit <= 0:
            return 0.0
        
        # Base risk decreases over time (if not denied yet, less likely to be denied)
        base_risk = 0.10  # 10% base risk
        
        # Query historical data if available
        try:
            query = """
                SELECT 
                    COUNT(*) FILTER (WHERE payment_status = 'DENIED')::float / COUNT(*) as denial_rate
                FROM eligibility_transactions
                WHERE eligibility_status = 'YES'
                    AND event_tense = 'PAST'
                    AND days_since_visit BETWEEN :min_days AND :max_days
            """
            values = {
                "min_days": max(1, days_since_visit - 30),
                "max_days": days_since_visit + 30
            }
            row = await database.fetch_one(query=query, values=values)
            if row and row.get("denial_rate"):
                base_risk = float(row["denial_rate"])
        except Exception as e:
            logger.debug(f"Could not query historical denial data: {e}")
        
        if emit_step:
            try:
                if asyncio.iscoroutinefunction(emit_step):
                    await emit_step("retrospective_denial_risk", {
                        "risk": base_risk,
                        "days_since_visit": days_since_visit,
                        "explanation": f"Retrospective denial risk: {base_risk:.1%} based on historical patterns"
                    })
                else:
                    emit_step("retrospective_denial_risk", {
                        "risk": base_risk,
                        "days_since_visit": days_since_visit,
                        "explanation": f"Retrospective denial risk: {base_risk:.1%} based on historical patterns"
                    })
            except Exception as e:
                logger.debug(f"Error emitting retrospective_denial_risk: {e}")
        
        return base_risk
    
    async def _compute_payer_error_risk(
        self, case_state: CaseState, emit_step: Optional[Callable] = None
    ) -> float:
        """Compute probability of payer system error"""
        payer_id = case_state.health_plan.payer_id
        
        if not payer_id:
            return 0.05  # Default 5% if no payer info
        
        # Query historical payer error rates
        base_risk = 0.05  # Default 5%
        
        try:
            query = """
                SELECT 
                    COUNT(*) FILTER (WHERE error_type IS NOT NULL)::float / COUNT(*) as error_rate
                FROM eligibility_transactions
                WHERE payer_id = :payer_id
            """
            values = {"payer_id": payer_id}
            row = await database.fetch_one(query=query, values=values)
            if row and row.get("error_rate"):
                base_risk = float(row["error_rate"])
        except Exception as e:
            logger.debug(f"Could not query payer error data: {e}")
        
        if emit_step:
            try:
                if asyncio.iscoroutinefunction(emit_step):
                    await emit_step("payer_error_risk", {
                        "risk": base_risk,
                        "payer_id": payer_id,
                        "explanation": f"Payer error risk: {base_risk:.1%} for payer {payer_id}"
                    })
                else:
                    emit_step("payer_error_risk", {
                        "risk": base_risk,
                        "payer_id": payer_id,
                        "explanation": f"Payer error risk: {base_risk:.1%} for payer {payer_id}"
                    })
            except Exception as e:
                logger.debug(f"Error emitting payer_error_risk: {e}")
        
        return base_risk
    
    async def _compute_provider_error_risk(
        self, case_state: CaseState, emit_step: Optional[Callable] = None
    ) -> float:
        """Compute probability of provider data error"""
        # For now, use default risk
        # In future, could query by provider_id if available in visits
        
        base_risk = 0.03  # Default 3%
        
        # Could query by provider from visits if available
        if case_state.timing.related_visits:
            # Use first visit's provider if available
            provider = case_state.timing.related_visits[0].provider if case_state.timing.related_visits else None
            if provider:
                try:
                    query = """
                        SELECT 
                            COUNT(*) FILTER (WHERE error_type IS NOT NULL)::float / COUNT(*) as error_rate
                        FROM eligibility_transactions
                        WHERE provider_id = :provider_id
                    """
                    values = {"provider_id": provider}
                    row = await database.fetch_one(query=query, values=values)
                    if row and row.get("error_rate"):
                        base_risk = float(row["error_rate"])
                except Exception as e:
                    logger.debug(f"Could not query provider error data: {e}")
        
        if emit_step:
            try:
                if asyncio.iscoroutinefunction(emit_step):
                    await emit_step("provider_error_risk", {
                        "risk": base_risk,
                        "explanation": f"Provider error risk: {base_risk:.1%}"
                    })
                else:
                    emit_step("provider_error_risk", {
                        "risk": base_risk,
                        "explanation": f"Provider error risk: {base_risk:.1%}"
                    })
            except Exception as e:
                logger.debug(f"Error emitting provider_error_risk: {e}")
        
        return base_risk
    
    def _explain_risks(self, risks: Dict[str, float], event_tense: EventTense) -> str:
        """Generate human-readable explanation of risks"""
        if not risks:
            return "No risks identified."
        
        lines = ["Risk factors identified:"]
        risk_descriptions = {
            "coverage_loss": "Coverage loss before DOS",
            "payer_error": "Payer system error",
            "provider_error": "Provider data error",
            "retrospective_denial": "Retrospective payment denial"
        }
        
        for risk_name, risk_prob in risks.items():
            if risk_prob > 0.01:
                desc = risk_descriptions.get(risk_name, risk_name.replace("_", " ").title())
                lines.append(f"  - {desc}: {risk_prob:.1%}")
        
        return "\n".join(lines)
