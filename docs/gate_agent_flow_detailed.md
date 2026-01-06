# Gate Agent Flow - Detailed Documentation

## Overview

The gate agent follows a **4-step flow** to process user input and collect gate-based information. The flow is modular, with each step handling a specific responsibility.

## Architecture

```
append_message()
    ↓
Step 0: Load Gate Config & State
    ↓
Step 1: Set Current Gate
    ↓
Step 2: Determine Pass/Fail Status
    ↓
Step 3: Set Next Question
    ↓
Step 4: Establish Buttons & Update Status
    ↓
Return to Orchestrator
```

---

## Step 0: Load Gate Config & State

**Purpose**: Load the gate configuration and previous gate state from the database.

**What happens**:
- Loads gate configuration from JSON file (e.g., `gate_prompt_tabula_rasa.json`)
- Loads previous `GateState` from database (if exists)
- Prepares context for subsequent steps

**Output**: `gate_config`, `previous_state`

---

## Step 1: Set Current Gate

**Purpose**: Determine which gate to process based on the current state.

**Returns**: `(current_gate, should_exit, exit_result)`

### Case 1.1: First Time (No Previous State)

**Condition**: `previous_state is None` OR `previous_state.gates is empty`

**Flow**:
1. Set `current_gate = gate_config.gate_order[0]` (first gate)
2. Return `(first_gate, False, None)`

**Example**:
- User starts new session
- `current_gate = "1_patient_info_availability"`

---

### Case 1.2: Awaiting Confirmation

**Condition**: 
- `previous_state.status.pass_ == False`
- `previous_state.status.next_gate == None`
- `len(previous_state.gates) > 0`

**Sub-cases**:

#### Case 1.2.1: User Confirms

**User Input**: Contains confirmation phrases ("okay", "ok", "yes", "correct", "proceed", etc.)

**Flow**:
1. Detect confirmation in user text
2. Create confirmed state: `pass_=True`, `next_gate=None`
3. Save state to database
4. Emit `HANDOFF` artifact to planner
5. Return `(None, True, exit_result)` with `completion_status.ready_for_handoff=True`

**Example**:
- All gates answered, user sees summary
- User types: "Yes, that's correct"
- → Workflow completes, hands off to planner

---

#### Case 1.2.2: User Wants to Edit

**User Input**: Contains edit phrases ("edit", "change", "wrong", "no", etc.) OR any non-confirmation text

**Flow**:
1. Detect edit request (or non-confirmation)
2. Reset confirmation state: `pass_=False`
3. Determine `next_gate`:
   - Use `previous_state.status.next_gate` if available
   - Else find first missing gate (gate without classified value)
   - Else default to first gate
4. Save reset state
5. Return `(next_gate, False, None)`

**Example**:
- All gates answered, user sees summary
- User types: "Edit" or "That's wrong"
- → Reset to allow editing, set `current_gate` to appropriate gate

---

### Case 1.3: Normal Flow (Gates In Progress)

**Condition**: Not first time, not awaiting confirmation

**Flow**:
1. Use `previous_state.status.next_gate` as `current_gate`
2. If `current_gate is None`:
   - Check if in confirmation state (gates complete but not confirmed)
   - If yes, reset to gate 1 (start fresh)
   - Else default to first gate
3. Return `(current_gate, False, None)`

**Example**:
- Gate 1 answered, Gate 2 is next
- `current_gate = "2_insurance_history"`

---

## Step 2: Determine Pass/Fail Status

**Purpose**: Process user input for the current gate, extract value, check for limiting values.

**Returns**: `(gate_result, should_stop, stop_result, state_already_saved)`

**Input Types**:
- **Button Click**: User clicked a button (has `original_value` in transcript)
- **Text Input**: User typed free-form text

---

### Case 2.1: Gate 1 (Special Handling)

**Condition**: `current_gate == gate_config.gate_order[0]`

**Flow**:
1. **Skip LLM** - Always use direct matching
2. Check if user input matches `expected_categories` (case-insensitive)
3. If match found:
   - Set gate value with `confidence=1.0`
   - **Check limiting_values**: If matched category is in `limiting_values`:
     - Create stop state
     - Save state
     - Return `(None, True, stop_result, True)` → **Workflow stops**
   - Else:
     - Calculate next gate
     - Save state
     - Return `(gate_result, False, None, True)`

**Example**:
- Gate 1: "Do we have patient information?"
- User clicks "No" or types "No"
- "No" is in `limiting_values` → Workflow stops with stop message

---

### Case 2.2: Button Click (Gates 2+)

**Condition**: `is_button_click == True` (has `original_value`)

**Flow**:
1. **Check limiting_values first**:
   - If button value matches `limiting_values`:
     - Create stop state
     - Save state
     - Return `(None, True, stop_result, True)` → **Workflow stops**
2. **Else, use direct matching**:
   - Check if button value matches `expected_categories`
   - If match:
     - Set gate value with `confidence=1.0`
     - Calculate next gate
     - Save state
     - Return `(gate_result, False, None, True)`

