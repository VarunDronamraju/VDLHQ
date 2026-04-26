from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.schemas.lead import AnalyticsSnapshot, BookingDetail, LeadAction, LeadBrief, LeadDetail, PermitUpdate
from app.db.session import get_db
from app.models.core import Booking, Lead, LeadStatus, Permit
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
    db: AsyncSession = Depends(get_db),
):
    """
    Performs a manual state transition.
    """
    engine = WorkflowEngine(db)
    try:
        await engine.transition(lead_id=lead_id, target_state=body.target_state, trigger=body.trigger, actor=body.actor)
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
    Update permit status (Stub for A4 integration in Phase 11).
    """
    result = await db.execute(select(Permit).where(Permit.id == permit_id, Permit.booking_id == booking_id))
    permit = result.scalar_one_or_none()

    if not permit:
        raise HTTPException(status_code=404, detail="Permit not found")

    permit.status = body.status
    if body.rejection_notes:
        permit.rejection_notes = body.rejection_notes

    await db.commit()
    return {"status": "updated", "permit_id": str(permit_id)}


@router.get("/analytics", response_model=AnalyticsSnapshot)
async def get_analytics(
    db: AsyncSession = Depends(get_db),
):
    """
    Returns aggregated metrics (Stub for Phase 12).
    """
    # Real implementation will read from analytics_snapshots table
    # For now, we'll do a live count of lead statuses

    status_counts = {}
    for s in LeadStatus:
        res = await db.execute(select(func.count(Lead.id)).where(Lead.status == s))
        status_counts[s.value] = res.scalar()

    total_res = await db.execute(select(func.count(Lead.id)))
    total_leads = total_res.scalar()

    # Simple conversion rate (booked / total)
    booked_res = await db.execute(select(func.count(Lead.id)).where(Lead.status == LeadStatus.booked))
    booked_count = booked_res.scalar()
    conv_rate = (booked_count / total_leads) if total_leads > 0 else 0.0

    return {"status_counts": status_counts, "total_leads": total_leads, "conversion_rate": round(conv_rate, 4)}
