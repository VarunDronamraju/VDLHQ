# LocationHQ — Full Build Guide (v2 — Stack-Corrected)
**Execution Reference for a Single Developer**
**Stack: FastAPI · Async SQLAlchemy · Neon PostgreSQL + pgvector · Groq (LLaMA) · sentence-transformers (local)**

---

## Corrections Made to v1

| # | What Was Wrong | What It Is Now |
|---|---|---|
| 1 | Anthropic Claude SDK throughout | Groq API with generic HTTP retry logic |
| 2 | OpenAI embeddings, 1536 dimensions | sentence-transformers `all-MiniLM-L6-v2`, 384 dimensions |
| 3 | Vector column `Vector(1536)` | Vector column `Vector(384)` |
| 4 | JWT auth introduced in Phase 3 | Auth deferred — not needed for current build phase |
| 5 | Scheduler introduced at Phase 11 | Scheduler deferred to Phase 8 (after core pipeline works) |
| 6 | Analytics introduced at Phase 13 | Analytics deferred to Phase 9 |
| 7 | Permit service introduced at Phase 9 | Permits deferred to Phase 10 |
| 8 | `anthropic.RateLimitError`, `anthropic.InternalServerError` | Generic `httpx` exceptions, status-code-based retry |
| 9 | `anthropic.AsyncAnthropic()` client | `groq.AsyncGroq()` client |
| 10 | Execution order was feature-driven, not dependency-driven | Execution order is now build-dependency-driven |

**Nothing changed:**
- C1 WorkflowEngine transition logic
- workflow_state audit design
- Agent boundaries (A1–A6) and responsibilities
- Pipeline structure (A1 → A2 → C2 → C1)
- Async-first system design
- DB schema (except Vector dimension)

---

## What LocationHQ Actually Is

LocationHQ is a **film location scouting operations platform**. It replaces a manual, call-heavy process with a structured, partially automated pipeline.

### The Business Problem It Solves

A film location agency receives 20–30 inquiries per day from production companies needing shoot locations. Currently:
- Every inquiry is handled over calls
- Data is scattered, inconsistent, duplicated
- Follow-ups are manual and inconsistent
- Leads drop off because no one followed up in time
- Permit tracking is done informally
- There is no single source of truth

### What the System Does

**For Clients (Production Companies):**
- Submit a structured inquiry: shoot type, dates, budget, location requirements
- Receive a shortlist of matching locations with AI-generated reasoning
- Confirm a location and track the booking through permit approval to shoot day
- Get automated updates at every stage — no need to call and ask

**For Ops (The Agency Team):**
- See every lead in a pipeline view with current status and time-in-state
- Get notified when leads need attention (manual review, permit delays, failed sends)
- Override any lead state manually when edge cases require it
- Track permit lifecycles without managing spreadsheets
- See conversion analytics: intake → matched → booked → closed

**The AI Layer Does:**
- Parse free-text inquiry submissions into structured fields (A1) — via Groq/LLaMA
- Score whether a lead has enough information to proceed (A2) — via Groq/LLaMA
- Embed client requirements and find semantically matching locations via pgvector (A3) — local embeddings
- Infer permit requirements from shoot context and location (A4) — via Groq/LLaMA
- Rewrite outbound messages with appropriate tone (A5) — optional, Groq/LLaMA
- Generate personalised re-engagement messages for inactive leads (A6) — via Groq/LLaMA

**The AI Layer Does NOT Do:**
- Make decisions — all state transitions are deterministic, controlled by C1
- Send messages without templates — A5 is template-first
- Run autonomously — every AI output returns to C1 before state changes

### The Core Guarantee
Every lead's complete journey is recorded in `workflow_state`. Every state change goes through C1. Nothing advances without the previous step succeeding.

---

## Async — System Requirement

**The entire system is async. This is not optional.**

- SQLAlchemy is wired as `AsyncSession` — sync handlers block the event loop
- All LLM calls (A1, A2, A3, A4, A5, A6) are I/O-bound and non-blocking
- APScheduler runs as `AsyncIOScheduler` on the same event loop
- BackgroundTasks run on the same event loop as the API server

**Rule:** Every route handler is `async def`. Every DB call is `await db.execute(...)`. Every service method is `async def`.

### Environment Requirements (Corrected)

```toml
[tool.poetry.dependencies]
python = "^3.11"
fastapi = "^0.111"
uvicorn = "^0.29"
sqlalchemy = {version = "^2.0", extras = ["asyncio"]}
asyncpg = "^0.29"
groq = "^0.9"                          # LLM provider (replaces anthropic)
sentence-transformers = "^3.0"         # local embeddings (replaces openai)
apscheduler = "^3.10"
pgvector = "^0.3"
pydantic = "^2.0"
pydantic-settings = "^2.0"
httpx = "^0.27"
structlog = "^24.1"
tenacity = "^8.2"
python-jose = "^3.3"                   # JWT — wired later
```

---

## Execution Order (Corrected)

Build in this order. Each phase has hard dependencies on the previous.

```
Phase 1  — Foundation                    ✅ COMPLETE
Phase 2  — Schema completion (all models)
Phase 3  — POST /inquiry endpoint
Phase 4  — C1 WorkflowEngine
Phase 5  — LLM client utility (Groq)
Phase 6  — Intake pipeline (A1 + A2 + C2 + BackgroundTask)
Phase 7  — A3 Matching (local embeddings + pgvector)
Phase 8  — A5 Communication service
Phase 9  — APScheduler + all scheduler jobs
Phase 10 — GET endpoints (client + ops reads)
Phase 11 — Permits (A4)
Phase 12 — Analytics (C5)
Phase 13 — A6 Nurturing + C4 Follow-up
Phase 14 — JWT auth wired across all endpoints
Phase 15 — System resilience + observability
```

**Why this order:**
- C1 must exist before any pipeline can run
- LLM client must exist before A1/A2
- A1/A2 must work before matching (A3) is meaningful
- Comms (A5) must exist before scheduler jobs that trigger sends
- Scheduler requires comms to be functional
- Auth is the last thing wired — every endpoint works without it first, auth is an overlay

---

## PHASE 1 — Foundation ✅ COMPLETE

**Completed:**
- FastAPI + Uvicorn + Pydantic v2
- Neon PostgreSQL via async SQLAlchemy
- `.env` / `.env.example` configured
- `Client`, `Lead`, `WorkflowState` models
- Tables created and verified in Neon
- `/health` endpoint

**Git tag:** `v0.1.0-foundation`

---

## PHASE 2 — Schema Completion (All Models)

*All DB models must exist before any service builds on them.*

### Step 2.1 — Correct the Vector Dimension

**CRITICAL CORRECTION:** The vector column on `locations` must be `Vector(384)` not `Vector(1536)`.

`all-MiniLM-L6-v2` produces **384-dimensional** vectors. Using 1536 would store and query incompatible data.

```python
# app/models/location.py
from pgvector.sqlalchemy import Vector

class Location(Base):
    __tablename__ = "locations"
    id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name         = Column(String(255), nullable=False)
    type         = Column(String(100), nullable=False)
    address      = Column(Text, nullable=False)
    available    = Column(Boolean, nullable=False, default=True)
    embedding    = Column(Vector(384), nullable=True)   # ← 384, NOT 1536
    metadata_    = Column("metadata", JSONB, nullable=False, default=dict)
    created_at   = Column(TIMESTAMPTZ, nullable=False, server_default=func.now())
```

### Step 2.2 — Add Remaining Models

