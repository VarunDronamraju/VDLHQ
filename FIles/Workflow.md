# WORKFLOW.md — LocationHQ

All workflows are orchestrated by C1 WorkflowEngine. No workflow path executes without C1 controlling the state transition. Workflows are not linear in production — loops, retries, and inactivity exits exist at multiple stages.

---

## W1 — Inquiry Intake

**Trigger:** Client submits `POST /inquiry`

**Path:**

```
1. API validates required fields
   → If validation fails: 422, no lead created

2. C3.lookup(email, phone)
   → If existing client: pre-fill known fields, return client_id
   → If new client: create clients record, return new client_id

3. Create leads record
   → status: new
   → intake_data: raw form submission

4. Return 202 to client

5. [BackgroundTask] run_intake_pipeline(lead_id)

6. A1.parse(raw_form_data)
   → Structured fields extracted
   → Write to leads.intake_data
   → If A1 fails: raise IntakeParseFailure
     → Lead stays in 'new'
     → Error logged to system_errors
     → Inactivity scanner surfaces after 6h

7. A2.score(structured_fields)
   → Returns: score, status ('ready' | 'needs_info'), missing_fields
   → If A2 fails: raise ReadinessFailure
     → Lead stays in 'new'
     → Error logged

8. C2.route(lead_id, score, status)
   → If ready:   action = 'start_matching'
   → If needs_info: action = 'trigger_followup'

9. C1.transition(lead_id, target_state, context)
   → If ready:     → W2 (Location Matching)
   → If needs_info: → W3 (Incomplete Inquiry Recovery)
```

---

## W2 — Location Matching

**Trigger:** Lead reaches `ready` state

**Path:**

```
1. C1.transition(lead_id, 'matching_in_progress', context)
   → Writes status: matching_in_progress
   → Writes workflow_state row

2. [BackgroundTask] A3.match(lead_id, intake_data)

3. A3 embeds client requirements
   → text-embedding-3-small, 1536 dims

4. A3 runs pgvector cosine similarity query
   SELECT ... FROM locations WHERE available = true
   ORDER BY embedding <=> $query_vec LIMIT 10

5. A3 LLM ranks and explains shortlist

6. Evaluate results:

   CASE A — Good match (top score >= 0.65):
     → A3 returns MatchingResult(shortlist)
     → C1.transition(lead_id, 'matched', context)
     → C1 stores shortlist on lead record
     → A5 sends shortlist to client (template: 'shortlist_sent')

   CASE B — Poor match AND clarification_count == 0:
     → A3 returns ClarificationNeeded(question)
     → C1.transition(lead_id, 'needs_clarification', context)
     → A5 sends clarification question to client
     → System waits for client response (POST /client/leads/:id)
     → On client response: run_matching_pipeline(lead_id) re-triggered
     → leads.clarification_count incremented to 1

   CASE C — Poor match AND clarification_count >= 1:
     → A3 returns MatchingFailed()
     → C1.transition(lead_id, 'manual_review', context)
     → A5 notifies ops team
     → Ops team resolves → POST /ops/leads/:id/action
     → C1.transition(lead_id, 'ready', context)
     → clarification_count reset to 0
     → Re-enters W2 from step 1

7. Client reviews shortlist:

   IF client confirms a location:
     → POST /client/leads/:id (or ops confirms on client's behalf)
     → C1.transition(lead_id, 'booked', context)
     → W4 (Booking and Permit Lifecycle)

   IF client rejects shortlist:
     → C1.transition(lead_id, 'ready', context)
     → Re-enters W2 from step 1 (clarification_count preserved)
```

---

## W3 — Incomplete Inquiry Recovery

**Trigger:** Lead reaches `needs_info` state

**Path:**

```
1. Lead status: needs_info
   → leads.missing_fields populated

2. Follow-up scanner job (every 2h) checks:
   → leads in needs_info
   → updated_at < 72h ago
   → no follow-up sent (communications_log check)

3. C4.build_followup(lead_id, missing_fields)
   → Constructs follow-up context targeting only missing fields
   → Passes context to A5

4. A5 sends targeted follow-up message
   → Template: 'followup_missing_fields'
   → Logged to communications_log

5. Client updates inquiry:
   → POST /client/leads/:id with missing field values

6. run_intake_pipeline(lead_id) re-triggered
   → A1 re-parses updated intake_data
   → A2 re-scores
   → If ready: C1.transition → W2
   → If still needs_info: follow-up cycle continues (within 72h window)

7. If no response after 7+ days:
   → Inactivity scanner (every 6h) detects updated_at > 7 days
   → C1.transition(lead_id, 'inactive', context)
   → W9 (Inactive Lead Nurturing)
```

