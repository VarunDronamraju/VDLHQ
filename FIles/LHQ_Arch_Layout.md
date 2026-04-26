LocationHQ Final Architecture Specification
1. System Structure
Directory Layout
/locationhq
  /api
    routes/
      intake.py        ← form submission, partial saves
      leads.py         ← lead reads, manual overrides
      bookings.py      ← booking and permit actions
      client.py        ← client dashboard endpoints
      ops.py           ← internal dashboard endpoints
    middleware.py      ← auth, request ID, logging
    dependencies.py    ← shared FastAPI Depends

  /services
    /core
      workflow_engine.py     ← C1
      routing_service.py     ← C2
      profile_service.py     ← C3
      followup_service.py    ← C4
      analytics_service.py   ← C5
    /ai
      intake_service.py      ← A1
      readiness_service.py   ← A2
      matching_service.py    ← A3
      permit_service.py      ← A4
      communication_service.py ← A5
      nurturing_service.py   ← A6

  /models
    lead.py
    booking.py
    client.py
    location.py
    permit.py
    workflow_state.py

  /scheduler
    jobs.py            ← all APScheduler job definitions

  /db
    session.py         ← SQLAlchemy async engine, session factory
    migrations/        ← Alembic

  /config
    settings.py        ← Pydantic BaseSettings

  main.py              ← app factory, scheduler startup

Module Boundaries
Each service module is a class. Services do not import each other directly except through C1. The dependency direction is:
API routes → C1 WorkflowEngine → AI/Core services
AI services → DB (read only, via repository layer)
AI services → A5 (outbound comms only)
C1 → DB (all writes to lead.status)

No service writes lead.status except C1. This is enforced by convention at first, then by a DB-level trigger in a second pass if drift is detected.
2. WorkflowEngine (C1)  Detailed Design
Transition Map
new              → [needs_info, ready]
needs_info       → [ready, inactive]
ready            → [matching_in_progress]
matching_in_progress → [needs_clarification, matched, manual_review]
needs_clarification  → [matching_in_progress]  ← max once, enforced by clarification_count
matched          → [ready, booked, inactive]
booked           → [permit_pending]
permit_pending   → [permit_submitted]
permit_submitted → [permit_in_review]
permit_in_review → [permit_approved, permit_rejected]
permit_rejected  → [permit_pending]
permit_approved  → [coordination]
coordination     → [closed]
inactive         → [needs_info, archived]
manual_review    → [ready]                      ← ops manually resets after resolution
archived         → []
closed           → []

Transition Method Contract
C1.transition(lead_id, target_state, context) → Result

Execution sequence inside every call:
Load current lead state from DB
Validate target state is in ALLOWED_TRANSITIONS[current_state]  raise if not
For needs_clarification → matching_in_progress: check clarification_count < 1  if not, force manual_review instead
Execute downstream action (the service call associated with this transition)
Only if step 4 succeeds: write new state to lead.status in DB
Write row to workflow_state audit table (previous state, new state, timestamp, trigger)
Trigger A5 communication if the transition has an associated template
Step 4 and step 5 are atomic in intent: if the downstream call fails, the state does not advance. This is not a database transaction across both  the downstream call is external (LLM, email). The guarantee is: state only changes after the work is confirmed done.
Enforcement
lead.status is written only inside C1.transition(). No other module calls db.execute(UPDATE leads SET status...).
Enforced initially by code structure (single write path). The workflow_state audit log makes violations detectable  if lead.status changes without a corresponding workflow_state row, something bypassed C1.
A DB-level check constraint on valid state values prevents garbage states regardless of source.




3. Execution Model
Synchronous vs Asynchronous Boundary
Operation
Sync/Async
Why
Form validation and lead record creation
Sync
Must confirm receipt to client
A1 intake parsing (LLM)
Async (BackgroundTask)
Can take 3–10s, no need to block
A2 readiness scoring
Async (BackgroundTask)
Follows A1 in same task chain
C2 routing
Async (BackgroundTask)
Follows A2
A3 matching (embedding + LLM)
Async (BackgroundTask)
Slow, non-blocking
A5 send communication
Async (BackgroundTask)
Fire-and-observe
Dashboard reads
Sync
Fast DB reads, no LLM
Manual ops actions
Sync
Immediate feedback expected
Permit status updates
Sync
Ops-triggered, immediate