**Example**:
- Gate 2: "Does patient have insurance history?"
- User clicks "No"
- "No" is not in `limiting_values` → Continue to next gate

---

### Case 2.3: Text Input (Gates 2+)

**Condition**: `is_button_click == False` (free-form text)

**Flow**:
1. **Call LLM** to extract gate value from text
2. **After LLM extraction**, check all gates for `limiting_values`:
   - Iterate through all gates in config
   - If any gate has a value in `limiting_values`:
     - Create stop state
     - Save state
     - Return `(gate_result, True, stop_result, True)` → **Workflow stops**
3. **Else**, continue:
   - Return `(gate_result, False, None, False)`

**Example**:
- Gate 2: "Does patient have insurance history?"
- User types: "I'm not sure, but I think there might be some issues"
- LLM extracts: "Yes" or "Partial"
- Check limiting_values → Continue

---

### Case 2.4: Extraction Failure

**Condition**: `gate_result is None` after LLM call

**Flow**:
- Return `(None, False, None, False)`
- Step 3 will handle error message

---

## Step 3: Set Next Question

**Purpose**: Determine what message/question to send to the user.

**Returns**: `raw_message` (string)

---

### Case 3.1: Extraction Failed

**Condition**: `extraction_failed == True` (gate_result is None)

**Flow**:
- Return error message: "I'm having trouble understanding your response. Could you please rephrase or select one of the options?"

---

### Case 3.2: Gate Failed (Limiting Value)

**Condition**: `gate_failed == True` (limiting value matched)

**Flow**:
- Return stop message from gate config (`gate_def.stop_message`)
- **Note**: This case should rarely be reached, as Step 2 returns early with `stop_result`

---

### Case 3.3: All Gates Complete (Awaiting Confirmation)

**Condition**: `gate_result.pass_ == True`

**Flow**:
1. Build dynamic summary:
   - Problem statement
   - All gate questions and answers
   - "Please review the information above. Is this correct?"
2. Emit `PROBLEM_STATEMENT` artifact
3. Update draft plan with problem statement
4. Return summary message

**Example Output**:
```
## Summary of Collected Information

**Problem Statement:** [summary]

**Your Answers:**

**Do we have patient information available?**
→ Yes (from: "Yes")

**Does the patient have insurance history?**
→ No (from: "No")

---

**Please review the information above.**

Is this correct?
```

---

### Case 3.4: Next Gate Question

**Condition**: `gate_result.pass_ == False` (gates not complete)

**Flow**:
- Format next gate question using `_format_gate_response()`
- Return formatted question text

**Example**:
- Gate 2 is next
- Return: "Does the patient have a known history of inconsistencies in their insurance coverage?"

---

## Step 4: Establish Buttons & Update Status

**Purpose**: Build buttons for user interaction and determine completion status.

**Returns**: `(buttons, button_context, button_metadata, completion_status)`

---

### Case 4.1: Gates Complete (Awaiting Confirmation)

**Condition**: `gate_result.pass_ == True`

**Flow**:
1. Build confirmation buttons from config:
   - "Looks Good" (confirms)
   - "Edit Answers" (edits)
2. Set `button_context = "gate_confirmation"`
3. Set `completion_status`:
   - `is_complete = False` (not complete until user confirms)
   - `completion_reason = "awaiting_user_confirmation"`
   - `ready_for_handoff = False`
4. **Save state with `pass_=False`** (awaiting confirmation)
5. Return buttons and status

**Example**:
- All gates answered
- Buttons: ["Looks Good", "Edit Answers"]
- State saved with `pass_=False`, `next_gate=None`

---

### Case 4.2: Next Gate Has Expected Categories

**Condition**: `gate_result.next_gate` exists AND has `expected_categories`

**Flow**:
1. Build gate buttons from config for `next_gate`
2. Set `button_context = "gate_question"`
3. Set `button_metadata = {"gate_key": next_gate}`
4. Set `completion_status`:
   - `is_complete = False`
   - `completion_reason = gate_result.decision`
   - `ready_for_handoff = False`
5. Return buttons and status

**Example**:
- Gate 2 is next
- Gate 2 has `expected_categories = ["Yes", "No", "Partial"]`
- Buttons: ["Yes", "No", "Partial"]

---

### Case 4.3: No Buttons

**Condition**: No next gate OR next gate has no `expected_categories`

**Flow**:
- Return `(None, None, None, completion_status)`

---

## Complete Flow Examples

### Example 1: Happy Path (All Gates Answered)

