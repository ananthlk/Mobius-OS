# Gate Agent / Gate Stages Refactoring Plan

## Executive Summary

This document outlines a comprehensive refactoring plan for the gate agent and gate stages modules. The current implementation has grown organically and suffers from several structural issues that impact maintainability, testability, and extensibility.

**Current State:**
- `ShapingManager`: 1,270 lines - Too many responsibilities
- `GateEngine`: 759 lines - Mixed concerns
- `Orchestrator`: 1,789 lines - Overly complex coordination
- `gate_models.py`: 697 lines - Good structure, but could be split

**Target State:**
- Clear separation of concerns
- Single Responsibility Principle adherence
- Improved testability
- Better extensibility
- Reduced coupling

---

## 1. Current Architecture Issues

### 1.1 ShapingManager - God Object Anti-Pattern

**Problems:**
- **1,270 lines** - Violates Single Responsibility Principle
- Manages too many concerns:
  - Session lifecycle management
  - Gate state persistence (DB operations)
  - Gate execution coordination
  - Response formatting
  - Button generation (UI concerns)
  - Template retrieval
  - Planner coordination
  - Transcript management
  - Early stop logic
  - Confirmation handling
  - Activity logging

**Evidence:**
```python
# ShapingManager has 15+ methods doing different things:
- _load_gate_state()          # Persistence
- _save_gate_state()          # Persistence
- _load_gate_config()         # Config loading
- _format_gate_response()     # Presentation
- _emit_gate_router_options() # UI/Button generation
- create_session()            # Session management
- append_message()            # 600+ lines - does everything
- _retrieve_template_for_planner() # Template management
```

### 1.2 GateEngine - Mixed Concerns

**Problems:**
- Prompt building mixed with execution logic
- LLM calling embedded directly
- State merging logic is complex and hard to test
- No clear separation between orchestration and execution

**Evidence:**
```python
# GateEngine mixes:
- execute_gate()              # Orchestration
- _build_extraction_prompt()   # Prompt engineering
- _call_llm()                  # LLM integration
- _merge_state()               # State management
- _select_next_gate()          # Business logic
- _check_completion()          # Validation
```

### 1.3 Orchestrator - Overly Complex

**Problems:**
- 1,789 lines handling too many coordination concerns
- Mixed responsibilities:
  - Session state management
  - Message routing
  - Phase transitions
  - Button matching
  - Transcript enhancement
  - Journey state updates

### 1.4 Code Duplication

**Issues:**
- Gate state serialization/deserialization duplicated
- Button generation patterns repeated
- Response formatting scattered across modules
- Early stop logic embedded in multiple places

### 1.5 Tight Coupling

**Issues:**
- ShapingManager directly calls database
- ShapingManager directly formats responses
- ShapingManager directly generates UI buttons
- GateEngine tightly coupled to LLM service
- Hard to mock for testing

---

## 2. Proposed Architecture

### 2.1 Layer Separation

```
┌─────────────────────────────────────────────────────────┐
│                    Presentation Layer                    │
│  - GateResponseFormatter                                 │
│  - GateButtonBuilder                                     │
│  - GateUICoordinator                                     │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│                   Orchestration Layer                    │
│  - GateOrchestrator                                      │
│  - GatePhaseManager                                      │
│  - GateSessionCoordinator                                │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│                    Business Logic Layer                  │
│  - GateEngine (refactored)                               │
│  - GateCompletionChecker                                │
│  - GateStateMerger                                       │
│  - GateSelector                                          │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│                    Service Layer                         │
│  - GateStateRepository                                   │
│  - GateConfigLoader                                      │
│  - GatePromptBuilder                                     │
│  - GateLLMService                                        │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│                    Data Layer                            │
│  - GateModels (existing, keep)                           │
│  - Database (existing)                                   │
└─────────────────────────────────────────────────────────┘
```

### 2.2 New Module Structure

