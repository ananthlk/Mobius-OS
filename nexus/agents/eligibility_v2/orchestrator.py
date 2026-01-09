"""
Eligibility Agent V2 - Orchestrator

Main orchestrator that coordinates the eligibility assessment workflow.
"""
import logging
import json
import hashlib
import time
from typing import Optional, Dict, Any
from datetime import date, datetime
from copy import deepcopy

from nexus.agents.eligibility_v2.models import (
    CaseState, UIEvent, LLMPlanResponse, ScoreState, CompletionStatus,
    EligibilityStatus, EventTense, ProductType, VisitInfo, EligibilityCheckSource,
    EvidenceStrength, ContractStatus, Sex
)
from nexus.agents.eligibility_v2.interpreter import EligibilityInterpreter
from nexus.agents.eligibility_v2.scorer import EligibilityScorer
from nexus.agents.eligibility_v2.planner import EligibilityPlanner
from nexus.agents.eligibility_v2.completion_checker import CompletionChecker
from nexus.services.eligibility_v2.case_repository import CaseRepository
from nexus.services.eligibility_v2.turn_repository import TurnRepository
from nexus.services.eligibility_v2.scoring_repository import ScoringRepository
from nexus.services.eligibility_v2.llm_call_repository import LLMCallRepository
from nexus.modules.database import database

logger = logging.getLogger("nexus.eligibility_v2.orchestrator")


