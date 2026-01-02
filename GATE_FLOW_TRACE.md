# Gate Engine Flow Trace
## Query: "can i check medicaid eligibility for this patient"

### Step-by-Step Execution Trace

#### 1. Frontend Request
```
POST /api/workflows/shaping/start
{
  "query": "can i check medicaid eligibility for this patient",
  "user_id": "user_123"
}
```

#### 2. Orchestrator.start_shaping_session()
- Calls: `shaping_manager.create_session("user_123", "can i check medicaid eligibility for this patient")`

#### 3. ShapingManager.create_session()

**3.1 Resolve Model Context**
- Calls: `config_manager.resolve_app_context("workflow", "user_123")`
- Returns: `{model_id: "gemini-1.5-pro", ...}`

**3.2 Decide Strategy**
- Calls: `consultant_brain.decide_strategy("can i check medicaid eligibility for this patient")`
- Returns: `{strategy: "TABULA_RASA", reasoning: "...", context: {manuals: [], history: []}}`

**3.3 Load Gate Config** ⚠️ **CRITICAL STEP**
- Calls: `_load_gate_config("TABULA_RASA", session_id=None)`
- Which calls: `prompt_manager.get_prompt(module_name="workflow", domain="eligibility", mode="TABULA_RASA", step="gate")`
- **Expected prompt key**: `workflow:eligibility:TABULA_RASA:gate`
- **Database query**:
  ```sql
  SELECT prompt_config, version, description 
  FROM prompt_templates 
  WHERE prompt_key = 'workflow:eligibility:TABULA_RASA:gate' 
    AND is_active = true
  ORDER BY version DESC
  LIMIT 1
  ```

**Possible Outcomes:**

**A. Prompt NOT FOUND** ❌
- `prompt_data = None`
- `gate_config = None`
- **Error raised**: `ValueError("Gate config not found for strategy 'TABULA_RASA'. Prompt must have GATE_ORDER and GATES defined.")`
- **Result**: Request fails with 500 error

**B. Prompt FOUND but NO GATE_ORDER** ❌
- `prompt_data` exists but `config.get("GATE_ORDER")` is missing
- `gate_config = None`
- **Error raised**: Same ValueError as above
- **Result**: Request fails with 500 error

**C. Prompt FOUND with GATE_ORDER** ✅
- `prompt_data` exists
- `config.get("GATE_ORDER")` exists (e.g., `["1_data_availability", "2_use_case", "3_edge_case"]`)
- `config.get("GATES")` exists
- `GateConfig.from_prompt_config(config)` creates GateConfig object
- **Continues to next step**

**3.4 Execute Gate Engine** (if prompt found)
- Calls: `gate_engine.execute_gate(...)`
  ```python
  gate_result = await self.gate_engine.execute_gate(
      user_text="can i check medicaid eligibility for this patient",
      gate_config=gate_config,  # From step 3.3
      previous_state=None,      # First turn
      actor="user",
      session_id=None,          # Not created yet
      user_id="user_123"
  )
  ```

**3.4.1 Build Extraction Prompt**
- `_build_extraction_prompt()` creates prompt with:
  - System instructions from `gate_config.system_instructions`
  - LLM role from `gate_config.llm_role`
  - Current gate state: "(empty - starting fresh)"
  - User input: "can i check medicaid eligibility for this patient"
  - Task instructions
  - Output format: `gate_config.strict_json_schema`
  - Mandatory logic from `gate_config.mandatory_logic`

**3.4.2 Call LLM**
- `_call_llm()`:
  - Resolves model context: `config_manager.resolve_app_context("workflow", "user_123")`
  - **Note**: `session_id=None`, so enriched thinking is NOT emitted yet
  - Calls: `llm_service.generate_text(prompt=llm_prompt, ...)`
  - LLM returns JSON response (expected format):
    ```json
    {
      "summary": "User wants to check Medicaid patient eligibility",
      "gates": {
        "1_data_availability": {
          "raw": "can i check medicaid eligibility for this patient",
          "classified": null
        },
        "2_use_case": {
          "raw": null,
          "classified": null
        },
        "3_edge_case": {
          "raw": null,
          "classified": null
        }
      },
      "status": {
        "pass": false,
        "next_gate": "1_data_availability",
        "next_query": "Do you have the necessary information to check eligibility?"
      }
    }
    ```