---

## W4 — Booking and Permit Lifecycle

**Trigger:** Client confirms a location (lead transitions to `booked`)

**Path:**

```
1. C1.transition(lead_id, 'booked', context)
   → Creates bookings record
   → Writes status: booked

2. A4.generate_checklist(booking_id, shoot_type, location, duration)
   → Infers permit requirements
   → Creates permits record with status: pending
   → Returns checklist

3. C1.transition(lead_id, 'permit_pending', context)
   → A5 sends permit checklist to client and ops team
   → Template: 'permit_process_initiated'

4. Ops team works through checklist, submits permits to authority

5. Ops updates permit status:
   → POST /ops/bookings/:id/permit { status: 'submitted' }
   → A4 updates permits.status to 'submitted'
   → C1.transition(lead_id, 'permit_submitted', context)
   → A5 notifies client: submission confirmed

6. Authority reviews:
   → Ops updates: POST /ops/bookings/:id/permit { status: 'in_review' }
   → C1.transition(lead_id, 'permit_in_review', context)
   → A5 notifies client: under review

7a. IF approved:
   → Ops updates: POST /ops/bookings/:id/permit { status: 'approved' }
   → A4 returns approval → C1.transition(lead_id, 'permit_approved', context)
   → A5 notifies client: approved
   → C1.transition(lead_id, 'coordination', context)
   → Shoot coordination begins

7b. IF rejected:
   → Ops updates: POST /ops/bookings/:id/permit { status: 'rejected', notes: '...' }
   → A4 returns rejection → C1 keeps lead in 'permit_rejected'
   → A5 notifies ops and client: rejected, reason
   → Flagged for manual resolution
   → After resolution: POST /ops/bookings/:id/permit { status: 'pending' }
   → C1.transition(lead_id, 'permit_pending', context)
   → Re-enters from step 4

8. Shoot coordination completes:
   → Ops confirms: POST /ops/leads/:id/action { action: 'transition', target_state: 'closed' }
   → C1.transition(lead_id, 'closed', context)
   → A5 sends closing message to client

PERMIT REMINDERS (parallel):
   → Permit reminder job (daily) checks:
     → permits stuck beyond expected_approval_days in any active stage
     → A5 sends reminder to ops and client
     → Template: 'permit_reminder'
```

---

## W5 — Communication Triggers

**Trigger:** Any state transition, time-based reminder, inactivity detection, or permit update

A5 is triggered in three distinct scenarios:

```
TRIGGER 1 — State transition with template:
  C1.transition() completes
  → C1 checks: does this transition have an associated template?
  → If yes: C1 calls A5 with template_name and context
  → A5 sends, logs to communications_log

TRIGGER 2 — Time-based reminder (scheduler):
  Permit reminder job detects permit overdue
  → Calls A5 directly with template: 'permit_reminder'
  Follow-up scanner detects needs_info with no follow-up
  → Calls C4 → C4 passes context to A5

TRIGGER 3 — Inactivity detection (scheduler):
  Inactivity scanner detects stale lead
  → C1.transition(lead_id, 'inactive')
  → A5 sends inactivity notification
  → A6 picks up for nurturing on weekly cadence
```

**Template → State mapping (examples):**

| State Transition | Template |
|---|---|
| `new → needs_info` | `intake_needs_info` |
| `ready → matching_in_progress` | `matching_started` |
| `matching_in_progress → matched` | `shortlist_sent` |
| `matching_in_progress → needs_clarification` | `clarification_request` |
| `matching_in_progress → manual_review` | `ops_review_notif` (to ops) |
| `matched → booked` | `booking_confirmed` |
| `booked → permit_pending` | `permit_process_initiated` |
| `permit_pending → permit_submitted` | `permit_submitted_notif` |
| `permit_in_review → permit_approved` | `permit_approved_notif` |
| `permit_in_review → permit_rejected` | `permit_rejected_notif` |
| `permit_approved → coordination` | `coordination_started` |
| `coordination → closed` | `shoot_completed` |
| `needs_info → inactive` | `inactivity_notice` |

