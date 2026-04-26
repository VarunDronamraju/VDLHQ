from uuid import UUID

from app.core.error_logger import log_system_error
from app.core.exceptions import IntakeParseFailure, InvalidTransition, ReadinessFailure
from app.db.session import get_async_session
from app.services.ai import intake_service, readiness_service
from app.services.core.routing_service import routing_service
from app.services.core.workflow_engine import WorkflowEngine


async def run_intake_pipeline(lead_id: UUID) -> None:
    """
    Runs A1 → A2 → C2 → C1 transition in sequence.
    This is designed to run as a BackgroundTask.
    Failure at any step is logged but does not crash the task.
    """
    async with get_async_session() as db:
        engine = WorkflowEngine(db)

        # 1. A1: Parse raw intake_data into structured fields
        try:
            structured_data = await intake_service.parse(lead_id, db)
            # Flush updates to intake_data
            await db.commit()
        except IntakeParseFailure as e:
            await log_system_error(db, "intake_pipeline", lead_id, e)
            return

        # 2. A2: Score completeness
        try:
            readiness_result = await readiness_service.score(lead_id, structured_data, db)
            # Commit updates to readiness_score and missing_fields
            await db.commit()
        except ReadinessFailure as e:
            await log_system_error(db, "intake_pipeline", lead_id, e)
            return

        # 3. C2: Route to next state
        routing_decision = routing_service.route(readiness_result.status)

        # 4. C1: Authoritative Transition
        try:
            await engine.transition(lead_id=lead_id, target_state=routing_decision.target_state, trigger="intake_pipeline", actor="system")
            await db.commit()
        except (InvalidTransition, Exception) as e:
            await log_system_error(db, "intake_pipeline", lead_id, e)
