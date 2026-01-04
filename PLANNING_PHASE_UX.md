# Planning Phase - User Experience Walkthrough

## Overview
This document describes the step-by-step user experience when transitioning from the Gate Phase to the Planning Phase in the workflow builder.

---

## Current State: Gate Phase Complete

**User's View:**
- User is in the workflow builder interface
- Left rail shows the draft plan (phases and steps) generated during gate phase
- Right side shows the chat interface with "Problem Shaping Agent" header
- Progress header at top shows status: "GATHERING" or "GATES_COMPLETE"
- User has been answering gate questions in the chat

---

## Step 1: Gate Completion Detection & Transition Announcement

### What Happens:
- System detects that `gate_state.status.pass_ == True`
- Backend emits `ARTIFACTS` event with type `PLANNING_PHASE_STARTED`
- Frontend receives the event and triggers transition

### What User Sees:

**1.1 Chat Window Transformation:**
- **Header changes**: "Problem Shaping Agent" → "Planning Phase Agent" (with new icon/badge)
- **Visual animation**: A subtle slide-in animation with a blue gradient background
- **Banner appears**: A prominent banner at the top of the chat window:
  ```
  🎯 PLANNING PHASE STARTED
  ──────────────────────────────
  We've gathered all the information we need. Now let's refine your workflow plan together.
  ```

**1.2 Progress Header Update:**
- Status badge changes from "GATHERING" → "PLANNING" (with new color: purple/blue)
- Progress bar animates from ~30% to ~40%
- Current step shows: "Planning Phase"

**1.3 System Message in Chat:**
A new system message appears in the chat (with bot icon):
```
🎉 Great! We've completed the information gathering phase.

I've created an initial workflow plan based on our conversation. 
Now we'll work together to refine it, step by step.

Here's what we'll do in this phase:
• Review each phase of your workflow
• Validate that we have all the information needed
• Choose how each step should be executed (I can do it, we work together, or you handle it)
• Check for any potential delays or issues
• Get your sign-off on each phase

Ready to begin? I'll show you an overview of the plan first.
```

---

## Step 2: Planning Phase Overview

### What Happens:
- Backend generates overview of the draft plan
- Frontend displays `PlanningPhaseOverview` component
- User sees summary of what will be reviewed

### What User Sees:

**2.1 Overview Card Appears:**
A large card slides in from the right side (or appears in the left rail area), showing:

```
┌─────────────────────────────────────────────────────────┐
│ 📋 WORKFLOW PLAN OVERVIEW                                │
├─────────────────────────────────────────────────────────┤
│                                                          │
│ Plan Name: "Eligibility Verification Workflow"          │
│ Goal: Verify patient insurance coverage and benefits    │
│                                                          │
│ ┌──────────────────────────────────────────────────┐  │
│ │ PHASE 1: Data Collection                          │  │
│ │ • Step 1: Verify patient insurance coverage       │  │
│ │ • Step 2: Retrieve member demographics           │  │
│ │ • Step 3: Check benefit eligibility               │  │
│ └──────────────────────────────────────────────────┘  │
│                                                          │
│ ┌──────────────────────────────────────────────────┐  │
│ │ PHASE 2: Verification                             │  │
│ │ • Step 4: Validate coverage dates                 │  │
│ │ • Step 5: Calculate copay amounts                │  │
│ └──────────────────────────────────────────────────┘  │
│                                                          │
│ ┌──────────────────────────────────────────────────┐  │
│ │ PHASE 3: Notification                             │  │
│ │ • Step 6: Send eligibility confirmation           │  │
│ └──────────────────────────────────────────────────┘  │
│                                                          │
│ Total: 3 phases, 6 steps                               │
│                                                          │
│ [Start Review] button (primary, blue)                  │
└─────────────────────────────────────────────────────────┘
```

**2.2 Chat Message:**
System message in chat:
```
I've organized your workflow into 3 phases with 6 steps total.

Click "Start Review" to begin. We'll go through each phase one at a time, 
and I'll help you validate everything before we proceed.
```

**User Action:** Clicks "Start Review" button

