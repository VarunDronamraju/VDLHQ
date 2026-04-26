import uuid

import pytest
from fastapi import status
from httpx import ASGITransport, AsyncClient

from app.db.session import get_async_session
from app.main import app
from app.models.core import Client, Lead, LeadStatus
from tests.conftest import create_test_token


@pytest.mark.asyncio
async def test_auth_missing_token():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/v1/client/dashboard")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert "Not authenticated" in response.json()["detail"]


@pytest.mark.asyncio
async def test_auth_invalid_token():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/v1/client/dashboard", headers={"Authorization": "Bearer invalid-token"})
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_auth_role_restriction():
    # Client trying to access ops route
    token = create_test_token("user123", "client", str(uuid.uuid4()))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/v1/ops/pipeline", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
async def test_client_data_isolation():
    async with get_async_session() as db:
        # Create Client A and Lead A
        c_a = Client(name="Client A", email=f"a_{uuid.uuid4().hex}@test.com")
        db.add(c_a)
        await db.flush()
        l_a = Lead(client_id=c_a.id, status=LeadStatus.new, intake_data={})
        db.add(l_a)

        # Create Client B and Lead B
        c_b = Client(name="Client B", email=f"b_{uuid.uuid4().hex}@test.com")
        db.add(c_b)
        await db.flush()
        l_b = Lead(client_id=c_b.id, status=LeadStatus.new, intake_data={})
        db.add(l_b)

        await db.commit()

        client_a_id = str(c_a.id)
        lead_b_id = str(l_b.id)

    # Authenticate as Client A
    token_a = create_test_token("user_a", "client", client_a_id)

    # Try to access Lead B
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get(f"/api/v1/client/leads/{lead_b_id}", headers={"Authorization": f"Bearer {token_a}"})

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "access denied" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_ops_access():
    token_ops = create_test_token("ops_user", "ops")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/v1/ops/pipeline", headers={"Authorization": f"Bearer {token_ops}"})
    assert response.status_code == status.HTTP_200_OK


@pytest.mark.asyncio
async def test_internal_endpoint_protection():
    # Client trying to access internal retry
    token_client = create_test_token("user123", "client", str(uuid.uuid4()))
    lead_id = uuid.uuid4()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post(f"/api/v1/internal/retry/{lead_id}", headers={"Authorization": f"Bearer {token_client}"})
    assert response.status_code == status.HTTP_403_FORBIDDEN