BackgroundTasks Usage
On form submission:
API receives POST /inquiry
→ Validate and write lead (status: new) to DB
→ Return 202 immediately
→ Enqueue background task: run_intake_pipeline(lead_id)

run_intake_pipeline is a single async function that runs A1 → A2 → C2 → C1.transition() in sequence. Each step depends on the previous. If any step fails, execution stops and the lead remains in its current state.
BackgroundTasks in FastAPI runs in the same process on the same event loop after the response is sent. This is sufficient for 20-30 leads/day. The risk is: if the process restarts mid-task, the task is lost. Recovery is via inactivity detection  leads stuck in new or needs_info for too long surface automatically.
LLM Execution Placement
All LLM calls are wrapped in a shared llm_client.call() utility that handles:
Timeout (30s default, 60s for complex generation)
Retry with exponential backoff (max 3 attempts, for 429 and 5xx only)
Structured logging (model, input tokens, output tokens, latency, cost estimate)
Failure propagation  raises on exhausted retries, does not silently return empty
LLM calls never happen in synchronous request handlers. All LLM-dependent services (A1, A2, A3, A4, A5 optional rewrite) run inside background tasks or scheduler jobs.

4. Scheduling Model
APScheduler runs inside the FastAPI process, started on application startup. All scheduled jobs are defined in scheduler/jobs.py and registered at startup.
Job
Frequency
Action
Inactivity scanner
Every 6 hours
Finds leads in needs_info or matched with no update in 7+ days → C1.transition(lead_id, "inactive")
Permit reminder
Daily
Finds permits stuck in any stage beyond expected duration → A5 sends reminder to ops and client
Nurturing runner
Weekly
Finds leads in inactive → A6 builds message → A5 sends
Follow-up scanner
Every 2 hours
Finds leads in needs_info under 72 hours old with no follow-up sent → C4 → A5
Analytics refresh
Daily
C5 runs aggregations, caches results for dashboard

Each scheduled job:
Reads from DB to find affected leads
Calls C1 for any state transitions
Logs execution (found N leads, actioned M)
Does not fail silently  exceptions are caught, logged, and surfaced as an alert

5. Data Model Decisions
PostgreSQL as Source of Truth
Every piece of system state lives in PostgreSQL. BackgroundTasks handle async execution and APScheduler handles scheduling. No Redis or external queue is used. No in-memory state exists outside of a single request or background job lifecycle.
Core Tables
leads
id, client_id, status (enum, constrained), readiness_score,
missing_fields (jsonb), clarification_count (int, default 0),
created_at, updated_at

workflow_state (append-only audit log)
id, lead_id, previous_state, new_state, trigger (string),
actor (service name or user id), created_at

bookings
id, lead_id, client_id, location_id, status, shoot_date,
budget, created_at, updated_at

permits
id, booking_id, permit_type, status (enum), checklist (jsonb),
created_at, updated_at

clients
id, name, email, phone, profile_data (jsonb), created_at, updated_at

locations
id, name, type, address, available (bool), embedding (vector(1536)),
metadata (jsonb), created_at

communications_log
id, lead_id, booking_id, template_name, channel, sent_at, status

State Handling Rule
lead.status is an enum column with a DB-level CHECK constraint on valid values. Status is only written by C1. The workflow_state table records every transition  this is the audit trail and the mechanism for detecting any bypass.
pgvector Usage
The locations table has an embedding vector(1536) column. A3 embeds the client's requirements at query time using the same model used at ingestion. Similarity search runs as a single SQL query with pgvector's cosine distance operator. No separate vector database. Index type: ivfflat with lists = 50 (sufficient for a location inventory in the hundreds).
Re-embedding locations on update is handled by a service call  when a location record is updated, its embedding is recomputed and stored. No streaming pipeline needed at this scale.
6. API Structure
Surfaces
Client-facing
POST /inquiry              ← full form submission
POST /inquiry/partial      ← partial save (F11)
GET  /client/dashboard     ← status, history, updates
GET  /client/leads/:id     ← single lead status
POST /client/leads/:id     ← update inquiry fields

Ops-facing
GET  /ops/pipeline         ← all leads by stage
GET  /ops/leads/:id        ← full lead detail with audit trail
POST /ops/leads/:id/action ← manual state override, reassign
GET  /ops/bookings         ← booking pipeline
POST /ops/bookings/:id/permit ← update permit status
GET  /ops/analytics        ← dashboard aggregations

