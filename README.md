# LocationHQ

## What It Is

LocationHQ is an operations platform for film, advertising, and media shoot coordination. It connects production houses with location owners and manages the full lifecycle: inquiry intake → lead qualification → location matching → booking → permits → shoot coordination → close.

The system replaces call-heavy manual coordination with a state-driven workflow — structured intake, automated communication, and internal ops visibility — while keeping humans in control of final decisions.

---

## Core Problem It Solves

| Problem | System Response |
|---|---|
| Inquiry handling via calls (10–30 min per lead) | Structured digital intake form with partial save |
| No defined lead pipeline | State machine with 15 explicit states, enforced by C1 |
| Scattered data and repeated collection | Centralized PostgreSQL; client profiles pre-fill on re-inquiry |
| Manual follow-ups and inconsistent communication | Automated messaging triggered by state changes and inactivity |
| No visibility into bookings or permit status | Internal ops dashboard; client-facing status view |
| Permit handling case-by-case | Structured permit lifecycle tracked inside the system |

---

## Architecture Overview

**Pattern:** Modular monolith — single deployable unit, single PostgreSQL database, all state in the DB.

**Stack:**
- FastAPI (API layer + BackgroundTasks for async execution)
- PostgreSQL + pgvector (primary data store + vector similarity search)
- APScheduler (in-process scheduling)
- Anthropic Claude (AI services only, never controlling flow)

**No:** Redis, Celery, Kafka, separate worker processes, separate vector database.

```
/locationhq
  /api/routes/          ← intake, leads, bookings, client, ops endpoints
  /services
    /core/              ← C1, C2, C3, C4, C5 (deterministic, no LLM)
    /ai/                ← A1, A2, A3, A4, A5, A6 (LLM-assisted)
  /models/              ← lead, booking, client, location, permit, workflow_state
  /scheduler/jobs.py    ← all APScheduler job definitions
  /db/                  ← SQLAlchemy async engine, Alembic migrations
  /config/settings.py   ← Pydantic BaseSettings
  main.py               ← app factory, scheduler startup
```

---

## Dependency Direction

```
API routes → C1 WorkflowEngine → AI / Core services
AI services read from DB and return results to C1; they do not write state directly
AI services → A5 (outbound comms only)
C1 → DB (sole writer of lead.status)
```

No service writes `lead.status` except C1. All orchestration flows through C1; auxiliary services may call A5 for communication.

---

## Lead State Machine

```
new
 ├─→ needs_info          (missing fields or below readiness threshold)
 │    ├─→ ready          (client provides missing fields, readiness passes)
 │    └─→ inactive       (no response after 7+ days)
 │         └─→ archived  (no response after extended nurturing period)
 └─→ ready               (readiness passes on first attempt)
      └─→ matching_in_progress
           ├─→ needs_clarification  (poor match results; one clarification loop)
           │    └─→ matching_in_progress  (max once, enforced by clarification_count)
           ├─→ matched              (shortlist sent to client)
           │    ├─→ ready           (client rejects; re-enters routing and matching)
           │    ├─→ booked          (client confirms location)
           │    │    └─→ permit_pending
           │    │         └─→ permit_submitted
           │    │              └─→ permit_in_review
           │    │                   ├─→ permit_approved
           │    │                   │    └─→ coordination
           │    │                   │         └─→ closed
           │    │                   └─→ permit_rejected
           │    │                        └─→ permit_pending  (resubmission after resolution)
           │    └─→ inactive        (no client response after 7+ days at matched)
           └─→ manual_review        (clarification loop exhausted; ops takes over)
                └─→ ready           (ops resolves; clarification_count reset to 0)
```

**Enforcement:** `lead.status` is a constrained enum column with a DB-level CHECK constraint. Every transition writes an append-only row to `workflow_state`. Any status change without a corresponding `workflow_state` row indicates a C1 bypass.

---

## Workflow Engine (C1) — Transition Contract

Every state change calls:

```
C1.transition(lead_id, target_state, context) → Result
```