**Files to create:**
```
app/models/location.py
app/models/booking.py
app/models/permit.py
app/models/communications_log.py
app/models/system_error.py
```

**`booking.py`:**
```python
class Booking(Base):
    __tablename__ = "bookings"
    id             = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lead_id        = Column(UUID(as_uuid=True), ForeignKey("leads.id"), nullable=False)
    client_id      = Column(UUID(as_uuid=True), ForeignKey("clients.id"), nullable=False)
    location_id    = Column(UUID(as_uuid=True), ForeignKey("locations.id"), nullable=False)
    status         = Column(String(50), nullable=False, default="confirmed")
    shoot_date     = Column(Date, nullable=True)
    shoot_end_date = Column(Date, nullable=True)
    budget         = Column(Numeric(12, 2), nullable=True)
    notes          = Column(Text, nullable=True)
    created_at     = Column(TIMESTAMPTZ, nullable=False, server_default=func.now())
    updated_at     = Column(TIMESTAMPTZ, nullable=False, server_default=func.now())
```

**`permit.py`:**
```python
class Permit(Base):
    __tablename__ = "permits"
    id               = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    booking_id       = Column(UUID(as_uuid=True), ForeignKey("bookings.id"), nullable=False)
    permit_type      = Column(String(100), nullable=False)
    status           = Column(String(50), nullable=False, default="pending")
    checklist        = Column(JSONB, nullable=False, default=dict)
    rejection_notes  = Column(Text, nullable=True)
    created_at       = Column(TIMESTAMPTZ, nullable=False, server_default=func.now())
    updated_at       = Column(TIMESTAMPTZ, nullable=False, server_default=func.now())
```

**`communications_log.py`:**
```python
class CommunicationsLog(Base):
    __tablename__ = "communications_log"
    id            = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lead_id       = Column(UUID(as_uuid=True), ForeignKey("leads.id"), nullable=True)
    booking_id    = Column(UUID(as_uuid=True), ForeignKey("bookings.id"), nullable=True)
    template_name = Column(String(100), nullable=False)
    channel       = Column(String(20), nullable=False)   # 'email' | 'whatsapp'
    status        = Column(String(20), nullable=False, default="pending")  # 'pending'|'sent'|'failed'
    sent_at       = Column(TIMESTAMPTZ, nullable=True)
    error_detail  = Column(Text, nullable=True)
    created_at    = Column(TIMESTAMPTZ, nullable=False, server_default=func.now())
```

**`system_error.py`:**
```python
class SystemError(Base):
    __tablename__ = "system_errors"
    id         = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source     = Column(String(100), nullable=False)
    lead_id    = Column(UUID(as_uuid=True), ForeignKey("leads.id"), nullable=True)
    error_type = Column(String(100), nullable=False)
    message    = Column(Text, nullable=False)
    detail     = Column(JSONB, nullable=False, default=dict)
    created_at = Column(TIMESTAMPTZ, nullable=False, server_default=func.now())
```

### Step 2.3 — Run Alembic Migration

```bash
alembic revision --autogenerate -m "add_remaining_models_384_vector"
alembic upgrade head
```

### Step 2.4 — Enable pgvector + Create Index

```sql
-- Run once on Neon if not already present
CREATE EXTENSION IF NOT EXISTS vector;

-- After migration, create the similarity search index
-- ivfflat with lists=50 is correct for hundreds of locations
CREATE INDEX idx_locations_embedding ON locations
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 50);
```

### Verification

```sql
-- Confirm all 8 tables exist
\dt

-- Confirm vector column is 384 dimensions
SELECT column_name, udt_name
FROM information_schema.columns
WHERE table_name = 'locations' AND column_name = 'embedding';

-- Insert a test location with a 384-dim zero vector to confirm column accepts it
INSERT INTO locations (name, type, address, available)
VALUES ('Test Location', 'industrial', 'Mumbai', true);
```

**Git commit:** `feat: all remaining models, Vector(384) for all-MiniLM-L6-v2`
**Git tag:** `v0.2.0-schema-complete`

---

## PHASE 3 — POST /inquiry Endpoint

*Client + Lead creation, initial WorkflowState. No auth yet. No pipeline yet.*

### Step 3.1 — Schemas

**File:** `app/api/schemas/intake.py`

```python
from pydantic import BaseModel, model_validator
from typing import Optional
import uuid


class ContactSchema(BaseModel):
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    company: Optional[str] = None

    @model_validator(mode="after")
    def email_or_phone_required(self):
        if not self.email and not self.phone:
            raise ValueError("Either email or phone is required")
        return self


class DatesSchema(BaseModel):
    start: Optional[str] = None
    end: Optional[str] = None


class BudgetSchema(BaseModel):
    min: Optional[float] = None
    max: Optional[float] = None
    currency: Optional[str] = "INR"


class InquiryRequest(BaseModel):
    contact: ContactSchema
    shoot_type: str
    dates: Optional[DatesSchema] = None
    budget: Optional[BudgetSchema] = None
    location_type: Optional[str] = None
    crew_size: Optional[int] = None
    requirements: Optional[str] = None


class InquiryResponse(BaseModel):
    lead_id: uuid.UUID
    client_id: uuid.UUID
    status: str
    message: str
```

### Step 3.2 — Route

**File:** `app/api/routes/intake.py`

```python
from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.models.client import Client
from app.models.lead import Lead
from app.models.workflow_state import WorkflowState
from app.api.schemas.intake import InquiryRequest, InquiryResponse

router = APIRouter()


@router.post("/inquiry", response_model=InquiryResponse, status_code=202)
async def submit_inquiry(
    body: InquiryRequest,
    db: AsyncSession = Depends(get_db),
):
    # Step 1: Lookup or create client
    client = None

    if body.contact.email:
        result = await db.execute(
            select(Client).where(Client.email == body.contact.email)
        )
        client = result.scalar_one_or_none()

    if client is None and body.contact.phone:
        result = await db.execute(
            select(Client).where(Client.phone == body.contact.phone)
        )
        client = result.scalar_one_or_none()

    if client is None:
        client = Client(
            name=body.contact.name,
            email=body.contact.email,
            phone=body.contact.phone,
            profile_data={"company": body.contact.company} if body.contact.company else {},
        )
        db.add(client)
        await db.flush()  # get client.id before lead FK

    # Step 2: Build intake_data
    intake_data = {
        "shoot_type": body.shoot_type,
        "dates": body.dates.model_dump() if body.dates else None,
        "budget": body.budget.model_dump() if body.budget else None,
        "location_type": body.location_type,
        "crew_size": body.crew_size,
        "requirements": body.requirements,
        "contact": body.contact.model_dump(),
    }

    # Step 3: Create lead
    lead = Lead(
        client_id=client.id,
        status="new",
        intake_data=intake_data,
        missing_fields=[],
        clarification_count=0,
    )
    db.add(lead)
    await db.flush()  # get lead.id before workflow_state FK

    # Step 4: Write initial workflow_state row
    ws = WorkflowState(
        lead_id=lead.id,
        previous_state="",
        new_state="new",
        trigger="inquiry_submission",
        actor="api",
    )
    db.add(ws)

    # Step 5: Single atomic commit
    await db.commit()

    return InquiryResponse(
        lead_id=lead.id,
        client_id=client.id,
        status="new",
        message="Inquiry received.",
    )
```

### Step 3.3 — Register Router

```python
# app/main.py
from app.api.routes.intake import router as intake_router
app.include_router(intake_router)
```

### Verification

