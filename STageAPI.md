## POST /inquiry — Implementation

---

### 1. Endpoint Design

**Request:**
```json
{
  "contact": {
    "name": "Arjun Mehta",
    "email": "arjun@blueframe.in",
    "phone": "+91-9876543210",
    "company": "Blue Frame Productions"
  },
  "shoot_type": "commercial",
  "dates": { "start": "2025-03-10", "end": "2025-03-12" },
  "budget": { "min": 50000, "max": 80000, "currency": "INR" },
  "location_type": "industrial warehouse",
  "crew_size": 25,
  "requirements": "Loading dock, 3-phase power"
}
```

**Required fields:** `contact.name` + (`contact.email` OR `contact.phone`) + `shoot_type`

**Response `202 Accepted`:**
```json
{
  "lead_id": "uuid",
  "client_id": "uuid",
  "status": "new",
  "message": "Inquiry received."
}
```

**Error `422`:**
```json
{
  "error": "validation_error",
  "detail": "shoot_type is required",
  "request_id": "uuid"
}
```

---

### 2. File Structure

```
/api/routes/intake.py       ← endpoint lives here
/api/schemas/intake.py      ← Pydantic request/response models
```

No new services. No new abstractions. DB session from existing `get_db`.

---

### 3. Schemas — `/api/schemas/intake.py`

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

---

### 4. Route — `/api/routes/intake.py`

```python
import uuid
from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from db.session import get_db
from models.client import Client
from models.lead import Lead
from models.workflow_state import WorkflowState
from api.schemas.intake import InquiryRequest, InquiryResponse

router = APIRouter()


@router.post("/inquiry", response_model=InquiryResponse, status_code=202)
async def submit_inquiry(
    body: InquiryRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    # ── Step 1: Look up or create Client ──────────────────────────────────
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
        await db.flush()   # assigns client.id before Lead FK needs it

    # ── Step 2: Build intake_data dict ────────────────────────────────────
    intake_data = {
        "shoot_type": body.shoot_type,
        "dates": body.dates.model_dump() if body.dates else None,
        "budget": body.budget.model_dump() if body.budget else None,
        "location_type": body.location_type,
        "crew_size": body.crew_size,
        "requirements": body.requirements,
        "contact": body.contact.model_dump(),
    }

    # ── Step 3: Create Lead ───────────────────────────────────────────────
    lead = Lead(
        client_id=client.id,
        status="new",
        intake_data=intake_data,
        missing_fields=[],
        clarification_count=0,
    )
    db.add(lead)
    await db.flush()   # assigns lead.id before WorkflowState FK needs it

    # ── Step 4: Write initial WorkflowState row ───────────────────────────
    workflow_entry = WorkflowState(
        lead_id=lead.id,
        previous_state="",          # no prior state on creation
        new_state="new",
        trigger="inquiry_submission",
        actor="api",
    )
    db.add(workflow_entry)

    # ── Step 5: Commit everything atomically ──────────────────────────────
    await db.commit()

    return InquiryResponse(
        lead_id=lead.id,
        client_id=client.id,
        status="new",
        message="Inquiry received.",
    )
```

---

### 5. Register Route — `main.py`

```python
from api.routes.intake import router as intake_router

app.include_router(intake_router)
```

---

### 6. DB Interaction Flow (Step-by-Step)

```
POST /inquiry arrives
│
├─ Pydantic validates body
│   └─ 422 immediately if contact.name missing,
│      shoot_type missing, or no email/phone
│
├─ Step 1: SELECT client by email → match or None
│          SELECT client by phone → match or None
│          INSERT client if no match → flush (get ID)
│
├─ Step 2: Build intake_data dict from body
│
├─ Step 3: INSERT lead (status="new") → flush (get ID)
│
├─ Step 4: INSERT workflow_state row
│           previous_state = ""
│           new_state      = "new"
│           trigger        = "inquiry_submission"
│           actor          = "api"
│
└─ Step 5: db.commit() — single atomic commit
           202 returned with lead_id + client_id
```

---

### 7. Key Decisions

| Decision | Rationale |
|---|---|
| `flush()` before `commit()` | Gets DB-assigned IDs for FK references without a separate transaction |
| Single `commit()` at the end | Client + Lead + WorkflowState are atomic — none without the others |
| `previous_state = ""` on creation | No prior state exists; distinguishes from real transitions |
| No BackgroundTask yet | Phase 3 scope only — pipeline trigger comes in next phase |
| Lookup by email first, phone second | Matches C3 profile logic without importing C3 |

---

### What's Not Here (By Design)

- No `run_intake_pipeline` call — that's Phase 4
- No auth middleware — wire in when JWT is ready
- No `request_id` header injection — that's middleware scope
- No C3 service class — the lookup is inline as specified (no new abstractions)