```
nexus/
├── agents/
│   └── gate_agent.py              # NEW: Main gate agent (thin orchestrator)
├── services/
│   ├── gate/
│   │   ├── __init__.py
│   │   ├── state_repository.py    # NEW: Gate state persistence
│   │   ├── config_loader.py       # NEW: Gate config loading
│   │   ├── prompt_builder.py      # NEW: Prompt construction
│   │   └── llm_service.py        # NEW: LLM integration (wrapper)
│   └── session/
│       └── gate_session_manager.py # NEW: Session lifecycle
├── engines/
│   └── gate/
│       ├── __init__.py
│       ├── gate_engine.py         # REFACTORED: Core execution
│       ├── completion_checker.py  # NEW: Completion logic
│       ├── state_merger.py        # NEW: State merging
│       └── gate_selector.py       # NEW: Next gate selection
├── coordinators/
│   └── gate/
│       ├── __init__.py
│       ├── gate_orchestrator.py   # NEW: High-level coordination
│       ├── phase_manager.py       # NEW: Phase transitions
│       └── confirmation_handler.py # NEW: Confirmation logic
├── formatters/
│   └── gate/
│       ├── __init__.py
│       ├── response_formatter.py  # NEW: Response formatting
│       └── button_builder.py      # NEW: Button generation
└── core/
    └── gate_models.py             # KEEP: Data models (maybe split)
```

---

## 3. Detailed Refactoring Plan

### Phase 1: Extract Service Layer (Week 1)

**Goal:** Separate persistence and configuration concerns from business logic.

#### 3.1.1 Create `GateStateRepository`

**Extract from:** `ShapingManager._load_gate_state()` and `_save_gate_state()`

**New File:** `nexus/services/gate/state_repository.py`

```python
class GateStateRepository:
    """Handles all gate state persistence operations."""
    
    async def load(self, session_id: int) -> Optional[GateState]
    async def save(self, session_id: int, gate_state: GateState) -> None
    async def exists(self, session_id: int) -> bool
    async def delete(self, session_id: int) -> None
```

**Benefits:**
- Single source of truth for state persistence
- Easy to mock for testing
- Can add caching layer later
- Can swap storage backend

#### 3.1.2 Create `GateConfigLoader`

**Extract from:** `ShapingManager._load_gate_config()`

**New File:** `nexus/services/gate/config_loader.py`

```python
class GateConfigLoader:
    """Loads and validates gate configurations."""
    
    async def load(self, strategy: str, session_id: Optional[int] = None) -> Optional[GateConfig]
    async def validate(self, config: GateConfig) -> List[str]  # Returns validation errors
    async def get_default_config(self) -> GateConfig
```

**Benefits:**
- Centralized config loading
- Validation in one place
- Easy to add config caching

#### 3.1.3 Create `GatePromptBuilder`

**Extract from:** `GateEngine._build_extraction_prompt()`

**New File:** `nexus/services/gate/prompt_builder.py`

```python
class GatePromptBuilder:
    """Builds prompts for gate extraction."""
    
    def build_extraction_prompt(
        self,
        user_text: str,
        gate_config: GateConfig,
        current_state: Optional[GateState],
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> str
```

**Benefits:**
- Separates prompt engineering from execution
- Easy to test prompt variations
- Can add prompt versioning

#### 3.1.4 Create `GateLLMService`

**Extract from:** `GateEngine._call_llm()`

**New File:** `nexus/services/gate/llm_service.py`

```python
class GateLLMService:
    """Handles LLM calls for gate extraction."""
    
    async def extract_gate_values(
        self,
        prompt: str,
        gate_config: GateConfig,
        session_id: Optional[int] = None,
        user_id: Optional[str] = None
    ) -> str
```

**Benefits:**
- Isolates LLM integration
- Easy to swap LLM providers
- Can add retry logic, rate limiting

**Migration Steps:**
1. Create new service files
2. Move code from ShapingManager/GateEngine
3. Update imports in ShapingManager
4. Test with existing functionality
5. Remove old code

---

### Phase 2: Extract Business Logic (Week 2)

**Goal:** Separate business logic from orchestration.

#### 3.2.1 Refactor `GateEngine`

**Current:** 759 lines doing everything

**Target:** ~300 lines focused on orchestration

**Extract to separate classes:**

**`nexus/engines/gate/completion_checker.py`**
```python
class GateCompletionChecker:
    """Determines if all gates are complete."""
    
    def check(
        self,
        gate_config: GateConfig,
        current_state: GateState,
        user_override: bool = False
    ) -> Tuple[bool, GateDecision]
    
    def get_missing_gates(
        self,
        gate_config: GateConfig,
        current_state: GateState
    ) -> List[str]
```