---

## Step 3: Phase-by-Phase Review (Phase 1 Example)

### What Happens:
- System loads Phase 1 details
- Validates each step (tool matching, info completeness)
- Checks for delays
- Displays `PhaseReview` component

### What User Sees:

**3.1 Phase Header:**
```
┌─────────────────────────────────────────────────────────┐
│ PHASE 1: Data Collection                                │
│ ─────────────────────────────────────────────────────── │
│ Collect patient and insurance information               │
│                                                          │
│ Progress: [████░░░░░░] 0/3 steps reviewed              │
└─────────────────────────────────────────────────────────┘
```

**3.2 Step Cards (One for each step):**

**Step 1 Card:**
```
┌─────────────────────────────────────────────────────────┐
│ STEP 1: Verify patient insurance coverage               │
├─────────────────────────────────────────────────────────┤
│                                                          │
│ Tool Status: ✅ Matched                                 │
│   → Tool: eligibility_verifier                         │
│                                                          │
│ Information Status: ⚠️  Missing 2 items                 │
│   ✅ Patient ID (from gate_state)                       │
│   ✅ Payer Name (from gate_state)                       │
│   ❌ Member ID (missing)                                 │
│   ❌ Date of Birth (missing)                            │
│                                                          │
│ Execution Mode: [Select Mode ▼]                        │
│   ○ Agent Mode - I'll execute this automatically        │
│   ○ Copilot Mode - We'll work together                  │
│   ○ User-Owned - You'll handle this                    │
│                                                          │
│ Delays: ⚠️  Potential delay detected                    │
│   • Tool may take 2-3 seconds to respond                │
│   • If member ID not found, manual lookup required     │
│                                                          │
│ [Edit Step] [Delete Step]                               │
└─────────────────────────────────────────────────────────┘
```

**Step 2 Card:**
```
┌─────────────────────────────────────────────────────────┐
│ STEP 2: Retrieve member demographics                   │
├─────────────────────────────────────────────────────────┤
│                                                          │
│ Tool Status: ✅ Matched                                 │
│   → Tool: member_lookup                                 │
│                                                          │
│ Information Status: ✅ Complete                         │
│   ✅ All required inputs available                      │
│                                                          │
│ Execution Mode: [Select Mode ▼]                        │
│   ○ Agent Mode - I'll execute this automatically        │
│   ○ Copilot Mode - We'll work together                  │
│   ○ User-Owned - You'll handle this                    │
│                                                          │
│ Delays: ✅ No delays expected                           │
│                                                          │
│ [Edit Step] [Delete Step]                               │
└─────────────────────────────────────────────────────────┘
```

**3.3 Missing Information Alert:**
If any step has missing information, a prominent alert appears:
```
┌─────────────────────────────────────────────────────────┐
│ ⚠️  MISSING INFORMATION                                 │
├─────────────────────────────────────────────────────────┤
│ Step 1 needs the following before it can execute:      │
│                                                          │
│ • Member ID - Required for eligibility lookup           │
│ • Date of Birth - Required for patient verification    │
│                                                          │
│ [Provide Information] button                            │
└─────────────────────────────────────────────────────────┘
```

**3.4 Chat Interaction:**
System message:
```
Let's review Phase 1: Data Collection

I see that Step 1 is missing Member ID and Date of Birth. 
Would you like to:
1. Provide that information now
2. Mark this step for manual review later
3. Remove this step if it's not needed

Also, how would you like Step 1 to be executed?
- Agent Mode: I'll automatically verify coverage when the workflow runs
- Copilot Mode: I'll help you verify, but you'll make the final decision
- User-Owned: You'll handle the verification yourself
```

---

## Step 4: User Interactions - Execution Mode Selection

### What User Sees:

**4.1 Mode Selector Dropdown:**
When user clicks "Select Mode", a dropdown appears:
```
┌─────────────────────────────────────┐
│ Execution Mode                      │
├─────────────────────────────────────┤
│ 🤖 Agent Mode                       │
│   Mobius will execute automatically  │
│                                     │
│ 👥 Copilot Mode                     │
│   We work together                  │
│                                     │
│ 👤 User-Owned Mode                  │
│   You handle it, I provide support  │
└─────────────────────────────────────┘
```