1. **Step 0**: Load config, no previous state
2. **Step 1**: First time → `current_gate = "1_patient_info_availability"`
3. **Step 2**: Gate 1, user clicks "Yes" → Direct match, not limiting → `gate_result.pass_=False`, `next_gate="2_insurance_history"`
4. **Step 3**: Next gate question → "Does the patient have insurance history?"
5. **Step 4**: Build buttons for Gate 2 → ["Yes", "No", "Partial"]
6. **User clicks "No"**
7. **Step 1**: Normal flow → `current_gate = "2_insurance_history"`
8. **Step 2**: Button click, not limiting → `gate_result.pass_=True` (all gates complete)
9. **Step 3**: All gates complete → Show summary
10. **Step 4**: Confirmation buttons → ["Looks Good", "Edit Answers"]
11. **User clicks "Looks Good"**
12. **Step 1**: Awaiting confirmation, user confirms → Exit with `ready_for_handoff=True`

---

### Example 2: Early Stop (Limiting Value)

1. **Step 0**: Load config, no previous state
2. **Step 1**: First time → `current_gate = "1_patient_info_availability"`
3. **Step 2**: Gate 1, user clicks "No" → Direct match, "No" in `limiting_values` → **Stop workflow**
4. **Return**: Stop message from config, `is_complete=True`, `ready_for_handoff=False`

---

### Example 3: Edit After Confirmation

1. **Step 0**: Load config, previous state exists (all gates answered, awaiting confirmation)
2. **Step 1**: Awaiting confirmation, user types "Edit" → Reset state, find first gate → `current_gate = "1_patient_info_availability"`
3. **Step 2**: Gate 1, user types "Yes" → Direct match → Continue
4. **Step 3**: Next gate question
5. **Step 4**: Build buttons for next gate

---

### Example 4: Text Input (Not Button Click)

1. **Step 0**: Load config, previous state exists
2. **Step 1**: Normal flow → `current_gate = "2_insurance_history"`
3. **Step 2**: Text input → Call LLM → Extract value → Check limiting_values → Continue
4. **Step 3**: Next gate question or summary
5. **Step 4**: Build buttons or confirmation buttons

---

## State Transitions

### Gate State Fields

- `gates`: Dict of `{gate_key: GateValue}` - Collected gate values
- `status.pass_`: Boolean - True if all gates answered (may be awaiting confirmation)
- `status.next_gate`: String or None - Next gate to ask, or None if complete
- `status.next_query`: String or None - Next question text

### State Transitions

1. **Initial**: `gates={}`, `pass_=False`, `next_gate="1_patient_info_availability"`
2. **Gate 1 Answered**: `gates={"1_patient_info_availability": GateValue(...)}`, `pass_=False`, `next_gate="2_insurance_history"`
3. **All Gates Answered**: `gates={...}`, `pass_=False`, `next_gate=None` (awaiting confirmation)
4. **User Confirmed**: `gates={...}`, `pass_=True`, `next_gate=None` (ready for handoff)
5. **Workflow Stopped**: `gates={...}`, `pass_=True`, `next_gate=None` (limiting value)

---

## Key Design Decisions

1. **Gate 1 Special Handling**: Always uses direct matching, never calls LLM (performance optimization)
2. **Button Clicks vs Text**: Button clicks bypass LLM (direct matching), text input uses LLM
3. **Limiting Values Check**: Happens at multiple points:
   - Gate 1: After direct match
   - Button clicks: Before direct match
   - Text input: After LLM extraction
4. **Confirmation State**: Gates are marked complete (`pass_=True`) but then reset to `pass_=False` when awaiting confirmation
5. **State Saving**: State is saved:
   - After direct matches (immediately)
   - After LLM extraction (if not already saved)
   - When awaiting confirmation (with `pass_=False`)
   - When workflow stops (with `pass_=True`)

---

## Error Handling

1. **Extraction Failure**: Step 3 returns error message, user can retry
2. **Missing Gate Config**: Returns early with error
3. **Invalid Gate Key**: Returns early with error
4. **Database Errors**: Logged, may cause state inconsistency (should be handled by retry logic)

---

## Testing Scenarios

1. ✅ First time user → Gate 1 question
2. ✅ Button click → Direct match, continue
3. ✅ Text input → LLM extraction, continue
4. ✅ Limiting value (Gate 1) → Stop workflow
5. ✅ Limiting value (Gate 2+) → Stop workflow
6. ✅ All gates answered → Show summary, confirmation buttons
7. ✅ User confirms → Handoff to planner
8. ✅ User edits → Reset to appropriate gate
9. ✅ Extraction failure → Error message, retry
10. ✅ Edit after confirmation → Reset state, continue

---

## File References

- **Main Logic**: `nexus/modules/shaping_manager.py`
  - `append_message()`: Main entry point
  - `_step1_set_current_gate()`: Step 1
  - `_step2_determine_pass_fail()`: Step 2
  - `_step3_set_next_question()`: Step 3
  - `_step4_establish_buttons()`: Step 4

- **Gate Engine**: `nexus/brains/gate_engine.py`
  - `execute_gate()`: LLM extraction for text input

- **Gate Models**: `nexus/core/gate_models.py`
  - `GateState`, `GateValue`, `StatusInfo`, `GateConfig`

- **Gate Config**: `nexus/configs/gate_prompt_tabula_rasa.json`
  - Gate definitions, questions, expected categories, limiting values