**`nexus/engines/gate/state_merger.py`**
```python
class GateStateMerger:
    """Merges new gate values into existing state."""
    
    def merge(
        self,
        previous_state: Optional[GateState],
        parsed_state: GateState,
        gate_config: GateConfig,
        user_text: str
    ) -> GateState
```

**`nexus/engines/gate/gate_selector.py`**
```python
class GateSelector:
    """Selects the next gate to ask."""
    
    def select_next(
        self,
        gate_config: GateConfig,
        current_state: GateState,
        llm_recommendation: Optional[str] = None
    ) -> Optional[str]
```

**Refactored `GateEngine`:**
```python
class GateEngine:
    """Orchestrates gate execution."""
    
    def __init__(self):
        self.completion_checker = GateCompletionChecker()
        self.state_merger = GateStateMerger()
        self.gate_selector = GateSelector()
        self.prompt_builder = GatePromptBuilder()
        self.llm_service = GateLLMService()
        self.parser = GateJsonParser()
    
    async def execute_gate(...) -> ConsultantResult:
        # Orchestrates the flow, delegates to services
```

**Benefits:**
- Each class has single responsibility
- Easy to test individual components
- Can optimize individual pieces
- Clear dependencies

---

### Phase 3: Extract Presentation Layer (Week 3)

**Goal:** Separate UI concerns from business logic.

#### 3.3.1 Create `GateResponseFormatter`

**Extract from:** `ShapingManager._format_gate_response()`

**New File:** `nexus/formatters/gate/response_formatter.py`

```python
class GateResponseFormatter:
    """Formats gate responses for display."""
    
    def format_gate_response(
        self,
        result: ConsultantResult,
        user_id: Optional[str] = None,
        session_id: Optional[int] = None
    ) -> str
    
    def format_confirmation_summary(
        self,
        gate_state: GateState,
        gate_config: GateConfig
    ) -> str
    
    def format_stop_message(
        self,
        gate_key: str,
        reason: str
    ) -> str
```

#### 3.3.2 Create `GateButtonBuilder`

**Extract from:** `ShapingManager._emit_gate_router_options()`

**New File:** `nexus/formatters/gate/button_builder.py`

```python
class GateButtonBuilder:
    """Builds UI buttons for gate interactions."""
    
    def build_gate_buttons(
        self,
        gate_key: str,
        gate_config: GateConfig,
        session_id: int,
        user_id: Optional[str] = None
    ) -> List[Dict[str, Any]]
    
    def build_confirmation_buttons(
        self,
        session_id: int,
        user_id: Optional[str] = None
    ) -> List[Dict[str, Any]]
    
    def get_display_labels(
        self,
        gate_key: str,
        category: str
    ) -> str
```

**Benefits:**
- UI logic separated from business logic
- Easy to change UI without touching core
- Can add different UI formats (web, mobile, CLI)

---

### Phase 4: Extract Coordination Layer (Week 4)

**Goal:** Separate high-level coordination from execution.

#### 3.4.1 Create `GateOrchestrator`

**Extract from:** Parts of `ShapingManager.append_message()`

**New File:** `nexus/coordinators/gate/gate_orchestrator.py`

```python
class GateOrchestrator:
    """Coordinates gate collection workflow."""
    
    def __init__(self):
        self.gate_engine = GateEngine()
        self.state_repo = GateStateRepository()
        self.config_loader = GateConfigLoader()
        self.response_formatter = GateResponseFormatter()
        self.button_builder = GateButtonBuilder()
        self.confirmation_handler = ConfirmationHandler()
    
    async def process_user_input(
        self,
        session_id: int,
        user_input: str,
        user_id: str
    ) -> GateResponse
```

#### 3.4.2 Create `ConfirmationHandler`

**Extract from:** `ShapingManager.append_message()` (confirmation logic)

**New File:** `nexus/coordinators/gate/confirmation_handler.py`

```python
class ConfirmationHandler:
    """Handles gate confirmation workflow."""
    
    def detect_confirmation(self, user_text: str) -> bool
    def detect_edit_request(self, user_text: str) -> bool
    async def handle_confirmation(
        self,
        session_id: int,
        gate_state: GateState
    ) -> ConfirmationResult
```

