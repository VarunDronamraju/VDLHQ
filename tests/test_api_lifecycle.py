import uuid

from fastapi.testclient import TestClient

from app.core.exceptions import LHQException
from app.db.session import get_db
from app.main import app


def _inquiry_payload():
    return {
        "contact": {
            "name": "API Lifecycle",
            "email": f"api_{uuid.uuid4().hex[:10]}@example.com",
            "phone": f"+91{uuid.uuid4().int % 10**10:010d}",
            "company": "QA",
        },
        "shoot_type": "commercial",
        "location_type": "studio",
        "requirements": "natural light",
    }


def test_inquiry_valid_request_lifecycle(monkeypatch):
    class _Result:
        def scalar_one_or_none(self):
            return None

    class _FakeDb:
        def __init__(self):
            self._added = []

        async def execute(self, _stmt):
            return _Result()

        def add(self, obj):
            self._added.append(obj)

        async def flush(self):
            for obj in self._added:
                if getattr(obj, "id", None) is None:
                    setattr(obj, "id", uuid.uuid4())

        async def commit(self):
            return None

    async def _noop_pipeline(_lead_id):
        return None

    async def _noop_connection():
        return True

    async def _override_db():
        yield _FakeDb()

    monkeypatch.setattr("app.api.routes.intake.run_intake_pipeline", _noop_pipeline)
    monkeypatch.setattr("app.main.test_connection", _noop_connection)
    monkeypatch.setattr("app.main.start_scheduler", lambda: None)
    monkeypatch.setattr("app.main.stop_scheduler", lambda: None)
    app.dependency_overrides[get_db] = _override_db

    try:
        with TestClient(app) as client:
            response = client.post("/api/v1/inquiry", json=_inquiry_payload())
            assert response.status_code == 202
            body = response.json()
            assert body["status"] == "new"
            assert "lead_id" in body and "client_id" in body
    finally:
        app.dependency_overrides.clear()


def test_inquiry_invalid_payload_returns_422(monkeypatch):
    class _FakeDb:
        pass

    async def _override_db():
        yield _FakeDb()

    async def _noop_connection():
        return True

    monkeypatch.setattr("app.main.test_connection", _noop_connection)
    monkeypatch.setattr("app.main.start_scheduler", lambda: None)
    monkeypatch.setattr("app.main.stop_scheduler", lambda: None)
    app.dependency_overrides[get_db] = _override_db

    invalid = {"contact": {"name": "No Contact"}, "shoot_type": "commercial"}
    try:
        with TestClient(app) as client:
            response = client.post("/api/v1/inquiry", json=invalid)
            assert response.status_code == 422
    finally:
        app.dependency_overrides.clear()


def test_workflow_lhq_exception_maps_to_400(monkeypatch):
    async def _raise_lhq(self, **_kwargs):
        raise LHQException("workflow failure")

    class _FakeDb:
        pass

    async def _override_db():
        yield _FakeDb()

    async def _noop_connection():
        return True

    monkeypatch.setattr("app.services.core.workflow_engine.WorkflowEngine.transition", _raise_lhq)
    monkeypatch.setattr("app.main.test_connection", _noop_connection)
    monkeypatch.setattr("app.main.start_scheduler", lambda: None)
    monkeypatch.setattr("app.main.stop_scheduler", lambda: None)
    app.dependency_overrides[get_db] = _override_db

    try:
        with TestClient(app) as client:
            response = client.post(
                f"/api/v1/leads/{uuid.uuid4()}/transition",
                params={"new_state": "ready", "trigger": "pytest"},
            )
            assert response.status_code == 400
            assert response.json()["detail"] == "workflow failure"
    finally:
        app.dependency_overrides.clear()


def test_workflow_unhandled_exception_maps_to_500(monkeypatch):
    async def _raise_unknown(self, **_kwargs):
        raise RuntimeError("boom")

    class _FakeDb:
        pass

    async def _override_db():
        yield _FakeDb()

    async def _noop_connection():
        return True

    monkeypatch.setattr("app.services.core.workflow_engine.WorkflowEngine.transition", _raise_unknown)
    monkeypatch.setattr("app.main.test_connection", _noop_connection)
    monkeypatch.setattr("app.main.start_scheduler", lambda: None)
    monkeypatch.setattr("app.main.stop_scheduler", lambda: None)
    app.dependency_overrides[get_db] = _override_db

    try:
        with TestClient(app) as client:
            response = client.post(
                f"/api/v1/leads/{uuid.uuid4()}/transition",
                params={"new_state": "ready", "trigger": "pytest"},
            )
            assert response.status_code == 500
            assert response.json()["detail"] == "Internal server error during transition"
    finally:
        app.dependency_overrides.clear()
