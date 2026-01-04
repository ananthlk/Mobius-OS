# Eligibility Check Workflow - Step-by-Step Walkthrough

This document describes what happens when you start the server and check for eligibility, including what you'll see in the frontend and server logs.

## Prerequisites

1. **Start the server:**
   ```bash
   cd "/Users/ananth/Personal AI Projects/Mobius OS"
   ./MobiusOSRun
   # Or manually:
   # uvicorn nexus.app:app --host 0.0.0.0 --port 8000 --reload
   ```

2. **Ensure database migrations are run:**
   ```bash
   # Migration 026 should be applied
   # Visit: http://localhost:8000/api/system/migrate
   ```

3. **Seed the prompts (if not already done):**
   ```bash
   python nexus/scripts/seed_bounded_plan_prompts.py
   ```

4. **Seed test patients (recommended for consistent testing):**
   ```bash
   python nexus/scripts/seed_test_patients.py
   ```
   
   This creates 8 pre-defined test patients:
   - **TEST001-TEST005**: Standard patients (all views available)
   - **TEST006**: Missing EMR view (tests unavailable data handling)
   - **TEST007**: Missing Health Plan view
   - **TEST008**: Missing System view
   
   **Note:** Patient generation is **dynamic** - if you provide a name that doesn't exist, the system will automatically generate a patient profile. The seed script just creates known test patients for consistent testing.

---

## Step-by-Step Flow

### **STEP 1: Server Startup**

**Server Logs:**
```
🌀 Awakening Mobius OS...
   [1/4] Clearing neural pathways (Ports 3000, 8000)...
   [2/4] Checking emotional memory (PostgreSQL)...
   [3/4] Ignition: Nexus (Brain)...
   [4/4] Opening eyes: Portal (Interface)...
✨ Mobius is Online.
   -> Portal: http://localhost:3000
   -> Nexus: http://localhost:8000
```

**What happens:**
- FastAPI server starts on port 8000
- Frontend (Next.js) starts on port 3000
- Database connection established
- Routers registered (including `user_profile_router`)

---

### **STEP 2: User Initiates Eligibility Check**

**Frontend:**
- User navigates to workflow builder
- User types: "I need to check eligibility for a patient"
- User clicks "Diagnose" or presses Enter

**API Call:**
```
POST /api/workflows/shaping/start
Body: {
  "query": "I need to check eligibility for a patient",
  "user_id": "user_123"
}
```

**Server Logs:**
```
[PlanningPhaseBrain.announce_planning_phase_start] ENTRY | session_id=1, user_id=user_123
[ShapingManager.create_session] Creating new session for user_123
[WorkflowOrchestrator.start_shaping_session] ENTRY | user_id=user_123, query=I need to check eligibility...
[ConsultantBrain.diagnose] Analyzing query...
[PlannerBrain.update_draft_plan] Generating draft plan...
```

**Frontend Response:**
- Session created with `session_id`
- User sees chat interface with initial response
- Left rail shows draft plan (if available)

---

### **STEP 3: Gate Phase (Consultant Phase)**

**What happens:**
- Consultant brain asks clarifying questions
- Gate engine collects required information
- Draft plan is generated and stored

**Server Logs:**
```
[GateEngine.process_gate] Processing gate: patient_info
[ConsultantBrain.clarify] Asking question: What is the patient's name?
[PlannerBrain.update_draft_plan] Draft plan updated with gates
```

**Frontend:**
- User sees questions in chat
- User answers questions
- Draft plan appears in left rail with gates and steps

**Database:**
```sql
-- shaping_sessions table updated:
draft_plan = {
  "name": "Eligibility Verification",
  "goal": "Verify member eligibility",
  "gates": [
    {
      "id": "gate_1",
      "steps": [
        {"id": "step_1", "description": "Get patient information", ...},
        {"id": "step_2", "description": "Check eligibility status", ...}
      ]
    }
  ]
}
```

---

### **STEP 4: Planning Phase Announcement**

