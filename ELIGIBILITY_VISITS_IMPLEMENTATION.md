# Eligibility Visits Implementation Guide

This document outlines the changes needed to:
1. Include visits in process events (thinking view)
2. Ensure visit data flows to conversational agent
3. Update conversational agent to include visits in output
4. Display visits in process view (frontend)

## Files That Need to Be Restored/Modified

### Backend Files:
1. `nexus/agents/eligibility_v2/orchestrator.py` - Add visits to process events
2. `nexus/routers/eligibility_v2_router.py` - Pass visit data to conversational agent
3. `nexus/brains/conversational_agent.py` - Format responses with visit data

### Frontend Files:
1. `surfaces/portal/components/eligibility_v2/EligibilityProcessView.tsx` - Display visits in thinking view

---

## 1. Include Visits in Process Events (Orchestrator)

**File:** `nexus/agents/eligibility_v2/orchestrator.py`

**Location:** In `_load_patient_data()` method, after visits are loaded and eligibility/probability computed

**Change:**
```python
# After loading visits and computing eligibility/probability
if visit_infos:
    # Emit process event with visit details
    visits_summary = []
    for visit in visit_infos:
        visit_summary = {
            "visit_date": visit.visit_date.isoformat() if visit.visit_date else None,
            "visit_type": visit.visit_type,
            "status": visit.status,
            "eligibility_status": visit.eligibility_status.value if visit.eligibility_status else None,
            "eligibility_probability": visit.eligibility_probability,
            "event_tense": visit.event_tense.value if visit.event_tense else None
        }
        visits_summary.append(visit_summary)
    
    await self._emit_process_event(
        session_id,
        "patient_loading",
        "complete",
        f"Patient details loaded - Found {len(visit_infos)} visits/appointments",
        {
            "patient_summary": {
                "name": f"{case_state.patient.first_name} {case_state.patient.last_name}",
                "dob": case_state.patient.date_of_birth.isoformat() if case_state.patient.date_of_birth else None,
                "insurance": case_state.health_plan.payer_name,
                "member_id": case_state.patient.member_id
            },
            "visits": visits_summary  # Include visits in the process event data
        }
    )
```

---

## 2. Pass Visit Data to Conversational Agent (Router)

**File:** `nexus/routers/eligibility_v2_router.py`

**Location:** When formatting `presentation_summary` through conversational agent

**Change:**
```python
# Extract visit-specific probability data from case_state
visit_probabilities = []
case_state = result.get("case_state")
if case_state:
    # Handle both dict and Pydantic model
    if hasattr(case_state, 'timing'):
        timing = case_state.timing
    elif isinstance(case_state, dict):
        timing = case_state.get("timing", {})
    else:
        timing = {}
    
    related_visits = timing.get("related_visits", []) if isinstance(timing, dict) else getattr(timing, "related_visits", [])
    
    if related_visits:
        for visit in related_visits:
            # Handle both dict and Pydantic model
            if isinstance(visit, dict):
                visit_date = visit.get("visit_date")
                probability = visit.get("eligibility_probability")
                status = visit.get("eligibility_status")
                event_tense = visit.get("event_tense")
                visit_type = visit.get("visit_type")
            else:
                visit_date = visit.visit_date.isoformat() if visit.visit_date else None
                probability = visit.eligibility_probability
                status = visit.eligibility_status.value if visit.eligibility_status else None
                event_tense = visit.event_tense.value if visit.event_tense else None
                visit_type = visit.visit_type
            
            if visit_date and probability is not None:
                visit_probabilities.append({
                    "visit_date": visit_date if isinstance(visit_date, str) else visit_date.isoformat() if visit_date else None,
                    "eligibility_probability": float(probability) if probability is not None else None,
                    "eligibility_status": status if isinstance(status, str) else status.value if status else None,
                    "event_tense": event_tense if isinstance(event_tense, str) else event_tense.value if event_tense else None,
                    "visit_type": visit_type
                })

# Then pass to conversational agent
formatted_summary = await conversational_agent.format_response(
    raw_response=raw_summary,
    user_id=user_id,
    context={
        "session_id": session_id,
        "conversation_history": conversation_history,
        "operation": "eligibility_response",
        "source": "eligibility_v2",
        "visit_probabilities": visit_probabilities  # This should include all visits
    }
)
```

**Apply this change in TWO places:**
1. In the `submit_user_message` endpoint (around line 226)
2. In the `submit_form` endpoint (around line 355)

---

## 3. Update Conversational Agent to Format with Visit Data

