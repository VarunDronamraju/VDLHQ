import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import update

from app.db.session import get_async_session
from app.models.core import Client, CommunicationsLog, Lead, LeadStatus
from app.scheduler.jobs import run_nurturing_runner, scan_followup_leads
from app.services.ai.nurturing_service import nurturing_service
from app.services.core.followup_service import followup_service


@pytest.mark.asyncio
async def test_followup_service_logic():
    lead_id = uuid.uuid4()
    context = followup_service.build_followup(lead_id=lead_id, client_name="Test Client", shoot_type="commercial", missing_fields=["budget", "dates"])

    assert context.template_name == "followup_missing_fields"
    assert "Test Client" in context.template_data["client_name"]
    assert "budget" in context.template_data["missing_fields_list"]
    assert "dates" in context.template_data["missing_fields_list"]
    assert context.channel == "email"


@pytest.mark.asyncio
async def test_nurturing_service_generate(monkeypatch):
    # Mock LLM
    async def mock_call(*args, **kwargs):
        return "This is a personalized re-engagement message."

    monkeypatch.setattr("app.services.ai.llm_client.call", mock_call)

    async with get_async_session() as db:
        c = Client(name="Nurture Client", email=f"nurture_{uuid.uuid4().hex}@test.com")
        db.add(c)
        await db.flush()

        lead = Lead(
            client_id=c.id,
            status=LeadStatus.inactive,
            intake_data={"shoot_type": "film", "requirements": "old warehouse"},
        )
        db.add(lead)
        await db.commit()
        lead_id = lead.id

    async with get_async_session() as db:
        res = await nurturing_service.generate(lead_id, db)

    assert "personalized" in res["body"]
    assert "film" in res["subject"]
    assert res["channel"] == "email"


@pytest.mark.asyncio
async def test_nurturing_service_fallback(monkeypatch):
    # Mock LLM Failure
    async def mock_call_fail(*args, **kwargs):
        raise Exception("Groq Error")

    monkeypatch.setattr("app.services.ai.llm_client.call", mock_call_fail)

    async with get_async_session() as db:
        c = Client(name="Fallback Client", email=f"fall_{uuid.uuid4().hex}@test.com")
        db.add(c)
        await db.flush()

        lead = Lead(client_id=c.id, status=LeadStatus.inactive, intake_data={"shoot_type": "music video"})
        db.add(lead)
        await db.commit()
        lead_id = lead.id

    async with get_async_session() as db:
        res = await nurturing_service.generate(lead_id, db)

    assert "recently added several new locations" in res["body"]
    assert "Fallback Client" in res["body"]
    assert "music video" in res["subject"]


@pytest.mark.asyncio
async def test_scan_followup_job_deduplication(monkeypatch):
    send_count = 0

    async with get_async_session() as db:
        c = Client(name="Dup Client", email=f"dup_{uuid.uuid4().hex}@test.com")
        db.add(c)
        await db.flush()

        lead = Lead(
            client_id=c.id,
            status=LeadStatus.needs_info,
            missing_fields=["budget"],
            intake_data={"shoot_type": "photo"},
        )
        db.add(lead)
        await db.commit()
        await db.refresh(lead)

        # Explicitly set old updated_at
        from sqlalchemy import update

        old_time = datetime.now(timezone.utc) - timedelta(days=2)
        await db.execute(update(Lead).where(Lead.id == lead.id).values(updated_at=old_time))
        await db.commit()
        lead_id = lead.id

    async def mock_send(**kwargs):
        nonlocal send_count
        if kwargs.get("lead_id") == lead_id:
            send_count += 1

        # Mocking the log entry that A5 would create
        async with get_async_session() as db:
            log = CommunicationsLog(lead_id=kwargs.get("lead_id"), template_name=kwargs.get("template_name"), channel=kwargs.get("channel"), status="sent")
            db.add(log)
            await db.commit()

    monkeypatch.setattr("app.services.ai.communication_service.send", mock_send)

    # Run job once
    await scan_followup_leads()
    assert send_count == 1

    # Run job again - should NOT send again due to log check
    await scan_followup_leads()
    assert send_count == 1


@pytest.mark.asyncio
async def test_run_nurturing_runner_job(monkeypatch):
    send_called = False

    async def mock_send(**kwargs):
        nonlocal send_called
        send_called = True

    monkeypatch.setattr("app.services.ai.communication_service.send", mock_send)

    async with get_async_session() as db:
        c = Client(name="Nurture Job Client", email=f"nj_{uuid.uuid4().hex}@test.com")
        db.add(c)
        await db.flush()

        # Lead inactive for 10 days
        old_time = datetime.now(timezone.utc) - timedelta(days=10)
        lead = Lead(client_id=c.id, status=LeadStatus.inactive, intake_data={}, updated_at=old_time)
        db.add(lead)
        await db.commit()

        # Update updated_at explicitly to bypass onupdate
        await db.execute(update(Lead).where(Lead.id == lead.id).values(updated_at=old_time))
        await db.commit()

    await run_nurturing_runner()
    assert send_called is True