#### 3.4.3 Create `GatePhaseManager`

**New File:** `nexus/coordinators/gate/phase_manager.py`

```python
class GatePhaseManager:
    """Manages phase transitions in gate workflow."""
    
    def should_show_confirmation(self, gate_state: GateState) -> bool
    def should_transition_to_planning(self, completion_status: Dict) -> bool
    async def transition_to_planning(
        self,
        session_id: int,
        gate_state: GateState
    ) -> None
```

**Benefits:**
- Clear workflow coordination
- Easy to add new phases
- Testable phase transitions

---

### Phase 5: Refactor ShapingManager (Week 5)

**Goal:** Make ShapingManager a thin session manager.

#### 3.5.1 New ShapingManager Structure

**Target:** ~300 lines (down from 1,270)

```python
class ShapingManager:
    """Manages workflow shaping sessions."""
    
    def __init__(self):
        self.gate_orchestrator = GateOrchestrator()
        self.session_manager = GateSessionManager()
    
    async def create_session(...) -> int:
        # Creates session, delegates to orchestrator
    
    async def append_message(...) -> Dict[str, Any]:
        # Routes to appropriate handler (gate, planning, etc.)
    
    async def get_session(...) -> Dict[str, Any]:
        # Returns session data
```

**What Gets Removed:**
- All gate state persistence → `GateStateRepository`
- All gate config loading → `GateConfigLoader`
- All response formatting → `GateResponseFormatter`
- All button building → `GateButtonBuilder`
- All gate execution → `GateOrchestrator`
- All confirmation logic → `ConfirmationHandler`

**What Stays:**
- Session creation/retrieval
- High-level message routing
- Integration with other managers (planner, consultant)

---

## 4. Implementation Strategy

### 4.1 Incremental Migration

**Principle:** Refactor incrementally, maintain functionality at each step.

**Strategy:**
1. Create new classes alongside old code
2. Update old code to use new classes (dependency injection)
3. Test thoroughly
4. Remove old code
5. Repeat for next component

### 4.2 Testing Strategy

**For Each Phase:**
1. Write unit tests for new classes
2. Write integration tests for refactored components
3. Run existing test suite
4. Manual testing in staging

**Test Coverage Goals:**
- Unit tests: 80%+ coverage for new classes
- Integration tests: All critical paths
- E2E tests: Full gate workflow

### 4.3 Backward Compatibility

**Approach:**
- Keep existing public APIs during transition
- Use adapter pattern where needed
- Deprecate old methods gradually
- Document migration path

---

## 5. Code Quality Improvements

### 5.1 Reduce Complexity

**Current Issues:**
- `append_message()`: 600+ lines, multiple responsibilities
- Deeply nested conditionals
- Mixed abstraction levels

**Target:**
- Methods < 50 lines
- Cyclomatic complexity < 10
- Clear separation of concerns

### 5.2 Improve Testability

**Current Issues:**
- Hard to mock database calls
- Hard to test in isolation
- Tight coupling

**Target:**
- Dependency injection everywhere
- Interface-based design
- Easy to mock all dependencies

### 5.3 Better Error Handling

**Current Issues:**
- Errors swallowed in some places
- Inconsistent error handling
- Hard to debug

**Target:**
- Explicit error types
- Proper error propagation
- Comprehensive logging

---

## 6. Migration Checklist

### Phase 1: Services
- [ ] Create `GateStateRepository`
- [ ] Create `GateConfigLoader`
- [ ] Create `GatePromptBuilder`
- [ ] Create `GateLLMService`
- [ ] Update `ShapingManager` to use services
- [ ] Update `GateEngine` to use services
- [ ] Write tests
- [ ] Remove old code

### Phase 2: Business Logic
- [ ] Create `GateCompletionChecker`
- [ ] Create `GateStateMerger`
- [ ] Create `GateSelector`
- [ ] Refactor `GateEngine`
- [ ] Write tests
- [ ] Remove old code

### Phase 3: Presentation
- [ ] Create `GateResponseFormatter`
- [ ] Create `GateButtonBuilder`
- [ ] Update `ShapingManager` to use formatters
- [ ] Write tests
- [ ] Remove old code

