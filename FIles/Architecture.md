# ARCHITECTURE.md — LocationHQ

---

## 1. Pattern

**Modular monolith.** Single deployable unit. All services are Python classes in a structured module hierarchy. No inter-process communication. No message broker. All system state lives in PostgreSQL.

This is not a microservices system. Services communicate through C1 in-process. The boundaries are enforced by code structure, not network isolation.

---

## 2. Directory Structure

```
/locationhq
  /api
    routes/
      intake.py          ← POST /inquiry, POST /inquiry/partial
      leads.py           ← lead reads, manual overrides
      bookings.py        ← booking and permit actions
      client.py          ← client dashboard endpoints
      ops.py             ← internal dashboard endpoints
    middleware.py        ← auth verification, request ID injection, structured logging
    dependencies.py      ← shared FastAPI Depends (get_db, get_current_user, role checks)

  /services
    /core
      workflow_engine.py     ← C1: state machine owner and orchestrator
      routing_service.py     ← C2: post-readiness routing logic
      profile_service.py     ← C3: client profile management
      followup_service.py    ← C4: follow-up scheduling for needs_info leads
      analytics_service.py   ← C5: aggregation queries for dashboard
    /ai
      intake_service.py      ← A1: raw inquiry → structured fields
      readiness_service.py   ← A2: completeness scoring
      matching_service.py    ← A3: location search and ranking
      permit_service.py      ← A4: permit inference and lifecycle
      communication_service.py ← A5: outbound message sending (only layer)
      nurturing_service.py   ← A6: long-term inactive lead re-engagement

  /models
    lead.py
    booking.py
    client.py
    location.py
    permit.py
    workflow_state.py

  /scheduler
    jobs.py              ← all APScheduler job registrations

  /db
    session.py           ← SQLAlchemy async engine, session factory
    migrations/          ← Alembic migration files

  /config
    settings.py          ← Pydantic BaseSettings

  main.py                ← app factory, lifespan startup (scheduler init)
```

---

## 3. Component Breakdown

### API Layer

FastAPI application. Handles HTTP request validation, auth enforcement, and response serialization. Does not contain business logic. Hands off to C1 or core services directly for synchronous operations. For async operations, enqueues a BackgroundTask and returns immediately.

**Middleware stack (in order):**
1. Request ID injection — generates UUID, attaches to `request.state`
2. Structured logging — logs request received, request completed, duration
3. Authentication — verifies JWT, attaches user and role to `request.state`
4. Route handler

### C1 — WorkflowEngine

The central orchestrator. The only component that writes `lead.status`. Receives a transition intent, validates it against the allowed transition map, executes the associated downstream service call, and only then writes the new state.

All other services return results to C1. C1 decides whether to advance state.

### Core Services (C2–C5)

