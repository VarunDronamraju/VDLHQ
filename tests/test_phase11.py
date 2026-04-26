import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.db.session import get_async_session
from app.main import app
from app.models.core import Booking, Client, Lead, LeadStatus, Location, Permit


@pytest.mark.asyncio
async def test_generate_checklist_studio():
    async with get_async_session() as db:
        c = Client(name="Permit Client", email=f"permit_{uuid.uuid4().hex}@test.com")
        db.add(c)
        await db.flush()
        loc = Location(name="Studio X", type="studio", address="123")
        db.add(loc)
        await db.flush()
        lead = Lead(client_id=c.id, status=LeadStatus.matched, intake_data={"shoot_type": "commercial"})
        db.add(lead)
        await db.flush()
        booking = Booking(lead_id=lead.id, client_id=c.id, location_id=loc.id, status="confirmed")
        db.add(booking)
        await db.commit()
        booking_id = booking.id

    from app.services.ai.permit_service import permit_service

    async with get_async_session() as db:
        res = await permit_service.generate_checklist(booking_id, db)
        await db.commit()

    assert res["status"] == "pending"
    assert res["permit_type"] == "internal_studio_approval"

    async with get_async_session() as db:
        p = await db.get(Permit, uuid.UUID(res["permit_id"]))
        assert p is not None
        assert p.status == "pending"


@pytest.mark.asyncio
async def test_update_permit_lifecycle():
    async with get_async_session() as db:
        c = Client(name="Lifecycle Client", email=f"life_{uuid.uuid4().hex}@test.com")
        db.add(c)
        await db.flush()
        loc = Location(name="Street Y", type="street", address="456")
        db.add(loc)
        await db.flush()
        # Lead must be in permit_pending to transition to permit_submitted
        lead = Lead(client_id=c.id, status=LeadStatus.permit_pending, intake_data={})
        db.add(lead)
        await db.flush()
        booking = Booking(lead_id=lead.id, client_id=c.id, location_id=loc.id, status="confirmed")
        db.add(booking)
        await db.flush()
        permit = Permit(booking_id=booking.id, permit_type="municipal", status="pending", checklist={})
        db.add(permit)
        await db.commit()
        booking_id = booking.id
        permit_id = permit.id
        lead_id = lead.id

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # 1. pending -> submitted
        resp = await ac.post(f"/api/v1/ops/bookings/{booking_id}/permit/{permit_id}", json={"status": "submitted"})
        assert resp.status_code == 200
        assert resp.json()["lead_state"] == "permit_submitted"

        # 2. submitted -> in_review
        resp = await ac.post(f"/api/v1/ops/bookings/{booking_id}/permit/{permit_id}", json={"status": "in_review"})
        assert resp.status_code == 200
        assert resp.json()["lead_state"] == "permit_in_review"

        # 3. in_review -> approved
        resp = await ac.post(f"/api/v1/ops/bookings/{booking_id}/permit/{permit_id}", json={"status": "approved"})
        assert resp.status_code == 200
        assert resp.json()["lead_state"] == "permit_approved"

        async with get_async_session() as db:
            l_updated = await db.get(Lead, lead_id)
            # Should have auto-transitioned to coordination
            assert l_updated.status == LeadStatus.coordination


@pytest.mark.asyncio
async def test_permit_reminders(monkeypatch):
    send_called = False

    async def mock_send(**kwargs):
        nonlocal send_called
        send_called = True

    monkeypatch.setattr("app.services.ai.communication_service.send", mock_send)

    async with get_async_session() as db:
        c = Client(name="Reminder Client", email=f"rem_{uuid.uuid4().hex}@test.com")
        db.add(c)
        await db.flush()
        loc = Location(name="Old Location", type="park", address="789")
        db.add(loc)
        await db.flush()
        lead = Lead(client_id=c.id, status=LeadStatus.booked, intake_data={})
        db.add(lead)
        await db.flush()
        booking = Booking(lead_id=lead.id, client_id=c.id, location_id=loc.id, status="confirmed")
        db.add(booking)
        await db.flush()
        from datetime import datetime, timedelta, timezone

        old_time = datetime.now(timezone.utc) - timedelta(days=10)
        permit = Permit(booking_id=booking.id, permit_type="film", status="submitted", checklist={"expected_approval_days": 3}, updated_at=old_time)
        db.add(permit)
        await db.commit()

    from app.scheduler.jobs import run_permit_reminders

    await run_permit_reminders()

    assert send_called is True


@pytest.mark.asyncio
async def test_booked_transition_triggers_pipeline(monkeypatch):
    pipeline_called = False

    async def mock_pipeline(lead_id, booking_id):
        nonlocal pipeline_called
        pipeline_called = True

    monkeypatch.setattr("app.api.routes.ops.run_booking_pipeline", mock_pipeline)

    async with get_async_session() as db:
        c = Client(name="Book Trigger Client", email=f"bt_{uuid.uuid4().hex}@test.com")
        db.add(c)
        await db.flush()
        loc = Location(name="Target Loc", type="studio", address="101")
        db.add(loc)
        await db.flush()
        lead = Lead(client_id=c.id, status=LeadStatus.matched, intake_data={})
        db.add(lead)
        await db.commit()
        lead_id = lead.id
        loc_id = loc.id

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        payload = {"target_state": "booked", "metadata": {"location_id": str(loc_id)}}
        resp = await ac.post(f"/api/v1/ops/leads/{lead_id}/action", json=payload)
        assert resp.status_code == 200
        assert pipeline_called is True

        # Verify booking created
        async with get_async_session() as db:
            stmt = select(Booking).where(Booking.lead_id == lead_id)
            res = await db.execute(stmt)
            b = res.scalar_one_or_none()
            assert b is not None
            assert b.location_id == loc_id
