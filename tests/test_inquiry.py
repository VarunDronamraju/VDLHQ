import uuid

import pytest
from fastapi import BackgroundTasks
from pydantic import ValidationError
from sqlalchemy import select

from app.api.routes.intake import submit_inquiry
from app.api.schemas.intake import InquiryRequest
from app.db.session import get_async_session
from app.models.core import Client


def _payload(email: str, phone: str):
    return {
        "contact": {
            "name": "Inquiry Test",
            "email": email,
            "phone": phone,
            "company": "QA",
        },
        "shoot_type": "commercial",
        "location_type": "studio",
        "requirements": "natural light",
    }


@pytest.mark.asyncio
async def test_new_client_creation(monkeypatch):
    async def _noop_pipeline(_lead_id):
        return None

    monkeypatch.setattr("app.api.routes.intake.run_intake_pipeline", _noop_pipeline)
    email = f"inquiry_new_{uuid.uuid4().hex[:8]}@example.com"
    phone = f"+91{uuid.uuid4().int % 10**10:010d}"
    body = InquiryRequest.model_validate(_payload(email=email, phone=phone))
    background = BackgroundTasks()
    async with get_async_session() as db:
        result = await submit_inquiry(body=body, background_tasks=background, db=db)
        assert result.status == "new"
    async with get_async_session() as db:
        found = (await db.execute(select(Client).where(Client.id == result.client_id))).scalar_one_or_none()
        assert found is not None
        assert found.email == email


@pytest.mark.asyncio
async def test_existing_client_lookup(monkeypatch):
    async def _noop_pipeline(_lead_id):
        return None

    monkeypatch.setattr("app.api.routes.intake.run_intake_pipeline", _noop_pipeline)
    email = f"inquiry_existing_{uuid.uuid4().hex[:8]}@example.com"
    async with get_async_session() as db:
        seeded = Client(
            name="Existing Client",
            email=email,
            phone="+910000000778",
            profile_data={},
        )
        db.add(seeded)
        await db.commit()
        await db.refresh(seeded)
        existing_id = seeded.id

    body = InquiryRequest.model_validate(_payload(email=email, phone="+910000000778"))
    background = BackgroundTasks()
    async with get_async_session() as db:
        result = await submit_inquiry(body=body, background_tasks=background, db=db)
        assert result.client_id == existing_id


def test_invalid_payload_rejection():
    with pytest.raises(ValidationError):
        InquiryRequest.model_validate(
            {
                "contact": {"name": "No Contact"},
                "shoot_type": "commercial",
            }
        )
