import asyncio
from datetime import datetime, timedelta, timezone
from sqlalchemy import select
import structlog

from app.db.session import get_async_session
from app.models.core import Lead, LeadStatus, Client
from app.services.ai import communication_service
from app.core.error_logger import log_system_error

logger = structlog.get_logger()

async def scan_inactive_leads():
    """
    Background job to follow up with leads stuck in 'needs_info'.
    """
    logger.info("job_start", job="inactivity_scanner")
    
    async with get_async_session() as db:
        # Leads in 'needs_info' updated more than 24 hours ago
        # (For testing, we can use a shorter interval if needed)
        threshold = datetime.now(timezone.utc) - timedelta(hours=24)
        
        stmt = (
            select(Lead, Client)
            .join(Client)
            .filter(Lead.status == LeadStatus.needs_info)
            .filter(Lead.updated_at < threshold)
        )
        
        result = await db.execute(stmt)
        inactive_leads = result.all()
        
        logger.info("inactive_leads_found", count=len(inactive_leads))
        
        for lead, client in inactive_leads:
            try:
                # Send follow-up
                await communication_service.send(
                    template_name="followup_missing_fields",
                    template_data={
                        "client_name": client.name,
                        "shoot_type": lead.intake_data.get("shoot_type", "shoot"),
                        "missing_fields_list": "- " + "\n- ".join(lead.missing_fields),
                        "email": client.email
                    },
                    channel="email",
                    db=db,
                    lead_id=lead.id,
                    rewrite=True
                )
                
                # Update 'updated_at' to avoid double-processing in the next hour
                # In a real system, we'd increment a 'followup_count'
                lead.updated_at = datetime.now(timezone.utc)
                await db.commit()
                
            except Exception as e:
                await log_system_error(db, "inactivity_scanner_job", lead.id, e)

    logger.info("job_complete", job="inactivity_scanner")