**When:** After gate phase completes (all gates passed)

**Server Logs:**
```
[PlanningPhaseBrain.announce_planning_phase_start] ENTRY | session_id=1, user_id=user_123
[PlanningPhaseBrain.announce_planning_phase_start] EXIT | Announcement complete
[WorkflowOrchestrator._format_emit_and_persist] ENTRY | session_id=1
[WorkflowOrchestrator._format_emit_and_persist] System/button-generated message - skipping conversational agent
[WorkflowOrchestrator._format_emit_and_persist] EXIT | Message persisted to transcript
```

**Frontend:**
- User sees message: **"🎯 Planning Phase Started - We've gathered all the information we need. Now let's build your workflow plan. What would you like to do next?"**
- User sees **4 buttons**:
  1. "I have an existing saved workflow that I would like to execute" (disabled)
  2. **"I want to create a new workflow"** (primary, enabled) ← User clicks this
  3. "Guide me" (disabled)
  4. "Refine my answers (reinvoke gate stage)" (disabled)

---

### **STEP 5: User Clicks "Create New Workflow"**

**Frontend:**
- Button click triggers API call

**API Call:**
```
POST /api/workflows/shaping/{session_id}/planning-phase/decision
Body: {
  "choice": "create_new",
  "user_id": "user_123"
}
```

**Server Logs:**
```
[PlanningPhaseBrain.handle_build_reuse_decision] ENTRY | session_id=1, choice=create_new
[PlanningPhaseBrain.handle_build_reuse_decision] STARTING_BOUNDED_PLAN | session_id=1
[PlanningPhaseBrain.handle_build_reuse_decision] LOADED_CONTEXT | draft_plan_gates=1, tasks=5, tools=12
[BoundedPlanBrain.start_session] ENTRY | session_id=1, draft_plan_keys=['name', 'goal', 'gates'], tools_count=12
[BoundedPlanBrain.start_session] STATE_CREATED | known_fields=0, context_keys=['draft_plan_summary']
[BoundedPlanBrain.start_session] CALLING_develop_bound_plan | initial_call
[BoundedPlanBrain.develop_bound_plan] ENTRY | session_id=1, draft_plan_steps=2, tools_count=12, known_fields=0
[BoundedPlanBrain.develop_bound_plan] BUILDING_INPUT | known_fields=0, blockers=0
[BoundedPlanBrain.develop_bound_plan] RETRIEVING_PROMPT | step=bounded_plan_builder
[PROMPT_MANAGER] get_prompt | Looking for key: 'workflow:eligibility:TABULA_RASA:bounded_plan_builder'
[PROMPT_MANAGER] Found prompt for key 'workflow:eligibility:TABULA_RASA:bounded_plan_builder' | Version: 1
[BoundedPlanBrain.develop_bound_plan] PROMPT_RETRIEVED | prompt_config_keys=['ROLE', 'CONTEXT', 'ANALYSIS', 'OUTPUT', 'CONSTRAINTS']
[BoundedPlanBrain.develop_bound_plan] BUILDING_PROMPT | using_PromptBuilder
[BoundedPlanBrain.develop_bound_plan] PROMPT_BUILT | system_prompt_length=2847
[BoundedPlanBrain.develop_bound_plan] GETTING_MODEL_CONTEXT | module=workflow
[BoundedPlanBrain.develop_bound_plan] MODEL_CONTEXT_RETRIEVED | model_id=gemini-1.5-flash
[BoundedPlanBrain.develop_bound_plan] CALLING_LLM | prompt_length=2847
[BoundedPlanBrain.develop_bound_plan] LLM_RESPONSE | response_length=1234, first_100_chars={"meta":{"plan_id":"eligibility_verification","workflow":"Verify member eligibility","phase":"BOUND"
[BoundedPlanBrain.develop_bound_plan] PARSING_JSON | starting_parse
[BoundedPlanBrain._parse_bound_plan_response] ENTRY | response_length=1234
[BoundedPlanBrain._parse_bound_plan_response] FOUND_CODE_BLOCK | length=1200
[BoundedPlanBrain._parse_bound_plan_response] PARSED_FROM_CODE_BLOCK | success
[BoundedPlanBrain.develop_bound_plan] JSON_PARSED | schema_version=BoundPlanSpec_v1, steps_count=2, blockers_count=1
[BoundedPlanBrain.develop_bound_plan] DETERMINING_READINESS | analyzing_blockers
[BoundedPlanBrain.develop_bound_plan] READINESS_DETERMINED | status=NEEDS_INPUT
[BoundedPlanBrain.develop_bound_plan] NEXT_INPUT_REQUEST | blocker_type=missing_information, writes_to=['patient_id', 'patient_name']
[BoundedPlanBrain.develop_bound_plan] EXIT | plan_readiness=NEEDS_INPUT, blockers=1, has_next_input=True
[BoundedPlanBrain.start_session] STATE_UPDATE | plan_readiness=NEEDS_INPUT, blockers=1
[BoundedPlanBrain.start_session] STATE_PERSISTED | session_id=1
[BoundedPlanBrain._call_presenter_llm] ENTRY | session_id=1
[BoundedPlanBrain._call_presenter_llm] EXIT | has_message=True, has_question=True
[PlanningPhaseBrain.handle_build_reuse_decision] BOUNDED_PLAN_STARTED | known_fields=0
[WorkflowOrchestrator._format_emit_and_persist] ENTRY | session_id=1
[WorkflowOrchestrator._format_emit_and_persist] System/button-generated message - skipping conversational agent
[WorkflowOrchestrator._format_emit_and_persist] EXIT | Message persisted to transcript
```