class EligibilityOrchestrator:
    """
    Main orchestrator for Eligibility Agent V2.
    Coordinates interpreter, scorer, planner, and tool execution.
    """
    
    def __init__(self):
        self.interpreter = EligibilityInterpreter()
        self.scorer = EligibilityScorer()
        self.planner = EligibilityPlanner()
        self.completion_checker = CompletionChecker()
        self.case_repo = CaseRepository()
        self.turn_repo = TurnRepository()
        self.scoring_repo = ScoringRepository()
        self.llm_call_repo = LLMCallRepository()
    
    async def process_turn(
        self,
        case_id: str,
        ui_event: UIEvent,
        session_id: Optional[int] = None,
        patient_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process a single turn (user message or form submission).
        
        Returns:
            Dict with case_state, score_state, next_questions, improvement_plan, presentation_summary
        """
        logger.info(f"Processing turn for case {case_id}")
        
        # 1. Get or create case
        case_pk = await self.case_repo.get_or_create_case(case_id, session_id)
        
        # 2. Load current case state
        case_state = await self.case_repo.get_case_state(case_pk)
        if not case_state:
            case_state = CaseState()
        
        # 3. Load patient data if patient_id provided (always fresh, never cached)
        if patient_id:
            await self._emit_process_event(session_id, "patient_loading", "in_progress", "Loading patient EMR record...")
            case_state = await self._load_patient_data(case_state, patient_id, session_id)
            await self._emit_process_event(session_id, "patient_loading", "complete", "Patient details loaded")
        
        # 4. Interpret user input
        await self._emit_process_event(session_id, "interpretation", "in_progress", "Interpreting user input - extracting information from message...")
        interpret_response = await self.interpreter.interpret(
            case_state=case_state,
            ui_event=ui_event,
            case_pk=case_pk
        )
        
        # Apply interpreter suggestions deterministically
        case_state = self._deterministically_update_case_state(
            case_state=case_state,
            update_source="interpreter",
            updates=interpret_response.suggested_updates.model_dump()
        )
        
        completion_status = interpret_response.completion
        
        # Check for missing fields after interpretation
        missing_fields = completion_status.missing_fields
        missing_msg = f"Interpretation complete"
        if missing_fields:
            missing_msg += f" - Missing fields: {', '.join(missing_fields)}"
        await self._emit_process_event(session_id, "interpretation", "complete", missing_msg)
        
        # 5. Perform eligibility check if insurance info is available
        if case_state.health_plan.payer_name and case_state.patient.member_id:
            eligibility_result = await self._check_and_perform_eligibility_check(case_state, session_id)
            # Apply eligibility check updates deterministically
            case_state = self._deterministically_update_case_state(
                case_state=case_state,
                update_source="eligibility_check",
                updates={},  # Updates come from eligibility_result
                eligibility_check_result=eligibility_result
            )
        
        # 6. Score
        await self._emit_process_event(session_id, "scoring", "in_progress", "Scoring engine initiated - calculating eligibility probability...")
        # Create emit callback for calculation steps
        async def emit_calculation(step: str, data: Dict[str, Any]) -> None:
            """Emit calculation step as thinking message"""
            await self._emit_thinking_message(
                session_id=session_id,
                phase="scoring",
                message=f"[Calculation: {step}] {data.get('explanation', data.get('message', ''))}",
                metadata={"calculation_step": step, **data}
            )
        
        score_state = await self.scorer.score(case_state, emit_calculation=emit_calculation)
        
        # 6.5. If we have visits with probabilities, compute weighted average for case-level probability
        if case_state.timing.related_visits and len(case_state.timing.related_visits) > 0:
            weighted_avg = self._compute_weighted_average_probability(case_state.timing.related_visits)
            if weighted_avg is not None:
                # Update base_probability with weighted average
                score_state.base_probability = weighted_avg
                # Also update state_probabilities if available
                if score_state.state_probabilities:
                    # For now, update eligible probability (main one)
                    # In future, could compute weighted averages for all states
                    score_state.state_probabilities["eligible"] = weighted_avg
                logger.info(
                    f"Updated case-level probability to weighted average: {weighted_avg:.2%} "
                    f"from {len(case_state.timing.related_visits)} visits"
                )
        
        # Prepare scoring summary data for status bar
        scoring_data = {
            "overall_probability": score_state.base_probability,
            "confidence": score_state.base_confidence,
            "visits": []
        }
        
        # Extract visit dates and probabilities
        if case_state.timing.related_visits:
            for visit in case_state.timing.related_visits:
                visit_data = {
                    "visit_date": visit.visit_date.isoformat() if visit.visit_date else None,
                    "probability": visit.eligibility_probability,
                    "status": visit.eligibility_status.value if visit.eligibility_status else None,
                    "visit_type": visit.visit_type
                }
                scoring_data["visits"].append(visit_data)
        
        await self._emit_process_event(
            session_id, 
            "scoring", 
            "complete", 
            f"Scoring complete - Overall Likelihood: {score_state.base_probability:.1%}",
            data=scoring_data
        )
        
        # 7. Plan
        await self._emit_process_event(session_id, "planning", "in_progress", "Planning phase initiated - generating questions and improvement plan...")
        plan_response = await self.planner.plan(
            case_state=case_state,
            score_state=score_state,
            completion_status=completion_status
        )
        await self._emit_process_event(
            session_id,
            "planning",
            "complete",
            f"Planning complete\nGenerated {len(plan_response.next_questions)} question(s)\nCreated {len(plan_response.improvement_plan)} improvement action(s)"
        )
        
        # 8. Save state
        await self.case_repo.update_case_state(case_pk, case_state)
        await self.scoring_repo.create_score_run(case_pk, None, score_state, "v1")
        
        # 9. Return result
        return {
            "case_id": case_id,
            "case_pk": case_pk,
            "status": "COMPLETE",
            "case_state": case_state.model_dump(),
            "score_state": score_state.model_dump(),
            "next_questions": [q.model_dump() for q in plan_response.next_questions],
            "improvement_plan": [a.model_dump() for a in plan_response.improvement_plan],
            "presentation_summary": plan_response.presentation_summary,
            "completion": completion_status.model_dump()
        }
    
    async def _load_patient_data(
        self,
        case_state: CaseState,
        patient_id: str,
        session_id: Optional[int] = None
    ) -> CaseState:
        """
        Load patient data from EMR/tools.
        Always loads fresh data (never cached).
        """
        from nexus.tools.eligibility.gate1_data_retrieval import (
            EMRPatientDemographicsRetriever,
            EMRPatientInsuranceInfoRetriever,
            EMRPatientVisitsRetriever
        )
        from nexus.tools.eligibility.eligibility_270_transaction import Eligibility270TransactionTool
        
        # Load demographics
        demographics_tool = EMRPatientDemographicsRetriever()
        try:
            demographics = await demographics_tool.run_async(patient_id)
            if demographics:
                case_state.patient.member_id = demographics.get("member_id")
                case_state.patient.first_name = demographics.get("first_name")
                case_state.patient.last_name = demographics.get("last_name")
                case_state.patient.date_of_birth = demographics.get("date_of_birth")
                # Handle sex field - convert string to enum if needed
                sex_value = demographics.get("sex")
                if sex_value:
                    if isinstance(sex_value, str):
                        try:
                            from nexus.agents.eligibility_v2.models import Sex
                            case_state.patient.sex = Sex(sex_value)
                        except ValueError:
                            case_state.patient.sex = None
                    else:
                        case_state.patient.sex = sex_value
                else:
                    case_state.patient.sex = None
                logger.info(f"Loaded demographics for patient {patient_id}")
                
                # Emit thinking message with demographics metadata
                demographics_summary = f"Retrieved demographics: {demographics.get('first_name')} {demographics.get('last_name')}"
                if demographics.get("date_of_birth"):
                    demographics_summary += f", DOB: {demographics.get('date_of_birth')}"
                if demographics.get("member_id"):
                    demographics_summary += f", Member ID: {demographics.get('member_id')}"
                # Add data_type for structured parsing
                demographics_metadata = {
                    "data_type": "demographics",
                    **demographics
                }
                await self._emit_thinking_message(session_id, "patient_loading", demographics_summary, demographics_metadata)
        except Exception as e:
            logger.warning(f"Failed to load demographics for {patient_id}: {e}")
            await self._emit_thinking_message(session_id, "patient_loading", f"Failed to load demographics: {str(e)}")
        
        # Load insurance
        insurance_tool = EMRPatientInsuranceInfoRetriever()
        try:
            insurance = await insurance_tool.run_async(patient_id)
            if insurance:
                case_state.health_plan.payer_name = insurance.get("payer_name")
                case_state.health_plan.payer_id = insurance.get("payer_id")
                case_state.health_plan.plan_name = insurance.get("plan_name")
                case_state.patient.member_id = insurance.get("member_id") or case_state.patient.member_id
                logger.info(f"Loaded insurance info for patient {patient_id}")
                
                # Emit thinking message with insurance metadata
                insurance_summary = f"Retrieved insurance: {insurance.get('payer_name')}"
                if insurance.get("payer_id"):
                    insurance_summary += f" (Payer ID: {insurance.get('payer_id')})"
                if insurance.get("plan_name"):
                    insurance_summary += f", Plan: {insurance.get('plan_name')}"
                if insurance.get("member_id"):
                    insurance_summary += f", Member ID: {insurance.get('member_id')}"
                # Add data_type for structured parsing
                insurance_metadata = {
                    "data_type": "insurance",
                    **insurance
                }
                await self._emit_thinking_message(session_id, "patient_loading", insurance_summary, insurance_metadata)
        except Exception as e:
            logger.warning(f"Failed to load insurance for {patient_id}: {e}")
            await self._emit_thinking_message(session_id, "patient_loading", f"Failed to load insurance: {str(e)}")
        
        # Perform eligibility check if we have insurance info
        if case_state.health_plan.payer_name and case_state.patient.member_id:
            eligibility_result = await self._check_and_perform_eligibility_check(case_state, session_id)
            # Apply eligibility check updates deterministically
            case_state = self._deterministically_update_case_state(
                case_state=case_state,
                update_source="eligibility_check",
                updates={},  # Updates come from eligibility_result
                eligibility_check_result=eligibility_result
            )
        
        # Load visits/appointments (±6 months = 180 days)
        visits_tool = EMRPatientVisitsRetriever()
        visit_infos = []
        try:
            visits = await visits_tool.run_async(patient_id=patient_id, lookback_days=180, lookahead_days=180)
            if visits:
                today = date.today()
                for visit in visits:
                    visit_date_str = visit.get("visit_date")
                    if visit_date_str:
                        try:
                            # Handle both string and date objects
                            if isinstance(visit_date_str, str):
                                visit_date = datetime.strptime(visit_date_str, "%Y-%m-%d").date()
                            elif isinstance(visit_date_str, date):
                                visit_date = visit_date_str
                            else:
                                logger.debug(f"Could not parse visit date {visit_date_str}: unexpected type")
                                continue
                            
                            visit_info = VisitInfo(
                                visit_id=visit.get("visit_id"),
                                visit_date=visit_date,
                                visit_type=visit.get("visit_type"),
                                status=visit.get("status"),
                                provider=visit.get("provider"),
                                location=visit.get("location")
                            )
                            visit_infos.append(visit_info)
                        except Exception as e:
                            logger.debug(f"Could not parse visit date {visit_date_str}: {e}")
                            continue
                
                # Deterministically set dos_date from visits if not already set
                if not case_state.timing.dos_date and visit_infos:
                    # Priority 1: Most future scheduled visit
                    future_scheduled = [v for v in visit_infos if v.status == "scheduled" and v.visit_date >= today]
                    if future_scheduled:
                        # Use the most future scheduled visit
                        most_future = max(future_scheduled, key=lambda v: v.visit_date)
                        case_state.timing.dos_date = most_future.visit_date
                        case_state.timing.event_tense = EventTense.FUTURE
                        logger.debug(f"Set dos_date from most future scheduled visit: {most_future.visit_date}")
                    else:
                        # Priority 2: Most recent completed visit
                        past_completed = [v for v in visit_infos if v.status == "completed" and v.visit_date < today]
                        if past_completed:
                            most_recent = max(past_completed, key=lambda v: v.visit_date)
                            case_state.timing.dos_date = most_recent.visit_date
                            case_state.timing.event_tense = EventTense.PAST
                            logger.debug(f"Set dos_date from most recent completed visit: {most_recent.visit_date}")
                        else:
                            # Priority 3: Most recent visit overall (any status)
                            most_recent = max(visit_infos, key=lambda v: v.visit_date)
                            case_state.timing.dos_date = most_recent.visit_date
                            if most_recent.visit_date >= today:
                                case_state.timing.event_tense = EventTense.FUTURE
                            else:
                                case_state.timing.event_tense = EventTense.PAST
                            logger.debug(f"Set dos_date from most recent visit: {most_recent.visit_date}")
                
                # Set event_tense deterministically if dos_date is set but event_tense is unknown
                if case_state.timing.dos_date and case_state.timing.event_tense == EventTense.UNKNOWN:
                    if case_state.timing.dos_date >= today:
                        case_state.timing.event_tense = EventTense.FUTURE
                    else:
                        case_state.timing.event_tense = EventTense.PAST
                    logger.debug(f"Set event_tense based on dos_date: {case_state.timing.dos_date} -> {case_state.timing.event_tense}")
                
                # Compute eligibility and probability for each visit (if eligibility check was performed)
                if case_state.eligibility_check.checked and visit_infos:
                    logger.info(f"Computing eligibility and probability for {len(visit_infos)} visits")
                    updated_visits = []
                    for visit in visit_infos:
                        updated_visit = await self._compute_visit_eligibility_and_probability(
                            case_state, visit, self.scorer
                        )
                        updated_visits.append(updated_visit)
                    visit_infos = updated_visits
                    logger.info(f"Completed eligibility and probability computation for {len(updated_visits)} visits")
                
                case_state.timing.related_visits = visit_infos
                logger.info(f"Loaded {len(visit_infos)} visits for patient {patient_id}")
                
                # Emit thinking message with visits metadata
                visits_summary_text = f"Retrieved {len(visit_infos)} visit(s)/appointment(s)"
                if visit_infos:
                    upcoming = [v for v in visit_infos if v.visit_date and v.visit_date >= date.today()]
                    past = [v for v in visit_infos if v.visit_date and v.visit_date < date.today()]
                    if upcoming:
                        visits_summary_text += f" ({len(upcoming)} upcoming, {len(past)} past)"
                    else:
                        visits_summary_text += f" ({len(past)} past)"
                
                visits_metadata = []
                for visit in visit_infos:
                    # Handle visit_date - could be date object or string
                    visit_date_str = None
                    if visit.visit_date:
                        if isinstance(visit.visit_date, date):
                            visit_date_str = visit.visit_date.isoformat()
                        elif isinstance(visit.visit_date, str):
                            visit_date_str = visit.visit_date
                    
                    # Handle eligibility_status - could be enum or string
                    eligibility_status_str = None
                    if visit.eligibility_status:
                        if hasattr(visit.eligibility_status, 'value'):
                            eligibility_status_str = visit.eligibility_status.value
                        elif isinstance(visit.eligibility_status, str):
                            eligibility_status_str = visit.eligibility_status
                    
                    # Handle event_tense - could be enum or string
                    event_tense_str = None
                    if visit.event_tense:
                        if hasattr(visit.event_tense, 'value'):
                            event_tense_str = visit.event_tense.value
                        elif isinstance(visit.event_tense, str):
                            event_tense_str = visit.event_tense
                    
                    visit_summary = {
                        "visit_date": visit_date_str,
                        "visit_type": visit.visit_type,
                        "status": visit.status,
                        "eligibility_status": eligibility_status_str,
                        "eligibility_probability": visit.eligibility_probability,
                        "event_tense": event_tense_str
                    }
                    visits_metadata.append(visit_summary)
                
                # Add data_type for structured parsing
                visits_metadata_with_type = {
                    "data_type": "visits",
                    "visits": visits_metadata
                }
                await self._emit_thinking_message(session_id, "patient_loading", visits_summary_text, visits_metadata_with_type)
                
                # Emit process event with visit details
                visits_summary = visits_metadata
                
                await self._emit_process_event(
                    session_id,
                    "patient_loading",
                    "complete",
                    f"Patient details loaded - Found {len(visit_infos)} visits/appointments",
                    {
                        "patient_summary": {
                            "name": f"{case_state.patient.first_name} {case_state.patient.last_name}",
                            "dob": case_state.patient.date_of_birth.isoformat() if case_state.patient.date_of_birth and isinstance(case_state.patient.date_of_birth, date) else (case_state.patient.date_of_birth if case_state.patient.date_of_birth else None),
                            "insurance": case_state.health_plan.payer_name,
                            "member_id": case_state.patient.member_id
                        },
                        "visits": visits_summary  # Include visits in the process event data
                    }
                )
        except Exception as e:
            logger.warning(f"Failed to load visits for patient {patient_id}: {e}")
        
        return case_state
    
    async def _compute_visit_eligibility_and_probability(
        self,
        case_state: CaseState,
        visit_info: VisitInfo,
        scorer: EligibilityScorer
    ) -> VisitInfo:
        """
        Compute eligibility status and probability for a specific visit.
        """
        if not visit_info.visit_date:
            return visit_info
        
        today = date.today()
        visit_date = visit_info.visit_date
        
        # 1. Classify visit as PAST or FUTURE
        if visit_date < today:
            visit_info.event_tense = EventTense.PAST
        elif visit_date > today:
            visit_info.event_tense = EventTense.FUTURE
        else:
            visit_info.event_tense = EventTense.PAST
        
        # 2. Check if visit date falls within coverage window
        coverage_start = case_state.eligibility_truth.coverage_window_start
        coverage_end = case_state.eligibility_truth.coverage_window_end
        
        if coverage_start and coverage_end:
            try:
                start_date = datetime.fromisoformat(coverage_start).date()
                end_date = datetime.fromisoformat(coverage_end).date()
                
                if start_date <= visit_date <= end_date:
                    visit_info.eligibility_status = EligibilityStatus.YES
                else:
                    visit_info.eligibility_status = EligibilityStatus.NO
            except Exception as e:
                logger.debug(f"Could not parse coverage dates for visit {visit_info.visit_id}: {e}")
                visit_info.eligibility_status = EligibilityStatus.NOT_ESTABLISHED
        else:
            visit_info.eligibility_status = EligibilityStatus.NOT_ESTABLISHED
        
        # 3. Compute probability for this visit date
        try:
            temp_case_state = deepcopy(case_state)
            temp_case_state.timing.dos_date = visit_date
            temp_case_state.timing.event_tense = visit_info.event_tense
            
            # For visit scoring, don't emit calculation steps (too verbose)
            score_state = await scorer.score(temp_case_state, emit_calculation=None)
            visit_info.eligibility_probability = score_state.base_probability
            # Store full score_state for drill-down view
            visit_info.score_state = score_state
            logger.debug(
                f"Computed probability for visit {visit_info.visit_id} ({visit_date}): "
                f"{visit_info.eligibility_probability:.2%}, status={visit_info.eligibility_status}"
            )
        except Exception as e:
            logger.warning(f"Failed to compute probability for visit {visit_info.visit_id}: {e}")
            visit_info.eligibility_probability = None
            visit_info.score_state = None
        
        return visit_info
    
    def _compute_weighted_average_probability(self, visits: list[VisitInfo], tau: int = 90) -> Optional[float]:
        """
        Compute weighted average of visit probabilities using recency boost.
        
        Formula: w_i = exp(-|days_from_today| / τ)
        Where τ (tau) is the time constant (default 90 days).
        Closer visits get higher weight.
        
        Args:
            visits: List of VisitInfo objects with eligibility_probability
            tau: Time constant for exponential decay (default 90 days)
        
        Returns:
            Weighted average probability (0.0-1.0) or None if no valid visits
        """
        from math import exp
        
        today = date.today()
        
        # Filter visits with valid probabilities
        valid_visits = [
            v for v in visits 
            if v.eligibility_probability is not None 
            and v.visit_date is not None
        ]
        
        if not valid_visits:
            return None
        
        if len(valid_visits) == 1:
            # Single visit: return its probability directly
            return valid_visits[0].eligibility_probability
        
        # Compute weights using exponential decay
        weights = []
        probabilities = []
        
        for visit in valid_visits:
            days_diff = abs((visit.visit_date - today).days)
            weight = exp(-days_diff / tau)
            weights.append(weight)
            probabilities.append(visit.eligibility_probability)
        
        # Normalize weights
        total_weight = sum(weights)
        if total_weight == 0:
            return None
        
        # Compute weighted average
        weighted_sum = sum(p * w for p, w in zip(probabilities, weights))
        weighted_avg = weighted_sum / total_weight
        
        logger.debug(
            f"Computed weighted average probability: {weighted_avg:.2%} "
            f"from {len(valid_visits)} visits (tau={tau} days)"
        )
        
        return weighted_avg
    
    async def _check_and_perform_eligibility_check(
        self,
        case_state: CaseState,
        session_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Perform 270 eligibility transaction if not already cached.
        Returns the raw eligibility check result (not updated CaseState).
        The result should be applied deterministically via _deterministically_update_case_state.
        """
        from nexus.tools.eligibility.eligibility_270_transaction import Eligibility270TransactionTool
        
        # Check cache
        if case_state.eligibility_check.checked and case_state.eligibility_check.result_raw:
            try:
                cached_result = json.loads(case_state.eligibility_check.result_raw)
                cached_member_id = cached_result.get("member_id") or cached_result.get("insurance_id")
                current_member_id = case_state.patient.member_id
                
                if cached_member_id == current_member_id:
                    # Determine status from cached result for emitting
                    active_window = None
                    for window in cached_result.get("eligibility_windows", []):
                        if window.get("status") == "active":
                            active_window = window
                            break
                    
                    status = EligibilityStatus.YES if active_window else EligibilityStatus.NO
                    
                    # Emit thinking message with cached eligibility metadata
                    eligibility_metadata = {
                        "data_type": "eligibility",
                        "status": status.value,
                        "coverage_start": active_window["effective_date"] if active_window else None,
                        "coverage_end": active_window["end_date"] if active_window else None,
                        "product_type": case_state.health_plan.product_type.value if case_state.health_plan.product_type != ProductType.UNKNOWN else None,
                        "plan_name": case_state.health_plan.plan_name,
                        "member_id": case_state.patient.member_id,
                        "payer_name": case_state.health_plan.payer_name,
                        "summary": f"Using cached eligibility check for member {current_member_id}",
                        "cached": True
                    }
                    eligibility_message = f"Eligibility check (cached): {status.value}"
                    if active_window:
                        eligibility_message += f" - Coverage: {active_window['effective_date']} to {active_window['end_date']}"
                    await self._emit_thinking_message(
                        session_id,
                        "patient_loading",
                        eligibility_message,
                        eligibility_metadata
                    )
                    
                    await self._emit_process_event(
                        session_id,
                        "eligibility_check",
                        "complete",
                        f"Using cached eligibility check for member {current_member_id}: {status.value}",
                        {
                            "status": status.value,
                            "coverage_start": active_window["effective_date"] if active_window else None,
                            "coverage_end": active_window["end_date"] if active_window else None,
                            "product_type": case_state.health_plan.product_type.value if case_state.health_plan.product_type != ProductType.UNKNOWN else None,
                            "plan_name": case_state.health_plan.plan_name,
                            "member_id": case_state.patient.member_id,
                            "payer_name": case_state.health_plan.payer_name,
                            "cached": True
                        }
                    )
                    return cached_result
            except Exception as e:
                logger.debug(f"Error parsing cached eligibility result: {e}, performing new check")
        
        # Perform new check
        await self._emit_process_event(session_id, "eligibility_check", "in_progress", "Checking eligibility with payer...")
        
        try:
            tool = Eligibility270TransactionTool()
            result = await tool.execute(
                insurance_id=case_state.patient.member_id,
                insurance_name=case_state.health_plan.payer_name
            )
            
            # Find active window for emitting
            active_window = None
            for window in result.get("eligibility_windows", []):
                if window.get("status") == "active":
                    active_window = window
                    break
            
            status = EligibilityStatus.YES if active_window else EligibilityStatus.NO
            
            if active_window:
                summary = (
                    f"✅ Member {case_state.patient.member_id} is ELIGIBLE. "
                    f"Coverage period: {active_window['effective_date']} to {active_window['end_date']}. "
                    f"Status: Active coverage confirmed via 270 transaction."
                )
            else:
                summary = f"❌ Member {case_state.patient.member_id} is NOT ELIGIBLE."
            
            # Emit thinking message with eligibility metadata
            eligibility_metadata = {
                "data_type": "eligibility",
                "status": status.value,
                "coverage_start": active_window["effective_date"] if active_window else None,
                "coverage_end": active_window["end_date"] if active_window else None,
                "product_type": case_state.health_plan.product_type.value if case_state.health_plan.product_type != ProductType.UNKNOWN else None,
                "plan_name": case_state.health_plan.plan_name,
                "member_id": case_state.patient.member_id,
                "payer_name": case_state.health_plan.payer_name,
                "summary": summary,
                "cached": False
            }
            eligibility_message = f"Eligibility check: {status.value}"
            if active_window:
                eligibility_message += f" - Coverage: {active_window['effective_date']} to {active_window['end_date']}"
            await self._emit_thinking_message(
                session_id,
                "patient_loading",  # Use same phase as other patient data
                eligibility_message,
                eligibility_metadata
            )
            
            await self._emit_process_event(
                session_id,
                "eligibility_check",
                "complete",
                f"Eligibility check complete: {status.value}. {summary}",
                {
                    "status": status.value,
                    "coverage_start": active_window["effective_date"] if active_window else None,
                    "coverage_end": active_window["end_date"] if active_window else None,
                    "product_type": case_state.health_plan.product_type.value if case_state.health_plan.product_type != ProductType.UNKNOWN else None,
                    "plan_name": case_state.health_plan.plan_name,
                    "member_id": case_state.patient.member_id,
                    "payer_name": case_state.health_plan.payer_name,
                    "summary": summary
                }
            )
            
            return result
        except Exception as e:
            logger.error(f"Failed to perform eligibility check: {e}", exc_info=True)
            await self._emit_process_event(session_id, "eligibility_check", "error", f"Eligibility check failed: {str(e)}")
            return {}
    
    def _deterministically_update_case_state(
        self,
        case_state: CaseState,
        update_source: str,  # "eligibility_check", "interpreter", "scoring"
        updates: Dict[str, Any],
        eligibility_check_result: Optional[Dict[str, Any]] = None
    ) -> CaseState:
        """
        Deterministically update CaseState based on trusted sources.
        
        Args:
            case_state: Current case state
            update_source: Source of updates ("eligibility_check", "interpreter", "scoring")
            updates: Dictionary of updates to apply
            eligibility_check_result: Raw eligibility check result (if update_source is "eligibility_check")
        
        Returns:
            Updated CaseState
        """
        logger.info(f"Deterministically updating case state from {update_source}")
        
        if update_source == "eligibility_check":
            # Updates from 270 transaction result
            if eligibility_check_result:
                active_window = None
                for window in eligibility_check_result.get("eligibility_windows", []):
                    if window.get("status") == "active":
                        active_window = window
                        break
                
                if active_window:
                    # Update eligibility_truth deterministically
                    case_state.eligibility_truth.status = EligibilityStatus.YES
                    case_state.eligibility_truth.coverage_window_start = active_window["effective_date"]
                    case_state.eligibility_truth.coverage_window_end = active_window["end_date"]
                    case_state.eligibility_truth.evidence_strength = EvidenceStrength.HIGH
                    
                    # Infer product type deterministically
                    if case_state.health_plan.product_type == ProductType.UNKNOWN:
                        plan_name_lower = active_window.get("plan_name", "").lower()
                        payer_name_lower = case_state.health_plan.payer_name.lower() if case_state.health_plan.payer_name else ""
                        
                        if "medicaid" in plan_name_lower or "medicaid" in payer_name_lower:
                            case_state.health_plan.product_type = ProductType.MEDICAID
                        elif "medicare" in plan_name_lower or "medicare" in payer_name_lower:
                            case_state.health_plan.product_type = ProductType.MEDICARE
                        elif "dsnp" in plan_name_lower:
                            case_state.health_plan.product_type = ProductType.DSNP
                        elif any(term in plan_name_lower for term in ["commercial", "ppo", "hmo", "epo"]):
                            case_state.health_plan.product_type = ProductType.COMMERCIAL
                        else:
                            case_state.health_plan.product_type = ProductType.COMMERCIAL
                    
                    # Update plan name if not set
                    if not case_state.health_plan.plan_name or case_state.health_plan.plan_name == "UNKNOWN":
                        case_state.health_plan.plan_name = active_window.get("plan_name")
                else:
                    # No active window found - patient is NOT eligible
                    case_state.eligibility_truth.status = EligibilityStatus.NO
                    case_state.eligibility_truth.evidence_strength = EvidenceStrength.HIGH
                    # Clear coverage window since there's no active coverage
                    case_state.eligibility_truth.coverage_window_start = None
                    case_state.eligibility_truth.coverage_window_end = None
                
                # Update eligibility_check metadata
                case_state.eligibility_check.checked = True
                case_state.eligibility_check.check_date = date.today()
                case_state.eligibility_check.source = EligibilityCheckSource.CLEARINGHOUSE
                case_state.eligibility_check.result_raw = json.dumps(eligibility_check_result)
        
        elif update_source == "interpreter":
            # Updates from LLM interpretation (user input)
            # Only apply safe, validated updates
            
            # Patient updates
            if updates.get("patient_updates") and isinstance(updates["patient_updates"], dict):
                patient_updates = updates["patient_updates"]
                if "first_name" in patient_updates and patient_updates["first_name"]:
                    case_state.patient.first_name = patient_updates["first_name"]
                if "last_name" in patient_updates and patient_updates["last_name"]:
                    case_state.patient.last_name = patient_updates["last_name"]
                if "date_of_birth" in patient_updates and patient_updates["date_of_birth"]:
                    # Parse and validate date
                    try:
                        if isinstance(patient_updates["date_of_birth"], str):
                            case_state.patient.date_of_birth = datetime.fromisoformat(patient_updates["date_of_birth"]).date()
                        elif isinstance(patient_updates["date_of_birth"], date):
                            case_state.patient.date_of_birth = patient_updates["date_of_birth"]
                    except Exception as e:
                        logger.warning(f"Invalid date_of_birth in interpreter updates: {e}")
                if "member_id" in patient_updates and patient_updates["member_id"]:
                    case_state.patient.member_id = patient_updates["member_id"]
                if "sex" in patient_updates and patient_updates["sex"]:
                    try:
                        case_state.patient.sex = Sex(patient_updates["sex"])
                    except ValueError:
                        logger.warning(f"Invalid sex value: {patient_updates['sex']}")
            
            # Health plan updates
            if updates.get("health_plan_updates") and isinstance(updates["health_plan_updates"], dict):
                hp_updates = updates["health_plan_updates"]
                if "payer_name" in hp_updates and hp_updates["payer_name"]:
                    case_state.health_plan.payer_name = hp_updates["payer_name"]
                if "payer_id" in hp_updates and hp_updates["payer_id"]:
                    case_state.health_plan.payer_id = hp_updates["payer_id"]
                if "plan_name" in hp_updates and hp_updates["plan_name"]:
                    case_state.health_plan.plan_name = hp_updates["plan_name"]
                if "product_type" in hp_updates and hp_updates["product_type"]:
                    try:
                        case_state.health_plan.product_type = ProductType(hp_updates["product_type"])
                    except ValueError:
                        logger.warning(f"Invalid product_type: {hp_updates['product_type']}")
                if "contract_status" in hp_updates and hp_updates["contract_status"]:
                    try:
                        case_state.health_plan.contract_status = ContractStatus(hp_updates["contract_status"])
                    except ValueError:
                        logger.warning(f"Invalid contract_status: {hp_updates['contract_status']}")
            
            # Timing updates
            if updates.get("timing_updates") and isinstance(updates["timing_updates"], dict):
                timing_updates = updates["timing_updates"]
                if "dos_date" in timing_updates and timing_updates["dos_date"]:
                    try:
                        if isinstance(timing_updates["dos_date"], str):
                            case_state.timing.dos_date = datetime.fromisoformat(timing_updates["dos_date"]).date()
                        elif isinstance(timing_updates["dos_date"], date):
                            case_state.timing.dos_date = timing_updates["dos_date"]
                        # Deterministically set event_tense
                        if case_state.timing.dos_date:
                            today = date.today()
                            if case_state.timing.dos_date <= today:
                                case_state.timing.event_tense = EventTense.PAST
                            else:
                                case_state.timing.event_tense = EventTense.FUTURE
                    except Exception as e:
                        logger.warning(f"Invalid dos_date in interpreter updates: {e}")
        
        elif update_source == "scoring":
            # Updates from scoring results (if any)
            # For now, scoring doesn't update case_state, but this is a placeholder
            # for future deterministic updates based on score_state
            pass
        
        return case_state
    
    async def _emit_thinking_message(
        self,
        session_id: Optional[int],
        phase: str,
        message: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Emit a thinking message with metadata for streaming in the thinking box.
        """
        if not session_id:
            return
        
        try:
            query = """
            INSERT INTO memory_events (session_id, bucket_type, payload)
            VALUES (:sid, :bucket, :payload)
            """
            payload = {
                "phase": phase,
                "message": message,
                "timestamp": datetime.now().isoformat()
            }
            if metadata:
                payload["metadata"] = metadata
            
            await database.execute(
                query=query,
                values={
                    "sid": session_id,
                    "bucket": "THINKING",
                    "payload": json.dumps(payload)
                }
            )
            logger.debug(f"✅ Emitted thinking message: {phase} - {message[:50]}... (session_id={session_id})")
        except Exception as e:
            logger.warning(f"Failed to emit thinking message: {e}", exc_info=True)
    
    async def _emit_process_event(
        self,
        session_id: Optional[int],
        phase: str,
        status: str,
        message: str,
        data: Optional[Dict[str, Any]] = None
    ):
        """
        Emit a process event to memory_events table for thinking view.
        """
        if not session_id:
            logger.warning(f"⚠️ Cannot emit process event: session_id is None (phase={phase}, status={status})")
            return
        
        try:
            query = """
            INSERT INTO memory_events (session_id, bucket_type, payload)
            VALUES (:sid, :bucket, :payload)
            """
            payload = {
                "phase": phase,
                "status": status,
                "message": message,
                "timestamp": datetime.now().isoformat()
            }
            if data:
                payload["data"] = data
            
            await database.execute(
                query=query,
                values={
                    "sid": session_id,
                    "bucket": "ELIGIBILITY_PROCESS",
                    "payload": json.dumps(payload)
                }
            )
            logger.debug(f"✅ Emitted process event: {phase} - {status} (session_id={session_id})")
        except Exception as e:
            logger.warning(f"Failed to emit process event: {e}", exc_info=True)
