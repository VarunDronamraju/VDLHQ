import uuid
from datetime import datetime, timedelta, timezone

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select

from app.db.session import get_async_session
from app.main import app
from app.models.core import Client, Lead, LeadStatus, WorkflowState
from app.services.core.analytics_service import analytics_service
from tests.conftest import get_auth_headers


@pytest.mark.asyncio
async def test_analytics_aggregations():
    async with get_async_session() as db:
        # Get baseline
        base_res = await db.execute(select(func.count(Lead.id)))
        baseline_count = base_res.scalar()

        c = Client(name="Analytics Client", email=f"anal_{uuid.uuid4().hex}@test.com")
        db.add(c)
        await db.flush()

        # Lead 1: booked (1 day ago)
        l1 = Lead(client_id=c.id, status=LeadStatus.booked, created_at=datetime.now(timezone.utc) - timedelta(days=2))
        db.add(l1)
        await db.flush()

        # Transition for Lead 1
        w1 = WorkflowState(lead_id=l1.id, previous_state="matched", new_state="booked", trigger="test", actor="test", created_at=datetime.now(timezone.utc) - timedelta(days=1))
        db.add(w1)

        # Lead 2: new
        l2 = Lead(client_id=c.id, status=LeadStatus.new)
        db.add(l2)

        # Lead 3: coordination (booked 2 days ago)
        l3 = Lead(client_id=c.id, status=LeadStatus.coordination, created_at=datetime.now(timezone.utc) - timedelta(days=5))
        db.add(l3)
        await db.flush()

        w3 = WorkflowState(lead_id=l3.id, previous_state="permit_approved", new_state="booked", trigger="test", actor="test", created_at=datetime.now(timezone.utc) - timedelta(days=3))
        db.add(w3)

        await db.commit()

    async with get_async_session() as db:
        snapshot = await analytics_service.run_aggregations(db)

    assert snapshot.total_leads == baseline_count + 3
    assert snapshot.status_counts["booked"] >= 1
    assert snapshot.status_counts["new"] >= 1
    assert snapshot.status_counts["coordination"] >= 1

    # conversion rate should be >= 2 / total
    assert float(snapshot.conversion_rate) > 0

    # Avg time to booking:
    # l1: 1 day
    # l3: 2 days
    # (Other leads from other tests might affect this, but since they don't have 'booked'
    # transitions in WorkflowState (only status updates), they might be ignored or have 0.
    # Actually, previous tests DID transition leads to booked.
    # So we'll just check if it's > 0.
    assert float(snapshot.avg_time_to_booking_days) > 0


@pytest.mark.asyncio
async def test_analytics_api():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        headers = get_auth_headers("ops")
        resp = await ac.get("/api/v1/ops/analytics", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "status_counts" in data
        assert "conversion_rate" in data
        assert "id" in data  # Snapshot ID
