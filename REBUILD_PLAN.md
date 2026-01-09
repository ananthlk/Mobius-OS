# Eligibility V2 Rebuild Plan

## Status: Files need to be recreated from scratch

Based on the detailed summary, the following files need to be recreated:

### Core Files (Priority 1):
1. ✅ `nexus/agents/eligibility_v2/__init__.py` - Created
2. ⏳ `nexus/agents/eligibility_v2/models.py` - Pydantic models
3. ⏳ `nexus/agents/eligibility_v2/orchestrator.py` - Main orchestrator with visit support
4. ⏳ `nexus/routers/eligibility_v2_router.py` - API endpoints with visit data passing

### Supporting Files (Priority 2):
5. ⏳ `nexus/services/eligibility_v2/case_repository.py`
6. ⏳ `nexus/services/eligibility_v2/scoring_repository.py`
7. ⏳ `nexus/services/eligibility_v2/turn_repository.py`
8. ⏳ `nexus/services/eligibility_v2/plan_step_repository.py`
9. ⏳ `nexus/services/eligibility_v2/llm_call_repository.py`
10. ⏳ `nexus/services/eligibility_v2/snapshot_repository.py`
11. ⏳ `nexus/services/eligibility_v2/feedback_repository.py`
12. ⏳ `nexus/services/eligibility_v2/propensity_repository.py`
13. ⏳ `nexus/services/eligibility_v2/lookup_repository.py`

### Agent Components (Priority 2):
14. ⏳ `nexus/agents/eligibility_v2/interpreter.py`
15. ⏳ `nexus/agents/eligibility_v2/scorer.py`
16. ⏳ `nexus/agents/eligibility_v2/planner.py`
17. ⏳ `nexus/agents/eligibility_v2/completion_checker.py`
18. ⏳ `nexus/agents/eligibility_v2/consistency_validator.py`
19. ⏳ `nexus/agents/eligibility_v2/state_machine.py`
20. ⏳ `nexus/agents/eligibility_v2/idempotency_handler.py`
21. ⏳ `nexus/agents/eligibility_v2/exceptions.py`

### Frontend Files (Priority 2):
22. ⏳ `surfaces/portal/components/eligibility_v2/EligibilityProcessView.tsx`
23. ⏳ `surfaces/portal/components/eligibility_v2/EligibilityChat.tsx`
24. ⏳ `surfaces/portal/components/eligibility_v2/EligibilitySidebar.tsx`

### Configuration Files (Priority 3):
25. ⏳ `nexus/configs/prompts/eligibility_v2_interpreter.json`
26. ⏳ `nexus/configs/prompts/eligibility_v2_planner.json`

## Implementation Notes:

- All files should include visit-related functionality from the start
- Process events should include visit data
- Conversational agent should receive visit probabilities
- Frontend should display visits in thinking view

## Next Steps:

1. Create models.py with all Pydantic models (including VisitInfo)
2. Create orchestrator.py with visit loading and process events
3. Create router.py with visit data passing to conversational agent
4. Update conversational_agent.py to format with visit data
5. Create frontend components to display visits