**4.2 Visual Feedback:**
- Selected mode gets highlighted with a colored border
- Icon changes to reflect selection (🤖 / 👥 / 👤)
- Description updates to show what was selected

**4.3 Chat Confirmation:**
System message updates:
```
✅ Execution mode set for Step 1: Agent Mode

I'll automatically verify patient insurance coverage when this workflow runs. 
I'll use the eligibility_verifier tool with the information we have.

Is this correct?
```

---

## Step 5: Providing Missing Information

### What User Sees:

**5.1 Information Request Modal/Card:**
If user clicks "Provide Information", a form appears:
```
┌─────────────────────────────────────────────────────────┐
│ Provide Missing Information for Step 1                  │
├─────────────────────────────────────────────────────────┤
│                                                          │
│ Member ID:                                               │
│ [________________________]                              │
│                                                          │
│ Date of Birth:                                           │
│ [MM/DD/YYYY]                                             │
│                                                          │
│ [Cancel]  [Save Information]                            │
└─────────────────────────────────────────────────────────┘
```

**5.2 Chat Alternative:**
User can also type in chat:
```
User: "The member ID is M123456 and DOB is 01/15/1985"
```

System responds:
```
✅ Got it! I've updated Step 1 with:
• Member ID: M123456
• Date of Birth: 01/15/1985

Step 1 is now ready. Information Status: ✅ Complete
```

**5.3 Visual Update:**
The Step 1 card updates:
- Information Status changes from "⚠️ Missing 2 items" → "✅ Complete"
- Missing items list disappears
- Green checkmark appears

---

## Step 6: Delay Warnings

### What User Sees:

**6.1 Delay Warning Badge:**
If delays are detected, a warning badge appears on the step card:
```
┌─────────────────────────────────────────────────────────┐
│ ⚠️  DELAY WARNING                                       │
├─────────────────────────────────────────────────────────┤
│ This step may experience delays:                        │
│                                                          │
│ • Tool response time: 2-3 seconds (normal)              │
│ • If member not found: +30 seconds for manual lookup   │
│ • Peak hours (9am-5pm): +10 seconds queue time         │
│                                                          │
│ Estimated total time: 2-43 seconds                      │
│                                                          │
│ [Acknowledge]                                            │
└─────────────────────────────────────────────────────────┘
```

**6.2 Chat Explanation:**
System message:
```
⚠️  I've detected a potential delay for Step 1.

The eligibility_verifier tool typically responds in 2-3 seconds, 
but if the member ID isn't found in our system, it may require a 
manual lookup which could add 30 seconds.

During peak hours (9am-5pm), there's also a queue that might add 
10 seconds.

Would you like to:
1. Proceed anyway (I'll handle the delay)
2. Add a timeout/fallback step
3. Change the execution mode to Copilot so you can intervene
```

---

## Step 7: Step Collaboration (Adding/Removing Steps)

### What User Sees:

**7.1 Add Step Button:**
At the bottom of the phase, there's an "Add Step" button:
```
┌─────────────────────────────────────────────────────────┐
│ [+ Add Step to Phase 1]                                 │
└─────────────────────────────────────────────────────────┘
```

**7.2 Add Step Modal:**
When clicked, a modal appears:
```
┌─────────────────────────────────────────────────────────┐
│ Add New Step to Phase 1                                 │
├─────────────────────────────────────────────────────────┤
│                                                          │
│ Step Description:                                        │
│ [________________________________________________]       │
│                                                          │
│ Tool (optional):                                        │
│ [Select Tool ▼]                                          │
│   • eligibility_verifier                                 │
│   • member_lookup                                        │
│   • benefit_calculator                                   │
│   • [Custom/Manual]                                      │
│                                                          │
│ [Cancel]  [Add Step]                                     │
└─────────────────────────────────────────────────────────┘
```

