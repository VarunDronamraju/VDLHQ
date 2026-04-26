from types import SimpleNamespace
from uuid import uuid4

import pytest
import groq
import httpx

from app.core.exceptions import IntakeParseFailure, InvalidTransition, LLMFailure, ReadinessFailure
from app.core import scheduler as core_scheduler
from app.pipelines import intake_pipeline
from app.scheduler import jobs as scheduler_jobs
from app.services.ai import llm_client


class _FakeResult:
    def __init__(self, rows):
        self._rows = rows

    def fetchall(self):
        return self._rows

    def all(self):
        return self._rows


class _FakeDb:
    def __init__(self, execute_result):
        self.execute_result = execute_result
        self.commits = 0

    async def execute(self, _stmt):
        return self.execute_result

    async def commit(self):
        self.commits += 1


class _FakeSessionCtx:
    def __init__(self, db):
        self.db = db

    async def __aenter__(self):
        return self.db

    async def __aexit__(self, exc_type, exc, tb):
        return False


@pytest.mark.asyncio
async def test_intake_pipeline_logs_on_parse_failure(monkeypatch):
    fake_db = _FakeDb(_FakeResult([]))
    logged = []

    async def _parse(_lead_id, _db):
        raise IntakeParseFailure("bad raw payload")

    async def _log(_db, source, lead_id, error):
        logged.append((source, lead_id, type(error).__name__))

    monkeypatch.setattr(intake_pipeline, "get_async_session", lambda: _FakeSessionCtx(fake_db))
    monkeypatch.setattr(intake_pipeline.intake_service, "parse", _parse)
    monkeypatch.setattr(intake_pipeline, "log_system_error", _log)

    await intake_pipeline.run_intake_pipeline(uuid4())
    assert logged and logged[0][0] == "intake_pipeline"


@pytest.mark.asyncio
async def test_intake_pipeline_logs_on_readiness_failure(monkeypatch):
    fake_db = _FakeDb(_FakeResult([]))
    logged = []

    async def _parse(_lead_id, _db):
        return {"shoot_type": "x", "contact": {}}

    async def _score(_lead_id, _structured, _db):
        raise ReadinessFailure("missing deep fields")

    async def _log(_db, source, lead_id, error):
        logged.append((source, lead_id, type(error).__name__))

    monkeypatch.setattr(intake_pipeline, "get_async_session", lambda: _FakeSessionCtx(fake_db))
    monkeypatch.setattr(intake_pipeline.intake_service, "parse", _parse)
    monkeypatch.setattr(intake_pipeline.readiness_service, "score", _score)
    monkeypatch.setattr(intake_pipeline, "log_system_error", _log)

    await intake_pipeline.run_intake_pipeline(uuid4())
    assert any(item[2] == "ReadinessFailure" for item in logged)


@pytest.mark.asyncio
async def test_intake_pipeline_logs_invalid_transition(monkeypatch):
    fake_db = _FakeDb(_FakeResult([]))
    logged = []

    async def _parse(_lead_id, _db):
        return {"shoot_type": "x"}

    async def _score(_lead_id, _structured, _db):
        return SimpleNamespace(status="ready")

    def _route(_status):
        return SimpleNamespace(target_state="matching_in_progress")

    class _FailEngine:
        def __init__(self, _db):
            pass

        async def transition(self, **_kwargs):
            raise InvalidTransition("new", "matching_in_progress")

    async def _log(_db, source, lead_id, error):
        logged.append((source, lead_id, type(error).__name__))

    monkeypatch.setattr(intake_pipeline, "get_async_session", lambda: _FakeSessionCtx(fake_db))
    monkeypatch.setattr(intake_pipeline.intake_service, "parse", _parse)
    monkeypatch.setattr(intake_pipeline.readiness_service, "score", _score)
    monkeypatch.setattr(intake_pipeline.routing_service, "route", _route)
    monkeypatch.setattr(intake_pipeline, "WorkflowEngine", _FailEngine)
    monkeypatch.setattr(intake_pipeline, "log_system_error", _log)

    await intake_pipeline.run_intake_pipeline(uuid4())
    assert any(item[2] == "InvalidTransition" for item in logged)


def test_start_scheduler_register_crash_propagates(monkeypatch):
    started = {"value": False}
    fake_scheduler = SimpleNamespace(
        running=False,
        start=lambda: started.__setitem__("value", True),
    )
    monkeypatch.setattr(core_scheduler, "scheduler", fake_scheduler)

    def _raise(_scheduler):
        raise RuntimeError("register crash")

    monkeypatch.setattr("app.scheduler.jobs.register_all_jobs", _raise)

    with pytest.raises(RuntimeError):
        core_scheduler.start_scheduler()
    assert started["value"] is False