```bash
# Full payload
curl -X POST http://localhost:8000/inquiry \
  -H "Content-Type: application/json" \
  -d '{
    "contact": {"name": "Arjun Mehta", "email": "arjun@test.com"},
    "shoot_type": "commercial",
    "dates": {"start": "2025-03-10", "end": "2025-03-12"},
    "budget": {"min": 50000, "max": 80000, "currency": "INR"},
    "location_type": "industrial warehouse"
  }'
# → 202 with lead_id and client_id

# Missing shoot_type
curl -X POST http://localhost:8000/inquiry \
  -d '{"contact": {"name": "Test", "email": "t@t.com"}}'
# → 422

# Missing both email and phone
curl -X POST http://localhost:8000/inquiry \
  -d '{"contact": {"name": "Test"}, "shoot_type": "commercial"}'
# → 422
```

```sql
-- Confirm atomic write: exactly 1 of each
SELECT * FROM clients ORDER BY created_at DESC LIMIT 1;
SELECT * FROM leads ORDER BY created_at DESC LIMIT 1;
SELECT * FROM workflow_state ORDER BY created_at DESC LIMIT 1;

-- Re-submit with same email → same client_id, new lead_id
```

**Git commit:** `feat: POST /inquiry — atomic client + lead + workflow_state`
**Git tag:** `v0.3.0-intake-endpoint`

---

## PHASE 4 — C1 WorkflowEngine

*State machine. All subsequent phases depend on this. Build before any pipeline.*

### Step 4.1 — Custom Exceptions

**File:** `app/core/exceptions.py`

```python
class LeadNotFound(Exception):
    def __init__(self, lead_id):
        super().__init__(f"Lead not found: {lead_id}")

class InvalidTransition(Exception):
    def __init__(self, current: str, target: str):
        super().__init__(f"Invalid transition: {current} → {target}")

class LLMFailure(Exception): ...
class IntakeParseFailure(Exception): ...
class ReadinessFailure(Exception): ...
class MatchingFailure(Exception): ...
```

### Step 4.2 — WorkflowEngine

**File:** `app/services/core/workflow_engine.py`

```python
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.lead import Lead
from app.models.workflow_state import WorkflowState
from app.core.exceptions import LeadNotFound, InvalidTransition

ALLOWED_TRANSITIONS = {
    "new":                  ["needs_info", "ready"],
    "needs_info":           ["ready", "inactive"],
    "ready":                ["matching_in_progress"],
    "matching_in_progress": ["needs_clarification", "matched", "manual_review"],
    "needs_clarification":  ["matching_in_progress"],
    "matched":              ["ready", "booked", "inactive"],
    "booked":               ["permit_pending"],
    "permit_pending":       ["permit_submitted"],
    "permit_submitted":     ["permit_in_review"],
    "permit_in_review":     ["permit_approved", "permit_rejected"],
    "permit_rejected":      ["permit_pending"],
    "permit_approved":      ["coordination"],
    "coordination":         ["closed"],
    "inactive":             ["needs_info", "archived"],
    "manual_review":        ["ready"],
    "archived":             [],
    "closed":               [],
}


class WorkflowEngine:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def transition(
        self,
        lead_id: UUID,
        target_state: str,
        context: dict,
    ) -> Lead:
        """
        Execution sequence (strict):
        1. Load lead from DB
        2. Validate target_state is in ALLOWED_TRANSITIONS[current_state]
        3. Apply clarification_count guard if applicable
        4. Execute downstream callable if provided (raises on failure)
        5. Write new lead.status — ONLY if step 4 succeeded
        6. Append workflow_state row
        7. Commit and return updated lead
        """

        # Step 1: Load lead
        result = await self.db.execute(select(Lead).where(Lead.id == lead_id))
        lead = result.scalar_one_or_none()
        if not lead:
            raise LeadNotFound(lead_id)

        current_state = lead.status

        # Step 2: Validate transition
        if target_state not in ALLOWED_TRANSITIONS.get(current_state, []):
            raise InvalidTransition(current_state, target_state)

        # Step 3: Clarification count guard
        # If model wants to re-run matching after clarification but count is exhausted,
        # force manual_review instead
        if (current_state == "needs_clarification"
                and target_state == "matching_in_progress"
                and lead.clarification_count >= 1):
            target_state = "manual_review"

        # Step 4: Execute downstream action (optional)
        # Pass as context["downstream"] = async callable
        # If it raises, state does NOT advance
        downstream = context.get("downstream")
        if downstream:
            await downstream()

        # Step 5: Write new state — only reached if step 4 succeeded
        lead.status = target_state
        lead.updated_at = func.now()

        if target_state == "needs_clarification":
            lead.clarification_count += 1

        if current_state == "manual_review" and target_state == "ready":
            lead.clarification_count = 0

        # Step 6: Append audit row (never updated, never deleted)
        ws = WorkflowState(
            lead_id=lead.id,
            previous_state=current_state,
            new_state=target_state,
            trigger=context.get("trigger", "unknown"),
            actor=context.get("actor", "system"),
        )
        self.db.add(ws)

        # Step 7: Commit
        await self.db.commit()
        await self.db.refresh(lead)

        return lead
```

### Verification

```python
# Unit tests — run these before moving to Phase 5

# valid transition
lead = create_test_lead(status="new")
result = await engine.transition(lead.id, "ready", context={"trigger": "test", "actor": "test"})
assert result.status == "ready"
# workflow_state row exists: previous="new", new="ready"

# invalid transition
with pytest.raises(InvalidTransition):
    await engine.transition(lead.id, "booked", context={...})

# terminal state
lead_closed = create_test_lead(status="closed")
with pytest.raises(InvalidTransition):
    await engine.transition(lead_closed.id, "ready", context={...})

# clarification count guard
lead_clarif = create_test_lead(status="needs_clarification", clarification_count=1)
result = await engine.transition(lead_clarif.id, "matching_in_progress", context={...})
assert result.status == "manual_review"  # forced override

# manual_review → ready resets count
lead_mr = create_test_lead(status="manual_review", clarification_count=1)
result = await engine.transition(lead_mr.id, "ready", context={...})
assert result.clarification_count == 0
```

```sql
-- After each test transition, verify audit trail
SELECT previous_state, new_state, trigger, actor, created_at
FROM workflow_state
WHERE lead_id = '<test_lead_id>'
ORDER BY created_at;
-- Every transition must have exactly one row
```

**Git commit:** `feat: C1 WorkflowEngine — transition map, state guard, audit log`

---

## PHASE 5 — LLM Client Utility (Groq)

*Shared utility. All AI services (A1, A2, A4, A5, A6) call this. Build once.*

**File:** `app/services/ai/llm_client.py`

