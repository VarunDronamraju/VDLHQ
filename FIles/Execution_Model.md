# EXECUTION_MODEL.md — LocationHQ

---

## 1. Sync vs Async Boundaries

The execution boundary is straightforward: if the operation must complete before the HTTP response is sent, it is synchronous. If it can safely run after the response, it is async via BackgroundTask.

### Synchronous Operations

These run inside the request/response cycle. The client waits.

| Operation | Where | Why Synchronous |
|---|---|---|
| Form validation (Pydantic) | API route handler | Must fail fast; no point accepting an invalid form |
| Lead record creation | API route handler | Client needs confirmation the inquiry was received |
| Client profile lookup / creation (C3) | API route handler | Required to create the lead record |
| Dashboard reads — client and ops | API route handler | Fast DB reads; client is waiting for the page |
| Manual ops actions (state override, reassign) | API route handler | Ops expects immediate confirmation of their action |
| Permit status updates (ops-triggered) | API route handler | Ops is acting and needs to see the updated state |

### Asynchronous Operations

These are enqueued as FastAPI BackgroundTasks. The HTTP response is returned first. The task runs on the same event loop after the response is sent.

| Operation | Trigger | Why Async |
|---|---|---|
| Intake pipeline (A1 → A2 → C2 → C1) | POST /inquiry accepted | A1 LLM call takes 3–10s; blocking the response is not acceptable |
| Location matching pipeline (A3) | Lead reaches `ready` state | A3 embedding + LLM takes 5–15s |
| Clarification re-run (A3 re-triggered) | Client responds to clarification question | Same as above |
| Outbound communication (A5) | State transition with a template | Fire-and-observe; no need to wait for send confirmation |
| Intake pipeline retry | POST /internal/retry/:lead_id | Same as initial intake pipeline |

### Implications

- BackgroundTasks run in the same process on the same event loop as the API server
- They run after the response is sent — not concurrently with request processing
- If the process restarts while a BackgroundTask is executing, the task is lost with no retry
- Recovery for lost tasks: inactivity scanner detects stuck leads and surfaces them for manual retriggering

---

## 2. BackgroundTasks

FastAPI's `BackgroundTasks` is the mechanism. It is not a queue — it is in-process execution that happens after the response is sent. No external broker. No worker process.

### Adding a Task

```python
@app.post("/inquiry")
async def submit_inquiry(
    body: InquiryRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Synchronous work
    client = await profile_service.lookup_or_create(db, body.contact)
    lead = await create_lead(db, client.id, body)

    # Enqueue async work
    background_tasks.add_task(run_intake_pipeline, lead.id)

    return JSONResponse(
        status_code=202,
        content={"lead_id": str(lead.id), "status": "new"}
    )
```

### Pipeline Function Structure

Each pipeline function is a standalone async function that runs the full sequence for that operation. It is responsible for its own error handling and logging.

```python
async def run_intake_pipeline(lead_id: UUID) -> None:
    """
    Runs A1 → A2 → C2 → C1.transition() in sequence.
    Each step depends on the previous.
    Failure at any step: log error, stop execution, lead stays in current state.
    """
    try:
        structured_data = await intake_service.parse(lead_id)
    except IntakeParseFailure as e:
        await log_system_error("intake_pipeline", lead_id, e)
        return

    try:
        readiness_result = await readiness_service.score(lead_id, structured_data)
    except ReadinessFailure as e:
        await log_system_error("intake_pipeline", lead_id, e)
        return

    routing_decision = routing_service.route(readiness_result)

    try:
        await workflow_engine.transition(
            lead_id=lead_id,
            target_state=routing_decision.target_state,
            context={"trigger": "intake_pipeline", "actor": "workflow_engine"}
        )
    except TransitionError as e:
        await log_system_error("intake_pipeline", lead_id, e)
        return
```

### BackgroundTask Failure Behavior

