"""
Eligibility Agent V2 - Data Models

Pydantic models for eligibility case state, scoring, planning, and UI events.
"""
from enum import Enum
from typing import List, Optional, Dict, Any, Literal
from datetime import date, datetime
from pydantic import BaseModel, Field


# ============================================================================
# Enums
# ============================================================================

class EligibilityStatus(str, Enum):
    YES = "YES"
    NO = "NO"
    NOT_ESTABLISHED = "NOT_ESTABLISHED"
    UNKNOWN = "UNKNOWN"


class EventTense(str, Enum):
    PAST = "PAST"
    FUTURE = "FUTURE"
    UNKNOWN = "UNKNOWN"


class Sex(str, Enum):
    MALE = "MALE"
    FEMALE = "FEMALE"
    OTHER = "OTHER"
    UNKNOWN = "UNKNOWN"


class ProductType(str, Enum):
    MEDICAID = "MEDICAID"
    MEDICARE = "MEDICARE"
    DSNP = "DSNP"
    COMMERCIAL = "COMMERCIAL"
    OTHER = "OTHER"
    UNKNOWN = "UNKNOWN"


class ContractStatus(str, Enum):
    CONTRACTED = "CONTRACTED"
    NON_CONTRACTED = "NON_CONTRACTED"
    UNKNOWN = "UNKNOWN"


class EligibilityCheckSource(str, Enum):
    CLEARINGHOUSE = "CLEARINGHOUSE"
    PAYER_PORTAL = "PAYER_PORTAL"
    STATE_FILE = "STATE_FILE"
    EMR = "EMR"
    PATIENT_REPORT = "PATIENT_REPORT"
    MANUAL = "MANUAL"
    UNKNOWN = "UNKNOWN"


class CanonicalReason(str, Enum):
    NONE = "NONE"
    NOT_ENROLLED = "NOT_ENROLLED"
    TERMINATED = "TERMINATED"
    NOT_EFFECTIVE = "NOT_EFFECTIVE"
    COVERAGE_GAP = "COVERAGE_GAP"
    PLAN_MISMATCH = "PLAN_MISMATCH"
    SERVICE_NOT_COVERED = "SERVICE_NOT_COVERED"
    PROVIDER_NOT_IN_NETWORK = "PROVIDER_NOT_IN_NETWORK"
    AUTHORIZATION_REQUIRED = "AUTHORIZATION_REQUIRED"
    BENEFIT_EXHAUSTED = "BENEFIT_EXHAUSTED"
    OTHER = "OTHER"


class FixType(str, Enum):
    FIND_INFO = "FIND_INFO"
    RETRY_CHECK = "RETRY_CHECK"
    RESOLVE_IDENTITY = "RESOLVE_IDENTITY"
    RESOLVE_CONFLICT = "RESOLVE_CONFLICT"
    REINSTATE = "REINSTATE"
    WAIT_FOR_TIMING = "WAIT_FOR_TIMING"
    CONTRACT_GAP = "CONTRACT_GAP"
    NONE = "NONE"
    UNKNOWN = "UNKNOWN"


