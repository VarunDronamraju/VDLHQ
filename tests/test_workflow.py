import uuid

import pytest
from sqlalchemy import select

from app.core.exceptions import InvalidTransition
from app.db.session import get_async_session
from app.models.core import Client, Lead, LeadStatus, WorkflowState
from app.services.core.workflow_engine import WorkflowEngine


async def _create_lead(status: LeadStatus = LeadStatus.new) -> Lead:
    async with get_async_session() as db:
        client = Client(
            name="Workflow Test Client",
            email=f"workflow_{uuid.uuid4().hex[:10]}@example.com",
            phone="+910000000111",
            profile_data={},
        )
        db.add(client)
        await db.flush()

        lead = Lead(
            client_id=client.id,
            status=status,
            intake_data={"shoot_type": "commercial"},
        )
        db.add(lead)
        await db.commit()
        await db.refresh(lead)
        return lead


@pytest.mark.asyncio
async def test_valid_transition_succeeds():
    lead = await _create_lead(status=LeadStatus.new)
    async with get_async_session() as db:
        engine = WorkflowEngine(db)
        result = await engine.transition(
            lead_id=lead.id,
            target_state="ready",
            trigger="pytest_valid_transition",
            actor="pytest",
        )
        assert result["previous_state"] == "new"
        assert result["new_state"] == "ready"


@pytest.mark.asyncio
async def test_invalid_transition_fails_and_preserves_state():
    lead = await _create_lead(status=LeadStatus.new)
    async with get_async_session() as db:
        engine = WorkflowEngine(db)
        with pytest.raises(InvalidTransition):
            await engine.transition(
                lead_id=lead.id,
                target_state="booked",
                trigger="pytest_invalid_transition",
                actor="pytest",
            )

        refreshed = (await db.execute(select(Lead).where(Lead.id == lead.id))).scalar_one()
        assert refreshed.status == LeadStatus.new


@pytest.mark.asyncio
async def test_workflow_log_created():
    lead = await _create_lead(status=LeadStatus.new)
    async with get_async_session() as db:
        engine = WorkflowEngine(db)
        await engine.transition(
            lead_id=lead.id,
            target_state="ready",
            trigger="pytest_log_check",
            actor="pytest",
        )

        log = (
            (await db.execute(select(WorkflowState).where(WorkflowState.lead_id == lead.id, WorkflowState.trigger == "pytest_log_check").order_by(WorkflowState.created_at.desc())))
            .scalars()
            .first()
        )
        assert log is not None
        assert log.previous_state == "new"
        assert log.new_state == "ready"