**Frontend:**
- User sees message from presenter LLM, for example:
  - **"I've analyzed your eligibility verification workflow. I found 2 steps that need to be completed. To get started, I need some basic information about the patient."**
  - **Question: "What is the patient's name or member ID?"**

**Database:**
```sql
-- shaping_sessions table updated:
bounded_plan_state = {
  "session_id": 1,
  "known_fields": [],
  "known_context": {"draft_plan_summary": {...}},
  "last_bound_plan_spec": {
    "meta": {"schema_version": "BoundPlanSpec_v1"},
    "steps": [...],
    "blockers": [{"type": "missing_information", ...}],
    "plan_readiness": "NEEDS_INPUT",
    "next_input_request": {...}
  }
}
bound_plan_spec = {...}  -- Full BoundPlanSpec_v1
```

---

### **STEP 6: User Provides Patient Information**

**Frontend:**
- User types: **"John Doe"** or **"patient_name: John Doe"**

**API Call:**
```
POST /api/workflows/shaping/{session_id}/chat
Body: {
  "message": "John Doe",
  "user_id": "user_123"
}
```

**Server Logs:**
```
[PlanningPhaseBrain.handle_message] ENTRY | session_id=1, message_length=8
[PlanningPhaseBrain.handle_message] ROUTING_TO_BOUNDED_PLAN | session_id=1
[BoundedPlanBrain.handle_user_message] ENTRY | session_id=1, message_length=8, known_fields=0
[BoundedPlanBrain.handle_user_message] EXTRACTING_INPUT | checking_last_input_request
[BoundedPlanBrain.handle_user_message] EXTRACTING_INPUT | writes_to=['patient_id', 'patient_name']
[BoundedPlanBrain.handle_user_message] FIELD_EXTRACTED | field=patient_name, value_from_message
[BoundedPlanBrain.handle_user_message] STATE_UPDATE | known_fields=0 -> 1, new_fields=['patient_name']
[BoundedPlanBrain.handle_user_message] CHECKING_DATA_ENRICHMENT | checking_for_patient_info
[BoundedPlanBrain.handle_user_message] PATIENT_INFO_DETECTED | from_message_heuristic, identifier=John Doe
[BoundedPlanBrain.handle_user_message] FETCHING_PATIENT_PROFILE | identifier=John Doe
[BoundedPlanBrain._fetch_patient_profile] ENTRY | identifier=John Doe
[BoundedPlanBrain._fetch_patient_profile] SEARCHING_PATIENT | query=John Doe
[user_profile_endpoints.search_patients] ENTRY | name=John Doe, dob=None, patient_id=None
[UserProfileManager.search_patients] ENTRY | name=John Doe, dob=None, patient_id=None
[UserProfileManager.search_patients] EXIT | results_count=1
[user_profile_endpoints.search_patients] EXIT | results_count=1
[BoundedPlanBrain._fetch_patient_profile] PATIENT_FOUND | patient_id=PAT123456
[BoundedPlanBrain._fetch_patient_profile] FETCHING_EMR_VIEW | patient_id=PAT123456
[user_profile_endpoints.get_patient_emr] ENTRY | patient_id=PAT123456
[UserProfileManager.get_patient_emr_view] ENTRY | patient_id=PAT123456
[UserProfileManager.get_patient_emr_view] EXIT | data_keys=['diagnoses', 'medications', 'allergies', 'visits', 'labs', 'procedures']
[user_profile_endpoints.get_patient_emr] EXIT | emr_data_keys=['diagnoses', 'medications', 'allergies', 'visits', 'labs', 'procedures']
[BoundedPlanBrain._fetch_patient_profile] EMR_VIEW_RETRIEVED | keys=['diagnoses', 'medications', 'allergies', 'visits', 'labs', 'procedures']
[BoundedPlanBrain._fetch_patient_profile] FETCHING_SYSTEM_VIEW | patient_id=PAT123456
[UserProfileManager.get_patient_system_view] ENTRY | patient_id=PAT123456
[UserProfileManager.get_patient_system_view] EXIT | data_keys=['demographics', 'preferences', 'local_ids', 'registration']
[user_profile_endpoints.get_patient_system] EXIT | system_data_keys=['demographics', 'preferences', 'local_ids', 'registration']
[BoundedPlanBrain._fetch_patient_profile] SYSTEM_VIEW_RETRIEVED | keys=['demographics', 'preferences', 'local_ids', 'registration']
[BoundedPlanBrain._fetch_patient_profile] FETCHING_HEALTH_PLAN_VIEW | patient_id=PAT123456
[UserProfileManager.get_patient_health_plan_view] ENTRY | patient_id=PAT123456
[UserProfileManager.get_patient_health_plan_view] EXIT | data_keys=['carrier', 'member_id', 'group', 'coverage', 'benefits', 'eligibility']
[user_profile_endpoints.get_patient_health_plan] EXIT | health_plan_data_keys=['carrier', 'member_id', 'group', 'coverage', 'benefits', 'eligibility']
[BoundedPlanBrain._fetch_patient_profile] HEALTH_PLAN_VIEW_RETRIEVED | keys=['carrier', 'member_id', 'group', 'coverage', 'benefits', 'eligibility']
[BoundedPlanBrain._fetch_patient_profile] DATA_MERGED | views=['emr', 'system', 'health_plan'], extracted_fields=['patient_id', 'patient_name', 'date_of_birth', 'gender', 'address', 'phone', 'email', 'insurance_carrier', 'member_id', 'group_number', 'coverage_status']
[BoundedPlanBrain._fetch_patient_profile] EXIT | fields_count=12
[BoundedPlanBrain.handle_user_message] PATIENT_PROFILE_LOADED | fields_added=11, total_fields=12
[BoundedPlanBrain.handle_user_message] PATIENT_SUMMARY_UPDATED | summary_keys=['patient_id', 'has_emr_data', 'has_system_data', 'has_health_plan_data']
[BoundedPlanBrain.handle_user_message] CALLING_develop_bound_plan | with_updated_state
[BoundedPlanBrain.develop_bound_plan] ENTRY | session_id=1, draft_plan_steps=2, tools_count=12, known_fields=12
[BoundedPlanBrain.develop_bound_plan] BUILDING_INPUT | known_fields=12, blockers=1
[BoundedPlanBrain.develop_bound_plan] RETRIEVING_PROMPT | step=bounded_plan_builder
[BoundedPlanBrain.develop_bound_plan] PROMPT_RETRIEVED | prompt_config_keys=['ROLE', 'CONTEXT', 'ANALYSIS', 'OUTPUT', 'CONSTRAINTS']
[BoundedPlanBrain.develop_bound_plan] BUILDING_PROMPT | using_PromptBuilder
[BoundedPlanBrain.develop_bound_plan] PROMPT_BUILT | system_prompt_length=3124
[BoundedPlanBrain.develop_bound_plan] CALLING_LLM | prompt_length=3124
[BoundedPlanBrain.develop_bound_plan] LLM_RESPONSE | response_length=1456
[BoundedPlanBrain.develop_bound_plan] JSON_PARSED | schema_version=BoundPlanSpec_v1, steps_count=2, blockers_count=0
[BoundedPlanBrain.develop_bound_plan] READINESS_DETERMINED | status=READY_FOR_COMPILATION
[BoundedPlanBrain.develop_bound_plan] EXIT | plan_readiness=READY_FOR_COMPILATION, blockers=0, has_next_input=False
[BoundedPlanBrain.handle_user_message] DEVELOP_OUTPUT | plan_readiness=READY_FOR_COMPILATION, blockers=0, has_next_input=False
[BoundedPlanBrain.handle_user_message] CALLING_PRESENTER_LLM
[BoundedPlanBrain._call_presenter_llm] ENTRY | session_id=1
[BoundedPlanBrain._call_presenter_llm] EXIT | has_message=True, has_question=False
[BoundedPlanBrain.handle_user_message] PRESENTER_RESPONSE | message_length=156, has_question=False
[BoundedPlanBrain.handle_user_message] STATE_PERSISTED | session_id=1
[WorkflowOrchestrator._format_emit_and_persist] ENTRY | session_id=1
[WorkflowOrchestrator._format_emit_and_persist] System/button-generated message - skipping conversational agent
[WorkflowOrchestrator._format_emit_and_persist] EXIT | Message persisted to transcript
```

