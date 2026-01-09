# Requirements: ModuleJsonParser

## Purpose

A Python module that takes LLM output (text) or a user-edited state (dict), and produces:
- **Canonical validated state** - Normalized, validated GateState
- **Deterministic PASS/NO PASS decision** - System-owned decision, independent of LLM claims
- **Diff vs previous canonical state** - Track what changed

## Module Name

`nexus.core.gate_json_parser` or `nexus.core.json_parser` (extend existing)

## Inputs

```python
def parse(
    payload: Union[str, Dict[str, Any]],
    gate_config: GateConfig,
    previous_state: Optional[GateState] = None,
    actor: Literal["user", "assistant"] = "assistant"
) -> ParseResult
```

**Parameters:**
- `payload`: 
  - `str`: LLM response text containing JSON (may have markdown, thinking tags, etc.)
  - `dict`: Already-parsed JSON state (e.g., from UI editor)
- `gate_config`: GateConfig object (from prompt)
- `previous_state`: Optional previous GateState for diff computation
- `actor`: "user" (UI-edited) or "assistant" (LLM output) - affects validation strictness

## Outputs

```python
@dataclass
class ParseResult:
    ok: bool  # True if parsing succeeded
    canonical_state: Optional[GateState] = None  # Validated, canonicalized state
    decision: Optional[GateDecision] = None  # PASS/NO PASS decision
    diff: Optional[GateDiff] = None  # Changes from previous_state
    errors: List[ParseError] = None  # Structured errors (empty if ok=True)
    warnings: List[str] = None  # Non-fatal issues
```

```python
@dataclass
class GateState:
    summary: str  # <=200 chars, trimmed
    gates: Dict[str, GateValue]  # {"1_data_availability": GateValue(...), ...}
    status: StatusInfo

@dataclass
class GateValue:
    raw: Optional[str] = None  # User's verbatim input (trimmed, empty string → None)
    classified: Optional[str] = None  # Extracted/categorized value (trimmed, empty string → None)

@dataclass
class StatusInfo:
    pass: bool  # System-computed, overwrites LLM value
    next_gate: Optional[str] = None  # Gate key from gate_order
    next_query: Optional[str] = None  # Question from GateConfig (trimmed)
```

```python
@dataclass
class GateDecision:
    pass_: bool  # True if all required gates complete
    reason: str  # "all_required_complete", "user_override", "required_missing"
    next_gate: Optional[str] = None
    next_question: Optional[str] = None
```

```python
@dataclass
class GateDiff:
    actor: Literal["user", "assistant"]
    summary_changed: bool
    gates_added: List[str]  # New gate keys not in previous_state
    gates_removed: List[str]  # Gate keys removed (if deletion allowed)
    gates_raw_changed: List[str]  # Gate keys where raw value changed
    gates_classified_changed: List[str]  # Gate keys where classified value changed
```

```python
@dataclass
class ParseError:
    code: str  # Error type (see Error Codes below)
    message: str  # Human-readable message
    field_path: Optional[str] = None  # e.g., "gates.1_data_availability.raw"
    expected: Optional[str] = None  # Expected type/value
    actual: Optional[str] = None  # Actual value received
```

## JSON Extraction (if payload is str)

**Must handle:**
1. **Code fences**: Extract JSON from ```json ... ``` or ``` ... ```
2. **Leading/trailing text**: Find JSON object embedded in text
3. **Multiple JSON objects**: Choose first valid JSON object
4. **Thinking tags**: Remove `<thinking>...</thinking>` tags before extraction

**Algorithm:**
```python
def extract_json_string(text: str) -> Optional[str]:
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
```

**If no JSON found:**
- Return `ParseResult(ok=False, errors=[ParseError(code="invalid_json", message="No JSON object found in text")])`

## Validation Requirements

### 1. Top-Level Structure

**Required keys:**
- `summary` (must exist, must be string)
- `gates` (must exist, must be dict)
- `status` (must exist, must be dict)

**Validation:**
```python
if "summary" not in data:
    errors.append(ParseError(code="missing_key", field_path="summary", expected="string"))
if "gates" not in data:
    errors.append(ParseError(code="missing_key", field_path="gates", expected="dict"))
if "status" not in data:
    errors.append(ParseError(code="missing_key", field_path="status", expected="dict"))
```