**3.4.3 Parse LLM Response**
- `GateJsonParser.parse()`:
  - Extracts JSON from response
  - Validates against `strict_json_schema`
  - Canonicalizes (trims strings, converts empty to null)
  - Computes deterministic decision:
    - Finds first missing required gate: `1_data_availability`
    - Sets `status.pass = false`
    - Sets `status.next_gate = "1_data_availability"`
    - Sets `status.next_query = "Do you have the necessary information to check eligibility?"`

**3.4.4 Merge State**
- Previous state: `None` (first turn)
- Parsed state: LLM response
- Result: New `GateState` with extracted values

**3.4.5 Select Next Gate**
- Deterministic: Finds first missing required gate
- Returns: `"1_data_availability"`

**3.4.6 Check Completion**
- Required gates missing → `pass_ = False`
- Decision: `FAIL_REQUIRED_MISSING`

**3.4.7 Return Result**
```python
ConsultantResult(
    decision=GateDecision.FAIL_REQUIRED_MISSING,
    pass_=False,
    next_gate="1_data_availability",
    next_question="Do you have the necessary information to check eligibility?",
    proposed_state=GateState(...),
    updated_gates=["1_data_availability"]
)
```

**3.5 Format Response**
- `_format_gate_response()` creates:
  ```
  **User wants to check Medicaid patient eligibility**
  
  **Question:** Do you have the necessary information to check eligibility?
  
  *Gathering information: 1_data_availability*
  ```

**3.6 Create Session in Database**
- Inserts into `shaping_sessions`:
  ```sql
  INSERT INTO shaping_sessions (
    user_id, status, transcript, draft_plan, 
    consultant_strategy, rag_citations, 
    consultant_iteration_count, max_iterations,
    gate_state
  )
  VALUES (
    'user_123', 'GATHERING', 
    '[{"role":"user","content":"can i check medicaid eligibility..."}, ...]',
    '{}',
    'TABULA_RASA',
    '[]',
    1, 15,
    '{"summary":"User wants to check Medicaid patient eligibility","gates":{"1_data_availability":{"raw":"can i check medicaid eligibility...","classified":null}},"status":{"pass":false,"next_gate":"1_data_availability","next_query":"Do you have the necessary information to check eligibility?"}}'
  )
  RETURNING id
  ```
- Gets `session_id` (e.g., 66)

**3.7 Backfill Thinking Emissions**
- Sets `agent.session_id = 66`
- Emits thinking messages
- **Note**: Gate Engine's LLM thinking was NOT emitted (session_id was None)
- Future enhancement: Could backfill gate engine thinking after session creation

**3.8 Return Session ID**
- Returns: `66`

#### 4. Orchestrator Continues
- Diagnosis brain analyzes query
- Returns candidates
- Returns response to frontend:
  ```json
  {
    "session_id": 66,
    "candidates": [...],
    "transcript": [
      {
        "role": "user",
        "content": "can i check medicaid eligibility for this patient"
      },
      {
        "role": "system",
        "content": "**User wants to check Medicaid patient eligibility**\n\n**Question:** Do you have the necessary information to check eligibility?"
      }
    ],
    "system_intro": "Session Initialized"
  }
  ```

---

## Expected Behavior Summary

### ✅ Success Path (if prompt exists)
1. Prompt loaded: `workflow:eligibility:TABULA_RASA:gate`
2. Gate Engine executes
3. LLM extracts initial gate values
4. System asks first question: "Do you have the necessary information to check eligibility?"
5. Session created with `gate_state` stored
6. Frontend receives response with question

### ❌ Failure Path (if prompt missing)
1. Prompt lookup fails: `workflow:eligibility:TABULA_RASA:gate` not found
2. `ValueError` raised: "Gate config not found for strategy 'TABULA_RASA'..."
3. Request fails with 500 error
4. Frontend receives error response

---

## What to Check

1. **Database**: Does prompt exist?
   ```sql
   SELECT prompt_key, is_active 
   FROM prompt_templates 
   WHERE prompt_key = 'workflow:eligibility:TABULA_RASA:gate';
   ```

2. **Prompt Structure**: Does it have GATE_ORDER?
   ```sql
   SELECT prompt_config->'GATE_ORDER' 
   FROM prompt_templates 
   WHERE prompt_key = 'workflow:eligibility:TABULA_RASA:gate';
   ```

3. **Migration**: Has migration 015 been run? (adds gate_state column)

4. **Logs**: Check for:
   - `[PROMPT_MANAGER] Looking for key: 'workflow:eligibility:TABULA_RASA:gate'`
   - `[GATE_ENGINE] execute_gate | Actor: user`
   - Any ValueError messages