### Phase 4: Coordination
- [ ] Create `GateOrchestrator`
- [ ] Create `ConfirmationHandler`
- [ ] Create `GatePhaseManager`
- [ ] Update `ShapingManager` to use orchestrator
- [ ] Write tests
- [ ] Remove old code

### Phase 5: Final Refactor
- [ ] Simplify `ShapingManager`
- [ ] Update `Orchestrator` integration
- [ ] Final testing
- [ ] Documentation
- [ ] Code review

---

## 7. Success Metrics

### 7.1 Code Metrics

**Before:**
- ShapingManager: 1,270 lines, 15 methods
- GateEngine: 759 lines, 14 methods
- Average method length: ~80 lines
- Cyclomatic complexity: High

**After:**
- ShapingManager: ~300 lines, 5 methods
- GateEngine: ~300 lines, 3 methods
- Average method length: ~30 lines
- Cyclomatic complexity: Low

### 7.2 Quality Metrics

- Test coverage: 80%+
- Code duplication: < 5%
- Coupling: Low (clear interfaces)
- Cohesion: High (single responsibility)

### 7.3 Maintainability

- Time to add new gate type: < 2 hours
- Time to fix bug: < 1 hour
- Onboarding time: < 1 day

---

## 8. Risks and Mitigation

### 8.1 Risks

1. **Breaking Changes**
   - Risk: Existing functionality breaks
   - Mitigation: Incremental migration, comprehensive testing

2. **Performance Regression**
   - Risk: Additional abstraction layers slow down
   - Mitigation: Profile before/after, optimize hot paths

3. **Scope Creep**
   - Risk: Refactoring expands beyond plan
   - Mitigation: Strict phase boundaries, regular reviews

### 8.2 Rollback Plan

- Keep old code in separate branch
- Feature flags for new code
- Gradual rollout (10% → 50% → 100%)
- Monitor error rates

---

## 9. Timeline

**Total Duration:** 5 weeks

- **Week 1:** Phase 1 - Services (20 hours)
- **Week 2:** Phase 2 - Business Logic (20 hours)
- **Week 3:** Phase 3 - Presentation (15 hours)
- **Week 4:** Phase 4 - Coordination (15 hours)
- **Week 5:** Phase 5 - Final Refactor + Testing (20 hours)

**Buffer:** 10 hours for unexpected issues

**Total:** ~100 hours

---

## 10. Next Steps

1. **Review this plan** with team
2. **Prioritize phases** based on business needs
3. **Set up testing infrastructure** if needed
4. **Create feature branch** for refactoring
5. **Start with Phase 1** (lowest risk, highest value)

---

## Appendix: Code Examples

### Example: Before and After

**Before (ShapingManager.append_message - excerpt):**
```python
async def append_message(self, session_id: int, role: str, content: str):
    # 600+ lines doing everything:
    # - Load gate state
    # - Check early stop
    # - Execute gate
    # - Format response
    # - Build buttons
    # - Save state
    # - Emit artifacts
    # - Handle confirmation
    # ... etc
```

**After (ShapingManager.append_message):**
```python
async def append_message(self, session_id: int, role: str, content: str):
    """Routes message to appropriate handler."""
    if role == "user":
        return await self.gate_orchestrator.process_user_input(
            session_id, content, user_id
        )
    # Clean, simple, testable
```

**After (GateOrchestrator.process_user_input):**
```python
async def process_user_input(self, session_id: int, user_input: str, user_id: str):
    """Processes user input through gate workflow."""
    # Load state
    gate_state = await self.state_repo.load(session_id)
    gate_config = await self.config_loader.load(strategy)
    
    # Check early stop
    if self._should_stop_early(gate_state, user_input):
        return self._create_stop_response(...)
    
    # Execute gate
    result = await self.gate_engine.execute_gate(...)
    
    # Save state
    await self.state_repo.save(session_id, result.proposed_state)
    
    # Format response
    response = self.response_formatter.format(result)
    buttons = self.button_builder.build(result.next_gate, gate_config)
    
    return GateResponse(response, buttons, result.completion_status)
```

---

**Document Version:** 1.0  
**Last Updated:** 2026-01-06  
**Author:** AI Assistant  
**Status:** Draft - Pending Review


