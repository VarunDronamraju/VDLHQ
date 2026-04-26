from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.schemas.lead import BookingDetail, LeadAction, LeadBrief, LeadDetail, PermitUpdate
from app.db.session import get_db
from app.models.core import Booking, Lead, LeadStatus
from app.pipelines.booking_pipeline import run_booking_pipeline
from app.services.ai.permit_service import permit_service
from app.services.core.analytics_service import analytics_service
from app.services.core.workflow_engine import WorkflowEngine

router = APIRouter()


@router.get("/pipeline", response_model=List[LeadBrief])
async def get_pipeline(
    status: Optional[LeadStatus] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns all leads, filterable by status, paginated.
    """
    stmt = select(Lead).order_by(Lead.updated_at.desc()).limit(limit).offset(offset)
    if status:
        stmt = stmt.where(Lead.status == status)

    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/leads/{lead_id}", response_model=LeadDetail)
async def get_lead_detail_ops(
    lead_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Returns full detail for a lead including audit trail and communications.
    """
    stmt = select(Lead).where(Lead.id == lead_id).options(selectinload(Lead.workflow_history), selectinload(Lead.communications))
    result = await db.execute(stmt)
    lead = result.scalar_one_or_none()

    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    return lead


@router.post("/leads/{lead_id}/action", response_model=LeadDetail)
async def lead_action(
    lead_id: UUID,
    body: LeadAction,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """
    Performs a manual state transition.
    Handles side effects like Booking creation at the API/Service boundary.
    """
    engine = WorkflowEngine(db)

    # Pre-transition logic: Create booking if target is 'booked'
    booking_id = None
    if body.target_state == "booked":
        if not body.metadata or "location_id" not in body.metadata:
            raise HTTPException(status_code=400, detail="location_id required in metadata for 'booked' transition")

        # Load lead to get client_id
        lead_res = await db.execute(select(Lead).where(Lead.id == lead_id))
        lead_obj = lead_res.scalar_one_or_none()
        if not lead_obj:
            raise HTTPException(status_code=404, detail="Lead not found")

        loc_id = body.metadata["location_id"]
        booking = Booking(
            lead_id=lead_id,
            client_id=lead_obj.client_id,
            location_id=UUID(loc_id) if isinstance(loc_id, str) else loc_id,
            status="confirmed",
        )
        db.add(booking)
        await db.flush()  # Get booking_id
        booking_id = booking.id

    try:
        await engine.transition(lead_id=lead_id, target_state=body.target_state, trigger=body.trigger, actor=body.actor, metadata=body.metadata)
        await db.commit()

        # Post-transition side effects
        if body.target_state == "booked" and booking_id:
            background_tasks.add_task(run_booking_pipeline, lead_id, booking_id)

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Return updated lead
    stmt = select(Lead).where(Lead.id == lead_id).options(selectinload(Lead.workflow_history), selectinload(Lead.communications))
    result = await db.execute(stmt)
    return result.scalar_one()


@router.get("/bookings", response_model=List[BookingDetail])
async def get_bookings_pipeline(
    db: AsyncSession = Depends(get_db),
):
    """
    Returns booking pipeline with permit status.
    """
    stmt = select(Booking).options(selectinload(Booking.permits), selectinload(Booking.client), selectinload(Booking.location)).order_by(Booking.created_at.desc())
    result = await db.execute(stmt)
    bookings = result.scalars().all()

    response = []
    for b in bookings:
        response.append(
            {
                "id": b.id,
                "lead_id": b.lead_id,
                "client_name": b.client.name,
                "location_name": b.location.name,
                "status": b.status,
                "shoot_date": b.shoot_date,
                "shoot_end_date": b.shoot_end_date,
                "permits": b.permits,
            }
        )

    return response


@router.post("/bookings/{booking_id}/permit/{permit_id}")
async def update_permit_status_endpoint(
    booking_id: UUID,
    permit_id: UUID,
    body: PermitUpdate,
    db: AsyncSession = Depends(get_db),
):
    """
    Update permit status and trigger lead state transitions.
    """
    try:
        await permit_service.update_permit_status(permit_id=permit_id, new_status=body.status, notes=body.rejection_notes, db=db)

        # 2. Trigger WorkflowEngine transition based on permit status
        engine = WorkflowEngine(db)

        # We need the lead_id from the booking
        booking = await db.get(Booking, booking_id)
        lead_id = booking.lead_id

        status_to_state = {"submitted": "permit_submitted", "in_review": "permit_in_review", "approved": "permit_approved", "rejected": "permit_rejected", "pending": "permit_pending"}

        target_state = status_to_state.get(body.status)
        if target_state:
            await engine.transition(lead_id=lead_id, target_state=target_state, trigger="permit_update", actor="ops")

            # Special case: if approved, move to coordination automatically
            if target_state == "permit_approved":
                await engine.transition(lead_id=lead_id, target_state="coordination", trigger="permit_approved_auto", actor="system")

        await db.commit()

        return {"status": "updated", "permit_id": str(permit_id), "lead_state": target_state}

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/analytics")
async def get_analytics(
    db: AsyncSession = Depends(get_db),
):
    """
    Returns the latest aggregated metrics snapshot.
    """
    snapshot = await analytics_service.get_latest_snapshot(db)
    if not snapshot:
        # If no snapshot exists, generate one on the fly (first run)
        snapshot = await analytics_service.run_aggregations(db)

    return snapshot
