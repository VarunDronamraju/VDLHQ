from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.schemas.lead import ClientDashboard, LeadDetail, LeadUpdate
from app.db.session import get_db
from app.models.core import Booking, Client, Lead, Location
from app.pipelines.intake_pipeline import run_intake_pipeline

router = APIRouter()


@router.get("/dashboard", response_model=ClientDashboard)
async def get_dashboard(
    client_id: UUID = Query(..., description="Client ID (temporary until auth)"),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns leads and bookings for the specified client.
    """
    # Verify client exists
    client_result = await db.execute(select(Client).where(Client.id == client_id))
    if not client_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Client not found")

    # Fetch leads
    leads_result = await db.execute(select(Lead).where(Lead.client_id == client_id).order_by(Lead.created_at.desc()))
    leads = leads_result.scalars().all()

    # Fetch bookings with location names
    bookings_result = await db.execute(select(Booking, Location.name.label("location_name")).join(Location).where(Booking.client_id == client_id).order_by(Booking.created_at.desc()))

    bookings_data = []
    for row in bookings_result.all():
        booking, loc_name = row
        # Manually create the object for the schema since we joined
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
    client_id: UUID = Query(..., description="Client ID for verification"),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns full detail for a single lead, restricted to the owning client.
    """
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
    client_id: UUID = Query(..., description="Client ID for verification"),
    db: AsyncSession = Depends(get_db),
):
    """
    Updates inquiry fields and re-triggers the intake pipeline.
    """
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
