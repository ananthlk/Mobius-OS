"""
Plan Extractor and Updater

Reusable component for extracting and updating plans from various sources.
Follows module:domain:strategy:step pattern for consistency.
"""

import logging
from typing import Dict, Any, Optional, List
from nexus.core.tree_structure_manager import TreePath, tree_structure_manager
from nexus.core.plan_models import WorkflowPlan, WorkflowPhase, WorkflowStep
from nexus.core.gate_models import GateState

logger = logging.getLogger("nexus.core.plan_extractor")

class PlanExtractor:
    """
    Reusable component for extracting plans from templates, gate states, or other sources.
    """
    
    def __init__(self):
        pass
    
    def extract_plan_from_template(
        self,
        template_config: Dict[str, Any],
        gate_state: GateState,
        path: TreePath
    ) -> WorkflowPlan:
        """
        Extract a plan from a template configuration with hierarchical structure.
        Structure: gates → sub_levels (gate response values) → tasks
        
        Args:
            template_config: Template configuration with gates and sub_levels
            gate_state: Current gate state for context
            path: Tree path for this plan (module:domain:strategy:step)
        
        Returns:
            WorkflowPlan object
        """
        from nexus.core.plan_models import PlanMetadata
        
        plan = WorkflowPlan(
            problem_statement=gate_state.summary,
            name=template_config.get("name"),
            goal=template_config.get("goal"),
            metadata=PlanMetadata(
                parent_template_key=f"{path.module}:{path.domain}:{path.strategy}:template"
            )
        )
        
        # Check if template uses new hierarchical structure (gates with sub_levels)
        if "gates" in template_config:
            # Extract gates (new hierarchical structure)
            for gate_data in template_config.get("gates", []):
                phase = self._extract_gate_with_sub_levels(gate_data, gate_state)
                if phase:  # Only add if gate has steps after pruning
                    plan.phases.append(phase)
        else:
            # Legacy: Extract phases (backward compatibility)
            for phase_data in template_config.get("phases", []):
                phase = self._extract_phase(phase_data, gate_state)
                plan.phases.append(phase)
        
        return plan
    
    def extract_plan_from_gate_state(
        self,
        gate_state: GateState,
        path: TreePath
    ) -> WorkflowPlan:
        """
        Extract a plan directly from gate state.
        Uses deterministic mapping based on gate selections.
        """
        from nexus.core.plan_models import PlanMetadata, WorkflowPhase, WorkflowStep
        
        plan = WorkflowPlan(
            problem_statement=gate_state.summary,
            metadata=PlanMetadata()
        )
        
        # Phase A: Retrieve Basic Information
        phase_a = self._generate_phase_a(gate_state)
        plan.phases.append(phase_a)
        
        # Phase B: Use-case specific
        phase_b = self._generate_phase_b(gate_state)
        plan.phases.append(phase_b)
        
        # Phase C: Check Eligibility
        phase_c = self._generate_phase_c(gate_state)
        plan.phases.append(phase_c)
        
        # Phase D: Next Steps
        phase_d = self._generate_phase_d(gate_state)
        plan.phases.append(phase_d)
        
        return plan
    
    def update_plan_from_selections(
        self,
        plan: WorkflowPlan,
        selections: Dict[str, Any],
        path: TreePath
    ) -> WorkflowPlan:
        """
        Update a plan based on user selections or agent enhancements.
        
        Args:
            plan: Existing plan
            selections: Dictionary of selections/enhancements
            path: Tree path for context
        
        Returns:
            Updated plan
        """
        # Update phases based on selections
        for phase in plan.phases:
            if phase.id in selections:
                self._update_phase(phase, selections[phase.id])
        
        # Update steps
        for phase in plan.phases:
            for step in phase.steps:
                step_key = f"{phase.id}.{step.id}"
                if step_key in selections:
                    self._update_step(step, selections[step_key])
        
        return plan
    
    def _extract_gate_with_sub_levels(
        self,
        gate_data: Dict[str, Any],
        gate_state: GateState
    ) -> Optional[WorkflowPhase]:
        """
        Extract a gate with sub-level pruning based on gate_state.
        
        Structure:
        - gate_data has "sub_levels" dict keyed by gate response values
        - Each sub_level has "tasks" array
        - We select the sub_level matching the gate_state value
        
        Args:
            gate_data: Gate data from template with sub_levels
            gate_state: Current gate state
        
        Returns:
            WorkflowPhase with pruned steps, or None if gate not answered
        """
        from nexus.core.plan_models import PhaseMetadata
        
        gate_key = gate_data.get("gate_key")
        if not gate_key:
            logger.warning(f"[PLAN_EXTRACTOR] Gate data missing gate_key: {gate_data.get('id')}")
            return None
        
        # Get gate value from gate_state
        gate_value_obj = gate_state.gates.get(gate_key)
        if not gate_value_obj or not gate_value_obj.classified:
            # Gate not answered yet - return None (will be skipped)
            logger.debug(f"[PLAN_EXTRACTOR] Gate {gate_key} not answered yet")
            return None
        
        gate_response_value = gate_value_obj.classified
        
        # Get sub_levels from gate_data
        sub_levels = gate_data.get("sub_levels", {})
        
        # Select the matching sub_level
        selected_sub_level = sub_levels.get(gate_response_value)
        
        # Fallback to "_default" if specific sub_level not found
        if not selected_sub_level:
            selected_sub_level = sub_levels.get("_default")
        
        if not selected_sub_level:
            logger.warning(
                f"[PLAN_EXTRACTOR] No sub_level found for gate {gate_key} "
                f"with value '{gate_response_value}'. Available: {list(sub_levels.keys())}"
            )
            return None
        
        # Create phase from gate
        # Extract gate number from gate_key (e.g., "1_patient_info_availability" -> "1")
        gate_num = gate_key.split("_")[0] if "_" in gate_key else gate_key
        phase = WorkflowPhase(
            id=gate_data.get("id", f"gate_{gate_num}"),
            name=gate_data.get("name", gate_key),
            description=gate_data.get("description", ""),
            metadata=PhaseMetadata()
        )
        
        # Store gate_key in metadata for planner to match
        phase.metadata.notes = f"gate_key:{gate_key}"
        
        # Extract tasks from selected sub_level
        tasks = selected_sub_level.get("tasks", [])
        for task_data in tasks:
            # Check if task has a condition (for nested conditions within sub_level)
            condition = task_data.get("condition")
            if condition:
                if not self._evaluate_condition(condition, gate_state):
                    logger.debug(
                        f"[PLAN_EXTRACTOR] Excluding task '{task_data.get('id')}' "
                        f"because condition '{condition}' did not match"
                    )
                    continue
            
            step = self._extract_step(task_data)
            phase.steps.append(step)
        
        logger.info(
            f"[PLAN_EXTRACTOR] Extracted gate {gate_key} ({gate_response_value}): "
            f"{len(phase.steps)} tasks from sub_level '{gate_response_value}'"
        )
        
        return phase
    
    def _evaluate_condition(
        self,
        condition: str,
        gate_state: GateState
    ) -> bool:
        """
        Evaluate a condition string against gate_state.
        
        Supports:
        - "1_patient_info_availability == 'Yes'" → checks gate_state.gates["1_patient_info_availability"].classified == "Yes"
        - "2_insurance_history == 'Yes' or 2_insurance_history == 'No'" → OR logic
        
        Args:
            condition: Condition string from template
            gate_state: Current gate state
        
        Returns:
            True if condition matches, False otherwise
        """
        if not condition:
            return True  # No condition means always include
        
        # Split by "or" to handle OR conditions
        or_parts = [part.strip() for part in condition.split(" or ")]
        
        for or_part in or_parts:
            # Parse "gate_key == 'value'"
            if "==" in or_part:
                var_part, value_part = or_part.split("==", 1)
                gate_key = var_part.strip()
                value = value_part.strip().strip("'\"")  # Remove quotes
                
                # Get gate value
                gate_value = gate_state.gates.get(gate_key)
                if not gate_value or not gate_value.classified:
                    continue  # Gate not answered yet
                
                # Check match
                if gate_value.classified == value:
                    return True  # One OR condition matched
        
        return False  # No conditions matched
    
    def _extract_phase(
        self,
        phase_data: Dict[str, Any],
        gate_state: GateState
    ) -> WorkflowPhase:
        """Extract a phase from phase data (legacy support)."""
        from nexus.core.plan_models import PhaseMetadata
        
        phase = WorkflowPhase(
            id=phase_data["id"],
            name=phase_data["name"],
            description=phase_data.get("description"),
            metadata=PhaseMetadata()
        )
        
        # Extract steps
        for step_data in phase_data.get("steps", []):
            # Check if step has a condition
            condition = step_data.get("condition")
            if condition:
                if not self._evaluate_condition(condition, gate_state):
                    logger.debug(
                        f"[PLAN_EXTRACTOR] Excluding step '{step_data.get('id')}' "
                        f"because condition '{condition}' did not match gate state"
                    )
                    continue
            
            step = self._extract_step(step_data)
            phase.steps.append(step)
        
        return phase
    
    def _extract_step(self, step_data: Dict[str, Any]) -> WorkflowStep:
        """Extract a step from step data (works for both 'steps' and 'tasks')."""
        from nexus.core.plan_models import StepMetadata
        
        return WorkflowStep(
            id=step_data["id"],
            description=step_data["description"],
            tool_hint=step_data.get("tool_hint"),
            timeline_estimate=step_data.get("timeline_estimate"),
            metadata=StepMetadata(),
            requires_human_review=step_data.get("requires_human_review", False),
            requires_human_action=step_data.get("requires_human_action", False)
        )
    
    def _generate_phase_a(self, gate_state: GateState) -> WorkflowPhase:
        """Generate Phase A: Retrieve Basic Information."""
        from nexus.core.plan_models import WorkflowPhase, WorkflowStep, PhaseMetadata
        
        steps = [
            WorkflowStep(
                id="step_a1",
                description="Retrieve patient demographics (name, DOB)",
                tool_hint="retrieve_patient_demographics"
            ),
            WorkflowStep(
                id="step_a2",
                description="Retrieve insurance information",
                tool_hint="retrieve_insurance_info"
            )
        ]
        
        # Add conditional step if needed
        patient_info = gate_state.gates.get("1_patient_info_availability")
        if patient_info and patient_info.classified == "Partial":
            steps.append(WorkflowStep(
                id="step_a3",
                description="Obtain missing patient information",
                tool_hint="request_patient_info",
                requires_human_action=True
            ))
        
        return WorkflowPhase(
            id="phase_a",
            name="Retrieve Basic Information",
            steps=steps,
            metadata=PhaseMetadata()
        )
    
    def _generate_phase_b(self, gate_state: GateState) -> WorkflowPhase:
        """Generate Phase B: Use-case specific."""
        from nexus.core.plan_models import WorkflowPhase, WorkflowStep, PhaseMetadata
        
        use_case = gate_state.gates.get("2_use_case")
        steps = []
        
        if use_case and use_case.classified:
            # Map use case to steps
            use_case_steps = self._get_use_case_steps(use_case.classified)
            steps = [
                WorkflowStep(
                    id=f"step_b{i+1}",
                    description=step_desc,
                    tool_hint=step_tool
                )
                for i, (step_desc, step_tool) in enumerate(use_case_steps)
            ]
        
        return WorkflowPhase(
            id="phase_b",
            name="Check Additional Details",
            steps=steps,
            metadata=PhaseMetadata()
        )
    
    def _generate_phase_c(self, gate_state: GateState) -> WorkflowPhase:
        """Generate Phase C: Check Eligibility."""
        from nexus.core.plan_models import WorkflowPhase, WorkflowStep, PhaseMetadata, StepMetadata
        
        step_metadata = StepMetadata(notes="Conditional: if direct unavailable")
        
        return WorkflowPhase(
            id="phase_c",
            name="Check Eligibility",
            steps=[
                WorkflowStep(
                    id="step_c1",
                    description="Check eligibility via direct insurance transaction",
                    tool_hint="check_eligibility_direct"
                ),
                WorkflowStep(
                    id="step_c2",
                    description="Check eligibility via HIE and historical context",
                    tool_hint="check_eligibility_imputed",
                    metadata=step_metadata
                )
            ],
            metadata=PhaseMetadata()
        )
    
    def _generate_phase_d(self, gate_state: GateState) -> WorkflowPhase:
        """Generate Phase D: Next Steps."""
        from nexus.core.plan_models import WorkflowPhase, WorkflowStep, PhaseMetadata
        
        ineligibility_handling = gate_state.gates.get("3_ineligibility_handling")
        handling_desc = ineligibility_handling.classified if ineligibility_handling else "Execute action"
        
        return WorkflowPhase(
            id="phase_d",
            name="Next Steps & Stakeholder Notification",
            steps=[
                WorkflowStep(
                    id="step_d_eligible",
                    description="If eligible: Confirm and notify stakeholders",
                    tool_hint="handle_eligible_outcome"
                ),
                WorkflowStep(
                    id="step_d_not_eligible",
                    description=f"If not eligible: {handling_desc}",
                    tool_hint="handle_not_eligible_outcome"
                ),
                WorkflowStep(
                    id="step_d_unable",
                    description="If unable to determine: Escalate and notify",
                    tool_hint="handle_unable_to_determine"
                )
            ],
            metadata=PhaseMetadata()
        )
    
    def _get_use_case_steps(self, use_case: str) -> List[tuple]:
        """Get steps for a specific use case."""
        use_case_map = {
            "insurance_billing_past_event": [
                ("Retrieve claim details for past event", "retrieve_claim_details"),
                ("Confirm service dates match eligibility period", "verify_service_date_eligibility")
            ],
            "insurance_billing_denial_dispute": [
                ("Retrieve denial details and reason", "retrieve_denial_details"),
                ("Verify eligibility at time of service", "verify_eligibility_at_service_date")
            ],
            "clinical_scheduling_future_dates": [
                ("Determine eligible dates for scheduling", "check_eligible_dates"),
                ("Check visit authorization limits", "check_visit_authorization")
            ],
            "balance_billing_estimation": [
                ("Calculate copay estimation", "calculate_copay_estimate"),
                ("Check deductible status", "check_deductible_status")
            ]
        }
        return use_case_map.get(use_case, [])
    
    def _update_phase(self, phase: WorkflowPhase, updates: Dict[str, Any]):
        """Update a phase with new data."""
        if "name" in updates:
            phase.name = updates["name"]
        if "description" in updates:
            phase.description = updates["description"]
        if "status" in updates:
            phase.metadata.status = updates["status"]
    
    def _update_step(self, step: WorkflowStep, updates: Dict[str, Any]):
        """Update a step with new data."""
        if "description" in updates:
            step.description = updates["description"]
        if "tool" in updates:
            from nexus.core.plan_models import ToolDefinition
            step.tool = ToolDefinition(**updates["tool"])
            step.metadata.tool_configured = True

# Singleton instance
plan_extractor = PlanExtractor()

