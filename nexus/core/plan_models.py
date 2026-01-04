"""
Workflow Plan Data Models

Defines the structure for workflow plans with metadata, state tracking,
and agent enhancement capabilities.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Literal, Any
from datetime import datetime
from enum import Enum

class PlanStatus(Enum):
    """Overall plan status."""
    DRAFT = "draft"
    USER_REVIEW = "user_review"
    USER_APPROVED = "user_approved"
    PLANNED_FOR_EXECUTION = "planned_for_execution"
    EXECUTING = "executing"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class PhaseStatus(Enum):
    """Phase-level status."""
    PLANNED = "planned"
    USER_APPROVED = "user_approved"
    READY = "ready"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    SKIPPED = "skipped"
    FAILED = "failed"

class StepStatus(Enum):
    """Step-level status."""
    PLANNED = "planned"
    USER_APPROVED = "user_approved"
    TOOL_CONFIGURED = "tool_configured"
    READY = "ready"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"

@dataclass
class PlanMetadata:
    """Metadata for the entire plan."""
    status: PlanStatus = PlanStatus.DRAFT
    created_at: datetime = field(default_factory=datetime.now)
    approved_at: Optional[datetime] = None
    approved_by: Optional[str] = None
    execution_started_at: Optional[datetime] = None
    execution_completed_at: Optional[datetime] = None
    version: int = 1
    parent_template_key: Optional[str] = None
    last_modified_by: Optional[str] = None
    last_modified_at: Optional[datetime] = None
    notes: Optional[str] = None

@dataclass
class PhaseMetadata:
    """Metadata for a phase."""
    status: PhaseStatus = PhaseStatus.PLANNED
    approved_at: Optional[datetime] = None
    execution_started_at: Optional[datetime] = None
    execution_completed_at: Optional[datetime] = None
    execution_order: int = 0
    can_skip: bool = False
    skip_reason: Optional[str] = None
    notes: Optional[str] = None

@dataclass
class ToolDefinition:
    """Tool definition with inputs/outputs."""
    tool_name: str
    tool_id: Optional[str] = None
    description: str = ""
    category: Optional[str] = None
    
    # Input mapping
    inputs: Dict[str, Any] = field(default_factory=dict)
    input_sources: Dict[str, str] = field(default_factory=dict)
    required_inputs: List[str] = field(default_factory=list)
    
    # Output mapping
    outputs: Dict[str, Any] = field(default_factory=dict)
    output_mapping: Dict[str, str] = field(default_factory=dict)
    
    # Execution config
    timeout_ms: Optional[int] = None
    retry_count: int = 0
    retry_delay_ms: int = 1000
    
    # Conditional execution
    condition: Optional[str] = None
    condition_expression: Optional[Dict[str, Any]] = None
    
    # Agent enhancements
    added_by_agent: bool = False
    added_by: Optional[str] = None
    added_at: Optional[datetime] = None
    enhancement_notes: Optional[str] = None

@dataclass
class StepMetadata:
    """Metadata for a step."""
    status: StepStatus = StepStatus.PLANNED
    approved_at: Optional[datetime] = None
    execution_started_at: Optional[datetime] = None
    execution_completed_at: Optional[datetime] = None
    execution_order: int = 0
    
    # Tool configuration
    tool: Optional[ToolDefinition] = None
    tool_configured: bool = False
    tool_configured_at: Optional[datetime] = None
    tool_configured_by: Optional[str] = None
    
    # Execution results
    execution_result: Optional[Dict[str, Any]] = None
    execution_error: Optional[str] = None
    execution_duration_ms: Optional[int] = None
    
    # Dependencies
    depends_on_steps: List[str] = field(default_factory=list)
    blocks_steps: List[str] = field(default_factory=list)
    
    # Agent enhancements
    enhanced_by_agents: List[str] = field(default_factory=list)
    enhancement_history: List[Dict[str, Any]] = field(default_factory=list)
    
    notes: Optional[str] = None
    can_skip: bool = False
    skip_reason: Optional[str] = None

@dataclass
class WorkflowStep:
    """Enhanced step with metadata and tool definition."""
    id: str
    description: str
    tool_hint: Optional[str] = None
    
    # Metadata
    metadata: StepMetadata = field(default_factory=StepMetadata)
    
    # Tool definition (can be added/enhanced by agents)
    tool: Optional[ToolDefinition] = None
    
    # Timeline
    timeline_estimate: Optional[str] = None
    estimated_duration_ms: Optional[int] = None
    
    # Human intervention
    requires_human_review: bool = False
    requires_human_action: bool = False
    human_action_description: Optional[str] = None

@dataclass
class WorkflowPhase:
    """Enhanced phase with metadata."""
    id: str
    name: str
    description: Optional[str] = None
    steps: List[WorkflowStep] = field(default_factory=list)
    
    # Metadata
    metadata: PhaseMetadata = field(default_factory=PhaseMetadata)
    
    # Phase-level config
    can_execute_parallel: bool = False
    requires_all_steps_complete: bool = True

@dataclass
class WorkflowPlan:
    """Complete workflow plan with metadata."""
    problem_statement: str
    name: Optional[str] = None
    goal: Optional[str] = None
    phases: List[WorkflowPhase] = field(default_factory=list)
    
    # Metadata
    metadata: PlanMetadata = field(default_factory=PlanMetadata)
    
    # Missing information
    missing_info: List[str] = field(default_factory=list)
    
    # Questions (if plan incomplete)
    questions: List[str] = field(default_factory=list)


