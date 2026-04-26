import uuid

import pytest
from sqlalchemy import select

from app.core.exceptions import IntakeParseFailure
from app.db.session import get_async_session
from app.models.core import Client, Lead, LeadStatus
from app.services.ai import intake_service


async def _create_lead(intake_data=None):
    async with get_async_session() as db:
        client = Client(
            name="Intake Client",
            email=f"intake_{uuid.uuid4().hex[:10]}@example.com",
            phone=f"+91{uuid.uuid4().int % 10**10:010d}",
            profile_data={},
        )
        db.add(client)
        await db.flush()
        lead = Lead(client_id=client.id, status=LeadStatus.new, intake_data=intake_data or {"shoot_type": "raw-shoot", "existing_key": "keep-me"})
        db.add(lead)
        await db.commit()
        await db.refresh(lead)
        return lead.id


@pytest.mark.asyncio
async def test_intake_parse_merges_partial_data(monkeypatch):
    async def _fake_call_json(**_kwargs):
        return {"shoot_type": "structured-shoot", "location_type": "warehouse"}

    monkeypatch.setattr(intake_service.llm_client, "call_json", _fake_call_json)
    lead_id = await _create_lead()

    async with get_async_session() as db:
        structured = await intake_service.parse(lead_id=lead_id, db=db)
        await db.commit()
        refreshed = (await db.execute(select(Lead).where(Lead.id == lead_id))).scalar_one()

    assert structured["location_type"] == "warehouse"
    assert refreshed.intake_data["existing_key"] == "keep-me"
    assert refreshed.intake_data["shoot_type"] == "structured-shoot"


@pytest.mark.asyncio
async def test_intake_parse_raises_when_lead_missing():
    async with get_async_session() as db:
        with pytest.raises(IntakeParseFailure):
            await intake_service.parse(lead_id=uuid.uuid4(), db=db)


@pytest.mark.asyncio
async def test_intake_parse_raises_on_llm_extraction_failure(monkeypatch):
    async def _boom(**_kwargs):
        raise RuntimeError("malformed extraction")

    monkeypatch.setattr(intake_service.llm_client, "call_json", _boom)
    lead_id = await _create_lead()

    async with get_async_session() as db:
        with pytest.raises(IntakeParseFailure):
            await intake_service.parse(lead_id=lead_id, db=db)
