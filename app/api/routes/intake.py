from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.db.session import get_db
from app.models.core import Client, Lead, WorkflowState, LeadStatus
from app.api.schemas.intake import InquiryRequest, InquiryResponse

router = APIRouter()

@router.post("/inquiry", response_model=InquiryResponse, status_code=202)
def submit_inquiry(
    body: InquiryRequest,
    db: Session = Depends(get_db),
):
    # ── Step 1: Look up or create Client ──────────────────────────────────
    client = None

    if body.contact.email:
        client = db.query(Client).filter(Client.email == body.contact.email).first()

    if client is None and body.contact.phone:
        client = db.query(Client).filter(Client.phone == body.contact.phone).first()

    if client is None:
        client = Client(
            name=body.contact.name,
            email=body.contact.email,
            phone=body.contact.phone,
            profile_data={"company": body.contact.company} if body.contact.company else {},
        )
        db.add(client)
        db.flush()   # assigns client.id before Lead FK needs it

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
        status=LeadStatus.new,
        intake_data=intake_data,
        missing_fields=[],
        clarification_count=0,
    )
    db.add(lead)
    db.flush()   # assigns lead.id before WorkflowState FK needs it

    # ── Step 4: Write initial WorkflowState row ───────────────────────────
    workflow_entry = WorkflowState(
        lead_id=lead.id,
        previous_state=None,          # no prior state on creation
        new_state="new",
        trigger="inquiry_submission",
        actor="api",
    )
    db.add(workflow_entry)

    # ── Step 5: Commit everything atomically ──────────────────────────────
    db.commit()

    return InquiryResponse(
        lead_id=lead.id,
        client_id=client.id,
        status="new",
        message="Inquiry received.",
    )
