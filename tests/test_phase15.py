import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from tests.conftest import get_auth_headers


@pytest.mark.asyncio
async def test_request_id_middleware():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        headers = get_auth_headers("ops")
        response = await ac.get("/api/v1/ops/analytics", headers=headers)
        assert response.status_code == 200
        assert "X-Request-ID" in response.headers
        assert len(response.headers["X-Request-ID"]) > 10


@pytest.mark.asyncio
async def test_error_logging_middleware(monkeypatch):
    async def _failing_health_check(*args, **kwargs):
        raise ValueError("Simulated failure for testing")

    monkeypatch.setattr("app.main.health_check", _failing_health_check)

    log_system_error_called = False

    async def _mock_log_system_error(db, source, lead_id, exc):
        nonlocal log_system_error_called
        if source == "GlobalExceptionHandler" and str(exc) == "Simulated analytics failure":
            log_system_error_called = True

    monkeypatch.setattr("app.core.error_logger.log_system_error", _mock_log_system_error)

    async def _failing_analytics(*args, **kwargs):
        raise ValueError("Simulated analytics failure")

    monkeypatch.setattr("app.services.core.analytics_service.analytics_service.get_latest_snapshot", _failing_analytics)

    async with AsyncClient(transport=ASGITransport(app=app, raise_app_exceptions=False), base_url="http://test") as ac:
        headers = get_auth_headers("ops")
        response = await ac.get("/api/v1/ops/analytics", headers=headers)
        assert response.status_code == 500

    assert log_system_error_called is True
