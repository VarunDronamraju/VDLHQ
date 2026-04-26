import uuid

import pytest
from sqlalchemy import select

from app.db.session import get_async_session
from app.models.core import Client, CommunicationsLog, Lead, LeadStatus
from app.services.ai.communication_service import send


async def _create_lead() -> Lead:
    async with get_async_session() as db:
        client = Client(
            name="Comms Test Client",
            email=f"comms_{uuid.uuid4().hex[:8]}@example.com",
            phone="+910000000901",
            profile_data={},
        )
        db.add(client)
        await db.flush()
        lead = Lead(client_id=client.id, status=LeadStatus.needs_info, intake_data={"shoot_type": "music video"}, missing_fields=["budget"])
        db.add(lead)
        await db.commit()
        await db.refresh(lead)
        return lead


@pytest.mark.asyncio
async def test_template_render_works_and_log_stored():
    lead = await _create_lead()
    async with get_async_session() as db:
        result = await send(
            template_name="followup_missing_fields",
            template_data={
                "client_name": "Comms Test Client",
                "shoot_type": "music video",
                "missing_fields_list": "- budget",
                "email": "comms@example.com",
            },
            channel="email",
            db=db,
            lead_id=lead.id,
            rewrite=False,
        )
        assert result.success is True

        log = (await db.execute(select(CommunicationsLog).where(CommunicationsLog.id == result.log_id).order_by(CommunicationsLog.created_at.desc()))).scalars().first()
        assert log is not None
        assert log.template_name == "followup_missing_fields"
        assert log.status == "sent"


@pytest.mark.asyncio
async def test_tone_rewrite_runs(monkeypatch):
    async def _fake_llm_call(*_args, **_kwargs):
        return "Warm rewritten message preserving facts."

    monkeypatch.setattr("app.services.ai.communication_service.llm_client.call", _fake_llm_call)

    lead = await _create_lead()
    async with get_async_session() as db:
        result = await send(
            template_name="followup_missing_fields",
            template_data={
                "client_name": "Comms Test Client",
                "shoot_type": "music video",
                "missing_fields_list": "- budget",
                "email": "comms@example.com",
            },
            channel="email",
            db=db,
            lead_id=lead.id,
            rewrite=True,
        )
        assert result.success is True
        assert result.log_id is not None
