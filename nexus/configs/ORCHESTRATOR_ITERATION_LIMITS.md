# Orchestrator Iteration Limits

## Overview
The orchestrator must track the number of Consultant invocations per session to prevent infinite loops. This is a safety mechanism that ensures the system doesn't get stuck in endless conversation loops.

## Implementation Pattern

### 1. Track Iterations in Session State

**Option A: Database Field (Recommended)**
```sql
-- Add to shaping_sessions table
ALTER TABLE shaping_sessions 
ADD COLUMN consultant_iteration_count INTEGER DEFAULT 0,
ADD COLUMN max_iterations INTEGER DEFAULT 15;
```

**Option B: In-Memory Tracking**
```python
# In orchestrator or shaping_manager
self._session_iterations: Dict[int, int] = {}
```

### 2. Check Before Each Consultant Call

**In `shaping_manager.append_message()` or `orchestrator.handle_chat_message()`:**

```python
async def append_message(self, session_id: int, role: str, content: str) -> None:
    # ... existing code ...
    
    # Check iteration limit BEFORE calling Consultant
    iteration_count = await self._get_iteration_count(session_id)
    max_iterations = await self._get_max_iterations(session_id)  # Default: 15
    
    if iteration_count >= max_iterations:
        await agent.emit("THINKING", {
            "message": f"Iteration limit reached ({max_iterations}). Stopping Consultant loop and using best available plan."
        })
        
        # Use best available plan from current state
        current_plan = await self._extract_best_plan_from_transcript(transcript)
        
        # Hand off to Planner with current state
        await self._force_handoff_to_planner(session_id, current_plan)
        
        # Log warning
        logger.warning(f"Session {session_id} hit iteration limit ({max_iterations})")
        return
    
    # Increment iteration count
    await self._increment_iteration_count(session_id)
    
    # Proceed with Consultant call
    # ... rest of existing code ...
```

### 3. Reset on Completion

When `completion_status.is_complete = true`, reset or stop tracking:

```python
# After parsing Consultant response
if completion_status.get("is_complete"):
    # Reset iteration count (or mark as complete)
    await self._reset_iteration_count(session_id)
    # Proceed with handoff
```

### 4. Configuration

Make max_iterations configurable:

```python
# In config or environment
CONSULTANT_MAX_ITERATIONS = int(os.getenv("CONSULTANT_MAX_ITERATIONS", "15"))

# Or per-session override
max_iterations = session.get("max_iterations", CONSULTANT_MAX_ITERATIONS)
```

## Behavior on Limit Reached

1. **Stop Consultant Loop**: Don't call Consultant again
2. **Extract Best Plan**: Use the most complete plan from current transcript/state
3. **Force Handoff**: Hand off to Planner with current state (even if incomplete)
4. **Log Warning**: Log that iteration limit was reached
5. **User Notification**: Optionally notify user that limit was reached and using best available plan

## Success Metrics

Track:
- Number of sessions that completed before hitting limit
- Number of sessions that hit limit
- Average iterations per completed session
- Average iterations per session (including incomplete)

## Example Implementation

```python
async def _get_iteration_count(self, session_id: int) -> int:
    """Get current iteration count for session."""
    query = "SELECT consultant_iteration_count FROM shaping_sessions WHERE id = :id"
    result = await database.fetch_one(query, {"id": session_id})
    return result["consultant_iteration_count"] if result else 0

async def _increment_iteration_count(self, session_id: int) -> None:
    """Increment iteration count."""
    query = """
        UPDATE shaping_sessions 
        SET consultant_iteration_count = consultant_iteration_count + 1,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = :id
    """
    await database.execute(query, {"id": session_id})

async def _reset_iteration_count(self, session_id: int) -> None:
    """Reset iteration count (on completion)."""
    query = """
        UPDATE shaping_sessions 
        SET consultant_iteration_count = 0,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = :id
    """
    await database.execute(query, {"id": session_id})
```