class EvidenceStrength(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    NONE = "NONE"


class CompletionStatus(str, Enum):
    COMPLETE = "COMPLETE"
    INCOMPLETE = "INCOMPLETE"
    NEEDS_INPUT = "NEEDS_INPUT"


# ============================================================================
# Core Models
# ============================================================================

class PatientDemographics(BaseModel):
    member_id: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    date_of_birth: Optional[date] = None
    sex: Optional[Sex] = None


class HealthPlanInfo(BaseModel):
    payer_name: Optional[str] = None
    payer_id: Optional[str] = None
    plan_name: Optional[str] = None
    product_type: ProductType = ProductType.UNKNOWN
    contract_status: ContractStatus = ContractStatus.UNKNOWN


class VisitInfo(BaseModel):
    """Information about a patient visit/appointment"""
    visit_id: Optional[str] = None
    visit_date: Optional[date] = None
    visit_type: Optional[str] = None  # e.g., "appointment", "encounter", "procedure"
    status: Optional[str] = None  # e.g., "scheduled", "completed", "cancelled"
    provider: Optional[str] = None
    location: Optional[str] = None
    eligibility_status: Optional[EligibilityStatus] = None
    eligibility_probability: Optional[float] = None  # 0.0-1.0
    event_tense: Optional[EventTense] = None


class TimingInfo(BaseModel):
    dos_date: Optional[date] = None
    event_tense: EventTense = EventTense.UNKNOWN
    related_visits: List[VisitInfo] = Field(default_factory=list)


class ReasonMapping(BaseModel):
    canonical_code: CanonicalReason = CanonicalReason.OTHER
    canonical_subreason: Optional[str] = None
    taxonomy_extension_proposed: bool = False
    extension_reason_label: Optional[str] = None
    extension_subreason_label: Optional[str] = None
    mapping_confidence: Optional[float] = None  # 0.0-1.0


class EligibilityCheck(BaseModel):
    checked: bool = False
    check_date: Optional[date] = None
    source: EligibilityCheckSource = EligibilityCheckSource.UNKNOWN
    result_raw: Optional[str] = None  # JSON string of raw result


class EligibilityTruth(BaseModel):
    status: EligibilityStatus = EligibilityStatus.NOT_ESTABLISHED
    evidence_strength: EvidenceStrength = EvidenceStrength.NONE
    coverage_window_start: Optional[str] = None  # ISO string
    coverage_window_end: Optional[str] = None  # ISO string
    reason: ReasonMapping = Field(default_factory=lambda: ReasonMapping())


class IneligibleExplanation(BaseModel):
    loss_timing: Optional[str] = None
    reinstate_possible: Optional[bool] = None
    reinstate_date: Optional[date] = None


class FixabilityInfo(BaseModel):
    fixable: bool = False
    fix_type: FixType = FixType.UNKNOWN
    estimated_fix_time: Optional[str] = None
    fix_steps: List[str] = Field(default_factory=list)


class CaseState(BaseModel):
    """Complete state of an eligibility case"""
    patient: PatientDemographics = Field(default_factory=PatientDemographics)
    health_plan: HealthPlanInfo = Field(default_factory=HealthPlanInfo)
    timing: TimingInfo = Field(default_factory=TimingInfo)
    eligibility_check: EligibilityCheck = Field(default_factory=EligibilityCheck)
    eligibility_truth: EligibilityTruth = Field(default_factory=EligibilityTruth)
    ineligible_explanation: Optional[IneligibleExplanation] = None
    fixability: FixabilityInfo = Field(default_factory=FixabilityInfo)


# ============================================================================
# Scoring Models
# ============================================================================

class ProbabilityInterval(BaseModel):
    lower_bound: float  # 0.0-1.0
    upper_bound: float  # 0.0-1.0
    confidence_level: float  # 0.0-1.0 (e.g., 0.95 for 95% CI)
    width: float  # 0.0-1.0 (upper - lower)


class VolatilityMetrics(BaseModel):
    standard_error: float
    standard_deviation: float  # 0.0-1.0
    coefficient_of_variation: float
    volatility_score: float  # 0.0-1.0 (0=stable, 1=highly volatile)


class BackoffPathStep(BaseModel):
    level: int  # Number of dimensions used
    dimensions: List[str]  # Which dimensions were used
    dimensions_str: str  # Human-readable string
    sample_size: int
    probability: Optional[float] = None
    ci_width: Optional[float] = None
    combined_confidence: Optional[float] = None
    status: Literal["found", "insufficient", "no_data"]


class ScoreState(BaseModel):
    base_probability: float  # 0.0-1.0
    base_confidence: float  # 0.0-1.0
    probability_interval: Optional[ProbabilityInterval] = None
    volatility: Optional[VolatilityMetrics] = None
    sample_size: Optional[int] = None
    sample_confidence: Optional[float] = None
    high_impact_fields: List[str] = Field(default_factory=list)
    backoff_path: List[BackoffPathStep] = Field(default_factory=list)
    backoff_level: Optional[int] = None
    backoff_dims: Optional[List[str]] = None
    drivers: List[Dict[str, Any]] = Field(default_factory=list)
    missing_inputs: List[str] = Field(default_factory=list)
    scoring_version: str = "v1"


# ============================================================================
# Planning Models
# ============================================================================

class NextQuestion(BaseModel):
    id: str
    text: str
    answer_format: Literal["MULTIPLE_CHOICE", "FREE_TEXT", "DATE", "BOOLEAN", "FORM"]
    options: List[str] = Field(default_factory=list)
    fills: List[str] = Field(default_factory=list)
    improves: List[Literal["CONFIDENCE", "PROBABILITY", "COMPLETENESS"]] = Field(default_factory=list)
    why: str
    formatted_text: Optional[str] = None  # Added by presenter


class ImprovementAction(BaseModel):
    action_id: str
    description: str
    requires: Literal["USER_INPUT", "TOOL_CALL", "MANUAL_PROCESS"]
    expected_effect: Literal["INCREASE_CONFIDENCE", "INCREASE_PROBABILITY", "RESOLVE_COMPLETENESS"]
    priority: int = 0
    formatted_description: Optional[str] = None  # Added by presenter


class CompletionStatusModel(BaseModel):
    status: CompletionStatus
    missing_fields: List[str] = Field(default_factory=list)


# ============================================================================
# LLM Response Models
# ============================================================================

class LLMInterpretResponse(BaseModel):
    updated_case_state: CaseState
    completion: CompletionStatusModel


class LLMPlanResponse(BaseModel):
    next_questions: List[NextQuestion] = Field(default_factory=list)
    improvement_plan: List[ImprovementAction] = Field(default_factory=list)
    presentation_summary: str = ""


# ============================================================================
# UI Event Models
# ============================================================================

class UIEvent(BaseModel):
    event_type: Literal["user_message", "form_submit", "button_click"]
    data: Dict[str, Any]
    client_event_id: Optional[str] = None
    timestamp: str  # ISO datetime string
