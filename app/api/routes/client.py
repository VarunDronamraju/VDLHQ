from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.dependencies import AuthenticatedUser, get_current_user
from app.api.schemas.lead import ClientDashboard, LeadDetail, LeadUpdate
from app.db.session import get_db
from app.models.core import Booking, Client, Lead, Location
from app.pipelines.intake_pipeline import run_intake_pipeline

router = APIRouter()


@router.get("/dashboard", response_model=ClientDashboard)
async def get_dashboard(
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user),
):
    """
    Returns leads and bookings for the authenticated client.
    """
    client_id = user.client_id
    if not client_id and user.role != "ops":
        raise HTTPException(status_code=403, detail="Access denied")

    # Verify client exists
    client_check = await db.execute(select(Client).where(Client.id == client_id))
    if not client_check.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Client not found")

    # If ops is viewing, they might need a client_id in query, but for now we follow user's context
    if not client_id:
        return ClientDashboard(leads=[], bookings=[])

    # DEMO MODE: If using the fixed demo ID, show all leads for visibility
    is_demo = str(client_id) == "00000000-0000-0000-0000-000000000001"

    # Fetch leads
    stmt = select(Lead).order_by(Lead.created_at.desc())
    if not is_demo:
        stmt = stmt.where(Lead.client_id == client_id)

    leads_result = await db.execute(stmt)
    leads = leads_result.scalars().all()

    # Fetch bookings for this client
    bookings_result = (
        await db.execute(select(Booking, Location.name.label("location_name")).join(Location).where(Booking.lead_id.in_([lead.id for lead in leads])).order_by(Booking.created_at.desc()))
        if leads
        else None
    )

    bookings_data = []
    if bookings_result:
        for row in bookings_result.all():
            booking, loc_name = row
            booking_brief = {
                "id": booking.id,
                "lead_id": booking.lead_id,
                "location_id": booking.location_id,
                "status": booking.status,
                "shoot_date": booking.shoot_date,
                "location_name": loc_name,
            }
            bookings_data.append(booking_brief)

    return ClientDashboard(leads=leads, bookings=bookings_data)


@router.get("/leads/{lead_id}", response_model=LeadDetail)
async def get_lead_detail(
    lead_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user),
):
    """
    Returns full detail for a single lead, restricted to the owning client.
    """
    client_id = user.client_id
    if not client_id and user.role != "ops":
        raise HTTPException(status_code=403, detail="Access denied")

    if not client_id:  # Ops with no client_id accessing client route
        raise HTTPException(status_code=403, detail="Client ID required")
    stmt = select(Lead).where(Lead.id == lead_id, Lead.client_id == client_id).options(selectinload(Lead.workflow_history), selectinload(Lead.communications))
    result = await db.execute(stmt)
    lead = result.scalar_one_or_none()

    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found or access denied")

    return lead


@router.post("/leads/{lead_id}", response_model=LeadDetail)
async def update_lead_inquiry(
    lead_id: UUID,
    body: LeadUpdate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user),
):
    """
    Updates inquiry fields and re-triggers the intake pipeline.
    """
    client_id = user.client_id
    if not client_id and user.role != "ops":
        raise HTTPException(status_code=403, detail="Access denied")

    if not client_id:
        raise HTTPException(status_code=403, detail="Client ID required")
    result = await db.execute(select(Lead).where(Lead.id == lead_id, Lead.client_id == client_id))
    lead = result.scalar_one_or_none()

    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found or access denied")

    # Update intake_data
    # We merge or replace? Spec says "update inquiry fields", usually means merge
    lead.intake_data = {**lead.intake_data, **body.intake_data}

    # We reset the status to 'new' if it was 'needs_info' to re-trigger properly?
    # Or just re-run pipeline on current status.
    # For now, just re-run pipeline.

    await db.commit()
    await db.refresh(lead)

    # Re-trigger intake pipeline
    background_tasks.add_task(run_intake_pipeline, lead.id)

    # Reload with relationships for response
    stmt = select(Lead).where(Lead.id == lead_id).options(selectinload(Lead.workflow_history), selectinload(Lead.communications))
    result = await db.execute(stmt)
    return result.scalar_one()