```python
import groq
import httpx
import structlog
import time
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

logger = structlog.get_logger()
_client = groq.AsyncGroq()   # reads GROQ_API_KEY from environment


# Retry on rate limits and transient server errors only.
# Do NOT retry on 400 (bad request) or 401 (auth).
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    retry=retry_if_exception_type((groq.RateLimitError, groq.InternalServerError)),
)
async def call(
    messages: list[dict],
    system: str,
    max_tokens: int = 1024,
    temperature: float = 0.0,
    service_name: str = "unknown",
    lead_id: str | None = None,
) -> str:
    """
    Shared Groq LLM call utility.

    Returns the assistant message content as a string.
    Raises LLMFailure after 3 exhausted retries.
    Logs every call: model, tokens, latency.

    Retry schedule:
    - Attempt 1: immediate
    - Attempt 2: ~2s + jitter
    - Attempt 3: ~8s + jitter
    - After attempt 3: raises groq.RateLimitError or groq.InternalServerError
    """
    start = time.time()

    full_messages = [{"role": "system", "content": system}] + messages

    response = await _client.chat.completions.create(
        model="llama3-8b-8192",          # fast, sufficient for A1/A2 tasks
        messages=full_messages,
        max_tokens=max_tokens,
        temperature=temperature,
    )

    latency_ms = round((time.time() - start) * 1000)
    usage = response.usage

    logger.info(
        "llm_call",
        service=service_name,
        model=response.model,
        input_tokens=usage.prompt_tokens,
        output_tokens=usage.completion_tokens,
        total_tokens=usage.total_tokens,
        latency_ms=latency_ms,
        lead_id=lead_id,
    )

    return response.choices[0].message.content


# For tasks needing structured JSON output
async def call_json(
    messages: list[dict],
    system: str,
    service_name: str = "unknown",
    lead_id: str | None = None,
) -> str:
    """
    Same as call() but instructs the model to return only valid JSON.
    Caller is responsible for json.loads() and validation.
    System prompt must include the JSON schema instruction.
    """
    json_system = (
        system
        + "\n\nYou MUST respond with only valid JSON. "
        + "No preamble. No explanation. No markdown fences."
    )
    return await call(
        messages=messages,
        system=json_system,
        temperature=0.0,
        service_name=service_name,
        lead_id=lead_id,
    )
```

**Environment variable required:**
```bash
# .env
GROQ_API_KEY=gsk_...
```

### Verification

```python
# Smoke test — call llm_client directly
import asyncio
from app.services.ai import llm_client

async def test():
    result = await llm_client.call(
        messages=[{"role": "user", "content": "Say hello in one word."}],
        system="You are a helpful assistant.",
        service_name="smoke_test",
    )
    print(result)  # Should print: Hello

asyncio.run(test())
```

```bash
# Confirm structured log output on every call:
# {"event": "llm_call", "service": "smoke_test", "model": "llama3-8b-8192",
#  "input_tokens": N, "output_tokens": N, "latency_ms": N}
```

**Git commit:** `feat: Groq LLM client utility — retry, structured logging, JSON mode`

---

## PHASE 6 — Intake Pipeline (A1 + A2 + C2 + BackgroundTask)

*Moves leads from 'new' to 'ready' or 'needs_info' asynchronously.*

### Step 6.1 — A1 IntakeService

**File:** `app/services/ai/intake_service.py`

```python
import json
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.lead import Lead
from app.services.ai import llm_client
from app.core.exceptions import IntakeParseFailure

SYSTEM_PROMPT = """You are a data extraction assistant for a film location agency.
Extract structured shoot requirements from the inquiry data provided.
Respond with ONLY valid JSON. No preamble. No explanation.

JSON schema:
{
  "shoot_type": "string",
  "dates": {"start": "YYYY-MM-DD or null", "end": "YYYY-MM-DD or null"},
  "budget": {"min": number or null, "max": number or null, "currency": "string"},
  "location_type": "string or null",
  "crew_size": number or null,
  "requirements": "string or null"
}

Rules:
- Normalise ambiguous budgets: "around 50k" → {"min": 45000, "max": 55000}
- If a field is genuinely absent, use null — do not invent values
- Dates must be ISO format or null"""


async def parse(lead_id: UUID, db: AsyncSession) -> dict:
    """
    Load lead.intake_data from DB.
    Call Groq to extract structured fields.
    Return structured dict.
    Raises IntakeParseFailure on LLM error or parse error.
    """
    result = await db.execute(select(Lead).where(Lead.id == lead_id))
    lead = result.scalar_one_or_none()
    if not lead:
        raise IntakeParseFailure(f"Lead {lead_id} not found")

    raw = json.dumps(lead.intake_data)
    user_message = f"Extract structured data from this inquiry:\n\n{raw}"

    try:
        raw_output = await llm_client.call_json(
            messages=[{"role": "user", "content": user_message}],
            system=SYSTEM_PROMPT,
            service_name="A1",
            lead_id=str(lead_id),
        )
        structured = json.loads(raw_output)
    except (json.JSONDecodeError, Exception) as e:
        raise IntakeParseFailure(f"A1 parse failed for lead {lead_id}: {e}") from e

    # Write structured fields back to lead
    lead.intake_data = {**lead.intake_data, **structured}
    await db.commit()

    return structured
```

### Step 6.2 — A2 ReadinessService

**File:** `app/services/ai/readiness_service.py`

```python
import json
from uuid import UUID
from dataclasses import dataclass
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.ai import llm_client
from app.core.exceptions import ReadinessFailure

READINESS_THRESHOLD = 0.80

SYSTEM_PROMPT = """You are a lead qualification assistant for a film location agency.
Evaluate whether this inquiry has enough information to proceed to location matching.

Required fields:
- contact (name + email or phone)
- shoot_type
- dates (start AND end — must be specific, not vague)
- budget (min AND max — must be a usable range, not vague like "around something")
- location_type

Scoring rules:
- Each required field that is present AND usable = 0.20
- A field that is present but unusable (vague, contradictory, impossible) = 0.00
- Score = sum of usable required fields / 5

Respond with ONLY valid JSON:
{
  "score": 0.0 to 1.0,
  "status": "ready" or "needs_info",
  "missing_fields": ["field_name", ...],
  "reasoning": "one sentence"
}"""


@dataclass
class ReadinessResult:
    score: float
    status: str
    missing_fields: list[str]
    reasoning: str


async def score(
    lead_id: UUID,
    structured_data: dict,
    db: AsyncSession,
) -> ReadinessResult:
    """
    Score lead completeness via Groq.
    Threshold: score >= 0.80 → 'ready', else 'needs_info'.
    Raises ReadinessFailure on LLM or parse error.
    """
    user_message = f"Evaluate this inquiry:\n\n{json.dumps(structured_data)}"

    try:
        raw_output = await llm_client.call_json(
            messages=[{"role": "user", "content": user_message}],
            system=SYSTEM_PROMPT,
            service_name="A2",
            lead_id=str(lead_id),
        )
        data = json.loads(raw_output)
    except (json.JSONDecodeError, Exception) as e:
        raise ReadinessFailure(f"A2 scoring failed for lead {lead_id}: {e}") from e

    score_val = float(data.get("score", 0.0))
    status = "ready" if score_val >= READINESS_THRESHOLD else "needs_info"

    return ReadinessResult(
        score=score_val,
        status=status,
        missing_fields=data.get("missing_fields", []),
        reasoning=data.get("reasoning", ""),
    )
```

### Step 6.3 — C2 RoutingService

**File:** `app/services/core/routing_service.py`

```python
from dataclasses import dataclass
from app.services.ai.readiness_service import ReadinessResult


@dataclass
class RoutingDecision:
    action: str
    target_state: str


class RoutingService:
    """
    Pure logic. No LLM. No DB. No side effects.
    Receives ReadinessResult, returns RoutingDecision.
    """

    def route(self, readiness_result: ReadinessResult) -> RoutingDecision:
        if readiness_result.status == "ready":
            return RoutingDecision(
                action="start_matching",
                target_state="matching_in_progress",
            )
        return RoutingDecision(
            action="trigger_followup",
            target_state="needs_info",
        )


routing_service = RoutingService()
```

### Step 6.4 — System Error Logger

**File:** `app/core/error_logger.py`