Webhooks / Internal
POST /internal/retry/:lead_id  ← manually re-trigger intake pipeline

Auth
Two roles: client and ops. JWT-based. Clients see only their own data enforced at the query level (all queries filter by client_id = current_user.client_id). Ops role has unrestricted read and write access to pipeline data.
7. Failure and Recovery Model
Core Rule
State advances only after downstream execution succeeds.
Implementation:
try:
    result = await downstream_service.execute(context)
except DownstreamFailure:
    log_failure(lead_id, attempted_state, error)
    # lead.status is NOT updated
    # workflow_state row is NOT written
    raise  # background task fails cleanly






Failure Scenarios
Failure Point
Lead State After Failure
Recovery Path
A1 fails (LLM timeout)
Remains new
Inactivity scanner surfaces it; ops retriggers via /internal/retry
A2 fails
Remains new
Same as above
A3 fails (embedding or LLM)
Remains ready
Inactivity scanner; ops retrigger
A3 clarification loop exhausted
C1 transitions to manual_review
Ops resolves manually, resets to ready
A5 send fails
State already advanced; communication log shows failure
Ops resend from dashboard; no state rollback
Permit submission fails
Remains permit_pending
A4 retries (3 attempts with backoff); escalates to ops if exhausted
Scheduler job crashes
Job logs exception; next run catches missed leads
Inactivity scanner is idempotent  re-running it is safe

A5 Special Case
A5 is the only service where failure does not block state advancement. State advances when the work (the business action) succeeds  A5 is a notification, not the business action. A5 failures are logged to communications_log with a failed status and surfaced on the ops dashboard for manual resend.
Recovery Surface
The ops dashboard must expose:
Leads stuck in a state for longer than expected (configurable threshold per state)
Communications that failed to send
Background task failures (logged to a system_errors table)
DLQ equivalent: a query view of leads in new or ready for more than 2 hours with no workflow_state update

8. Architecture Patterns Used
Modular monolith Single deployable unit. Services are modules with enforced boundaries. No inter-process communication. All state in PostgreSQL.
State machine pattern lead.status is the authoritative state. ALLOWED_TRANSITIONS map is the single definition of valid moves. C1 is the only executor. The workflow_state table is the event log.
Orchestration (C1 as orchestrator) C1 is the orchestrator  it receives the trigger, decides the next action, calls the appropriate service, and writes state. Services do not call each other. They return results to C1. This is intentional: it keeps the execution path readable as a single trace through C1.
Internal event-driven behavior (lightweight) State transitions function as internal events. Every C1.transition() call results in: state write + audit log row + downstream trigger (A5 or next service). This is not a message bus  it is synchronous in-process orchestration that produces the same logical effect.
Retry and fallback model LLM calls: retry on transient errors (429, 5xx), max 3 attempts, exponential backoff. State does not advance until success. On exhausted retries: fail the background task, leave lead in prior state, surface via inactivity detection. For A3 clarification: one retry at the business logic level (not a technical retry), then C1 forces manual_review. Permit rejections: explicit state (permit_rejected) with manual resolution path before resubmission.
9. Final Validation
No overengineering: No Redis, no Celery, no Kafka, no separate worker process. One FastAPI app, one PostgreSQL instance, one APScheduler instance inside the app. pgvector used inside existing PostgreSQL. Total infrastructure: one app server, one database.
Fits 20–30 leads/day: BackgroundTasks handles the async load comfortably. APScheduler handles all scheduling in-process. pgvector handles location similarity search on an inventory of hundreds of locations. No component is within an order of magnitude of its capacity limits.
Maintainable by a single developer: All execution traces through C1, making any lead's journey readable from the workflow_state table. One codebase, one deployment unit, one database to query. No distributed systems debugging. The ops dashboard surfaces everything that needs human attention without requiring log diving.
Upgrade path when needed: If volume grows to 200+ leads/day or LLM call failures need guaranteed retry, the AI services (A1–A6) are already isolated enough to move behind a Celery task queue without restructuring the rest of the system. The module boundaries are drawn for this migration.
This document is the implementation reference. Workflow logic, state definitions, and service responsibilities remain as specified in the system document. No changes made.