**Frontend:**
- User sees message: **"Perfect! I've loaded John Doe's profile and found all the information I need. Your workflow plan is now ready for compilation. All steps have been matched to tools and all required data is available."**

**Database:**
```sql
-- shaping_sessions table updated:
bounded_plan_state = {
  "session_id": 1,
  "known_fields": ["patient_id", "patient_name", "date_of_birth", "gender", "address", "phone", "email", "insurance_carrier", "member_id", "group_number", "coverage_status"],
  "known_context": {
    "patient_id": "PAT123456",
    "patient_name": "John Doe",
    "date_of_birth": "1980-01-15",
    "insurance_carrier": "UnitedHealthcare",
    "member_id": "MEM123456",
    "patient_profile_summary": {...}
  },
  "last_bound_plan_spec": {
    "plan_readiness": "READY_FOR_COMPILATION",
    "blockers": [],
    "steps": [
      {
        "id": "step_1",
        "selected_tool": "get_patient_details",
        "tool_parameters": {"patient_id": "PAT123456"}
      },
      {
        "id": "step_2",
        "selected_tool": "check_eligibility",
        "tool_parameters": {"member_id": "MEM123456"}
      }
    ]
  }
}
```

---

### **STEP 7: Plan Ready for Compilation**

**What happens:**
- `plan_readiness` = `"READY_FOR_COMPILATION"`
- All blockers resolved
- All steps have tools assigned
- All required data is available