```python
import traceback
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.system_error import SystemError


async def log_system_error(
    db: AsyncSession,
    source: str,
    lead_id: UUID | None,
    error: Exception,
) -> None:
    entry = SystemError(
        source=source,
        lead_id=lead_id,
        error_type=type(error).__name__,
        message=str(error),
        detail={"traceback": traceback.format_exc()},
    )
    db.add(entry)
    await db.commit()
```

### Step 6.5 — Pipeline Function

**File:** `app/pipelines/intake_pipeline.py`

```python
from uuid import UUID
from sqlalchemy import select

from app.db.session import get_async_session
from app.services.ai import intake_service, readiness_service
from app.services.core.routing_service import routing_service
from app.services.core.workflow_engine import WorkflowEngine
from app.core.exceptions import IntakeParseFailure, ReadinessFailure, InvalidTransition
from app.core.error_logger import log_system_error
from app.models.lead import Lead


async def run_intake_pipeline(lead_id: UUID) -> None:
    """
    Runs A1 → A2 → C2 → C1.transition() in sequence.
    Each step depends on the previous.
    Failure at any step: log to system_errors, return.
    Lead stays in its current state. No re-raise.
    """
    async with get_async_session() as db:
        engine = WorkflowEngine(db)

        # A1: Parse raw intake_data into structured fields
        try:
            structured_data = await intake_service.parse(lead_id, db)
        except IntakeParseFailure as e:
            await log_system_error(db, "intake_pipeline", lead_id, e)
            return

        # A2: Score completeness
        try:
            readiness_result = await readiness_service.score(lead_id, structured_data, db)
        except ReadinessFailure as e:
            await log_system_error(db, "intake_pipeline", lead_id, e)
            return

        # Update lead with readiness data
        result = await db.execute(select(Lead).where(Lead.id == lead_id))
        lead = result.scalar_one_or_none()
        if lead:
            lead.readiness_score = readiness_result.score
            lead.missing_fields = readiness_result.missing_fields
            await db.commit()

        # C2: Route to next state
        routing_decision = routing_service.route(readiness_result)

        # C1: Transition
        try:
            await engine.transition(
                lead_id=lead_id,
                target_state=routing_decision.target_state,
                context={
                    "trigger": "intake_pipeline",
                    "actor": "workflow_engine",
                },
            )
        except (InvalidTransition, Exception) as e:
            await log_system_error(db, "intake_pipeline", lead_id, e)
```

### Step 6.6 — Wire BackgroundTask into POST /inquiry

```python
# Update intake route to accept BackgroundTasks:

@router.post("/inquiry", response_model=InquiryResponse, status_code=202)
async def submit_inquiry(
    body: InquiryRequest,
    background_tasks: BackgroundTasks,          # ← add
    db: AsyncSession = Depends(get_db),
):
    # ... existing client/lead/workflow_state creation ...

    await db.commit()

    # Enqueue pipeline AFTER commit — lead must exist in DB before pipeline reads it
    background_tasks.add_task(run_intake_pipeline, lead.id)  # ← add

    return InquiryResponse(...)
```

### Verification

```bash
# Full payload with all fields
curl -X POST http://localhost:8000/inquiry -d '{...full payload...}'
# → 202 immediately

# Wait 5–15 seconds (Groq latency + 2 LLM calls)

# Check lead status
SELECT id, status, readiness_score, missing_fields FROM leads ORDER BY created_at DESC LIMIT 1;
# → status should be 'ready' or 'needs_info'
# → readiness_score populated

# Check audit trail
SELECT previous_state, new_state, trigger FROM workflow_state WHERE lead_id = '<id>';
# → Row 1: "" → "new" (trigger: inquiry_submission)
# → Row 2: "new" → "ready" OR "new" → "needs_info" (trigger: intake_pipeline)

# Submit incomplete payload (no dates, no budget)
# → Lead should land in 'needs_info'
# → missing_fields column populated with ["dates", "budget"]

# Check system_errors if pipeline fails
SELECT source, error_type, message FROM system_errors ORDER BY created_at DESC LIMIT 5;
```

**Git commit:** `feat: A1 intake parser (Groq), A2 readiness scorer (Groq), C2 router, intake pipeline BackgroundTask`
**Git tag:** `v0.4.0-intake-pipeline`

---

## PHASE 7 — A3 Matching Service (local embeddings + pgvector)

### Step 7.1 — Embedding Client (sentence-transformers, local)

**File:** `app/services/ai/embedding_client.py`

```python
from sentence_transformers import SentenceTransformer
import asyncio

# Loaded once at import time. Stays in memory.
# all-MiniLM-L6-v2 → 384-dimensional vectors
_model = SentenceTransformer("all-MiniLM-L6-v2")

EMBEDDING_DIM = 384  # must match Vector(384) in schema


def _embed_sync(text: str) -> list[float]:
    """Synchronous embedding — run in thread pool to avoid blocking event loop."""
    return _model.encode(text, normalize_embeddings=True).tolist()


async def embed_text(text: str) -> list[float]:
    """Async wrapper. Runs CPU-bound model in thread pool."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _embed_sync, text)


async def embed_batch(texts: list[str]) -> list[list[float]]:
    """Batch embed for ingestion efficiency."""
    loop = asyncio.get_event_loop()
    embeddings = await loop.run_in_executor(
        None,
        lambda: _model.encode(texts, normalize_embeddings=True).tolist()
    )
    return embeddings
```

**Why `run_in_executor`:** sentence-transformers is CPU-bound. Calling it directly in an async function blocks the event loop. `run_in_executor` moves it to a thread pool, keeping the event loop free.

### Step 7.2 — Location Ingestion Endpoint

**File:** `app/api/routes/admin.py`

```python
@router.post("/admin/locations", status_code=201)
async def create_location(body: LocationCreateRequest, db: AsyncSession = Depends(get_db)):
    # Build description string for embedding
    description = f"{body.name} {body.type} {body.address} {body.metadata.get('amenities', '')}"
    embedding = await embed_text(description)

    location = Location(
        name=body.name,
        type=body.type,
        address=body.address,
        available=body.available,
        embedding=embedding,       # 384-dim list
        metadata_=body.metadata,
    )
    db.add(location)
    await db.commit()
    return {"location_id": str(location.id)}


@router.put("/admin/locations/{location_id}")
async def update_location(location_id: UUID, body: LocationUpdateRequest, db: AsyncSession = Depends(get_db)):
    # On update, recompute embedding
    result = await db.execute(select(Location).where(Location.id == location_id))
    location = result.scalar_one_or_none()
    if not location:
        raise HTTPException(status_code=404)

    description = f"{location.name} {location.type} {location.address}"
    location.embedding = await embed_text(description)
    # Update other fields...
    await db.commit()
```

### Step 7.3 — A3 MatchingService

**File:** `app/services/ai/matching_service.py`