**File:** `nexus/brains/conversational_agent.py`

**Location:** In `format_response()` method, when building the formatting request

**Change:**
```python
# Add the current response to format
# Include visit-specific probability data if available
visit_probabilities = context.get("visit_probabilities", [])
formatting_request = f"Please format this response:\n\n{raw_response}"

if visit_probabilities:
    formatting_request += "\n\n**IMPORTANT: Date-of-Service-Specific Data**\n"
    formatting_request += "The following visits have been analyzed with specific eligibility probabilities:\n\n"
    for visit in visit_probabilities:
        visit_date = visit.get("visit_date", "Unknown date")
        probability = visit.get("eligibility_probability", 0)
        status = visit.get("eligibility_status", "UNKNOWN")
        event_tense = visit.get("event_tense", "UNKNOWN")
        visit_type = visit.get("visit_type", "")
        
        formatting_request += f"- **Date: {visit_date}** ({event_tense})\n"
        formatting_request += f"  - Eligibility Status: {status}\n"
        formatting_request += f"  - Probability: {probability:.1%}\n"
        if visit_type:
            formatting_request += f"  - Visit Type: {visit_type}\n"
        formatting_request += "\n"
    
    formatting_request += "**Your Task:**\n"
    formatting_request += "Organize your response by date of service. For each visit date, provide:\n"
    formatting_request += "1. The eligibility probability for that specific date\n"
    formatting_request += "2. Recommendations specific to that date (e.g., whether to proceed, what to check, etc.)\n"
    formatting_request += "3. Any date-specific considerations (e.g., coverage window, past vs future visit)\n"
    formatting_request += "\nFormat the response so it's clear which recommendations apply to which date."

messages.append({"role": "user", "content": formatting_request})
```

**Replace the existing line:**
```python
messages.append({"role": "user", "content": f"Please format this response:\n\n{raw_response}"})
```

---

## 4. Display Visits in Process View (Frontend)

**File:** `surfaces/portal/components/eligibility_v2/EligibilityProcessView.tsx`

**Location:** In the rendering logic for `patient_loading` complete events

**Change:**
Add this code after the existing patient summary display:

```typescript
{/* Add visits display */}
{event.data.visits && event.data.visits.length > 0 && (
  <div className="pl-2 border-l-2 border-gray-200 mt-2">
    <div className="font-medium text-gray-600 mb-0.5">Visits & Appointments:</div>
    <div className="space-y-1">
      {event.data.visits.map((visit: any, idx: number) => (
        <div key={idx} className="text-xs">
          <div className="font-medium">
            {visit.visit_date ? new Date(visit.visit_date).toLocaleDateString() : 'Date TBD'}
            {visit.event_tense && (
              <span className={`ml-2 px-1.5 py-0.5 rounded text-xs ${
                visit.event_tense === 'PAST' ? 'bg-gray-200 text-gray-700' : 'bg-blue-100 text-blue-700'
              }`}>
                {visit.event_tense}
              </span>
            )}
          </div>
          {visit.eligibility_status && (
            <div className="mt-0.5">
              <span className={`text-xs font-medium ${
                visit.eligibility_status === 'YES' ? 'text-green-600' : 
                visit.eligibility_status === 'NO' ? 'text-red-600' : 
                'text-gray-600'
              }`}>
                {visit.eligibility_status === 'YES' ? '✅ Eligible' : 
                 visit.eligibility_status === 'NO' ? '❌ Not Eligible' : 
                 '⏳ Unknown'}
              </span>
              {visit.eligibility_probability !== undefined && visit.eligibility_probability !== null && (
                <span className="ml-2 text-gray-600">
                  ({Math.round(visit.eligibility_probability * 100)}% probability)
                </span>
              )}
            </div>
          )}
          {visit.visit_type && (
            <div className="text-gray-500">{visit.visit_type}</div>
          )}
        </div>
      ))}
    </div>
  </div>
)}
```

---

## Testing Checklist

After implementing these changes:

1. ✅ Load a patient with multiple visits
2. ✅ Check that visits appear in the thinking/process view
3. ✅ Verify visit data (date, status, probability) is displayed correctly
4. ✅ Confirm conversational agent output includes date-specific recommendations
5. ✅ Test with both past and future visits
6. ✅ Verify visits with different eligibility statuses display correctly

---

## Notes

- The visit data should flow: Orchestrator → Process Event → Router → Conversational Agent → User Output
- All visits should be included, not just the primary DOS
- The conversational agent should organize recommendations by date
- The thinking view should show all visits with their eligibility status and probability