**Server Logs:**
```
[BoundedPlanBrain.develop_bound_plan] READINESS_DETERMINED | status=READY_FOR_COMPILATION
[BoundedPlanBrain.handle_user_message] EXIT | plan_readiness=READY_FOR_COMPILATION, has_question=False
```

**Frontend:**
- User sees success message
- Left rail shows completed plan with all steps assigned to tools
- Plan is ready to be compiled into a workflow recipe

---

## Key Log Patterns to Watch For

### **1. Bounded Plan Flow:**
```
[BoundedPlanBrain.*] ENTRY | ...
[BoundedPlanBrain.*] EXIT | ...
```

### **2. Patient Profile Fetching:**
```
[BoundedPlanBrain._fetch_patient_profile] SEARCHING_PATIENT | ...
[BoundedPlanBrain._fetch_patient_profile] PATIENT_FOUND | ...
[BoundedPlanBrain._fetch_patient_profile] EMR_VIEW_RETRIEVED | ...
[BoundedPlanBrain._fetch_patient_profile] SYSTEM_VIEW_RETRIEVED | ...
[BoundedPlanBrain._fetch_patient_profile] HEALTH_PLAN_VIEW_RETRIEVED | ...
```

### **3. LLM Calls:**
```
[BoundedPlanBrain.develop_bound_plan] CALLING_LLM | prompt_length=...
[BoundedPlanBrain.develop_bound_plan] LLM_RESPONSE | response_length=...
[BoundedPlanBrain.develop_bound_plan] JSON_PARSED | ...
```

