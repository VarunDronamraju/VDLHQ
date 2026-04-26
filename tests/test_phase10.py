import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.db.session import get_async_session
from app.main import app
from app.models.core import Booking, Client, Lead, LeadStatus, Location, Permit


@pytest.mark.asyncio
async def test_client_dashboard_valid():
    async with get_async_session() as db:
        c = Client(name="Dash Client", email=f"dash_{uuid.uuid4().hex}@test.com")
        db.add(c)
        await db.flush()
        lead = Lead(client_id=c.id, status=LeadStatus.new, intake_data={"shoot_type": "test"})
        db.add(lead)
        await db.commit()
        client_id = c.id

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get(f"/api/v1/client/dashboard?client_id={client_id}")
    assert response.status_code == 200
    assert "leads" in response.json()


@pytest.mark.asyncio
async def test_client_dashboard_invalid():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get(f"/api/v1/client/dashboard?client_id={uuid.uuid4()}")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_client_lead_detail_valid():
    async with get_async_session() as db:
        c = Client(name="Detail Client", email=f"detail_{uuid.uuid4().hex}@test.com")
        db.add(c)
        await db.flush()
        lead = Lead(client_id=c.id, status=LeadStatus.new, intake_data={"shoot_type": "detail"})
        db.add(lead)
        await db.commit()
        client_id = c.id
        lead_id = lead.id

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get(f"/api/v1/client/leads/{lead_id}?client_id={client_id}")
    assert response.status_code == 200
    assert response.json()["id"] == str(lead_id)


@pytest.mark.asyncio
async def test_client_lead_update_triggers_pipeline(monkeypatch):
    pipeline_called = False

    async def mock_pipeline(lead_id):
        nonlocal pipeline_called
        pipeline_called = True

    monkeypatch.setattr("app.api.routes.client.run_intake_pipeline", mock_pipeline)

    async with get_async_session() as db:
        c = Client(name="Update Client", email=f"update_{uuid.uuid4().hex}@test.com")
        db.add(c)
        await db.flush()
        lead = Lead(client_id=c.id, status=LeadStatus.new, intake_data={"shoot_type": "old"})
        db.add(lead)
        await db.commit()
        client_id = c.id
        lead_id = lead.id

    payload = {"intake_data": {"shoot_type": "new_type"}}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post(f"/api/v1/client/leads/{lead_id}?client_id={client_id}", json=payload)
    assert response.status_code == 200
    assert pipeline_called is True


@pytest.mark.asyncio
async def test_ops_pipeline_filters():
    async with get_async_session() as db:
        c = Client(name="Ops Client", email=f"ops_{uuid.uuid4().hex}@test.com")
        db.add(c)
        await db.flush()
        lead = Lead(client_id=c.id, status=LeadStatus.ready, intake_data={})
        db.add(lead)
        await db.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/v1/ops/pipeline?status=ready")
    assert response.status_code == 200
    assert any(le["status"] == "ready" for le in response.json())


@pytest.mark.asyncio
async def test_ops_lead_action_valid():
    async with get_async_session() as db:
        c = Client(name="Action Client", email=f"action_{uuid.uuid4().hex}@test.com")
        db.add(c)
        await db.flush()
        lead = Lead(client_id=c.id, status=LeadStatus.new, intake_data={})
        db.add(lead)
        await db.commit()
        lead_id = lead.id

    payload = {"target_state": "ready", "trigger": "ops_test", "actor": "pytest_ops"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post(f"/api/v1/ops/leads/{lead_id}/action", json=payload)
    assert response.status_code == 200
    assert response.json()["status"] == "ready"


@pytest.mark.asyncio
async def test_ops_bookings_pipeline():
    async with get_async_session() as db:
        c = Client(name="Ops Book Client", email=f"ops_book_{uuid.uuid4().hex}@test.com")
        db.add(c)
        await db.flush()
        loc = Location(name="Studio 2", type="studio", address="456")
        db.add(loc)
        await db.flush()
        lead = Lead(client_id=c.id, status=LeadStatus.matched, intake_data={})
        db.add(lead)
        await db.flush()
        b = Booking(lead_id=lead.id, client_id=c.id, location_id=loc.id, status="confirmed")
        db.add(b)
        await db.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/v1/ops/bookings")
    assert response.status_code == 200
    assert any(bk["client_name"] == "Ops Book Client" for bk in response.json())


@pytest.mark.asyncio
async def test_ops_permit_update():
    async with get_async_session() as db:
        c = Client(name="Permit Client", email=f"permit_{uuid.uuid4().hex}@test.com")
        db.add(c)
        await db.flush()
        loc = Location(name="Studio 3", type="studio", address="789")
        db.add(loc)
        await db.flush()
        lead = Lead(client_id=c.id, status=LeadStatus.matched, intake_data={})
        db.add(lead)
        await db.flush()
        b = Booking(lead_id=lead.id, client_id=c.id, location_id=loc.id, status="confirmed")
        db.add(b)
        await db.flush()
        p = Permit(booking_id=b.id, permit_type="film", status="pending")
        db.add(p)
        await db.commit()
        booking_id = b.id
        permit_id = p.id

    payload = {"status": "approved"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post(f"/api/v1/ops/bookings/{booking_id}/permit/{permit_id}", json=payload)
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_ops_analytics():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/v1/ops/analytics")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_internal_retry_valid(monkeypatch):
    pipeline_called = False

    async def mock_pipeline(lead_id):
        nonlocal pipeline_called
        pipeline_called = True

    monkeypatch.setattr("app.api.routes.workflow.run_intake_pipeline", mock_pipeline)
    async with get_async_session() as db:
        c = Client(name="Retry Client", email=f"retry_{uuid.uuid4().hex}@test.com")
        db.add(c)
        await db.flush()
        lead = Lead(client_id=c.id, status=LeadStatus.new, intake_data={})
        db.add(lead)
        await db.commit()
        lead_id = lead.id
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post(f"/api/v1/internal/retry/{lead_id}")
    assert response.status_code == 200
    assert pipeline_called is True
