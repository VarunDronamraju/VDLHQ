# AGENTS.md — LocationHQ Services

All services are Python classes. Core services (C1–C5) contain no LLM calls and no probabilistic logic. AI services (A1–A6) use the LLM at bounded, defined points and return structured results to C1.

**Universal rule:** No service writes `lead.status` except C1. AI services read from DB and return results to C1; they do not write state directly.

---

## Core Services (C1–C5)

---

### C1 — WorkflowEngine

**File:** `services/core/workflow_engine.py`

**Responsibility:**
The central orchestrator. Owns and enforces the state machine. The sole writer of `lead.status`. Receives a transition intent, validates it, executes the associated downstream service, and writes state only after that execution succeeds. Also responsible for detecting and acting on inactivity, and triggering time-based reminders via A5.

**Method signature:**
```
C1.transition(lead_id: UUID, target_state: str, context: dict) → TransitionResult
```

**Transition execution sequence:**
1. Load current `lead.status` and `updated_at` from DB
2. Validate `target_state` is in `ALLOWED_TRANSITIONS[current_state]` — raise `InvalidTransition` if not
3. If `needs_clarification → matching_in_progress`: check `clarification_count < 1` — if not, force `manual_review` instead
4. If `manual_review → ready`: reset `clarification_count = 0`
5. Execute downstream action (the service call for this transition)
6. **Only if step 5 succeeds**: write new `lead.status` to DB
7. Write append-only row to `workflow_state`
8. If this transition has an associated template: trigger A5

**LLM used:** No

**State effect:** Yes — sole writer of `lead.status` and `workflow_state`

**Transition map:**
```
new                  → [needs_info, ready]
needs_info           → [ready, inactive]
ready                → [matching_in_progress]
matching_in_progress → [needs_clarification, matched, manual_review]
needs_clarification  → [matching_in_progress]   ← max once (clarification_count < 1)
matched              → [ready, booked, inactive]
booked               → [permit_pending]
permit_pending       → [permit_submitted]
permit_submitted     → [permit_in_review]
permit_in_review     → [permit_approved, permit_rejected]
permit_rejected      → [permit_pending]
permit_approved      → [coordination]
coordination         → [closed]
inactive             → [needs_info, archived]
manual_review        → [ready]
archived             → []
closed               → []
```

---

### C2 — RoutingService

**File:** `services/core/routing_service.py`

**Responsibility:**
Post-readiness routing. Receives the readiness assessment result from A2 and determines the next action. Pure conditional logic — no LLM, no DB writes.

**Input:**
```python
lead_id: UUID
readiness_score: float       # 0.0 to 1.0
status: str                  # 'ready' | 'needs_info'
missing_fields: list[str]
```

**Output:**
```python
RoutingDecision(
    action: str,             # 'start_matching' | 'trigger_followup'
    target_state: str        # state to pass to C1.transition()
)
```

**Logic:**
- If `status == 'ready'` → action: `start_matching`, target_state: `matching_in_progress` → C1 calls A3
- If `status == 'needs_info'` → action: `trigger_followup`, target_state: `needs_info` → C1 calls C4

**LLM used:** No

**State effect:** No — returns decision to C1; C1 executes the transition

---

### C3 — ProfileService

**File:** `services/core/profile_service.py`

**Responsibility:**
Manages client records. On every new inquiry, attempts to match the submission to an existing client by email or phone. If matched, returns the existing profile and pre-filled fields. If not, creates a new client record. Pure CRUD.

**Input (lookup):**
```python
email: str
phone: str | None
new_inquiry_data: dict
```

**Output:**
```python
ProfileResult(
    client_id: UUID,
    is_existing: bool,
    pre_filled_fields: dict,    # fields carried from existing profile
    client: Client
)
```

**Logic:**
- Match by `email` first, then `phone` if no email match
- If existing: merge known `profile_data` with new submission — client confirms, not re-enters
- If new: create `clients` record

**LLM used:** No

**State effect:** No — writes `clients` records only, not `lead.status`

---

### C4 — FollowUpService

**File:** `services/core/followup_service.py`

**Responsibility:**
Triggers follow-up communication for leads in `needs_info` state. Rule-based scheduling — no LLM. Determines timing and constructs the communication context, then passes to A5. Does not send directly.

**Input:**
```python
lead_id: UUID
missing_fields: list[str]
hours_since_submission: float
```

**Output:**
```python
FollowUpContext(
    lead_id: UUID,
    template_name: str,         # e.g. 'followup_missing_fields'
    template_data: dict,        # field names, client name, inquiry link
    channel: str                # 'email' | 'whatsapp'
)
```

**Timing logic:**
- Triggered by the follow-up scanner job for leads in `needs_info` under 72 hours with no prior follow-up
- Only one follow-up per 24-hour window
- After 72 hours with no response: inactivity scanner takes over

**LLM used:** No

**State effect:** No — returns context to C1; C1 passes to A5

---

### C5 — AnalyticsService

**File:** `services/core/analytics_service.py`

