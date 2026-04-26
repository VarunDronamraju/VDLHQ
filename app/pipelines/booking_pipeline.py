from uuid import UUID

import structlog

from app.db.session import get_async_session
from app.services.ai.permit_service import permit_service
from app.services.core.workflow_engine import WorkflowEngine

logger = structlog.get_logger()


async def run_booking_pipeline(lead_id: UUID, booking_id: UUID) -> None:
    """
    Triggers after a lead is transitioned to 'booked'.
    1. A4.generate_checklist
    2. C1.transition(lead_id, 'permit_pending')
    """
    async with get_async_session() as db:
        engine = WorkflowEngine(db)

        try:
            # 1. Generate checklist (A4)
            # This creates the Permit record
            await permit_service.generate_checklist(booking_id, db)

            # 2. Transition lead to permit_pending (C1)
            await engine.transition(lead_id=lead_id, target_state="permit_pending", trigger="booking_pipeline_initiated", actor="system")

            await db.commit()
            logger.info("booking_pipeline_complete", lead_id=str(lead_id), booking_id=str(booking_id))

        except Exception as e:
            logger.error("booking_pipeline_failed", lead_id=str(lead_id), error=str(e))
            # Lead stays in 'booked' if this fails. Ops can re-trigger manually if needed.