---

## W6 — Client Profile Reuse

**Trigger:** Returning client submits a new inquiry

**Path:**

```
1. POST /inquiry received

2. C3.lookup(email, phone)
   → Match found: existing clients record returned
   → pre_filled_fields extracted from profile_data

3. New lead created:
   → intake_data pre-populated with known fields
   → Client confirms (not re-enters) pre-filled data

4. A1 processes confirmed data only
   → Skips re-collection of known fields
   → Focuses parsing on new/updated fields

5. A2 scores updated intake_data
   → Higher likelihood of 'ready' on first attempt for returning clients
```

---

## W7 — Ops Dashboard Updates

**Trigger:** Any state transition

**Path:**

```
1. C1.transition() writes lead.status to leads table
2. workflow_state row written
3. Ops dashboard reads leads and workflow_state tables directly
   → No separate sync job
   → No cache layer
   → GET /ops/pipeline queries live DB
   → GET /ops/leads/:id queries live DB with JOIN on workflow_state
```

---

## W9 — Inactive Lead Nurturing

**Trigger:** Lead transitions to `inactive` (from `needs_info` or `matched` after 7+ days of no client response)

**Path:**

```
1. Inactivity scanner detects lead:
   → status in ('needs_info', 'matched')
   → updated_at > 7 days ago

2. C1.transition(lead_id, 'inactive', context)
   → A5 sends inactivity notification to client
   → Template: 'inactivity_notice'

3. Nurturing runner job (weekly) picks up leads in 'inactive':

4. A6.generate(lead_id, client_id)
   → Loads client history and prior communications
   → LLM generates personalized re-engagement message
   → Falls back to standard template if LLM fails
   → Passes message to A5

5. A5 sends re-engagement message
   → Template: 'nurturing_reengagement'
   → Logged to communications_log

6a. IF client responds (POST /client/leads/:id or replies):
   → C1.transition(lead_id, 'needs_info', context)
   → Re-enters W1 (Inquiry Intake) or W3 (Incomplete Inquiry Recovery)

6b. IF no response after extended period (configurable, default 30 days in inactive):
   → Inactivity scanner or ops manual action
   → C1.transition(lead_id, 'archived', context)
   → A5 sends final archive notification (optional, ops-configured)
   → No further automated action
```

---

## Failure Paths Summary

| Stage | Failure | What Happens |
|---|---|---|
| A1 parse fails | LLM error or timeout | Lead stays `new`. Error logged. Inactivity scanner surfaces after 6h. Ops retriggers via `/internal/retry`. |
| A2 scoring fails | LLM error | Lead stays `new`. Same recovery as A1. |
| A3 matching fails | Embedding or LLM error | Lead stays `ready`. Inactivity scanner surfaces. Ops retrigger. |
| A3 clarification exhausted | `clarification_count >= 1`, still poor match | C1 forces `manual_review`. Ops resolves. `clarification_count` reset on `manual_review → ready`. |
| A5 send fails | Provider error | State not rolled back. Logged to `communications_log` with `status: failed`. Ops resends manually. |
| A4 permit submission fails | External or network error | Lead stays `permit_pending`. A4 retries 3 times with backoff. Escalates to ops after exhaustion. |
| BackgroundTask lost (process restart) | Uvicorn restart mid-task | Lead stuck in pre-transition state. Inactivity scanner surfaces on next run. |
| Scheduler job crashes | Unhandled exception | Exception caught, logged to `system_errors`, surfaced on ops dashboard. Next scheduled run re-attempts. |

---

## Retry Logic

- **LLM calls:** Max 3 attempts, exponential backoff, 429 and 5xx only. Raises `LLMFailure` on exhaustion.
- **A4 permit submission:** Max 3 attempts, exponential backoff. Escalates to ops after exhaustion.
- **A3 clarification:** 1 business-level retry (not a technical retry). `clarification_count` tracks this. On second failure → `manual_review`.
- **Scheduler jobs:** Idempotent — re-running is safe. No dedicated retry mechanism needed; next scheduled run catches missed leads.
- **BackgroundTasks:** No automatic retry. Recovery is via inactivity detection + `/internal/retry`.