If a BackgroundTask raises an unhandled exception:
- FastAPI catches it (does not crash the process)
- The exception should be caught inside the pipeline function and logged to `system_errors`
- The lead remains in its last valid state
- No automatic retry — recovery is via inactivity scanner + `/internal/retry`

---

## 3. APScheduler Jobs

APScheduler runs as `AsyncIOScheduler` inside the FastAPI process. Initialized in the application lifespan handler at startup.

### Initialization

```python
# main.py
from contextlib import asynccontextmanager
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from scheduler.jobs import register_all_jobs

scheduler = AsyncIOScheduler()

@asynccontextmanager
async def lifespan(app: FastAPI):
    register_all_jobs(scheduler)
    scheduler.start()
    yield
    scheduler.shutdown()

app = FastAPI(lifespan=lifespan)
```

### Job Registration

```python
# scheduler/jobs.py
def register_all_jobs(scheduler: AsyncIOScheduler) -> None:
    scheduler.add_job(scan_inactive_leads,   'interval', hours=6,   id='scan_inactive')
    scheduler.add_job(scan_followup_leads,   'interval', hours=2,   id='scan_followup')
    scheduler.add_job(run_permit_reminders,  'cron',     hour=8,    id='permit_reminder')
    scheduler.add_job(run_nurturing_runner,  'cron',     day_of_week='mon', hour=9, id='nurturing')
    scheduler.add_job(refresh_analytics,     'cron',     hour=1,    id='analytics_refresh')
```

### Job Definitions

---

#### `scan_inactive_leads` — Every 6 Hours

```
Purpose: Find leads that have been stuck without client response for 7+ days.

Query:
  SELECT id FROM leads
  WHERE status IN ('needs_info', 'matched')
  AND updated_at < NOW() - INTERVAL '7 days'

Action per lead:
  → C1.transition(lead_id, 'inactive', context={
      trigger: 'inactivity_scanner',
      actor: 'inactivity_scanner'
    })

Logging:
  → Log: "inactivity_scanner: found N leads, transitioned M"
  → Any transition failure: logged to system_errors, continues to next lead

Idempotency:
  → If a lead is already 'inactive', C1 will raise InvalidTransition
  → Caught, logged as warning, not an error — job continues
```

---

#### `scan_followup_leads` — Every 2 Hours

```
Purpose: Find leads in needs_info that haven't had a follow-up sent yet.

Query:
  SELECT l.id FROM leads l
  LEFT JOIN communications_log c
    ON c.lead_id = l.id
    AND c.template_name = 'followup_missing_fields'
    AND c.status = 'sent'
  WHERE l.status = 'needs_info'
  AND l.created_at > NOW() - INTERVAL '72 hours'
  AND c.id IS NULL

Action per lead:
  → C4.build_followup(lead_id, missing_fields)
  → Pass context to A5

Logging:
  → Log: "followup_scanner: found N leads, sent M follow-ups"
```

---

#### `run_permit_reminders` — Daily at 8 AM

```
Purpose: Find permits stuck beyond their expected approval window.

Query:
  SELECT p.id, p.booking_id, p.status, p.checklist->>'expected_approval_days' as days
  FROM permits p
  WHERE p.status IN ('pending', 'submitted', 'in_review')
  AND p.updated_at < NOW() - INTERVAL '1 day' * (checklist->>'expected_approval_days')::int

Action per permit:
  → A5 sends reminder to ops and client
  → Template: 'permit_reminder'
  → Channel: email

Logging:
  → Log: "permit_reminder: found N overdue permits, sent M reminders"
```

---

#### `run_nurturing_runner` — Weekly, Monday 9 AM

```
Purpose: Re-engage leads that have been inactive for 7+ days.

Query:
  SELECT id FROM leads
  WHERE status = 'inactive'

Action per lead:
  → A6.generate(lead_id, client_id)
  → A6 passes message to A5

Logging:
  → Log: "nurturing_runner: found N inactive leads, sent M messages"
```

---

#### `refresh_analytics` — Daily at 1 AM