Execution sequence:

1. Load current `lead.status` and `updated_at` from DB
2. Validate `target_state` is in `ALLOWED_TRANSITIONS[current_state]` — raise if not
3. For `needs_clarification → matching_in_progress`: check `clarification_count < 1`
4. For `manual_review → ready`: reset `clarification_count = 0`
5. Execute downstream action (service call associated with this transition)
6. **Only if step 5 succeeds**: write new `lead.status` to DB
7. Write row to `workflow_state` audit table
8. Trigger A5 if this transition has an associated communication template

**Core guarantee:** state only advances after downstream work is confirmed done. If the downstream call fails, status is not updated and the lead stays in its current state.

---

## Services

### Core Services — Fully Deterministic, No LLM

| Service | ID | Responsibility |
|---|---|---|
| WorkflowEngine | C1 | Owns and enforces the state machine. Only writer of `lead.status`. Triggers all downstream services. Handles retries and inactivity detection. |
| RoutingService | C2 | Routes leads post-readiness assessment: `ready` → A3, `needs_info` → C4. Pure conditional logic. |
| ProfileService | C3 | Manages client records. Matches by email/phone on re-inquiry, pre-fills known fields. Pure CRUD. |
| FollowUpService | C4 | Triggers within 0–72 hours of `needs_info` state. Rule-based scheduling. Passes context to A5 — does not send directly. |
| AnalyticsService | C5 | SQL aggregations on lead and booking data. Results stored for dashboard access. No LLM. |

### AI Services — LLM-Assisted, Never Flow-Controlling

| Service | ID | LLM Role |
|---|---|---|
| IntakeService | A1 | Parses raw inquiry text into structured fields. LLM required. |
| ReadinessService | A2 | Scores lead completeness. Outputs: `ready` or `needs_info` + missing field list. LLM required. |
| MatchingService | A3 | Embeds client requirements, runs pgvector similarity search, LLM ranks shortlist. One clarification loop allowed. If still no match: C1 forces `manual_review`. LLM required. |
| PermitService | A4 | Infers permit requirements, generates checklist, tracks permit lifecycle. Rules-based fallback available. LLM optional. |
| CommunicationService | A5 | Single outbound sending layer. Template-first — LLM may rewrite tone only, never facts. If rewrite fails validation, original template is sent. LLM optional. |
| NurturingService | A6 | Long-term re-engagement for leads inactive 7+ days. Cadence is deterministic. LLM personalizes message content only. Passes to A5 for sending. LLM optional. |

---

## Execution Model

| Operation | Execution |
|---|---|
| Form validation + lead creation | Synchronous — must confirm receipt |
| A1 → A2 → C2 → C1 intake pipeline | Async BackgroundTask — runs after 202 response |
| A3 matching | Async BackgroundTask |
| A5 communication | Async BackgroundTask (fire-and-observe) |
| Dashboard reads | Synchronous — fast DB reads |
| Manual ops actions | Synchronous — immediate feedback expected |
| Permit status updates | Synchronous — ops-triggered |

On form submission: validate and write lead (`status: new`), return 202, enqueue `run_intake_pipeline(lead_id)`. The pipeline runs A1 → A2 → C2 → C1.transition() sequentially. Any step failure stops execution; lead stays in current state.

All LLM calls go through a shared `llm_client.call()` utility: 30s timeout (60s for complex generation), retry with exponential backoff (max 3 attempts, 429/5xx only), structured logging, failure propagation (raises on exhausted retries).

---

## Scheduled Jobs

| Job | Frequency | Action |
|---|---|---|
| Inactivity scanner | Every 6 hours | Leads in `needs_info` or `matched` with no update in 7+ days → C1.transition(lead_id, "inactive") |
| Follow-up scanner | Every 2 hours | Leads in `needs_info` under 72 hours with no follow-up sent → C4 → A5 |
| Permit reminder | Daily | Permits stuck beyond expected duration → A5 sends reminder to ops and client |
| Nurturing runner | Weekly | Leads in `inactive` → A6 builds message → A5 sends |
| Analytics refresh | Daily | C5 runs aggregations, stores results for dashboard access |