### **4. State Updates:**
```
[BoundedPlanBrain.handle_user_message] STATE_UPDATE | known_fields=... -> ...
[BoundedPlanBrain.handle_user_message] PATIENT_PROFILE_LOADED | fields_added=...
```

### **5. Blocker Resolution:**
```
[BoundedPlanBrain.develop_bound_plan] NEXT_INPUT_REQUEST | blocker_type=..., writes_to=...
[BoundedPlanBrain.develop_bound_plan] READINESS_DETERMINED | status=...
```

---

## Troubleshooting

### **If patient profile not found:**
```
[BoundedPlanBrain._fetch_patient_profile] PATIENT_NOT_FOUND | no_results
```
**Solution:** 
1. **Option 1 (Recommended):** Run seed script to create test patients:
   ```bash
   python nexus/scripts/seed_test_patients.py
   ```
   Then use test patient names: "John Doe", "Jane Smith", "Michael Johnson", etc.

2. **Option 2:** Generate a synthetic patient on-demand:
   ```bash
   curl -X POST http://localhost:8000/api/user-profiles/generate \
     -H "Content-Type: application/json" \
     -d '{"name": "John Doe"}'
   ```
   
3. **Option 3:** Just provide any name - the system will automatically generate a patient profile dynamically when you provide the name in the workflow chat.

**Note:** Patient generation is **dynamic and deterministic** - same name always produces same patient data.

### **If prompts not found:**
```
[PROMPT_MANAGER] ERROR - prompt_templates table not found
```
**Solution:** Run migrations and seed prompts:
```bash
# Run migration
curl http://localhost:8000/api/system/migrate

# Seed prompts
python nexus/scripts/seed_bounded_plan_prompts.py
```

### **If JSON parsing fails:**
```
[BoundedPlanBrain._parse_bound_plan_response] ALL_PARSING_FAILED | error=...
```
**Solution:** Check LLM response format. The parser handles markdown code blocks, but malformed JSON will fail.

---

## Summary

**Total Steps:**
1. Server startup
2. User initiates eligibility check
3. Gate phase (consultant asks questions)
4. Planning phase announcement
5. User clicks "create new workflow"
6. Bounded plan starts (asks for patient info)
7. User provides patient name
8. Patient profile automatically fetched (EMR + System + Health Plan)
9. Bounded plan continues with enriched data
10. Plan ready for compilation

**Key Features:**
- ✅ Automatic patient profile fetching when name provided
- ✅ Multiple data views (EMR, system, health plan)
- ✅ Blocker-driven progression (one question at a time)
- ✅ Comprehensive debug logging at every step
- ✅ State persistence to database

