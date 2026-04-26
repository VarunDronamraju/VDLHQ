import uuid

import pytest
from pydantic import ValidationError
from sqlalchemy import select

from app.api.schemas.intake import InquiryRequest
from app.core.error_logger import log_system_error
from app.core.exceptions import InvalidTransition, LLMFailure
from app.db.session import get_async_session
from app.main import health_check
from app.models.core import Client, Lead, LeadStatus, SystemError
from app.services.ai import llm_client
from app.services.ai.embedding_client import embedding_client
from app.services.core.workflow_engine import WorkflowEngine


async def _create_lead() -> Lead:
    async with get_async_session() as db:
        client = Client(
            name="Break Test Client",
            email=f"break_{uuid.uuid4().hex[:8]}@example.com",
            phone="+910000000921",
            profile_data={},
        )
        db.add(client)
        await db.flush()
        lead = Lead(client_id=client.id, status=LeadStatus.new, intake_data={"shoot_type": "ad"})
        db.add(lead)
        await db.commit()
        await db.refresh(lead)
        return lead


@pytest.mark.asyncio
async def test_invalid_state_transition_fails_safely():
    lead = await _create_lead()
    async with get_async_session() as db:
        engine = WorkflowEngine(db)
        with pytest.raises(InvalidTransition):
            await engine.transition(lead.id, "booked", "pytest_break")
        refreshed = (await db.execute(select(Lead).where(Lead.id == lead.id))).scalar_one()
        assert refreshed.status == LeadStatus.new


def test_missing_required_fields_rejected():
    with pytest.raises(ValidationError):
        InquiryRequest.model_validate({"contact": {"name": "No Contact"}, "shoot_type": "ad"})


@pytest.mark.asyncio
async def test_db_connection_failure_returns_500():
    class FakeDb:
        async def execute(self, *args, **kwargs):
            raise RuntimeError("simulated db down")

    result = await health_check(db=FakeDb())
    assert "error" in result["checks"]["database"]


@pytest.mark.asyncio
async def test_llm_failure_simulation():
    with pytest.raises(LLMFailure):
        await llm_client.call(
            messages=[{"role": "user", "content": "ping"}],
            system="reply pong",
            model="definitely-invalid-model-name",
            service_name="pytest_break",
        )


@pytest.mark.asyncio
async def test_empty_embeddings_and_error_logging():
    vector = await embedding_client.embed("")
    assert len(vector) == 384

    async with get_async_session() as db:
        error = RuntimeError("forced break error")
        await log_system_error(db, "pytest_breaks", None, error)
        latest = (await db.execute(select(SystemError).where(SystemError.source == "pytest_breaks").order_by(SystemError.created_at.desc()))).scalars().first()
        assert latest is not None
        assert latest.error_type == "RuntimeError"