**Responsibility:**
Runs SQL aggregation queries on `leads`, `bookings`, and `workflow_state` tables. Stores computed results for dashboard reads. No LLM. No external dependencies.

**Input:**
```python
date_range: tuple[date, date] | None    # defaults to last 30 days
filters: dict | None
```

**Output:**
```python
AnalyticsResult(
    volume_by_status: dict[str, int],
    conversion_rate: float,             # new → booked
    avg_time_to_booking_days: float,
    drop_off_by_stage: dict[str, int],
    active_leads: int,
    bookings_this_period: int
)
```

**Storage:** Results are written to a dedicated `analytics_snapshots` table (or returned directly to the dashboard API endpoint). No in-memory caching — queries run against DB.

**LLM used:** No

**State effect:** No

---

## AI Services (A1–A6)

All AI services use the shared `llm_client.call()` utility. They read from DB to build context, call the LLM, and return structured results. They do not write `lead.status`.

---

### A1 — IntakeService

**File:** `services/ai/intake_service.py`

**Responsibility:**
Parses raw inquiry form submission into structured, validated lead fields. The first AI step in the intake pipeline. Handles free-text inputs, ambiguous date formats, and incomplete specifications.

**Input:**
```python
raw_form_data: dict     # raw submission from POST /inquiry
client_id: UUID
```

**Output:**
```python
StructuredIntakeData(
    shoot_type: str,
    dates: dict,                # { start, end }
    budget: dict,               # { min, max, currency }
    location_type: str,
    crew_size: int | None,
    requirements: str | None,
    contact: dict,
    raw_submission: str         # stored for audit
)
```

**LLM used:** Yes (required)
- Extracts and normalizes fields from free-text and form inputs
- Structured output via tool calling — JSON schema enforced

**State effect:** No — returns structured data to C1; C1 writes to `leads.intake_data`

**Failure behavior:** Raises `IntakeParseFailure` on exhausted LLM retries. Lead remains in `new`. Inactivity scanner surfaces it.

---

### A2 — ReadinessService

**File:** `services/ai/readiness_service.py`

**Responsibility:**
Scores lead completeness against the required field set. Determines whether the lead has enough information to proceed to matching or whether follow-up is needed.

**Required fields evaluated:**
- Contact information (name, email or phone)
- Shoot type
- Shoot dates (or date range)
- Budget (at minimum a range)
- Location type or requirements

**Input:**
```python
structured_intake: StructuredIntakeData
lead_id: UUID
```

**Output:**
```python
ReadinessResult(
    score: float,                   # 0.0 to 1.0
    status: str,                    # 'ready' | 'needs_info'
    missing_fields: list[str],      # empty if ready
    reasoning: str                  # stored for ops visibility
)
```

**Threshold:** `score >= 0.80` → `ready`. Below threshold → `needs_info`.

**LLM used:** Yes (required)
- Evaluates field completeness and quality, not just presence
- A field present but unusable (e.g. budget: "around something") counts as missing

**State effect:** No — returns result to C2 (which returns to C1); C1 executes transition

**Failure behavior:** Raises `ReadinessFailure`. Lead remains in `new`.

---

### A3 — MatchingService

**File:** `services/ai/matching_service.py`

**Responsibility:**
Finds and ranks locations matching the client's requirements. Runs pgvector semantic similarity search, then uses LLM to rank and explain the shortlist. Manages the clarification loop if initial results are poor.

**Input:**
```python
lead_id: UUID
intake_data: dict               # structured requirements from leads.intake_data
clarification_response: str | None   # populated on second run after clarification
```

**Execution flow:**

```
1. Embed client requirements using text-embedding-3-small
2. Run pgvector cosine similarity query on locations WHERE available = true
   SELECT id, name, metadata, 1 - (embedding <=> $query_vec) AS score
   FROM locations WHERE available = true
   ORDER BY embedding <=> $query_vec LIMIT 10
3. LLM ranks top results, filters poor fits, generates reasoning per location
4. If top similarity score < 0.65 AND clarification_count == 0:
   → Return ClarificationNeeded(question: str)
   → C1 transitions to needs_clarification, sends question to client via A5
5. If top similarity score < 0.65 AND clarification_count >= 1:
   → Return MatchingFailed()
   → C1 transitions to manual_review
6. Otherwise:
   → Return MatchingResult(shortlist: list[RankedLocation])
```

**Output (success):**
```python
MatchingResult(
    shortlist: list[RankedLocation(
        location_id: UUID,
        name: str,
        score: float,
        reasoning: str      # LLM explanation
    )],
    result_type: 'matched'
)
```

**Output (clarification needed):**
```python
ClarificationNeeded(
    question: str,          # targeted question for client
    result_type: 'needs_clarification'
)
```

**LLM used:** Yes (required)
- Embedding: `text-embedding-3-small` (same model used at location ingestion)
- Ranking and reasoning: Claude

**Clarification rule:** `clarification_count` is checked by C1 before calling A3 on a second run. A3 itself does not enforce the count — C1 does.

