from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.api.schemas.intake import InquiryRequest, InquiryResponse
from app.db.session import get_db
from app.models.core import Client, Lead, LeadStatus, WorkflowState
from app.pipelines.intake_pipeline import run_intake_pipeline

router = APIRouter()


@router.post("/inquiry", response_model=InquiryResponse, status_code=202)
async def submit_inquiry(
    body: InquiryRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    # ── Step 1: Look up or create Client ──────────────────────────────────
    client = None

    if body.contact.email:
        result = await db.execute(select(Client).filter(Client.email == body.contact.email))
        client = result.scalar_one_or_none()

    if client is None and body.contact.phone:
        result = await db.execute(select(Client).filter(Client.phone == body.contact.phone))
        client = result.scalar_one_or_none()

    if client is None:
        # Capture company and role in profile_data
        profile_data = {
            "company": body.contact.company or (body.client_profile.get("company") if body.client_profile else None),
            "role": body.contact.role or (body.client_profile.get("role") if body.client_profile else None),
        }
        client = Client(
            name=body.contact.name,
            email=body.contact.email,
            phone=body.contact.phone,
            profile_data={k: v for k, v in profile_data.items() if v is not None},
        )
        db.add(client)
        await db.flush()

    # ── Step 2: Build intake_data dict ────────────────────────────────────
    # We include everything in intake_data to ensure it's logged and available for AI
    intake_data = {
        "shoot_type": body.shoot_type,
        "dates": body.dates.model_dump() if body.dates and hasattr(body.dates, 'model_dump') else body.dates,
        "budget": body.budget,
        "location_type": body.location_type,
        "crew_size": body.crew_size,
        "requirements": body.requirements,
        "contact": body.contact.model_dump(),
        "client_profile": body.client_profile,
        "context": body.context, # CRITICAL: Store the location/production context
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
    await db.flush()

    # ── Step 4: Write initial WorkflowState row ───────────────────────────
    workflow_entry = WorkflowState(
        lead_id=lead.id,
        previous_state=None,
        new_state="new",
        trigger="inquiry_submission",
        actor="api",
    )
    db.add(workflow_entry)

    # ── Step 5: Commit everything atomically ──────────────────────────────
    await db.commit()

    # ── Step 6: Enqueue Intake Pipeline ───────────────────────────────────
    background_tasks.add_task(run_intake_pipeline, lead.id)

    return InquiryResponse(
        lead_id=lead.id,
        client_id=client.id,
        status="new",
        message="Inquiry received. Processing...",
    )
