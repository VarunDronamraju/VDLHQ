from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import InvalidTransition, LeadNotFound
from app.models.core import Lead, LeadStatus, WorkflowState

ALLOWED_TRANSITIONS = {
    "new": ["needs_info", "ready"],
    "needs_info": ["ready", "inactive"],
    "ready": ["matching_in_progress"],
    "matching_in_progress": ["needs_clarification", "matched", "manual_review"],
    "needs_clarification": ["matching_in_progress"],
    "matched": ["ready", "booked", "inactive"],
    "booked": ["permit_pending"],
    "permit_pending": ["permit_submitted"],
    "permit_submitted": ["permit_in_review"],
    "permit_in_review": ["permit_approved", "permit_rejected"],
    "permit_rejected": ["permit_pending"],
    "permit_approved": ["coordination"],
    "coordination": ["closed"],
    "inactive": ["needs_info", "archived"],
    "manual_review": ["ready"],
    "archived": [],
    "closed": [],
}


class WorkflowEngine:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def transition(self, lead_id: UUID, target_state: str, trigger: str, actor: str = "system", metadata: dict = None):
        """
        Authoritative lead state transition (Async).
        """
        result = await self.db.execute(select(Lead).filter(Lead.id == lead_id))
        lead = result.scalar_one_or_none()

        if not lead:
            raise LeadNotFound(lead_id)

        current_state = lead.status.value

        try:
            target_status = LeadStatus(target_state)
        except ValueError:
            raise InvalidTransition(current_state, target_state)

        if target_state not in ALLOWED_TRANSITIONS.get(current_state, []):
            raise InvalidTransition(current_state, target_state)

        # Clarification count guard
        if current_state == "needs_clarification" and target_state == "matching_in_progress" and lead.clarification_count >= 1:
            target_state = "manual_review"
            target_status = LeadStatus.manual_review

        lead.status = target_status
        lead.updated_at = func.now()

        if target_state == "needs_clarification":
            lead.clarification_count += 1

        if current_state == "manual_review" and target_state == "ready":
            lead.clarification_count = 0

        workflow_entry = WorkflowState(lead_id=lead_id, previous_state=current_state, new_state=target_state, trigger=trigger, actor=actor)

        self.db.add(workflow_entry)
        await self.db.commit()
        await self.db.refresh(lead)

        return {"lead_id": str(lead_id), "previous_state": current_state, "new_state": target_state, "trigger": trigger}