```python
import json
from uuid import UUID
from dataclasses import dataclass
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.services.ai.embedding_client import embed_text
from app.services.ai import llm_client
from app.core.exceptions import MatchingFailure

SIMILARITY_THRESHOLD = 0.65


@dataclass
class RankedLocation:
    location_id: str
    name: str
    score: float
    reasoning: str


@dataclass
class MatchingResult:
    result_type: str                    # 'matched' | 'needs_clarification' | 'failed'
    shortlist: list[RankedLocation] | None = None
    clarification_question: str | None = None


RANKING_SYSTEM = """You are a location matching assistant for a film location agency.
You will receive a client's shoot requirements and a list of candidate locations.
Rank the locations from most to least suitable. Remove any that are clearly unsuitable.
For each kept location, write one sentence explaining why it fits.

Respond with ONLY valid JSON:
{
  "ranked_locations": [
    {"location_id": "uuid", "reasoning": "one sentence"}
  ]
}"""


async def match(
    lead_id: UUID,
    intake_data: dict,
    db: AsyncSession,
) -> MatchingResult:
    """
    1. Build query string from intake_data
    2. Embed query with all-MiniLM-L6-v2 (384 dims)
    3. pgvector cosine similarity query against locations table
    4. LLM ranks and filters the candidate shortlist
    5. Return MatchingResult

    Threshold: top score >= 0.65 → matched
               top score < 0.65 → needs_clarification (first attempt) or failed (second)
    """

    # Build query string
    parts = [
        intake_data.get("shoot_type", ""),
        intake_data.get("location_type", ""),
        intake_data.get("requirements", ""),
    ]
    query_text = " ".join(p for p in parts if p)

    if not query_text.strip():
        raise MatchingFailure(f"Cannot match lead {lead_id}: no usable query text")

    # Embed query (384 dims, same model as ingestion)
    query_embedding = await embed_text(query_text)

    # pgvector cosine similarity query
    # <=> is cosine distance; 1 - distance = similarity
    similarity_query = text("""
        SELECT id::text, name, metadata,
               1 - (embedding <=> CAST(:query_vec AS vector)) AS similarity_score
        FROM locations
        WHERE available = true
          AND embedding IS NOT NULL
        ORDER BY embedding <=> CAST(:query_vec AS vector)
        LIMIT 10
    """)

    result = await db.execute(
        similarity_query,
        {"query_vec": str(query_embedding)}
    )
    candidates = result.fetchall()

    if not candidates:
        return MatchingResult(result_type="failed")

    top_score = candidates[0].similarity_score

    if top_score < SIMILARITY_THRESHOLD:
        return MatchingResult(
            result_type="needs_clarification",
            clarification_question=(
                "Could you tell us more about the specific environment you need? "
                "For example: indoor or outdoor, urban or rural, any specific facilities required?"
            ),
        )

    # LLM ranks the candidates
    candidates_payload = [
        {
            "location_id": row.id,
            "name": row.name,
            "score": round(row.similarity_score, 3),
            "metadata": row.metadata,
        }
        for row in candidates
    ]

    user_message = (
        f"Client requirements:\n{json.dumps(intake_data)}\n\n"
        f"Candidate locations:\n{json.dumps(candidates_payload)}"
    )

    try:
        raw_output = await llm_client.call_json(
            messages=[{"role": "user", "content": user_message}],
            system=RANKING_SYSTEM,
            service_name="A3",
            lead_id=str(lead_id),
        )
        ranked_data = json.loads(raw_output)
    except Exception as e:
        raise MatchingFailure(f"A3 LLM ranking failed for lead {lead_id}: {e}") from e

    # Map LLM output back to candidates with scores
    score_map = {row.id: row.similarity_score for row in candidates}
    shortlist = [
        RankedLocation(
            location_id=item["location_id"],
            name=next((r.name for r in candidates if r.id == item["location_id"]), ""),
            score=round(score_map.get(item["location_id"], 0.0), 3),
            reasoning=item.get("reasoning", ""),
        )
        for item in ranked_data.get("ranked_locations", [])
    ]

    return MatchingResult(result_type="matched", shortlist=shortlist)
```

### Step 7.4 — Matching Pipeline

**File:** `app/pipelines/matching_pipeline.py`

```python
async def run_matching_pipeline(lead_id: UUID) -> None:
    async with get_async_session() as db:
        engine = WorkflowEngine(db)

        result = await db.execute(select(Lead).where(Lead.id == lead_id))
        lead = result.scalar_one_or_none()
        if not lead:
            return

        try:
            matching_result = await matching_service.match(lead_id, lead.intake_data, db)
        except MatchingFailure as e:
            await log_system_error(db, "matching_pipeline", lead_id, e)
            return

        if matching_result.result_type == "matched":
            lead.intake_data = {
                **lead.intake_data,
                "matched_locations": [
                    {"location_id": l.location_id, "name": l.name,
                     "score": l.score, "reasoning": l.reasoning}
                    for l in matching_result.shortlist
                ]
            }
            await db.commit()

            await engine.transition(
                lead_id=lead_id,
                target_state="matched",
                context={"trigger": "matching_pipeline", "actor": "workflow_engine"},
            )

        elif matching_result.result_type == "needs_clarification":
            lead.intake_data = {
                **lead.intake_data,
                "clarification_question": matching_result.clarification_question,
            }
            await db.commit()

            await engine.transition(
                lead_id=lead_id,
                target_state="needs_clarification",
                context={"trigger": "matching_pipeline", "actor": "workflow_engine"},
            )

        else:  # failed
            await engine.transition(
                lead_id=lead_id,
                target_state="manual_review",
                context={"trigger": "matching_pipeline", "actor": "workflow_engine"},
            )
```

Wire into C1: when a lead transitions to `matching_in_progress`, enqueue `run_matching_pipeline`.

### Verification

```bash
# Insert 5+ test locations with embeddings via POST /admin/locations
# Submit a full inquiry → wait for intake pipeline
# If lead reaches 'ready', matching pipeline should auto-trigger

SELECT id, status, intake_data->'matched_locations' FROM leads
WHERE status IN ('matched', 'manual_review', 'needs_clarification');

# Confirm vector index is used (not a sequential scan)
EXPLAIN ANALYZE
SELECT 1 - (embedding <=> '[...384 values...]'::vector) AS score
FROM locations WHERE available = true
ORDER BY embedding <=> '[...384 values...]'::vector LIMIT 10;
# Look for "Index Scan using idx_locations_embedding"
```

**Git commit:** `feat: A3 matching — sentence-transformers 384-dim embeddings, pgvector query, Groq ranking`
**Git tag:** `v0.5.0-matching`

---

## PHASE 8 — A5 CommunicationService

*Template-first. The only outbound messaging layer.*

### Step 8.1 — Templates

**Directory:** `app/services/ai/templates/`

One `.txt` file per template. Variables use `{variable_name}` syntax.

```
shortlist_sent.txt
booking_confirmed.txt
permit_process_initiated.txt
permit_submitted_notif.txt
permit_approved_notif.txt
permit_rejected_notif.txt
coordination_started.txt
shoot_completed.txt
followup_missing_fields.txt
clarification_request.txt
inactivity_notice.txt
nurturing_reengagement.txt
ops_review_notif.txt
permit_reminder.txt
```

Example `shortlist_sent.txt`:
```
Hi {client_name},

We've found {location_count} location(s) that match your shoot requirements.

{location_list}

Please review and let us know which location you'd like to book, or if you'd like us to refine the search.
```

### Step 8.2 — CommunicationService

**File:** `app/services/ai/communication_service.py`