**7.3 Remove Step:**
Each step card has a "Delete Step" button. When clicked:
```
┌─────────────────────────────────────────────────────────┐
│ Confirm Deletion                                         │
├─────────────────────────────────────────────────────────┤
│ Are you sure you want to remove:                        │
│ "Step 1: Verify patient insurance coverage"?            │
│                                                          │
│ [Cancel]  [Delete Step]                                  │
└─────────────────────────────────────────────────────────┘
```

**7.4 Chat Collaboration:**
User can also type:
```
User: "I think we need an additional step to check for prior authorizations"
```

System responds:
```
Good idea! Let me add that step. 

What should this step do exactly?
1. Check if prior authorization exists
2. Request prior authorization if missing
3. Validate prior authorization details
4. Something else?

Also, which phase should this go in? Phase 1 (Data Collection) or Phase 2 (Verification)?
```

---

## Step 8: Phase Signoff

### What Happens:
- After all steps in a phase are reviewed
- User has selected execution modes
- Missing information is addressed (or acknowledged)
- System requests phase signoff

### What User Sees:

**8.1 Signoff Card Appears:**
```
┌─────────────────────────────────────────────────────────┐
│ ✅ PHASE 1 READY FOR SIGN-OFF                          │
├─────────────────────────────────────────────────────────┤
│                                                          │
│ Phase Summary:                                          │
│ • 3 steps reviewed                                      │
│ • All tools matched                                     │
│ • All information complete                               │
│ • Execution modes selected                              │
│                                                          │
│ Expected Outcomes:                                       │
│ • Patient insurance coverage verified                   │
│ • Member demographics retrieved                         │
│ • Benefit eligibility checked                           │
│                                                          │
│ Expected Timeline:                                      │
│ • Step 1: 2-3 seconds (Agent Mode)                     │
│ • Step 2: 1-2 seconds (Agent Mode)                     │
│ • Step 3: 2-4 seconds (Copilot Mode)                  │
│ • Total: ~5-9 seconds                                   │
│                                                          │
│ ⚠️  Note: Step 3 will require your input (Copilot)     │
│                                                          │
│ [ ] I understand what will happen                      │
│ [ ] I understand the expected timeline                 │
│                                                          │
│ [Sign Off on Phase 1] button (disabled until checked) │
└─────────────────────────────────────────────────────────┘
```

**8.2 Chat Confirmation:**
System message:
```
Phase 1 is ready for your sign-off!

Here's what will happen when this phase runs:
• Step 1: I'll automatically verify insurance coverage (2-3 sec)
• Step 2: I'll retrieve member demographics (1-2 sec)  
• Step 3: We'll work together to check benefits (2-4 sec, I'll need your input)

Total time: ~5-9 seconds

Please review the summary above and check the boxes to confirm you understand.
Then click "Sign Off on Phase 1" to proceed.
```

**8.3 User Actions:**
1. User reviews the summary
2. Checks both confirmation boxes
3. Clicks "Sign Off on Phase 1"

**8.4 Visual Feedback:**
- Phase header updates: "PHASE 1: Data Collection ✅ Signed Off"
- Progress bar updates: "1/3 phases signed off"
- Signoff card changes to a success state:
```
┌─────────────────────────────────────────────────────────┐
│ ✅ PHASE 1 SIGNED OFF                                   │
├─────────────────────────────────────────────────────────┤
│ Signed off at: Jan 15, 2025 2:30 PM                    │
│                                                          │
│ Ready to proceed to Phase 2                             │
│                                                          │
│ [Continue to Phase 2] button                            │
└─────────────────────────────────────────────────────────┘
```

---

## Step 9: Moving to Next Phase

### What User Sees:

**9.1 Phase Transition:**
When user clicks "Continue to Phase 2" or system auto-advances:
- Phase 1 cards collapse/fade out
- Phase 2 header slides in
- Phase 2 step cards appear
- Progress updates: "Phase 2 of 3"

**9.2 Chat Message:**
```
✅ Phase 1 signed off! Moving to Phase 2: Verification

Let's review the verification steps...
```

**9.3 Process Repeats:**
- Steps 3-8 repeat for Phase 2
- Then again for Phase 3
- Until all phases are signed off