All jobs are idempotent. Exceptions are caught, logged, and surfaced — no silent failures.

---

## API Surfaces

### Client-Facing
```
POST /inquiry              — full form submission
POST /inquiry/partial      — partial save (F11, saves as needs_info)
GET  /client/dashboard     — status, history, updates
GET  /client/leads/:id     — single lead status
POST /client/leads/:id     — update inquiry fields
```

### Ops-Facing
```
GET  /ops/pipeline              — all leads by stage
GET  /ops/leads/:id             — full lead detail with audit trail
POST /ops/leads/:id/action      — manual state override, reassign
GET  /ops/bookings              — booking pipeline
POST /ops/bookings/:id/permit   — update permit status
GET  /ops/analytics             — dashboard aggregations
```

### Internal
```
POST /internal/retry/:lead_id   — manually re-trigger intake pipeline
```

**Auth:** JWT-based, two roles — `client` (query-level isolation by `client_id`) and `ops` (unrestricted read/write).

---

## Data Model (Core Tables)

| Table | Key Columns |
|---|---|
| `leads` | `id, client_id, status (enum+CHECK), readiness_score, missing_fields (jsonb), clarification_count, created_at, updated_at` |
| `workflow_state` | `id, lead_id, previous_state, new_state, trigger, actor, created_at` — append-only audit log |
| `bookings` | `id, lead_id, client_id, location_id, status, shoot_date, budget, created_at, updated_at` |
| `permits` | `id, booking_id, permit_type, status (enum), checklist (jsonb), created_at, updated_at` |
| `clients` | `id, name, email, phone, profile_data (jsonb), created_at, updated_at` |
| `locations` | `id, name, type, address, available (bool), embedding vector(1536), metadata (jsonb), created_at` |
| `communications_log` | `id, lead_id, booking_id, template_name, channel, sent_at, status` |

`locations.embedding` uses `ivfflat` index with `lists = 50`. A3 embeds client requirements at query time using the same model used at ingestion. Similarity search runs as a single pgvector cosine distance query.

---

## Failure and Recovery

**Core rule:** state advances only after downstream execution succeeds.

| Failure | Lead State | Recovery |
|---|---|---|
| A1 or A2 fails | Remains `new` | Inactivity scanner surfaces it; ops retriggers via `/internal/retry` |
| A3 fails | Remains `ready` | Inactivity scanner; ops retrigger |
| Clarification loop exhausted | C1 transitions to `manual_review` | Ops resolves, resets to `ready` |
| A5 send fails | State already advanced | Logged to `communications_log`; ops resend from dashboard |
| Permit submission fails | Remains `permit_pending` | A4 retries (3 attempts, backoff); escalates to ops if exhausted |
| Scheduler crash | Job logs exception | Next run catches missed leads; inactivity scanner is idempotent |

**A5 special case:** A5 failure does not roll back state. Communication is a notification, not the business action. Failures are logged and surfaced on the ops dashboard.

**Ops dashboard surfaces:**
- Leads stuck beyond configurable threshold per state
- Failed communications
- Background task failures (logged to `system_errors` table)
- Leads in `new` or `ready` for 2+ hours with no `workflow_state` update

---

## System Principles

1. C1 WorkflowEngine is the single control point — nothing moves without it
2. Core services own reliability and all state transitions — no LLM in the control path
3. AI services assist where interpretation or personalization is needed — they never decide
4. A5 is the only outbound communication layer — C4 and A6 pass to A5, never send directly
5. LLM never controls flow — it only assists decisions and crafts communication
6. The `workflow_state` table is the complete audit trail — any lead's full journey is readable from it
7. The system is designed to surface problems to humans, not hide them

---

## Out of Scope (Future)

- F14: Location owner self-serve portal
- F15: Availability calendar
- F16: Review and feedback capture
- F17: Invoice and commission tracker
- F18: Contract and document storage