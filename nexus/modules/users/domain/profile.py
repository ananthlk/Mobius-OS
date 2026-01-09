"""
Profile Domain Models

Pure data models representing user profile entities.
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any, List


@dataclass
class BasicProfile:
    """Basic personal information profile."""
    user_id: int
    preferred_name: Optional[str] = None
    phone: Optional[str] = None
    mobile: Optional[str] = None
    alternate_email: Optional[str] = None
    timezone: str = "UTC"
    locale: str = "en-US"
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    metadata: Dict[str, Any] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class ProfessionalProfile:
    """Professional and organizational information profile."""
    user_id: int
    job_title: Optional[str] = None
    department: Optional[str] = None
    organization: Optional[str] = None
    manager_id: Optional[int] = None
    team_name: Optional[str] = None
    employee_id: Optional[str] = None
    office_location: Optional[str] = None
    start_date: Optional[str] = None
    metadata: Dict[str, Any] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class CommunicationProfile:
    """Communication preferences profile."""
    user_id: int
    communication_style: str = "professional"
    tone_preference: str = "balanced"
    prompt_style_id: Optional[int] = None
    preferred_language: str = "en"
    response_format_preference: str = "structured"
    notification_preferences: Dict[str, Any] = None
    engagement_level: str = "engaging"
    metadata: Dict[str, Any] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    def __post_init__(self):
        if self.notification_preferences is None:
            self.notification_preferences = {}
        if self.metadata is None:
            self.metadata = {}


@dataclass
class UseCaseProfile:
    """Workflow patterns and use cases profile."""
    user_id: int
    primary_workflows: List[Dict[str, Any]] = None
    workflow_frequency: Dict[str, Any] = None
    module_preferences: Dict[str, Any] = None
    task_patterns: List[Dict[str, Any]] = None
    domain_expertise: List[Dict[str, Any]] = None
    metadata: Dict[str, Any] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    def __post_init__(self):
        if self.primary_workflows is None:
            self.primary_workflows = []
        if self.workflow_frequency is None:
            self.workflow_frequency = {}
        if self.module_preferences is None:
            self.module_preferences = {}
        if self.task_patterns is None:
            self.task_patterns = []
        if self.domain_expertise is None:
            self.domain_expertise = []
        if self.metadata is None:
            self.metadata = {}


@dataclass
class AIPreferenceProfile:
    """AI interaction preferences profile."""
    user_id: int
    escalation_rules: Dict[str, Any] = None
    autonomy_level: str = "balanced"
    confidence_threshold: float = 0.70
    require_confirmation_for: List[str] = None
    preferred_model_preferences: Dict[str, Any] = None
    feedback_preferences: Dict[str, Any] = None
    preferred_strategy: Optional[str] = None
    strategy_preferences: Dict[str, Any] = None
    task_category_preferences: Dict[str, Any] = None
    task_domain_preferences: Dict[str, Any] = None
    metadata: Dict[str, Any] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    def __post_init__(self):
        if self.escalation_rules is None:
            self.escalation_rules = {}
        if self.require_confirmation_for is None:
            self.require_confirmation_for = []
        if self.preferred_model_preferences is None:
            self.preferred_model_preferences = {}
        if self.feedback_preferences is None:
            self.feedback_preferences = {}
        if self.strategy_preferences is None:
            self.strategy_preferences = {}
        if self.task_category_preferences is None:
            self.task_category_preferences = {}
        if self.task_domain_preferences is None:
            self.task_domain_preferences = {}
        if self.metadata is None:
            self.metadata = {}


@dataclass
class QueryHistoryProfile:
    """Query patterns and statistics profile."""
    user_id: int
    most_common_queries: List[Dict[str, Any]] = None
    query_categories: Dict[str, Any] = None
    search_patterns: List[Dict[str, Any]] = None
    question_templates: List[Dict[str, Any]] = None
    interaction_stats: Dict[str, Any] = None
    metadata: Dict[str, Any] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    def __post_init__(self):
        if self.most_common_queries is None:
            self.most_common_queries = []
        if self.query_categories is None:
            self.query_categories = {}
        if self.search_patterns is None:
            self.search_patterns = []
        if self.question_templates is None:
            self.question_templates = []
        if self.interaction_stats is None:
            self.interaction_stats = {}
        if self.metadata is None:
            self.metadata = {}