---

## Step 10: Planning Phase Complete

### What Happens:
- All phases have been reviewed and signed off
- System transitions to "Ready for Execution" state

### What User Sees:

**10.1 Completion Banner:**
```
┌─────────────────────────────────────────────────────────┐
│ 🎉 PLANNING PHASE COMPLETE                             │
├─────────────────────────────────────────────────────────┤
│                                                          │
│ All 3 phases have been reviewed and signed off:         │
│ ✅ Phase 1: Data Collection                             │
│ ✅ Phase 2: Verification                                │
│ ✅ Phase 3: Notification                                │
│                                                          │
│ Your workflow is ready to execute!                      │
│                                                          │
│ [Execute Workflow] button (primary, green)            │
│ [Save as Draft] button (secondary)                     │
└─────────────────────────────────────────────────────────┘
```

**10.2 Progress Header:**
- Status: "PLANNING" → "READY"
- Progress: ~75%
- Current step: "Ready for Execution"

**10.3 Chat Summary:**
```
🎉 Excellent! We've completed the planning phase.

Summary:
• 3 phases reviewed
• 6 steps validated
• All execution modes selected
• All information confirmed
• All phases signed off

Your workflow is ready to run. When you click "Execute Workflow", 
I'll follow the plan we've created together, using the execution 
modes you've selected for each step.

Ready to execute?
```

**10.4 Final Actions:**
- User can click "Execute Workflow" to start execution
- Or "Save as Draft" to save for later
- Or continue editing if needed

---

## Visual Layout Summary

### Screen Layout During Planning Phase:

```
┌─────────────────────────────────────────────────────────────────────┐
│ Progress Header: PLANNING | 3 phases | Phase 2 of 3 | 60% complete │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌──────────────────────┐  ┌────────────────────────────────────┐ │
│  │                      │  │  Planning Phase Agent              │ │
│  │  Left Rail:          │  │  ────────────────────────────────   │ │
│  │                      │  │                                    │ │
│  │  [Draft Plan]        │  │  Chat Messages...                 │ │
│  │  Phase 1 ✅          │  │                                    │ │
│  │  Phase 2 ⏳          │  │  System: "Let's review Phase 2..." │ │
│  │  Phase 3 ⏸          │  │                                    │ │
│  │                      │  │  [User input area]                │ │
│  │                      │  │                                    │ │
│  └──────────────────────┘  └────────────────────────────────────┘ │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐ │
│  │ Phase Review Panel (Center/Right)                             │ │
│  │                                                                │ │
│  │ PHASE 2: Verification                                          │ │
│  │ ──────────────────────────────────────────────────────────── │ │
│  │                                                                │ │
│  │ [Step 4 Card]                                                 │ │
│  │ [Step 5 Card]                                                 │ │
│  │                                                                │ │
│  │ [+ Add Step]                                                   │ │
│  │                                                                │ │
│  │ [Sign Off on Phase 2]                                         │ │
│  └──────────────────────────────────────────────────────────────┘ │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Key Interactions Summary

1. **Phase Transition**: Automatic detection → Visual announcement → Overview shown
2. **Phase Review**: Step-by-step validation → Mode selection → Information gathering
3. **Collaboration**: Add/remove steps → Modify descriptions → Reorder steps
4. **Signoff**: Review summary → Confirm understanding → Sign off
5. **Progression**: Move to next phase → Repeat → Complete all phases

---

## Error States & Edge Cases

### Missing Information:
- Red alert badge on step card
- Chat prompts for information
- Can't sign off phase until addressed (or explicitly marked for later)

### Tool Not Matched:
- Yellow warning badge
- Option to select tool manually
- Option to mark as "manual" step

### User Wants to Go Back:
- "Back to Phase 1" button available
- Can modify previous phases
- Signoff can be revoked

### User Wants to Skip Phase:
- "Skip Phase" option (with confirmation)
- Phase marked as "skipped"
- Can return to it later

---

This UX flow ensures users have full control and understanding of their workflow before execution, with clear communication at every step.