### 2. Summary Validation

- Must be string (not null, not dict, not list)
- Length <= 200 characters (per STRICT_JSON_SCHEMA)
- Empty string is valid (user hasn't provided summary yet)

**Validation:**
```python
if not isinstance(data.get("summary"), str):
    errors.append(ParseError(
        code="invalid_type",
        field_path="summary",
        expected="string",
        actual=type(data.get("summary")).__name__
    ))
elif len(data["summary"]) > 200:
    errors.append(ParseError(
        code="invalid_value",
        field_path="summary",
        expected="string <= 200 chars",
        actual=f"string with {len(data['summary'])} chars"
    ))
```

### 3. Gates Validation

**Gate keys must match GateConfig:**
- All keys in `data["gates"]` must exist in `gate_config.gates`
- Exception: If `actor="user"` and policy allows extras, allow additional keys
- If required gate key is missing and deletion not allowed → error

**Validation:**
```python
for gate_key in data.get("gates", {}):
    if gate_key not in gate_config.gates:
        if actor == "assistant":
            errors.append(ParseError(
                code="invalid_key",
                field_path=f"gates.{gate_key}",
                message=f"Gate key '{gate_key}' not in GateConfig"
            ))
        # If user and policy allows, just warn

# Check required gates are present
for gate_key, gate_def in gate_config.gates.items():
    if gate_def.required and gate_key not in data.get("gates", {}):
        if not (policy and policy.allow_user_delete_gate_keys and actor == "user"):
            errors.append(ParseError(
                code="missing_required_gate",
                field_path=f"gates.{gate_key}",
                message=f"Required gate '{gate_key}' is missing"
            ))
```

### 4. Gate Value Validation

**For each gate in `data["gates"]`:**

**Structure:**
- Must be dict with `raw` and/or `classified` keys
- Both must be string or null (not other types)

**Type validation:**
```python
gate_value = data["gates"][gate_key]
gate_def = gate_config.gates[gate_key]

# Check raw
if "raw" in gate_value:
    if not isinstance(gate_value["raw"], (str, type(None))):
        errors.append(ParseError(
            code="invalid_type",
            field_path=f"gates.{gate_key}.raw",
            expected="string or null",
            actual=type(gate_value["raw"]).__name__
        ))

# Check classified
if "classified" in gate_value:
    if not isinstance(gate_value["classified"], (str, type(None))):
        errors.append(ParseError(
            code="invalid_type",
            field_path=f"gates.{gate_key}.classified",
            expected="string or null",
            actual=type(gate_value["classified"]).__name__
        ))
    
    # Validate against expected_categories
    if gate_value["classified"] is not None and gate_def.expected_categories:
        if gate_value["classified"] not in gate_def.expected_categories:
            # Option 1: Error (strict)
            errors.append(ParseError(
                code="invalid_category",
                field_path=f"gates.{gate_key}.classified",
                expected=f"one of {gate_def.expected_categories}",
                actual=gate_value["classified"]
            ))
            # Option 2: Set to None (lenient) - choose based on policy
```

### 5. Status Validation

**Required fields:**
- `status.pass`: Must be boolean
- `status.next_gate`: Must be string, null, or match a gate key
- `status.next_query`: Must be string or null

**Validation:**
```python
status = data.get("status", {})
if "pass" not in status:
    errors.append(ParseError(code="missing_key", field_path="status.pass"))
elif not isinstance(status["pass"], bool):
    errors.append(ParseError(
        code="invalid_type",
        field_path="status.pass",
        expected="boolean",
        actual=type(status["pass"]).__name__
    ))

if "next_gate" in status and status["next_gate"] is not None:
    if not isinstance(status["next_gate"], str):
        errors.append(ParseError(
            code="invalid_type",
            field_path="status.next_gate",
            expected="string or null",
            actual=type(status["next_gate"]).__name__
        ))
    elif status["next_gate"] not in gate_config.gate_order:
        errors.append(ParseError(
            code="invalid_gate_key",
            field_path="status.next_gate",
            expected=f"one of {gate_config.gate_order}",
            actual=status["next_gate"]
        ))
```

## Canonicalization Requirements

**Apply to all string values:**

1. **Trim whitespace**: Remove leading/trailing whitespace, preserve internal
2. **Empty string → None**: Convert `""` to `None` for gate values (but NOT for summary)
3. **Ensure fields exist**: Add missing `raw`/`classified` as `None` based on gate mode

**Algorithm:**
```python
def canonicalize_state(data: Dict, gate_config: GateConfig) -> GateState:
    # 1. Canonicalize summary
    summary = data.get("summary", "")
    if isinstance(summary, str):
        summary = summary.strip()
        # Keep empty string for summary (don't convert to None)
    else:
        summary = ""
    
    # 2. Canonicalize gates
    canonical_gates = {}
    for gate_key in gate_config.gate_order:
        gate_def = gate_config.gates[gate_key]
        gate_data = data.get("gates", {}).get(gate_key, {})
        
        # Raw
        raw = gate_data.get("raw")
        if isinstance(raw, str):
            raw = raw.strip()
            raw = None if raw == "" else raw
        else:
            raw = None
        
        # Classified
        classified = gate_data.get("classified")
        if isinstance(classified, str):
            classified = classified.strip()
            classified = None if classified == "" else classified
            # Validate against expected_categories
            if classified and gate_def.expected_categories:
                if classified not in gate_def.expected_categories:
                    classified = None  # Invalid category → set to None
        else:
            classified = None
        
        canonical_gates[gate_key] = GateValue(raw=raw, classified=classified)
    
    # 3. Canonicalize status (will be recomputed, but preserve LLM values for now)
    status_data = data.get("status", {})
    status = StatusInfo(
        pass=status_data.get("pass", False),
        next_gate=status_data.get("next_gate"),
        next_query=status_data.get("next_query", "").strip() if status_data.get("next_query") else None
    )
    
    return GateState(summary=summary, gates=canonical_gates, status=status)
```

## Deterministic Decision Recomputation (System-Owned)

**Parser MUST compute and overwrite `status.pass`, `status.next_gate`, `status.next_query`**

**Algorithm:**
```python
def compute_decision(
    canonical_state: GateState,
    gate_config: GateConfig
) -> GateDecision:
    """
    Per MANDATORY_LOGIC step 5-7:
    - Find FIRST missing REQUIRED gate in gate_order
    - Gate is missing if: required=true AND classified is null
    - If found → NO PASS + next_question from GateConfig
    - Else → PASS + null next question
    """
    
    # Find first missing required gate
    for gate_key in gate_config.gate_order:
        gate_def = gate_config.gates[gate_key]
        gate_value = canonical_state.gates.get(gate_key)
        
        # Gate is missing if required and classified is null
        if gate_def.required:
            if gate_value is None or gate_value.classified is None:
                # Found missing required gate
                return GateDecision(
                    pass_=False,
                    reason="required_missing",
                    next_gate=gate_key,
                    next_question=gate_def.question
                )
    
    # All required gates have classified values
    return GateDecision(
        pass_=True,
        reason="all_required_complete",
        next_gate=None,
        next_question=None
    )
```

**Apply to canonical_state:**
```python
decision = compute_decision(canonical_state, gate_config)
canonical_state.status.pass = decision.pass_
canonical_state.status.next_gate = decision.next_gate
canonical_state.status.next_query = decision.next_question
```

## Diff Computation (System-Owned)

**Compare `previous_state` to `canonical_state`:**

**Algorithm:**
```python
def compute_diff(
    previous_state: Optional[GateState],
    canonical_state: GateState,
    actor: Literal["user", "assistant"]
) -> Optional[GateDiff]:
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
```

## Error Handling

### Error Codes

1. **`invalid_json`**: JSON parsing failed or no JSON found
2. **`missing_key`**: Required top-level key missing (summary, gates, status)
3. **`invalid_type`**: Value has wrong type (e.g., summary is dict instead of string)
4. **`invalid_value`**: Value violates constraints (e.g., summary > 200 chars)
5. **`invalid_key`**: Gate key not in GateConfig
6. **`missing_required_gate`**: Required gate key missing from gates dict
7. **`invalid_category`**: Classified value doesn't match expected_categories
8. **`invalid_gate_key`**: status.next_gate doesn't match any gate in gate_order
9. **`deletion_not_allowed`**: Required gate deleted but policy doesn't allow
10. **`schema_version_mismatch`**: Schema version incompatible (if versioning implemented)

### Error Collection

- Collect ALL errors (don't stop at first error)
- Return structured `ParseError` objects
- No stack traces in normal control flow
- Log errors for debugging but don't include in ParseResult

**Example:**
```python
errors = []
# ... validation code that appends to errors ...

if errors:
    return ParseResult(
        ok=False,
        canonical_state=None,
        decision=None,
        diff=None,
        errors=errors
    )
```

## Acceptance Tests

### Test 1: LLM returns invalid JSON
**Input**: `payload = "This is not JSON"`
**Expected**: `ParseResult(ok=False, errors=[ParseError(code="invalid_json")])`

### Test 2: LLM returns partial JSON missing gates
**Input**: `payload = '{"summary": "test", "gates": {}, "status": {"pass": false}}'`
**Expected**: 
- If actor="assistant": `ParseResult(ok=False, errors=[ParseError(code="missing_required_gate", field_path="gates.1_data_availability")])`
- If actor="user": May be ok if policy allows partial

### Test 3: User clears a value
**Input**: `payload = {"gates": {"1_data_availability": {"raw": null, "classified": null}}}`
**Expected**: 
- `canonical_state.gates["1_data_availability"].raw = None`
- `canonical_state.gates["1_data_availability"].classified = None`
- `diff.gates_raw_changed = ["1_data_availability"]` (if was previously set)

### Test 4: PASS/NO PASS is consistent
**Input**: LLM claims `status.pass = true` but required gates missing
**Expected**: 
- Parser overwrites `status.pass = false`
- `decision.pass_ = false`
- `decision.reason = "required_missing"`
- `status.next_gate` and `status.next_query` set to first missing required gate

### Test 5: Classified value doesn't match expected_categories
**Input**: `payload = {"gates": {"2_use_case": {"classified": "InvalidCategory"}}}`
**Expected**:
- Option A (strict): `ParseResult(ok=False, errors=[ParseError(code="invalid_category")])`
- Option B (lenient): `canonical_state.gates["2_use_case"].classified = None` (set to None)

### Test 6: Empty string canonicalization
**Input**: `payload = {"gates": {"1_data_availability": {"raw": "   ", "classified": ""}}}`
**Expected**:
- `canonical_state.gates["1_data_availability"].raw = None`
- `canonical_state.gates["1_data_availability"].classified = None`

### Test 7: Summary empty string preserved
**Input**: `payload = {"summary": ""}`
**Expected**: `canonical_state.summary = ""` (NOT None)

### Test 8: All required gates complete
**Input**: All required gates have `classified` values
**Expected**: 
- `decision.pass_ = True`
- `decision.reason = "all_required_complete"`
- `status.next_gate = None`
- `status.next_query = None`

## Implementation Notes

### Gate Mode Inference

Since prompt format doesn't have explicit `mode`, infer from `expected_categories`:
- If `expected_categories` is non-empty → `classified_required` mode
- If `expected_categories` is empty → `raw_required` mode

### Policy Object

If `GateConfig` doesn't have explicit `policy`, use defaults:
```python
class Policy:
    allow_user_delete_gate_keys: bool = False
    allow_user_clear_values: bool = True
    strict_classified_validation: bool = True  # Error vs set to None
```

### Schema Version

If `GateConfig` has `schema_version`, validate compatibility:
- Current parser supports version "1.0"
- Future versions may require migration logic

## File Structure

```
nexus/core/
  json_parser.py  # Extend existing or create new
  gate_models.py  # GateState, GateValue, StatusInfo, etc.
```

## Dependencies

- `nexus.core.gate_models` (GateConfig, GateState, GateValue, etc.)
- Standard library: `json`, `re`, `typing`

## Usage Example

```python
from nexus.core.json_parser import GateJsonParser
from nexus.core.gate_models import GateConfig, GateState

parser = GateJsonParser()

# Parse LLM output
result = parser.parse(
    payload=llm_response_text,
    gate_config=gate_config,
    previous_state=previous_state,
    actor="assistant"
)

if result.ok:
    # Use canonical state
    current_state = result.canonical_state
    decision = result.decision
    changes = result.diff
    
    # Check what changed
    if result.diff.gates_classified_changed:
        print(f"Updated gates: {result.diff.gates_classified_changed}")
else:
    # Handle errors
    for error in result.errors:
        print(f"Error: {error.code} at {error.field_path}: {error.message}")
```