```
Purpose: Pre-compute analytics aggregations for dashboard.

Action:
  → C5.run_aggregations()
  → Results written to analytics_snapshots table
  → GET /ops/analytics reads from analytics_snapshots

Logging:
  → Log: "analytics_refresh: completed in Xms"
```

---

## 4. LLM Call Utility

All LLM calls go through a shared `llm_client.call()` function. No service calls the Anthropic SDK directly.

```python
# services/ai/llm_client.py

async def call(
    messages: list[dict],
    system: str,
    tools: list[dict] | None = None,
    max_tokens: int = 1024,
    timeout: float = 30.0
) -> anthropic.types.Message:
    """
    Shared LLM call utility.

    - Timeout: 30s default, pass 60.0 for complex generation
    - Retry: exponential backoff, max 3 attempts
    - Retries only on: 429 (rate limit), 500/529 (server error)
    - Does NOT retry on: 400 (bad request), 401 (auth), context length errors
    - Raises LLMFailure on exhausted retries — never returns empty silently
    - Logs: model, input_tokens, output_tokens, latency_ms, estimated_cost_usd
    """
```

**Retry schedule:**
- Attempt 1: immediate
- Attempt 2: 2s delay (+ jitter)
- Attempt 3: 8s delay (+ jitter)
- After attempt 3: raise `LLMFailure`

**Logging per call:**
```json
{
  "event": "llm_call",
  "service": "A1",
  "model": "claude-sonnet-4-20250514",
  "input_tokens": 320,
  "output_tokens": 180,
  "latency_ms": 2140,
  "estimated_cost_usd": 0.0042,
  "attempt": 1,
  "lead_id": "uuid"
}
```

---

## 5. Failure Propagation

### In BackgroundTasks

```
run_intake_pipeline(lead_id)
  → A1.parse() raises IntakeParseFailure
  → Caught by pipeline function
  → log_system_error('intake_pipeline', lead_id, error)
  → Function returns (no re-raise)
  → Lead stays in 'new'
  → Inactivity scanner detects after 6h
  → Ops retriggers via /internal/retry
```

### In C1.transition()

```
C1.transition(lead_id, target_state, context)
  → Step 5: downstream_service.execute() raises DownstreamFailure
  → C1 catches the exception
  → lead.status NOT updated
  → workflow_state row NOT written
  → C1 re-raises DownstreamFailure
  → Calling pipeline function catches and logs
```

### In Scheduler Jobs

```
scan_inactive_leads()
  → C1.transition() raises for one lead (e.g. InvalidTransition — already inactive)
  → Job catches exception per-lead (not globally)
  → Logs warning for that lead
  → Continues to next lead
  → At end: logs summary "found N, actioned M, skipped K"
```

### In A5 (Special Case)

```
A5.send()
  → Provider returns error
  → A5 writes to communications_log: { status: 'failed', error_detail: '...' }
  → A5 returns CommunicationResult(success=False)
  → C1 receives the result
  → C1 does NOT roll back lead.status (state was already advanced before A5 was called)
  → Failed communication surfaced on ops dashboard via query on communications_log.status = 'failed'
```

---

## 6. Process Model

Single Uvicorn process. Single event loop. No threading model to worry about for standard operations.

```
[Uvicorn process]
  ├─ FastAPI app (handles HTTP requests)
  ├─ Event loop (runs async route handlers and BackgroundTasks)
  └─ APScheduler (AsyncIOScheduler — runs jobs on the same event loop)
```

**Concurrency behavior:**
- Multiple HTTP requests are handled concurrently via async I/O
- BackgroundTasks run on the same event loop — they do not block each other but they do share the loop with incoming requests
- Scheduler jobs run as coroutines on the same event loop
- At 20–30 leads/day, this is well within the capacity of a single process

**Shutdown:**
- SIGTERM triggers graceful shutdown via lifespan handler
- Scheduler is shut down cleanly: `scheduler.shutdown()`
- In-progress BackgroundTasks run to completion before process exits (FastAPI behavior)
- DB session factory is disposed cleanly