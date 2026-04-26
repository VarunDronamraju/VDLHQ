from datetime import datetime, timedelta, timezone

import structlog
from sqlalchemy import select

from app.core.error_logger import log_system_error
from app.core.exceptions import InvalidTransition
from app.db.session import get_async_session
from app.models.core import Booking, Client, Lead, LeadStatus, Permit
from app.services.ai import communication_service
from app.services.core.analytics_service import analytics_service
from app.services.core.workflow_engine import WorkflowEngine

logger = structlog.get_logger()


def register_all_jobs(scheduler):
    # Every 6 hours: move long-stale leads to 'inactive'
    scheduler.add_job(scan_inactive_leads, "interval", hours=6, id="scan_inactive", replace_existing=True)

    # Every 2 hours: send follow-ups for leads in 'needs_info'
    scheduler.add_job(scan_followup_leads, "interval", hours=2, id="scan_followup", replace_existing=True)

    # Daily at 8am: permit reminders
    scheduler.add_job(run_permit_reminders, "cron", hour=8, id="permit_reminder", replace_existing=True)

    # Weekly on Monday at 9am: nurturing runner
    scheduler.add_job(run_nurturing_runner, "cron", day_of_week="mon", hour=9, id="nurturing", replace_existing=True)

    # Daily at 1am: refresh analytics
    scheduler.add_job(refresh_analytics, "cron", hour=1, id="analytics_refresh", replace_existing=True)


async def scan_inactive_leads():
    """
    Every 6h. Leads in 'needs_info' or 'matched', updated_at > 7 days → transition to 'inactive'.
    """
    logger.info("job_start", job="scan_inactive_leads")
    found = actioned = skipped = 0

    async with get_async_session() as db:
        threshold = datetime.now(timezone.utc) - timedelta(days=7)

        stmt = select(Lead.id).filter(Lead.status.in_([LeadStatus.needs_info, LeadStatus.matched]), Lead.updated_at < threshold)

        result = await db.execute(stmt)
        lead_ids = [row[0] for row in result.fetchall()]
        found = len(lead_ids)

        engine = WorkflowEngine(db)
        for lead_id in lead_ids:
            try:
                await engine.transition(lead_id=lead_id, target_state="inactive", trigger="inactivity_scanner", actor="system")
                await db.commit()
                actioned += 1
            except InvalidTransition:
                skipped += 1
            except Exception as e:
                await log_system_error(db, "scan_inactive_leads", lead_id, e)

    logger.info("job_complete", job="scan_inactive_leads", found=found, actioned=actioned, skipped=skipped)


async def scan_followup_leads():
    """
    Every 2h. Leads in 'needs_info' updated > 24h ago, send follow-up if not already sent recently.
    """
    logger.info("job_start", job="scan_followup_leads")

    async with get_async_session() as db:
        threshold = datetime.now(timezone.utc) - timedelta(hours=24)

        # Select leads in needs_info that haven't been updated in 24h
        stmt = select(Lead, Client).join(Client).filter(Lead.status == LeadStatus.needs_info, Lead.updated_at < threshold)

        result = await db.execute(stmt)
        for lead, client in result.all():
            try:
                # Send follow-up via A5
                await communication_service.send(
                    template_name="followup_missing_fields",
                    template_data={
                        "client_name": client.name,
                        "shoot_type": lead.intake_data.get("shoot_type", "shoot"),
                        "missing_fields_list": "- " + "\n- ".join(lead.missing_fields) if lead.missing_fields else "Inquiry details",
                        "email": client.email,
                    },
                    channel="email",
                    db=db,
                    lead_id=lead.id,
                    rewrite=True,
                )

                # Update updated_at to prevent re-processing in next 2h
                lead.updated_at = datetime.now(timezone.utc)
                await db.commit()

            except Exception as e:
                await log_system_error(db, "scan_followup_leads", lead.id, e)

    logger.info("job_complete", job="scan_followup_leads")


async def run_permit_reminders():
    """
    Daily. Scans permits in 'pending', 'submitted', or 'in_review'
    that are past their expected_approval_days.
    """
    logger.info("job_start", job="run_permit_reminders")
    async with get_async_session() as db:
        # 1. Fetch active permits with their booking and client
        stmt = (
            select(Permit, Booking, Client)
            .join(Booking, Permit.booking_id == Booking.id)
            .join(Client, Booking.client_id == Client.id)
            .filter(Permit.status.in_(["pending", "submitted", "in_review"]))
        )
        result = await db.execute(stmt)
        for permit, booking, client in result.all():
            try:
                # 2. Check if overdue
                # expected_approval_days defaults to 3 if missing
                expected_days = permit.checklist.get("expected_approval_days", 3)
                if isinstance(expected_days, str):
                    expected_days = int(expected_days)

                threshold = permit.updated_at + timedelta(days=expected_days)
                if datetime.now(timezone.utc) > threshold:
                    # 3. Notify via A5
                    await communication_service.send(
                        template_name="permit_reminder",
                        template_data={"client_name": client.name, "permit_type": permit.permit_type, "status": permit.status, "email": client.email, "booking_id": str(booking.id)},
                        channel="email",
                        db=db,
                        booking_id=booking.id,
                        rewrite=True,
                    )

                    # Update updated_at to prevent spamming reminders every run if it runs often
                    # (though it's a daily cron, so it's fine)
                    permit.updated_at = datetime.now(timezone.utc)
                    await db.commit()
            except Exception as e:
                await log_system_error(db, "run_permit_reminders", booking.lead_id, e)

    logger.info("job_complete", job="run_permit_reminders")


async def run_nurturing_runner():
    """Stub for Phase 13"""
    logger.info("job_stub", job="run_nurturing_runner")


async def refresh_analytics():
    """
    Periodic job to update analytics snapshots.
    """
    logger.info("job_start", job="refresh_analytics")
    async with get_async_session() as db:
        try:
            snapshot = await analytics_service.run_aggregations(db)
            await db.commit()
            logger.info("analytics_refreshed", snapshot_id=str(snapshot.id))
        except Exception as e:
            await log_system_error(db, "refresh_analytics", None, e)