```python
import json
from pathlib import Path
from uuid import UUID
from dataclasses import dataclass
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.communications_log import CommunicationsLog
from app.services.ai import llm_client

TEMPLATES_DIR = Path(__file__).parent / "templates"

TONE_REWRITE_SYSTEM = """You are a professional communications editor for a film location agency.
Rewrite the message below in a warm, professional tone.

RULES (strict):
- Do NOT change any facts, dates, names, prices, or instructions
- Do NOT add information that is not in the original
- Do NOT remove any information from the original
- Only adjust phrasing and tone
- If you cannot improve the tone without breaking the rules, return the original unchanged"""


@dataclass
class CommunicationResult:
    success: bool
    log_id: UUID | None
    error: str | None = None


async def send(
    template_name: str,
    template_data: dict,
    channel: str,
    db: AsyncSession,
    lead_id: UUID | None = None,
    booking_id: UUID | None = None,
    rewrite: bool = False,
) -> CommunicationResult:
    """
    1. Load and render template
    2. (Optional) LLM tone rewrite via Groq
    3. Validate rewrite — fall back to original if invalid
    4. Send via channel provider stub
    5. Write to communications_log
    6. Return result

    CRITICAL: A5 failure never blocks state.
    State has already advanced before A5 is called.
    """

    # Step 1: Load and render template
    template_path = TEMPLATES_DIR / f"{template_name}.txt"
    if not template_path.exists():
        return CommunicationResult(success=False, log_id=None, error=f"Template not found: {template_name}")

    template = template_path.read_text()
    try:
        rendered = template.format(**template_data)
    except KeyError as e:
        return CommunicationResult(success=False, log_id=None, error=f"Missing template variable: {e}")

    message_body = rendered

    # Step 2 & 3: Optional LLM rewrite (Groq)
    if rewrite:
        try:
            rewritten = await llm_client.call(
                messages=[{"role": "user", "content": f"Rewrite this message:\n\n{rendered}"}],
                system=TONE_REWRITE_SYSTEM,
                service_name="A5",
                lead_id=str(lead_id) if lead_id else None,
            )
            # Validate: rewrite must not be shorter than 50% of original (basic sanity)
            if len(rewritten) >= len(rendered) * 0.5:
                message_body = rewritten
            # else: silently use original
        except Exception:
            pass  # LLM rewrite failure → use original, do not block send

    # Step 4: Send via channel stub
    send_success = await _send_via_channel(channel, template_data, message_body)

    # Step 5: Write to communications_log
    status = "sent" if send_success else "failed"
    log_entry = CommunicationsLog(
        lead_id=lead_id,
        booking_id=booking_id,
        template_name=template_name,
        channel=channel,
        status=status,
        error_detail=None if send_success else "Provider send failed",
    )
    if send_success:
        from datetime import datetime, timezone
        log_entry.sent_at = datetime.now(timezone.utc)

    db.add(log_entry)
    await db.commit()
    await db.refresh(log_entry)

    return CommunicationResult(success=send_success, log_id=log_entry.id)


async def _send_via_channel(channel: str, template_data: dict, body: str) -> bool:
    """Channel stubs. Replace internals with real provider without changing A5's interface."""
    if channel == "email":
        return await _send_email(template_data.get("email", ""), body)
    elif channel == "whatsapp":
        return await _send_whatsapp(template_data.get("phone", ""), body)
    return False


async def _send_email(to: str, body: str) -> bool:
    # Stub — log and return True
    import structlog
    structlog.get_logger().info("email_stub", to=to, body_length=len(body))
    return True


async def _send_whatsapp(to: str, body: str) -> bool:
    # Stub — log and return True
    import structlog
    structlog.get_logger().info("whatsapp_stub", to=to, body_length=len(body))
    return True
```

**Git commit:** `feat: A5 communication service — template rendering, Groq tone rewrite, comms log, channel stubs`

---

## PHASE 9 — APScheduler + All Scheduler Jobs

*All 5 jobs. Wire after A5 is working since jobs trigger sends.*

### Step 9.1 — Scheduler Init

```python
# app/main.py
from contextlib import asynccontextmanager
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.scheduler.jobs import register_all_jobs

scheduler = AsyncIOScheduler()

@asynccontextmanager
async def lifespan(app):
    register_all_jobs(scheduler)
    scheduler.start()
    yield
    scheduler.shutdown()

app = FastAPI(lifespan=lifespan)
```

### Step 9.2 — Jobs

**File:** `app/scheduler/jobs.py`

```python
import structlog
from app.db.session import get_async_session
from app.services.core.workflow_engine import WorkflowEngine
from app.core.error_logger import log_system_error
from app.core.exceptions import InvalidTransition

logger = structlog.get_logger()


def register_all_jobs(scheduler):
    scheduler.add_job(scan_inactive_leads,  "interval", hours=6,                      id="scan_inactive")
    scheduler.add_job(scan_followup_leads,  "interval", hours=2,                      id="scan_followup")
    scheduler.add_job(run_permit_reminders, "cron",     hour=8,                       id="permit_reminder")
    scheduler.add_job(run_nurturing_runner, "cron",     day_of_week="mon", hour=9,    id="nurturing")
    scheduler.add_job(refresh_analytics,    "cron",     hour=1,                       id="analytics_refresh")


async def scan_inactive_leads():
    """Every 6h. Leads in needs_info or matched, updated_at > 7 days → transition to inactive."""
    from sqlalchemy import select, text
    from app.models.lead import Lead

    found = actioned = skipped = 0
    async with get_async_session() as db:
        result = await db.execute(text("""
            SELECT id FROM leads
            WHERE status IN ('needs_info', 'matched')
            AND updated_at < NOW() - INTERVAL '7 days'
        """))
        lead_ids = [row.id for row in result.fetchall()]
        found = len(lead_ids)
        engine = WorkflowEngine(db)

        for lead_id in lead_ids:
            try:
                await engine.transition(
                    lead_id=lead_id,
                    target_state="inactive",
                    context={"trigger": "inactivity_scanner", "actor": "inactivity_scanner"},
                )
                actioned += 1
            except InvalidTransition:
                skipped += 1  # Already inactive — idempotent
            except Exception as e:
                await log_system_error(db, "inactivity_scanner", lead_id, e)

    logger.info("inactivity_scanner", found=found, actioned=actioned, skipped=skipped)


async def scan_followup_leads():
    """Every 2h. Leads in needs_info < 72h, no follow-up sent → C4 → A5."""
    # Implementation: query leads + LEFT JOIN communications_log
    # Pass to C4.build_followup() → A5.send()
    pass  # implement after C4 is built (Phase 13)


async def run_permit_reminders():
    """Daily 8am. Permits past expected_approval_days → A5 reminder."""
    pass  # implement after A4 is built (Phase 11)


async def run_nurturing_runner():
    """Weekly Monday 9am. Inactive leads → A6 → A5."""
    pass  # implement after A6 is built (Phase 13)


async def refresh_analytics():
    """Daily 1am. C5 aggregations → analytics_snapshots."""
    pass  # implement after C5 is built (Phase 12)
```

**Git commit:** `feat: APScheduler init, job registration, scan_inactive_leads implemented`

---

## PHASE 10 — GET Endpoints (Client + Ops Reads)

```
GET  /client/dashboard          → leads + bookings for current client
GET  /client/leads/:id          → single lead detail (enforced by client_id)
POST /client/leads/:id          → update inquiry fields, re-trigger pipeline
GET  /ops/pipeline              → all leads, filterable by status, paginated
GET  /ops/leads/:id             → full detail + audit trail + comms
POST /ops/leads/:id/action      → manual transition or reassign
GET  /ops/bookings              → booking pipeline with permit status
POST /ops/bookings/:id/permit   → update permit status (calls A4)
GET  /ops/analytics             → aggregated metrics (reads analytics_snapshots)
POST /internal/retry/:lead_id   → re-trigger intake pipeline
```

No auth wired yet — add role checks in Phase 14.

