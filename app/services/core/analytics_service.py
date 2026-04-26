# No imports needed here from datetime


from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.core import AnalyticsSnapshot, Lead, LeadStatus, WorkflowState


class AnalyticsService:
    async def run_aggregations(self, db: AsyncSession) -> AnalyticsSnapshot:
        """
        C5 - Aggregates lead metrics and saves a snapshot.
        """
        # 1. Status distribution
        status_stmt = select(Lead.status, func.count(Lead.id)).group_by(Lead.status)
        status_res = await db.execute(status_stmt)
        status_counts = {s.value: count for s, count in status_res.all()}

        # 2. Totals
        total_leads = sum(status_counts.values())

        active_statuses = [s.value for s in LeadStatus if s.value not in ["closed", "archived", "inactive"]]
        active_leads_count = sum(status_counts.get(s, 0) for s in active_statuses)

        # 3. Conversion Rate
        # leads reaching booked / total leads
        # Note: A more accurate conversion would be "ever reached booked",
        # but for simplicity we'll use current booked status or those past it.
        # However, per spec: "leads reaching booked / total new leads"
        # We'll use status.booked and beyond.
        post_booking_statuses = ["booked", "permit_pending", "permit_submitted", "permit_in_review", "permit_approved", "permit_rejected", "coordination", "closed"]
        reached_booked_count = sum(status_counts.get(s, 0) for s in post_booking_statuses)
        conversion_rate = (reached_booked_count / total_leads) if total_leads > 0 else 0.0

        # 4. Avg Time to Booking
        # We find the 'booked' transition for each lead
        subq = select(WorkflowState.lead_id, func.min(WorkflowState.created_at).label("booked_at")).where(WorkflowState.new_state == "booked").group_by(WorkflowState.lead_id).subquery()

        avg_time_stmt = select(func.avg(func.extract("epoch", subq.c.booked_at - Lead.created_at) / 86400)).join(subq, Lead.id == subq.c.lead_id)

        avg_res = await db.execute(avg_time_stmt)
        avg_time_days = avg_res.scalar() or 0.0

        # 5. Create Snapshot
        snapshot = AnalyticsSnapshot(
            status_counts=status_counts,
            total_leads=total_leads,
            active_leads_count=active_leads_count,
            conversion_rate=round(conversion_rate, 4),
            avg_time_to_booking_days=round(float(avg_time_days), 2),
        )

        db.add(snapshot)
        await db.flush()
        await db.refresh(snapshot)

        return snapshot

    async def get_latest_snapshot(self, db: AsyncSession) -> AnalyticsSnapshot:
        """
        Reads the most recent snapshot from the DB.
        """
        stmt = select(AnalyticsSnapshot).order_by(AnalyticsSnapshot.created_at.desc()).limit(1)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()


analytics_service = AnalyticsService()
