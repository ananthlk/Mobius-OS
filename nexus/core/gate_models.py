"""
Gate Engine Data Models

Domain-agnostic data structures for the Gate Engine system.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Literal, Any, Union
from datetime import datetime
from enum import Enum
import json
import re
import logging

logger = logging.getLogger("nexus.core.gate_models")


class GateDecision(Enum):
    """Decision types for gate completion."""
    PASS_OVERRIDE = "user_override"
    PASS_ALL_GATES = "all_gates_complete"
    PASS_REQUIRED_GATES = "all_required_complete"
    FAIL_REQUIRED_MISSING = "required_missing"


@dataclass
class GateValue:
    """Value for a single gate."""
    raw: Optional[str] = None  # User's verbatim input
    classified: Optional[str] = None  # Extracted/categorized value
    confidence: Optional[float] = None  # LLM confidence if applicable
    collected_at: Optional[datetime] = None


@dataclass
class StatusInfo:
    """Status information for gate state."""
    pass_: bool  # System-computed, overwrites LLM value (maps to JSON "pass")
    next_gate: Optional[str] = None  # Gate key from gate_order
    next_query: Optional[str] = None  # Question from GateConfig (trimmed)


@dataclass
class GateState:
    """Current state of all gates - matches STRICT_JSON_SCHEMA."""
    summary: str  # <=2000 chars, trimmed
    gates: Dict[str, GateValue] = field(default_factory=dict)  # {"1_data_availability": GateValue(...), ...}
    status: StatusInfo = field(default_factory=lambda: StatusInfo(pass_=False, next_gate=None, next_query=None))


@dataclass
class GateDef:
    """Definition for a single gate."""
    question: str
    required: bool
    expected_categories: List[str] = field(default_factory=list)  # For classification (empty list if no categories)
    # Note: mode and completion_rule inferred from expected_categories:
    # - If expected_categories is non-empty → classified_required
    # - If expected_categories is empty → raw_required


@dataclass
class Policy:
    """Policy settings for gate behavior."""
    allow_user_delete_gate_keys: bool = False
    allow_user_clear_values: bool = True
    strict_classified_validation: bool = False  # Error vs set to None when classified doesn't match (default: lenient)


@dataclass
class GateConfig:
    """Configuration structure from prompt - domain-agnostic."""
    path: Dict[str, str]  # {"interaction_type": "workflow", "workflow": "eligibility", ...}
    output_format: str  # "JSON_ONLY"
    mode: str  # "GATE_ONLY"
    llm_role: List[str]  # Array of role instructions
    gate_order: List[str]  # ["1_data_availability", "2_use_case", "3_fallback_policy", "4_constraints"]
    gates: Dict[str, GateDef]  # {"1_data_availability": GateDef(...), ...}
    mandatory_logic: List[str]  # Step-by-step instructions
    strict_json_schema: Dict[str, Any]  # Output schema definition
    system_instructions: str  # Additional context
    policy: Policy = field(default_factory=Policy)  # Policy settings
    
    @classmethod
    def from_prompt_config(cls, config: Dict[str, Any]) -> 'GateConfig':
        """Create GateConfig from prompt config dictionary."""
        # Extract gates
        gates = {}
        for gate_key, gate_data in config.get("GATES", {}).items():
            gates[gate_key] = GateDef(
                question=gate_data.get("question", ""),
                required=gate_data.get("required", False),
                expected_categories=gate_data.get("expected_categories", [])
            )
        
        # Extract policy if present
        policy_data = config.get("POLICY", {})
        policy = Policy(
            allow_user_delete_gate_keys=policy_data.get("allow_user_delete_gate_keys", False),
            allow_user_clear_values=policy_data.get("allow_user_clear_values", True),
            strict_classified_validation=policy_data.get("strict_classified_validation", False)  # Default: lenient
        )
        
        return cls(
            path=config.get("PATH", {}),
            output_format=config.get("OUTPUT_FORMAT", "JSON_ONLY"),
            mode=config.get("MODE", "GATE_ONLY"),
            llm_role=config.get("LLM_ROLE", []),
            gate_order=config.get("GATE_ORDER", []),
            gates=gates,
            mandatory_logic=config.get("MANDATORY_LOGIC", []),
            strict_json_schema=config.get("STRICT_JSON_SCHEMA", {}),
            system_instructions=config.get("SYSTEM_INSTRUCTIONS", ""),
            policy=policy
        )


@dataclass
class ConsultantResult:
    """Result from GateEngine execution."""
    decision: GateDecision  # Preliminary (parser is final authority)
    pass_: bool  # True when status.pass_ = true (maps to JSON "pass")
    next_gate: Optional[str]  # Gate key to ask next (from status.next_gate)
    next_question: Optional[str]  # The question to ask (from status.next_query)
    proposed_state: GateState  # Updated state after merge (matches STRICT_JSON_SCHEMA)
    updated_gates: List[str] = field(default_factory=list)  # Which gates were updated this turn


# ============================================================================
# JSON Parser Data Models
# ============================================================================

@dataclass
class ParseError:
    """Structured error for parsing failures."""
    code: str  # Error type
    message: str  # Human-readable message
    field_path: Optional[str] = None  # e.g., "gates.1_data_availability.raw"
    expected: Optional[str] = None  # Expected type/value
    actual: Optional[str] = None  # Actual value received


@dataclass
class GateDecisionResult:
    """
    System-computed decision about gate completion.
    Note: Named GateDecisionResult to avoid conflict with GateDecision Enum.
    """
    pass_: bool  # True if all required gates complete
    reason: str  # "all_required_complete", "user_override", "required_missing"
    next_gate: Optional[str] = None
    next_question: Optional[str] = None


@dataclass
class GateDiff:
    """Tracks changes between gate states."""
    actor: Literal["user", "assistant"]
    summary_changed: bool
    gates_added: List[str] = field(default_factory=list)  # New gate keys not in previous_state
    gates_removed: List[str] = field(default_factory=list)  # Gate keys removed (if deletion allowed)
    gates_raw_changed: List[str] = field(default_factory=list)  # Gate keys where raw value changed
    gates_classified_changed: List[str] = field(default_factory=list)  # Gate keys where classified value changed


@dataclass
class ParseResult:
    """Result of gate JSON parsing operation."""
    ok: bool  # True if parsing succeeded
    canonical_state: Optional[GateState] = None  # Validated, canonicalized state
    decision: Optional[GateDecisionResult] = None  # PASS/NO PASS decision
    diff: Optional[GateDiff] = None  # Changes from previous_state
    errors: List[ParseError] = field(default_factory=list)  # Structured errors (empty if ok=True)
    warnings: List[str] = field(default_factory=list)  # Non-fatal issues


# ============================================================================
# Gate JSON Parser
# ============================================================================

class GateJsonParser:
    """
    Parser for GateState JSON structures.
    
    Takes LLM output (text) or user-edited state (dict) and produces:
    - Canonical validated state (normalized, validated GateState)
    - Deterministic PASS/NO PASS decision (system-owned, independent of LLM claims)
    - Diff vs previous canonical state (track what changed)
    """
    
    def parse(
        self,
        payload: Union[str, Dict[str, Any]],
        gate_config: GateConfig,
        previous_state: Optional[GateState] = None,
        actor: Literal["user", "assistant"] = "assistant"
    ) -> ParseResult:
        """
        Parse payload into validated, canonicalized GateState.
        
        Args:
            payload: LLM response text (str) or already-parsed JSON state (dict)
            gate_config: GateConfig object (from prompt)
            previous_state: Optional previous GateState for diff computation
            actor: "user" (UI-edited) or "assistant" (LLM output) - affects validation strictness
        
        Returns:
            ParseResult with canonical_state, decision, diff, errors, warnings
        """
        errors: List[ParseError] = []
        warnings: List[str] = []
        
        # Step 1: Extract JSON if payload is string
        if isinstance(payload, str):
            json_str = self._extract_json_string(payload)
            if not json_str:
                return ParseResult(
                    ok=False,
                    errors=[ParseError(
                        code="invalid_json",
                        message="No JSON object found in text"
                    )]
                )
            try:
                data = json.loads(json_str)
            except json.JSONDecodeError as e:
                return ParseResult(
                    ok=False,
                    errors=[ParseError(
                        code="invalid_json",
                        message=f"JSON parse error: {str(e)}"
                    )]
                )
        elif isinstance(payload, dict):
            data = payload
        else:
            return ParseResult(
                ok=False,
                errors=[ParseError(
                    code="invalid_json",
                    message=f"Payload must be str or dict, got {type(payload).__name__}"
                )]
            )
        
        # Step 2: Validate structure
        validation_errors = self._validate(data, gate_config, actor)
        errors.extend(validation_errors)
        
        if errors:
            return ParseResult(ok=False, errors=errors)
        
        # Step 3: Canonicalize state
        canonical_state = self._canonicalize_state(data, gate_config, warnings)
        
        # Step 4: Compute deterministic decision (system-owned)
        decision = self._compute_decision(canonical_state, gate_config)
        
        # Apply decision to canonical_state.status
        canonical_state.status = StatusInfo(
            pass_=decision.pass_,
            next_gate=decision.next_gate,
            next_query=decision.next_question
        )
        
        # Step 5: Compute diff
        diff = self._compute_diff(previous_state, canonical_state, actor)
        
        return ParseResult(
            ok=True,
            canonical_state=canonical_state,
            decision=decision,
            diff=diff,
            errors=[],
            warnings=warnings
        )
    
    def _extract_json_string(self, text: str) -> Optional[str]:
        """
        Extract JSON string from text using multiple strategies.
        
        Handles:
        1. Code fences: Extract JSON from ```json ... ``` or ``` ... ```
        2. Leading/trailing text: Find JSON object embedded in text
        3. Multiple JSON objects: Choose first valid JSON object
        4. Thinking tags: Remove <thinking>...</thinking> tags before extraction
        """
        if not text:
            return None
        
        # 1. Remove thinking tags
        text = re.sub(r"<thinking>.*?</thinking>", "", text, flags=re.DOTALL).strip()
        
        # 2. Try markdown code blocks first
        code_block_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
        if code_block_match:
            return code_block_match.group(1).strip()
        
        # 3. Try to find JSON object with expected keys
        json_match = re.search(
            r'\{[^{}]*(?:"summary"|"gates"|"status")[^{}]*\}',
            text,
            re.DOTALL
        )
        if json_match:
            return json_match.group(0)
        
        # 4. Fallback: any JSON object
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if json_match:
            return json_match.group(0)
        
        return None
    
    def _validate(
        self,
        data: Dict[str, Any],
        gate_config: GateConfig,
        actor: Literal["user", "assistant"]
    ) -> List[ParseError]:
        """
        Validate JSON structure against GateConfig.
        
        Collects ALL errors (doesn't stop at first error).
        """
        errors: List[ParseError] = []
        
        # 1. Top-level structure validation
        if "summary" not in data:
            errors.append(ParseError(
                code="missing_key",
                field_path="summary",
                expected="string",
                message="Required key 'summary' is missing"
            ))
        if "gates" not in data:
            errors.append(ParseError(
                code="missing_key",
                field_path="gates",
                expected="dict",
                message="Required key 'gates' is missing"
            ))
        if "status" not in data:
            errors.append(ParseError(
                code="missing_key",
                field_path="status",
                expected="dict",
                message="Required key 'status' is missing"
            ))
        
        # If missing top-level keys, return early (can't validate further)
        if errors:
            return errors
        
        # 2. Summary validation
        summary = data.get("summary")
        if not isinstance(summary, str):
            errors.append(ParseError(
                code="invalid_type",
                field_path="summary",
                expected="string",
                actual=type(summary).__name__,
                message=f"Summary must be string, got {type(summary).__name__}"
            ))
        elif len(summary) > 2000:
            errors.append(ParseError(
                code="invalid_value",
                field_path="summary",
                expected="string <= 2000 chars",
                actual=f"string with {len(summary)} chars",
                message=f"Summary exceeds 2000 character limit (got {len(summary)} chars)"
            ))
        
        # 3. Gates validation
        gates_data = data.get("gates", {})
        if not isinstance(gates_data, dict):
            errors.append(ParseError(
                code="invalid_type",
                field_path="gates",
                expected="dict",
                actual=type(gates_data).__name__,
                message=f"Gates must be dict, got {type(gates_data).__name__}"
            ))
        else:
            # Check for invalid gate keys
            for gate_key in gates_data:
                if gate_key not in gate_config.gates:
                    if actor == "assistant":
                        errors.append(ParseError(
                            code="invalid_key",
                            field_path=f"gates.{gate_key}",
                            message=f"Gate key '{gate_key}' not in GateConfig"
                        ))
                    # If user and policy allows, just warn (handled in canonicalize)
            
            # Check required gates are present
            for gate_key, gate_def in gate_config.gates.items():
                if gate_def.required and gate_key not in gates_data:
                    if not (gate_config.policy.allow_user_delete_gate_keys and actor == "user"):
                        errors.append(ParseError(
                            code="missing_required_gate",
                            field_path=f"gates.{gate_key}",
                            message=f"Required gate '{gate_key}' is missing"
                        ))
            
            # Validate each gate value
            for gate_key, gate_value in gates_data.items():
                if gate_key not in gate_config.gates:
                    continue  # Already reported as invalid_key
                
                gate_def = gate_config.gates[gate_key]
                
                if not isinstance(gate_value, dict):
                    errors.append(ParseError(
                        code="invalid_type",
                        field_path=f"gates.{gate_key}",
                        expected="dict",
                        actual=type(gate_value).__name__,
                        message=f"Gate value must be dict, got {type(gate_value).__name__}"
                    ))
                    continue
                
                # Check raw
                if "raw" in gate_value:
                    raw_val = gate_value["raw"]
                    if not isinstance(raw_val, (str, type(None))):
                        errors.append(ParseError(
                            code="invalid_type",
                            field_path=f"gates.{gate_key}.raw",
                            expected="string or null",
                            actual=type(raw_val).__name__,
                            message=f"Raw value must be string or null, got {type(raw_val).__name__}"
                        ))
                
                # Check classified
                if "classified" in gate_value:
                    classified_val = gate_value["classified"]
                    if not isinstance(classified_val, (str, type(None))):
                        errors.append(ParseError(
                            code="invalid_type",
                            field_path=f"gates.{gate_key}.classified",
                            expected="string or null",
                            actual=type(classified_val).__name__,
                            message=f"Classified value must be string or null, got {type(classified_val).__name__}"
                        ))
                    elif classified_val is not None and gate_def.expected_categories:
                        if classified_val not in gate_def.expected_categories:
                            if gate_config.policy.strict_classified_validation:
                                errors.append(ParseError(
                                    code="invalid_category",
                                    field_path=f"gates.{gate_key}.classified",
                                    expected=f"one of {gate_def.expected_categories}",
                                    actual=classified_val,
                                    message=f"Classified value '{classified_val}' not in expected categories: {gate_def.expected_categories}"
                                ))
                            # If not strict, will be set to None in canonicalize
        
        # 4. Status validation
        status_data = data.get("status", {})
        if not isinstance(status_data, dict):
            errors.append(ParseError(
                code="invalid_type",
                field_path="status",
                expected="dict",
                actual=type(status_data).__name__,
                message=f"Status must be dict, got {type(status_data).__name__}"
            ))
        else:
            # Note: JSON uses "pass" but Python field is "pass_" (pass is reserved keyword)
            if "pass" not in status_data:
                errors.append(ParseError(
                    code="missing_key",
                    field_path="status.pass",
                    expected="boolean",
                    message="Required key 'status.pass' is missing"
                ))
            elif not isinstance(status_data["pass"], bool):
                errors.append(ParseError(
                    code="invalid_type",
                    field_path="status.pass",
                    expected="boolean",
                    actual=type(status_data["pass"]).__name__,
                    message=f"status.pass must be boolean, got {type(status_data['pass']).__name__}"
                ))
            
            if "next_gate" in status_data and status_data["next_gate"] is not None:
                next_gate_val = status_data["next_gate"]
                if not isinstance(next_gate_val, str):
                    errors.append(ParseError(
                        code="invalid_type",
                        field_path="status.next_gate",
                        expected="string or null",
                        actual=type(next_gate_val).__name__,
                        message=f"status.next_gate must be string or null, got {type(next_gate_val).__name__}"
                    ))
                elif next_gate_val not in gate_config.gate_order:
                    errors.append(ParseError(
                        code="invalid_gate_key",
                        field_path="status.next_gate",
                        expected=f"one of {gate_config.gate_order}",
                        actual=next_gate_val,
                        message=f"status.next_gate '{next_gate_val}' not in gate_order"
                    ))
            
            if "next_query" in status_data and status_data["next_query"] is not None:
                if not isinstance(status_data["next_query"], str):
                    errors.append(ParseError(
                        code="invalid_type",
                        field_path="status.next_query",
                        expected="string or null",
                        actual=type(status_data["next_query"]).__name__,
                        message=f"status.next_query must be string or null, got {type(status_data['next_query']).__name__}"
                    ))
        
        return errors
    
    def _canonicalize_state(
        self,
        data: Dict[str, Any],
        gate_config: GateConfig,
        warnings: List[str]
    ) -> GateState:
        """
        Canonicalize state by:
        1. Trimming whitespace from all string values
        2. Converting empty strings to None (except for summary)
        3. Ensuring all gate_order gates exist in gates dict
        4. Validating classified values against expected_categories
        """
        # 1. Canonicalize summary
        summary = data.get("summary", "")
        if isinstance(summary, str):
            summary = summary.strip()
            # Keep empty string for summary (don't convert to None)
        else:
            summary = ""
        
        # 2. Canonicalize gates
        canonical_gates: Dict[str, GateValue] = {}
        gates_data = data.get("gates", {})
        
        # Process gates in gate_order to ensure all are present
        for gate_key in gate_config.gate_order:
            gate_def = gate_config.gates.get(gate_key)
            if not gate_def:
                # Gate key in gate_order but not in gate_config.gates - skip
                continue
            
            gate_data = gates_data.get(gate_key, {})
            
            # Raw
            raw = gate_data.get("raw") if isinstance(gate_data, dict) else None
            if isinstance(raw, str):
                raw = raw.strip()
                raw = None if raw == "" else raw
            else:
                raw = None
            
            # Classified
            classified = gate_data.get("classified") if isinstance(gate_data, dict) else None
            if isinstance(classified, str):
                classified = classified.strip()
                classified = None if classified == "" else classified
                
                # Validate against expected_categories
                if classified and gate_def.expected_categories:
                    if classified not in gate_def.expected_categories:
                        # Invalid category - set to None (validation already handled errors if strict)
                        if not gate_config.policy.strict_classified_validation:
                            warnings.append(
                                f"Invalid category '{classified}' for gate '{gate_key}', setting to None"
                            )
                        classified = None
            else:
                classified = None
            
            canonical_gates[gate_key] = GateValue(raw=raw, classified=classified)
        
        # 3. Canonicalize status (will be recomputed, but preserve LLM values for now)
        status_data = data.get("status", {})
        next_query_val = status_data.get("next_query") if isinstance(status_data, dict) else None
        if isinstance(next_query_val, str):
            next_query_val = next_query_val.strip()
            next_query_val = None if next_query_val == "" else next_query_val
        else:
            next_query_val = None
        
        # Map JSON "pass" to Python "pass_" field (pass is reserved keyword)
        pass_val = status_data.get("pass", False) if isinstance(status_data, dict) else False
        status = StatusInfo(
            pass_=pass_val,
            next_gate=status_data.get("next_gate") if isinstance(status_data, dict) else None,
            next_query=next_query_val
        )
        
        return GateState(summary=summary, gates=canonical_gates, status=status)
    
    def _compute_decision(
        self,
        canonical_state: GateState,
        gate_config: GateConfig
    ) -> GateDecisionResult:
        """
        Compute deterministic PASS/NO PASS decision (system-owned).
        
        Per MANDATORY_LOGIC:
        - Find FIRST missing REQUIRED gate in gate_order
        - Gate is missing if: required=true AND classified is None
        - If found → NO PASS + next_question from GateConfig
        - Else → PASS + null next question
        """
        # Find first missing required gate
        for gate_key in gate_config.gate_order:
            gate_def = gate_config.gates.get(gate_key)
            if not gate_def:
                continue
            
            if gate_def.required:
                gate_value = canonical_state.gates.get(gate_key)
                if gate_value is None or gate_value.classified is None:
                    # Found missing required gate
                    return GateDecisionResult(
                        pass_=False,
                        reason="required_missing",
                        next_gate=gate_key,
                        next_question=gate_def.question
                    )
        
        # All required gates have classified values
        return GateDecisionResult(
            pass_=True,
            reason="all_required_complete",
            next_gate=None,
            next_question=None
        )
    
    def _compute_diff(
        self,
        previous_state: Optional[GateState],
        canonical_state: GateState,
        actor: Literal["user", "assistant"]
    ) -> Optional[GateDiff]:
        """
        Compute diff between previous_state and canonical_state.
        
        Returns:
            GateDiff with all changes, or None if no previous_state
        """
        if previous_state is None:
            # First state - everything is new
            return GateDiff(
                actor=actor,
                summary_changed=True,
                gates_added=list(canonical_state.gates.keys()),
                gates_removed=[],
                gates_raw_changed=list(canonical_state.gates.keys()),
                gates_classified_changed=list(canonical_state.gates.keys())
            )
        
        diff = GateDiff(
            actor=actor,
            summary_changed=(previous_state.summary != canonical_state.summary),
            gates_added=[],
            gates_removed=[],
            gates_raw_changed=[],
            gates_classified_changed=[]
        )
        
        # Find added gates
        for gate_key in canonical_state.gates:
            if gate_key not in previous_state.gates:
                diff.gates_added.append(gate_key)
        
        # Find removed gates
        for gate_key in previous_state.gates:
            if gate_key not in canonical_state.gates:
                diff.gates_removed.append(gate_key)
        
        # Find changed gates
        for gate_key in canonical_state.gates:
            prev_value = previous_state.gates.get(gate_key)
            curr_value = canonical_state.gates[gate_key]
            
            if prev_value is None:
                # New gate
                if curr_value.raw is not None:
                    diff.gates_raw_changed.append(gate_key)
                if curr_value.classified is not None:
                    diff.gates_classified_changed.append(gate_key)
            else:
                # Existing gate - check for changes
                if prev_value.raw != curr_value.raw:
                    diff.gates_raw_changed.append(gate_key)
                if prev_value.classified != curr_value.classified:
                    diff.gates_classified_changed.append(gate_key)
        
        return diff