def test_stop_scheduler_noop_when_not_running(monkeypatch):
    shutdown_called = {"value": False}
    fake_scheduler = SimpleNamespace(
        running=False,
        shutdown=lambda: shutdown_called.__setitem__("value", True),
    )
    monkeypatch.setattr(core_scheduler, "scheduler", fake_scheduler)
    core_scheduler.stop_scheduler()
    assert shutdown_called["value"] is False


def test_register_all_jobs_adds_expected_ids():
    calls = []

    class _FakeScheduler:
        def add_job(self, func, trigger, **kwargs):
            calls.append((func.__name__, trigger, kwargs["id"]))

    scheduler_jobs.register_all_jobs(_FakeScheduler())
    ids = {item[2] for item in calls}
    assert ids == {"scan_inactive", "scan_followup", "permit_reminder", "nurturing", "analytics_refresh"}


@pytest.mark.asyncio
async def test_scan_inactive_handles_invalid_transition_and_exception(monkeypatch):
    lead_1 = uuid4()
    lead_2 = uuid4()
    lead_3 = uuid4()
    fake_db = _FakeDb(_FakeResult([(lead_1,), (lead_2,), (lead_3,)]))
    logs = []

    class _Engine:
        def __init__(self, _db):
            self.calls = 0

        async def transition(self, **_kwargs):
            self.calls += 1
            if self.calls == 2:
                raise InvalidTransition("matched", "inactive")
            if self.calls == 3:
                raise RuntimeError("db timeout")

    async def _log(_db, source, lead_id, error):
        logs.append((source, str(lead_id), type(error).__name__))

    monkeypatch.setattr(scheduler_jobs, "get_async_session", lambda: _FakeSessionCtx(fake_db))
    monkeypatch.setattr(scheduler_jobs, "WorkflowEngine", _Engine)
    monkeypatch.setattr(scheduler_jobs, "log_system_error", _log)

    await scheduler_jobs.scan_inactive_leads()
    assert any(item[2] == "RuntimeError" for item in logs)


@pytest.mark.asyncio
async def test_scan_followup_logs_crash_mid_job(monkeypatch):
    lead = SimpleNamespace(id=uuid4(), intake_data={"shoot_type": "ad"}, missing_fields=["budget"], updated_at=None)
    client = SimpleNamespace(name="Client", email="x@example.com")
    fake_db = _FakeDb(_FakeResult([(lead, client)]))
    logs = []

    async def _send(**_kwargs):
        raise RuntimeError("provider down")

    async def _log(_db, source, lead_id, error):
        logs.append((source, str(lead_id), type(error).__name__))

    monkeypatch.setattr(scheduler_jobs, "get_async_session", lambda: _FakeSessionCtx(fake_db))
    monkeypatch.setattr(scheduler_jobs.communication_service, "send", _send)
    monkeypatch.setattr(scheduler_jobs, "log_system_error", _log)

    await scheduler_jobs.scan_followup_leads()
    assert logs and logs[0][0] == "scan_followup_leads"


@pytest.mark.asyncio
async def test_llm_call_retries_then_succeeds(monkeypatch):
    calls = {"n": 0}
    request = httpx.Request("POST", "https://api.groq.com/openai/v1/chat/completions")
    response = httpx.Response(500, request=request)

    async def _create(**_kwargs):
        calls["n"] += 1
        if calls["n"] < 3:
            raise groq.InternalServerError("temporary", response=response, body={"error": "temporary"})
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="ok"))],
            usage=SimpleNamespace(total_tokens=7),
        )

    monkeypatch.setattr(llm_client._client.chat.completions, "create", _create)
    result = await llm_client.call(messages=[{"role": "user", "content": "hi"}], system="reply")
    assert result == "ok"
    assert calls["n"] == 3


@pytest.mark.asyncio
async def test_llm_call_json_malformed_and_partial_json(monkeypatch):
    async def _bad_json(**_kwargs):
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content='{"status": "ok"'))],  # missing closing brace
            usage=SimpleNamespace(total_tokens=4),
        )

    monkeypatch.setattr(llm_client._client.chat.completions, "create", _bad_json)
    with pytest.raises(LLMFailure):
        await llm_client.call_json(messages=[{"role": "user", "content": "hi"}], system="return json")


@pytest.mark.asyncio
async def test_llm_call_json_generic_failure(monkeypatch):
    async def _boom(**_kwargs):
        raise TimeoutError("upstream timeout")

    monkeypatch.setattr(llm_client._client.chat.completions, "create", _boom)
    with pytest.raises(LLMFailure):
        await llm_client.call_json(messages=[{"role": "user", "content": "hi"}], system="return json")
