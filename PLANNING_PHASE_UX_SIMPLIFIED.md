# Planning Phase - Simplified UX Flow (Stub)

## Overview
This document describes the simplified, stubbed user experience for the Planning Phase.

---

## Current State: Gate Phase Complete

**User's View:**
- User is in the workflow builder interface
- Left rail shows draft plan (will become process cards)
- Right side shows chat interface
- Progress header shows "GATES_COMPLETE"
- User has completed answering gate questions

---

## Step 1: Gate Completion → Planning Phase Transition

### What Happens:
- System detects `gate_state.status.pass_ == True`
- Backend emits transition event
- Frontend receives event

### What User Sees:

**1.1 Chat Window Transformation:**
- **Header changes**: "Problem Shaping Agent" → **"Planning Phase"**
- **Layout changes**: Chat window expands to full right side
- **Left rail appears**: Process cards panel on the left

**1.2 System Message in Chat:**
```
🎯 Planning Phase Started

We've gathered all the information we need. Now let's build your workflow plan.

First, would you like to:
• Build a new workflow from scratch
• Reuse an existing workflow from your repository

[Build New] [Reuse from Repository] (Reuse coming soon)
```

**User Action:** Clicks "Build New" button

---

## Step 2: Build New Decision (Stub)

### What Happens:
- User selects "Build New"
- System proceeds with build new flow
- Reuse option is placeholder for future

### What User Sees:

**2.1 Chat Confirmation:**
```
✅ Building new workflow

I'll analyze the plan we created and check for any issues...
```

**2.2 System Computation Indicator:**
- Thinking animation appears
- "Analyzing plan..." message

---

## Step 3: System Computation & Step Highlighting

### What Happens:
- Backend analyzes draft plan
- Detects ambiguous steps
- Detects missing information
- Highlights problematic steps

### What User Sees:

**3.1 Left Rail - Process Cards:**
```
┌─────────────────────────────────────┐
│ PROCESS CARDS                       │
├─────────────────────────────────────┤
│                                     │
│ ┌─────────────────────────────────┐ │
│ │ PHASE 1: Data Collection        │ │
│ │ ─────────────────────────────── │ │
│ │                                 │ │
│ │ ⚠️  Step 1: Verify coverage     │ │
│ │    (Missing: Member ID, DOB)    │ │
│ │                                 │ │
│ │ ✅ Step 2: Retrieve demographics│ │
│ │                                 │ │
│ │ ⚠️  Step 3: Check benefits      │ │
│ │    (Ambiguous description)      │ │
│ └─────────────────────────────────┘ │
│                                     │
│ ┌─────────────────────────────────┐ │
│ │ PHASE 2: Verification           │ │
│ │ ─────────────────────────────── │ │
│ │ ✅ Step 4: Validate dates        │ │
│ │ ✅ Step 5: Calculate copay       │ │
│ └─────────────────────────────────┘ │
│                                     │
│ ┌─────────────────────────────────┐ │
│ │ PHASE 3: Notification           │ │
│ │ ─────────────────────────────── │ │
│ │ ✅ Step 6: Send confirmation   │ │
│ └─────────────────────────────────┘ │
└─────────────────────────────────────┘
```

**Visual Indicators:**
- **Yellow border/background**: Ambiguous steps (⚠️)
- **Red border/background**: Missing information steps (❌)
- **Green border**: OK steps (✅)
- **Clickable**: Cards can be clicked to select for review

**3.2 Chat Message:**
```
✅ Analysis complete

I've reviewed your workflow plan. Here's what I found:

⚠️  Some steps need attention:
• Step 1: Missing Member ID and Date of Birth
• Step 3: Description is a bit vague - could you clarify?

✅ Most steps look good and are ready to go.

Let me show you an overview of the entire plan...
```

---

## Step 4: Generic Overview Display

### What Happens:
- System generates generic overview
- Determines if cards need attention
- Shows conditional options

### What User Sees:

**4.1 Overview Card in Chat:**
```
┌─────────────────────────────────────────────────────────┐
│ 📋 WORKFLOW PLAN OVERVIEW                                │
├─────────────────────────────────────────────────────────┤
│                                                          │
│ Your workflow consists of:                              │
│ • 3 phases                                               │
│ • 6 steps total                                        │
│                                                          │
│ Phase 1: Data Collection                                │
│   • Collect patient and insurance information           │
│   • 3 steps                                              │
│                                                          │
│ Phase 2: Verification                                    │
│   • Validate coverage and calculate costs               │
│   • 2 steps                                              │
│                                                          │
│ Phase 3: Notification                                   │
│   • Send confirmation to patient                        │
│   • 1 step                                               │
│                                                          │
│ Expected Timeline: ~5-9 seconds                        │
│                                                          │
│ Expected Outcomes:                                      │
│ • Patient insurance coverage verified                   │
│ • Member demographics retrieved                         │
│ • Benefits calculated                                    │
│ • Confirmation sent to patient                          │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

**4.2 Conditional Options:**

**If NO cards need attention:**
```
What would you like to do?

[Approve Plan] [Review & Edit Plan] [Start New Plan]
```

**If cards DO need attention (current scenario):**
```
⚠️  Some steps need attention before approval.

What would you like to do?

