import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from app.db.session import get_async_session
from app.models.core import Client, CommunicationsLog, Lead, LeadStatus
from app.scheduler.jobs import scan_followup_leads


async def _create_stale_needs_info_lead() -> Lead:
    async with get_async_session() as db:
        client = Client(
            name="Scheduler Test Client",
            email=f"scheduler_{uuid.uuid4().hex[:8]}@example.com",
            phone="+910000000911",
            profile_data={},
        )
        db.add(client)
        await db.flush()
        lead = Lead(
            client_id=client.id,
            status=LeadStatus.needs_info,
            intake_data={"shoot_type": "commercial"},
            missing_fields=["dates"],
            updated_at=datetime.now(timezone.utc) - timedelta(hours=48),
        )
        db.add(lead)
        await db.commit()
        await db.refresh(lead)
        return lead


@pytest.mark.asyncio
async def test_job_executes_and_stale_lead_detected(monkeypatch):
    async def _fake_llm_call(*_args, **_kwargs):
        return "Follow-up rewrite."

    monkeypatch.setattr("app.services.ai.communication_service.llm_client.call", _fake_llm_call)

    lead = await _create_stale_needs_info_lead()
    await scan_followup_leads()

    async with get_async_session() as db:
        refreshed = (await db.execute(select(Lead).where(Lead.id == lead.id))).scalar_one()
        assert refreshed.updated_at > datetime.now(timezone.utc) - timedelta(minutes=10)

        sent = (
            (
                await db.execute(
                    select(CommunicationsLog).where(
                        CommunicationsLog.lead_id == lead.id,
                        CommunicationsLog.template_name == "followup_missing_fields",
                    )
                )
            )
            .scalars()
            .all()
        )
        assert len(sent) >= 1


@pytest.mark.asyncio
async def test_anti_spam_no_duplicate_triggers(monkeypatch):
    async def _fake_llm_call(*_args, **_kwargs):
        return "Follow-up rewrite."

    monkeypatch.setattr("app.services.ai.communication_service.llm_client.call", _fake_llm_call)

    lead = await _create_stale_needs_info_lead()
    await scan_followup_leads()
    await scan_followup_leads()

    async with get_async_session() as db:
        sent = (
            (
                await db.execute(
                    select(CommunicationsLog).where(
                        CommunicationsLog.lead_id == lead.id,
                        CommunicationsLog.template_name == "followup_missing_fields",
                    )
                )
            )
            .scalars()
            .all()
        )
        assert len(sent) == 1
