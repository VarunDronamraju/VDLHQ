import uuid

import pytest
from sqlalchemy import select

from app.core.exceptions import ReadinessFailure
from app.db.session import get_async_session
from app.models.core import Client, Lead, LeadStatus
from app.services.ai import readiness_service


async def _create_lead():
    async with get_async_session() as db:
        client = Client(
            name="Readiness Client",
            email=f"readiness_{uuid.uuid4().hex[:10]}@example.com",
            phone=f"+91{uuid.uuid4().int % 10**10:010d}",
            profile_data={},
        )
        db.add(client)
        await db.flush()
        lead = Lead(client_id=client.id, status=LeadStatus.new, intake_data={"shoot_type": "ad"})
        db.add(lead)
        await db.commit()
        await db.refresh(lead)
        return lead.id


@pytest.mark.asyncio
async def test_readiness_boundary_ready_at_threshold(monkeypatch):
    async def _fake_call_json(**_kwargs):
        return {"score": 0.80, "missing_fields": [], "reasoning": "enough info"}

    monkeypatch.setattr(readiness_service.llm_client, "call_json", _fake_call_json)
    lead_id = await _create_lead()

    async with get_async_session() as db:
        result = await readiness_service.score(lead_id=lead_id, structured_data={"x": 1}, db=db)
        await db.commit()
        refreshed = (await db.execute(select(Lead).where(Lead.id == lead_id))).scalar_one()

    assert result.status == "ready"
    assert float(refreshed.readiness_score) == 0.8
    assert refreshed.missing_fields == []


@pytest.mark.asyncio
async def test_readiness_boundary_needs_info_below_threshold(monkeypatch):
    async def _fake_call_json(**_kwargs):
        return {"score": 0.79, "missing_fields": ["dates"], "reasoning": "missing fields"}

    monkeypatch.setattr(readiness_service.llm_client, "call_json", _fake_call_json)
    lead_id = await _create_lead()

    async with get_async_session() as db:
        result = await readiness_service.score(lead_id=lead_id, structured_data={"x": 1}, db=db)

    assert result.status == "needs_info"
    assert result.missing_fields == ["dates"]


@pytest.mark.asyncio
async def test_readiness_raises_on_llm_failure(monkeypatch):
    async def _boom(**_kwargs):
        raise RuntimeError("llm unavailable")

    monkeypatch.setattr(readiness_service.llm_client, "call_json", _boom)
    lead_id = await _create_lead()

    async with get_async_session() as db:
        with pytest.raises(ReadinessFailure):
            await readiness_service.score(lead_id=lead_id, structured_data={"x": 1}, db=db)


@pytest.mark.asyncio
async def test_readiness_malformed_score_raises_value_error(monkeypatch):
    async def _bad_score(**_kwargs):
        return {"score": "not-a-number", "missing_fields": [], "reasoning": "bad"}

    monkeypatch.setattr(readiness_service.llm_client, "call_json", _bad_score)
    lead_id = await _create_lead()

    async with get_async_session() as db:
        with pytest.raises(ValueError):
            await readiness_service.score(lead_id=lead_id, structured_data={"x": 1}, db=db)