[Select Plan to Review] [Cancel]
```

**4.3 Chat Message:**
```
Here's an overview of your workflow plan.

I noticed that Step 1 and Step 3 need some attention. 
Would you like to review and fix those, or cancel and start over?

You can also click on the highlighted cards in the left panel 
to jump directly to a specific step.
```

---

## Step 5: User Choice - Three Stages

### Stage A: Approve (if all cards OK)

**What User Sees:**
```
┌─────────────────────────────────────────────────────────┐
│ ✅ PLAN APPROVED                                        │
├─────────────────────────────────────────────────────────┤
│                                                          │
│ Your workflow plan has been approved and is ready       │
│ to execute.                                             │
│                                                          │
│ Summary:                                                │
│ • 3 phases                                              │
│ • 6 steps                                               │
│ • All steps validated                                   │
│                                                          │
│ [Execute Workflow] [Save as Draft]                      │
└─────────────────────────────────────────────────────────┘
```

**Chat Message:**
```
✅ Plan approved!

Your workflow is ready to execute. All steps have been validated 
and are good to go.

Would you like to execute it now, or save it for later?
```

---

### Stage B: Review Plan

**What Happens:**
- User clicks "Select Plan to Review" or clicks a highlighted card
- System enters review mode
- Focuses on selected step/phase

**What User Sees:**

**5.1 Selected Step Highlighted:**
- Left rail: Selected card gets blue border
- Card expands to show details

**5.2 Review Panel in Chat:**
```
┌─────────────────────────────────────────────────────────┐
│ REVIEWING: Step 1 - Verify patient insurance coverage  │
├─────────────────────────────────────────────────────────┤
│                                                          │
│ Issue: Missing Information                              │
│                                                          │
│ Missing Fields:                                         │
│ • Member ID (required)                                  │
│ • Date of Birth (required)                              │
│                                                          │
│ [Provide Information] [Mark for Later] [Skip Step]      │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

**5.3 Chat Interaction:**
```
Let's review Step 1. I see it's missing Member ID and Date of Birth.

Would you like to:
1. Provide that information now
2. Mark this step to handle later
3. Skip this step if it's not needed

You can also edit the step description or change the tool if needed.
```

**5.4 After Review:**
- User provides info or makes changes
- System updates the card
- Returns to overview
- Options update based on remaining issues

---

### Stage C: Cancel

**What User Sees:**

**5.1 Cancellation Message:**
```
┌─────────────────────────────────────────────────────────┐
│ ⚠️  PLANNING PHASE CANCELLED                           │
├─────────────────────────────────────────────────────────┤
│                                                          │
│ You've cancelled the planning phase.                    │
│                                                          │
│ Returning to Gate Phase...                             │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

**5.2 Chat Message:**
```
Planning phase cancelled.

I'm returning you to the Gate Phase. You can restart 
the planning phase anytime after completing the gates.

[Return to Gate Phase]
```

**5.3 Redirect:**
- System redirects to gate phase
- Session state reset appropriately

---

## Visual Layout Summary

### Simplified Layout:

```
┌─────────────────────────────────────────────────────────────────────┐
│ Progress Header: PLANNING | 3 phases | 6 steps | 60% complete      │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌──────────────────────┐  ┌────────────────────────────────────┐ │
│  │                      │  │  Planning Phase                    │ │
│  │  Process Cards       │  │  ────────────────────────────────   │ │
│  │  (Left Rail)         │  │                                    │ │
│  │                      │  │  System: "Planning Phase Started"  │ │
│  │  [Phase 1 Card]      │  │                                    │ │
│  │    ⚠️ Step 1        │  │  [Overview Card]                  │ │
│  │    ✅ Step 2         │  │                                    │ │
│  │    ⚠️ Step 3         │  │  [Approve] [Review] [Cancel]      │ │
│  │                      │  │                                    │ │
│  │  [Phase 2 Card]      │  │  [User input area]                │ │
│  │    ✅ Step 4         │  │                                    │ │
│  │    ✅ Step 5         │  │                                    │ │
│  │                      │  │                                    │ │
│  │  [Phase 3 Card]      │  │                                    │ │
│  │    ✅ Step 6         │  │                                    │ │
│  │                      │  │                                    │ │
│  └──────────────────────┘  └────────────────────────────────────┘ │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Key Interactions Summary

1. **Gate Completion** → Planning Phase announcement
2. **Build New Decision** → User selects "Build New" (stub)
3. **System Computation** → Analysis, highlighting problematic steps
4. **Overview Display** → Generic overview with conditional options
5. **User Choice** → Approve / Review Plan / Cancel
6. **Stage Execution** → Execute selected stage

---

## Stub Limitations

1. **Reuse Option**: Placeholder, not functional
2. **Review Stage**: Basic stub, detailed editing coming later
3. **System Computation**: Basic ambiguity/missing info detection
4. **Overview**: Generic text, not highly customized
5. **Approve Stage**: Simple confirmation, execution mode selection later

---

## Next Steps (Future)

- Implement detailed step editing in Review stage
- Add execution mode selection
- Implement reuse from repository flow
- Add phase-by-phase signoff
- Add delay detection
- Add step collaboration (add/remove/modify)

---

This simplified flow provides the foundation for the planning phase, with clear stubs for future enhancements.


