"""
Planner JSON Parser - Handles nested/phased plan structures
"""
import json
import re
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

logger = logging.getLogger("nexus.planner.parser")


@dataclass
class ParsedPlan:
    """Normalized plan structure."""
    problem_statement: str
    name: str
    goal: str
    phases: List[Dict[str, Any]]
    missing_info: List[str]


class PlannerPlanParser:
    """
    Specialized parser for planner draft plans.
    Expects nested phases structure.
    """
    
    HUMAN_INTERVENTION_HINTS = ["human_intervention", "manual_review", "human_review", "manual_task"]
    
    def __init__(self):
        pass
    
    def parse(self, raw_response: str) -> ParsedPlan:
        """
        Parse LLM response into normalized plan structure.
        
        Args:
            raw_response: Raw LLM response text (may contain markdown, thinking tags, etc.)
        
        Returns:
            ParsedPlan with normalized structure
        """
        # Clean response
        cleaned = self._clean_response(raw_response)
        
        # Extract JSON
        json_str = self._extract_json(cleaned)
        
        if not json_str:
            raise ValueError("No JSON found in LLM response")
        
        # Parse JSON
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON: {e}")
        
        # Validate and normalize structure
        return self._normalize_plan(data)
    
    def _clean_response(self, text: str) -> str:
        """Remove markdown, thinking tags, etc."""
        # Remove thinking tags
        text = re.sub(r'<thinking>.*?</thinking>', '', text, flags=re.DOTALL | re.IGNORECASE)
        
        # Remove markdown code blocks
        text = re.sub(r'```json\s*', '', text, flags=re.IGNORECASE)
        text = re.sub(r'```\s*', '', text)
        
        return text.strip()
    
    def _extract_json(self, text: str) -> Optional[str]:
        """Extract JSON object from text."""
        # Try to find JSON object
        brace_count = 0
        start_idx = -1
        
        for i, char in enumerate(text):
            if char == '{':
                if start_idx == -1:
                    start_idx = i
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count == 0 and start_idx != -1:
                    return text[start_idx:i+1]
        
        return None
    
    def _normalize_plan(self, data: Dict[str, Any]) -> ParsedPlan:
        """
        Normalize plan to phases structure.
        """
        # Extract base fields
        problem_statement = data.get("problem_statement", "")
        name = data.get("name", "Workflow Plan")
        goal = data.get("goal", "")
        missing_info = data.get("missing_info", [])
        
        # Require phases structure
        if "phases" not in data or not isinstance(data["phases"], list):
            raise ValueError("Plan must have 'phases' array. Received structure: " + str(list(data.keys())))
        
        # Validate and clean phases
        validated_phases = []
        for phase in data["phases"]:
            validated_phase = self._validate_phase(phase)
            if validated_phase:
                validated_phases.append(validated_phase)
        
        if not validated_phases:
            raise ValueError("Plan must have at least one valid phase")
        
        return ParsedPlan(
            problem_statement=problem_statement,
            name=name,
            goal=goal,
            phases=validated_phases,
            missing_info=missing_info
        )
    
    def _validate_phase(self, phase: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Validate and clean a phase structure."""
        if not isinstance(phase, dict):
            logger.warning(f"Invalid phase: not a dict: {phase}")
            return None
        
        # Ensure required fields
        phase_id = phase.get("id")
        if not phase_id:
            logger.warning(f"Phase missing 'id', skipping: {phase}")
            return None
        
        phase_name = phase.get("name") or "Unnamed Phase"
        phase_description = phase.get("description") or ""
        steps = phase.get("steps", [])
        
        if not isinstance(steps, list):
            logger.warning(f"Phase {phase_id} has invalid steps, using empty list")
            steps = []
        
        # Validate steps
        validated_steps = []
        for step in steps:
            validated_step = self._validate_step(step)
            if validated_step:
                validated_steps.append(validated_step)
        
        return {
            "id": phase_id,
            "name": phase_name,
            "description": phase_description,
            "steps": validated_steps
        }
    
    def _validate_step(self, step: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Validate and clean a step structure."""
        if not isinstance(step, dict):
            logger.warning(f"Invalid step: not a dict: {step}")
            return None
        
        # Ensure required fields
        step_id = step.get("id")
        if not step_id:
            logger.warning(f"Step missing 'id', skipping: {step}")
            return None
        
        tool_hint = step.get("tool_hint", "")
        description = step.get("description", "")
        if not description:
            logger.warning(f"Step {step_id} missing 'description'")
        
        solves = step.get("solves", "")
        
        # Check if human intervention
        is_human_intervention = self._is_human_intervention(tool_hint)
        
        return {
            "id": step_id,
            "tool_hint": tool_hint,
            "description": description,
            "solves": solves,
            "requires_human_review": is_human_intervention or step.get("requires_human_review", False),
            "is_batch": step.get("is_batch", False),
            "tool_matched": False,  # Will be set during post-processing
            "tool_name": None,  # Will be set during post-processing
            "execution_conditions": step.get("execution_conditions", [])
        }
    
    def _is_human_intervention(self, tool_hint: str) -> bool:
        """Check if tool_hint indicates human intervention."""
        if not tool_hint:
            return False
        
        tool_hint_lower = tool_hint.lower().strip()
        return tool_hint_lower in self.HUMAN_INTERVENTION_HINTS
    
    def to_dict(self, parsed_plan: ParsedPlan) -> Dict[str, Any]:
        """Convert ParsedPlan back to dictionary format."""
        return {
            "problem_statement": parsed_plan.problem_statement,
            "name": parsed_plan.name,
            "goal": parsed_plan.goal,
            "phases": parsed_plan.phases,
            "missing_info": parsed_plan.missing_info
        }