**Git commit:** `feat: client + ops read/write endpoints, internal retry`

---

## PHASE 11 — A4 PermitService

```
generate_checklist(booking_id, shoot_type, location, duration)
  → Groq infers permit types + authority + expected_approval_days
  → Rules-based fallback for common types (no Groq needed)
  → Creates permits record, status: pending

update_permit_status(permit_id, new_status, notes)
  → Valid transitions: pending→submitted, submitted→in_review,
    in_review→approved|rejected, rejected→pending
  → On approved: returns result → C1 transitions to coordination
  → On rejected: returns result → C1 stays in permit_rejected, A5 notifies
```

Complete `run_permit_reminders` scheduler job in this phase.

**Git commit:** `feat: A4 permit service, permit lifecycle, permit_reminders scheduler job`

---

## PHASE 12 — C5 AnalyticsService

```
run_aggregations()
  → volume_by_status: COUNT(*) GROUP BY status
  → conversion_rate: leads reaching booked / total new leads in period
  → avg_time_to_booking_days: AVG(booked_at - created_at)
  → drop_off_by_stage: leads that left at each stage
  → active_leads: status NOT IN ('closed','archived','inactive')
  → Write to analytics_snapshots table

GET /ops/analytics reads from analytics_snapshots (not live query)
```

**Git commit:** `feat: C5 analytics, analytics_snapshots table, GET /ops/analytics`

---

## PHASE 13 — A6 Nurturing + C4 FollowUp

```
C4 FollowUpService (pure logic, no LLM):
  build_followup(lead_id, missing_fields)
  → Returns FollowUpContext(template_name, template_data, channel)
  → Does NOT send — returns context to caller → caller passes to A5

A6 NurturingService (Groq):
  generate(lead_id, client_id)
  → Load client history + prior comms from DB
  → Groq generates personalised re-engagement body
  → Fallback to standard template if Groq fails
  → Returns NurturingMessage → caller passes to A5
```

Complete `scan_followup_leads` and `run_nurturing_runner` scheduler jobs in this phase.

**Git commit:** `feat: C4 follow-up service, A6 nurturing service, remaining scheduler jobs`

---

## PHASE 14 — JWT Auth (Wired Across All Endpoints)

```python
# app/api/dependencies.py

async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    # Decode JWT, extract sub, role, client_id
    # Raise 401 if invalid/expired
    # Raise 403 if role insufficient

async def require_ops(user = Depends(get_current_user)) -> User:
    if user.role != "ops":
        raise HTTPException(status_code=403)
    return user
```

**JWT payload:**
```json
{
  "sub": "user_id",
  "role": "client",
  "client_id": "uuid",
  "exp": 1234567890
}
```

Add `Depends(get_current_user)` to every route. Add `Depends(require_ops)` to ops routes. Client routes filter all DB queries by `client_id = current_user.client_id`.

**Git commit:** `feat: JWT auth wired across all endpoints, role-based access`

---

## PHASE 15 — System Resilience + Observability

### Structured Logging

```python
import structlog

structlog.configure(
    processors=[
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ]
)
```

Every log line includes `request_id` and `lead_id` where relevant.

### Request ID Middleware

```python
@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response
```

### Extended Health Check

```python
@app.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)):
    checks = {}

    try:
        await db.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as e:
        checks["database"] = f"error: {e}"

    try:
        await db.execute(text("SELECT vector_dims('[1,2,3]'::vector)"))
        checks["pgvector"] = "ok"
    except Exception:
        checks["pgvector"] = "unavailable"

    checks["scheduler"] = "ok" if scheduler.running else "stopped"

    overall = "healthy" if all(v == "ok" for v in checks.values()) else "degraded"
    return JSONResponse(
        status_code=200 if overall == "healthy" else 503,
        content={"status": overall, "checks": checks},
    )
```

**Git commit:** `feat: structured logging, request_id middleware, extended health check`
**Git tag:** `v1.0.0`

---

## Git Tag Summary

| Tag | Phase | What's In It |
|---|---|---|
| `v0.1.0-foundation` | 1 | Scaffold, DB, base models, health |
| `v0.2.0-schema-complete` | 2 | All 8 models, Vector(384), pgvector index |
| `v0.3.0-intake-endpoint` | 3 | POST /inquiry, atomic write |
| `v0.4.0-intake-pipeline` | 6 | A1 (Groq), A2 (Groq), C2, BackgroundTask |
| `v0.5.0-matching` | 7 | A3, sentence-transformers 384-dim, pgvector |
| `v0.6.0-comms` | 8 | A5, templates, comms log |
| `v0.7.0-scheduler` | 9 | APScheduler, scan_inactive_leads |
| `v0.8.0-permits` | 11 | A4, permit lifecycle |
| `v0.9.0-full-pipeline` | 13 | A6, C4, all scheduler jobs complete |
| `v1.0.0` | 15 | Auth, logging, observability — production ready |

---

## Cross-Verification Queries

Run after each phase to confirm DB state matches expectations.

```sql
-- Pipeline overview
SELECT status, COUNT(*) FROM leads GROUP BY status ORDER BY count DESC;

-- Audit trail for a specific lead
SELECT previous_state, new_state, trigger, actor, created_at
FROM workflow_state WHERE lead_id = '<uuid>' ORDER BY created_at;

-- Every transition must have exactly one row here.
-- A lead.status change without a row here means C1 was bypassed.

-- Failed communications
SELECT template_name, channel, error_detail, created_at
FROM communications_log WHERE status = 'failed' ORDER BY created_at DESC;

-- System errors last 24h
SELECT source, error_type, message, created_at
FROM system_errors WHERE created_at > NOW() - INTERVAL '24 hours';

-- Leads stuck (no state update in 2h, not in terminal state)
SELECT id, status, updated_at FROM leads
WHERE status NOT IN ('closed', 'archived')
AND updated_at < NOW() - INTERVAL '2 hours';

-- Confirm vector dimension is 384
SELECT vector_dims(embedding) FROM locations WHERE embedding IS NOT NULL LIMIT 1;
-- Must return 384

-- Permits overdue
SELECT p.id, p.status, p.updated_at,
       (p.checklist->>'expected_approval_days')::int AS expected_days
FROM permits p
WHERE p.status IN ('pending', 'submitted', 'in_review')
AND p.updated_at < NOW() - INTERVAL '1 day' *
    (p.checklist->>'expected_approval_days')::int;
```

---

## Stack Alignment Confirmation

| Concern | v1 (wrong) | v2 (correct) |
|---|---|---|
| LLM SDK | `anthropic.AsyncAnthropic()` | `groq.AsyncGroq()` |
| LLM model | `claude-sonnet-4-20250514` | `llama3-8b-8192` |
| LLM retry exceptions | `anthropic.RateLimitError` | `groq.RateLimitError` |
| Embedding library | `openai` (cloud) | `sentence-transformers` (local) |
| Embedding model | `text-embedding-3-small` | `all-MiniLM-L6-v2` |
| Vector dimension | 1536 | 384 |
| pgvector column | `Vector(1536)` | `Vector(384)` |
| Auth introduced at | Phase 3 | Phase 14 |
| Scheduler introduced at | Phase 11 | Phase 9 |
| Analytics introduced at | Phase 13 | Phase 12 |
| C1 logic | ✅ unchanged | ✅ unchanged |
| workflow_state design | ✅ unchanged | ✅ unchanged |
| Agent boundaries | ✅ unchanged | ✅ unchanged |
| Async system design | ✅ unchanged | ✅ unchanged |