**State effect:** No — returns result to C1; C1 transitions and stores shortlist

---

### A4 — PermitService

**File:** `services/ai/permit_service.py`

**Responsibility:**
Infers permit requirements from shoot context, generates a structured checklist, and manages permit status updates throughout the lifecycle.

**Input (permit generation):**
```python
booking_id: UUID
shoot_type: str
location: Location
shoot_duration_days: int
```

**Output (permit generation):**
```python
PermitChecklist(
    permit_types: list[str],        # e.g. ['municipal', 'police_noc']
    checklist: dict,                # items, authority, expected_approval_days
    initial_status: 'pending'
)
```

**Input (status update):**
```python
permit_id: UUID
new_status: permit_status
notes: str | None
```

**Output (status update):**
```python
PermitUpdate(
    permit_id: UUID,
    previous_status: str,
    new_status: str,
    rejection_notes: str | None
)
```

**On approval:** Returns update to C1 → C1 transitions lead to `coordination`

**On rejection:** Returns update → C1 notifies ops via A5, lead stays in `permit_rejected` pending manual resolution

**LLM used:** Optional
- Rules-based fallback available for common shoot types
- LLM used for edge cases and novel location/shoot combinations

**State effect:** No — updates `permits` table status; does not write `lead.status`. Lead state transitions triggered by C1 based on A4's returned result.

---

### A5 — CommunicationService

**File:** `services/ai/communication_service.py`

**Responsibility:**
The single outbound message sending layer. Every email and WhatsApp message in the system goes through A5. Template-first — A5 looks up the pre-defined template for the context, optionally runs an LLM tone rewrite, validates the result, and sends. Logs every send attempt to `communications_log`.

**Input:**
```python
template_name: str
lead_id: UUID | None
booking_id: UUID | None
template_data: dict             # all variables the template needs
channel: str                    # 'email' | 'whatsapp'
```

**Output:**
```python
CommunicationResult(
    success: bool,
    communications_log_id: UUID,
    error: str | None
)
```

**Execution flow:**
```
1. Load template by template_name
2. Render template with template_data
3. (Optional) Run LLM tone rewrite
4. Validate rewrite:
   - No changed facts, dates, names, instructions
   - If validation fails: use original rendered template
5. Send via configured channel provider
6. Write to communications_log (status: sent | failed)
7. Return result
```

**LLM used:** Optional (tone rewrite only)
- Never changes facts, dates, client names, location names, or instructions
- If rewrite output fails validation, the original template is sent without retry
- LLM failure at rewrite step does not block the send

**State effect:** No — writes to `communications_log` only; never writes `lead.status`

**A5 failure behavior:** If the send itself fails (provider error), logs `status: failed` to `communications_log`. The lead state is not rolled back — state had already advanced before A5 was called. Failed sends are surfaced on the ops dashboard.

**Who calls A5:**
- C1 (on state transitions with an associated template)
- C4 (follow-up context passed via C1 → A5)
- A4 (permit updates — passed via C1 → A5)
- A6 (nurturing messages passed directly to A5)

---

### A6 — NurturingService

**File:** `services/ai/nurturing_service.py`

**Responsibility:**
Long-term re-engagement for leads that have been in `inactive` state. Generates a personalized re-engagement message based on client history and passes it to A5. The send cadence and timing are deterministic — determined by the scheduler, not the LLM.

**Input:**
```python
lead_id: UUID
client_id: UUID
days_inactive: int
prior_communications: list[dict]    # from communications_log
intake_data: dict                   # from leads.intake_data
```

**Output:**
```python
NurturingMessage(
    subject: str,               # email subject
    body: str,                  # personalized message body
    channel: str,               # 'email' | 'whatsapp'
    template_data: dict         # passed to A5 for logging
)
```

**Execution flow:**
```
1. Load client history and prior outreach context from DB
2. LLM generates personalized message body based on history
3. Validate: no invented facts, no false urgency
4. Pass to A5 for sending
```

**Cadence:** Weekly, controlled by the nurturing runner scheduler job. A6 does not decide timing.

**LLM used:** Optional (personalization only)
- If LLM fails, falls back to a standard re-engagement template
- LLM failure does not block the nurturing send

**State effect:** No — passes message to A5; does not write `lead.status`

---

## Service Interaction Summary

| Service | Calls | Called By |
|---|---|---|
| C1 | C2, C3, C4, C5, A1, A2, A3, A4, A5 | API routes, scheduler jobs |
| C2 | — | C1 |
| C3 | — | C1, API (on intake) |
| C4 | A5 (via C1) | C1, scheduler |
| C5 | — | Scheduler, API (analytics read) |
| A1 | DB (read), llm_client | C1 |
| A2 | DB (read), llm_client | C1 |
| A3 | DB (read), pgvector, llm_client | C1 |
| A4 | DB (read/write permits), llm_client | C1 |
| A5 | DB (write communications_log), message provider | C1, A6 |
| A6 | DB (read), llm_client, A5 | Scheduler (via C1) |