Fully deterministic. No LLM. Each is a focused class with a single responsibility. They receive inputs, execute logic or DB queries, and return results to C1 (or in C5's case, directly to API reads).

### AI Services (A1–A6)

LLM-assisted at specific bounded points. They read from DB to build context, call the LLM client utility, and return structured results to C1. They never write `lead.status`. A5 is the exception — it writes to `communications_log` as a record of outbound sends.

### Database Layer

PostgreSQL with pgvector extension. Single instance. All system state, audit logs, and vector embeddings live here. SQLAlchemy async engine with session factory injected via FastAPI dependency injection.

Alembic manages all schema migrations. No manual schema changes.

### Scheduler

APScheduler running inside the FastAPI process, initialized on application startup via the lifespan handler. All jobs defined in `scheduler/jobs.py`. Jobs are registered at startup and run on their defined intervals.

---

## 4. Dependency Flow

```
HTTP Request
    ↓
API Route Handler (FastAPI)
    ↓
C1 WorkflowEngine
    ├─→ C2 RoutingService        (routing decisions)
    ├─→ C3 ProfileService        (client record lookup/creation)
    ├─→ C4 FollowUpService       (follow-up scheduling)
    ├─→ C5 AnalyticsService      (aggregation, dashboard reads)
    ├─→ A1 IntakeService         (inquiry parsing)
    ├─→ A2 ReadinessService      (completeness scoring)
    ├─→ A3 MatchingService       (location search and ranking)
    ├─→ A4 PermitService         (permit inference and tracking)
    └─→ A5 CommunicationService  (all outbound messages)
         ↑
         └── also called by: C4, A6 (pass context; A5 sends)

AI services (A1–A6):
    ├─→ DB (read — build context for LLM calls)
    └─→ return results to C1 (never write lead.status)

C1:
    └─→ DB (write — lead.status, workflow_state rows)
```

**Rules:**
- No service imports another service directly
- All service calls originate from C1 (or from API layer for synchronous reads)
- A5 is the only outbound message sender; C4 and A6 pass context to A5, they do not send directly
- AI services read from DB and return results to C1; they do not write state directly

---

## 5. Execution Model

### Synchronous Operations

Run within the HTTP request/response cycle. Must complete before the response is returned.

| Operation | Handler |
|---|---|
| Form validation and lead record creation | API route → DB write → 202 returned |
| Dashboard reads (client and ops) | API route → DB read → response |
| Manual ops actions (state override, reassign) | API route → C1.transition() → DB write → response |
| Permit status updates (ops-triggered) | API route → A4 update → DB write → response |

### Asynchronous Operations

Enqueued as FastAPI BackgroundTasks. Run in the same process on the same event loop after the HTTP response is sent.

| Operation | Trigger |
|---|---|
| Intake pipeline (A1 → A2 → C2 → C1) | POST /inquiry accepted |
| Location matching pipeline (A3) | Lead reaches `ready` state |
| Outbound communication (A5) | Any state transition with a template |
| Retry of failed pipeline | POST /internal/retry/:lead_id |

### Pipeline Execution

The intake pipeline (`run_intake_pipeline`) is a single async function:

```
run_intake_pipeline(lead_id):
  1. A1.parse(raw_form_data)          → structured fields or raise
  2. A2.score(structured_fields)      → readiness_score, status, missing_fields or raise
  3. C2.route(lead_id, score, status) → routing_decision or raise
  4. C1.transition(lead_id, target_state, context)
```

Each step depends on the previous. A failure at any step stops the pipeline. The lead remains in its current state. The inactivity scanner surfaces stuck leads automatically.

### LLM Call Utility

All LLM calls go through a shared `llm_client.call()` wrapper:
- Timeout: 30s default, 60s for complex generation
- Retry: exponential backoff, max 3 attempts, 429 and 5xx only
- Logging: model, input tokens, output tokens, latency, cost estimate
- Failure: raises `LLMFailure` on exhausted retries — never returns empty silently

---

## 6. Scheduling Model

APScheduler is initialized in the FastAPI lifespan handler. All jobs are registered at startup from `scheduler/jobs.py`.

| Job | ID | Frequency | What It Does |
|---|---|---|---|
| Inactivity scanner | `scan_inactive` | Every 6 hours | Finds leads in `needs_info` or `matched` with `updated_at` older than 7 days → calls `C1.transition(lead_id, "inactive")` for each |
| Follow-up scanner | `scan_followup` | Every 2 hours | Finds leads in `needs_info` under 72 hours old with no follow-up sent → calls `C4 → A5` |
| Permit reminder | `permit_reminder` | Daily | Finds permits stuck beyond expected duration per stage → calls `A5` to send reminder to ops and client |
| Nurturing runner | `run_nurturing` | Weekly | Finds leads in `inactive` → calls `A6 → A5` for re-engagement message |
| Analytics refresh | `refresh_analytics` | Daily | Calls `C5` to run aggregations and store results for dashboard |

**Job execution rules:**
- Each job reads from DB, acts on affected records, logs `(found N leads, actioned M)`
- Jobs call C1 for any state transitions — they do not write `lead.status` directly
- All exceptions are caught, logged to `system_errors`, and surfaced on the ops dashboard
- All jobs are idempotent — safe to re-run if a prior run was interrupted

---

## 7. Data Ownership Rules

| Data | Owner | Writer |
|---|---|---|
| `lead.status` | C1 WorkflowEngine | C1 only |
| `workflow_state` rows | C1 WorkflowEngine | C1 only (append-only) |
| `clients` records | C3 ProfileService | C3 (create/update) |
| `bookings` records | C1 (on booking confirmation) | C1 |
| `permits` records | A4 PermitService | A4 (status updates within permit lifecycle) |
| `communications_log` rows | A5 CommunicationService | A5 only |
| `locations` records | Admin/ops (manual or API) | Direct DB or admin endpoint |
| `locations.embedding` | A3 MatchingService | A3 (on location update) |

**Critical constraint:** `lead.status` is a PostgreSQL enum column with a CHECK constraint on valid values. No garbage states can be inserted regardless of code path. The `workflow_state` table is the detection mechanism — any `lead.status` change without a corresponding `workflow_state` row means something bypassed C1.

---

## 8. Failure Handling Model

### Core Rule

State advances only after downstream execution succeeds. If the downstream service call raises, the status is not written and the `workflow_state` row is not created.

```
try:
    result = await downstream_service.execute(context)
except DownstreamFailure:
    log_failure(lead_id, attempted_state, error)
    # lead.status NOT updated
    # workflow_state row NOT written
    raise
```

### Failure Matrix

| Failure Point | Lead State After | Recovery |
|---|---|---|
| A1 fails (LLM timeout or parse error) | Remains `new` | Inactivity scanner surfaces after 6h; ops retriggers via `/internal/retry` |
| A2 fails | Remains `new` | Same as above |
| A3 fails (embedding or LLM) | Remains `ready` | Inactivity scanner; ops retrigger |
| A3 clarification loop exhausted | C1 transitions to `manual_review` | Ops resolves manually, resets to `ready`; `clarification_count` reset to 0 |
| A5 send fails | State already advanced | Logged to `communications_log` with `status: failed`; surfaced on ops dashboard for manual resend |
| Permit submission fails | Remains `permit_pending` | A4 retries (3 attempts, exponential backoff); escalates to ops after exhaustion |
| Scheduler job crashes | No state change | Exception logged to `system_errors`; next scheduled run catches missed leads |
| Process restart mid-BackgroundTask | Lead stuck in pre-transition state | Inactivity scanner surfaces it on next run |

### A5 Special Case

A5 is the only service where failure does not block state. Communication is a notification layer, not a business action. The business state has already advanced when A5 is called. A5 failures are logged and surfaced — never silently dropped.

### Recovery Surface (Ops Dashboard)

- Leads stuck in any state beyond a configurable threshold
- `communications_log` entries with `status: failed`
- `system_errors` table entries from scheduler or background task failures
- Query view: leads in `new` or `ready` with no `workflow_state` update in 2+ hours

---

## 9. Infrastructure

| Component | Technology | Notes |
|---|---|---|
| API server | FastAPI + Uvicorn | Async, single process |
| Database | PostgreSQL 16 | pgvector extension enabled |
| Vector search | pgvector (ivfflat, lists=50) | Inside existing PostgreSQL — no separate vector DB |
| Scheduler | APScheduler (AsyncIOScheduler) | Runs inside FastAPI process |
| Migrations | Alembic | All schema changes through migration files |
| Config | Pydantic BaseSettings | Environment variables + .env for development |
| LLM | Anthropic Claude (via SDK) | Wrapped in shared llm_client utility |

**No:** Redis, Celery, Kafka, RabbitMQ, separate worker process, separate vector database, external queue.