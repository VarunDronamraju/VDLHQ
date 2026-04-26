from types import SimpleNamespace

import pytest

from app.core import scheduler as core_scheduler


def test_start_scheduler_skips_when_already_running(monkeypatch):
    calls = {"register": 0, "start": 0}
    fake_scheduler = SimpleNamespace(
        running=True,
        start=lambda: calls.__setitem__("start", calls["start"] + 1),
    )

    def _register(_scheduler):
        calls["register"] += 1

    monkeypatch.setattr(core_scheduler, "scheduler", fake_scheduler)
    monkeypatch.setattr("app.scheduler.jobs.register_all_jobs", _register)

    core_scheduler.start_scheduler()
    assert calls["register"] == 0
    assert calls["start"] == 0


def test_scheduler_restart_behavior_registers_again(monkeypatch):
    calls = {"register": 0}
    state = {"running": False}

    def _start():
        state["running"] = True

    def _shutdown():
        state["running"] = False

    class _Sched:
        @property
        def running(self):
            return state["running"]

        start = staticmethod(_start)
        shutdown = staticmethod(_shutdown)

    def _register(_scheduler):
        calls["register"] += 1

    monkeypatch.setattr(core_scheduler, "scheduler", _Sched())
    monkeypatch.setattr("app.scheduler.jobs.register_all_jobs", _register)

    core_scheduler.start_scheduler()
    core_scheduler.stop_scheduler()
    core_scheduler.start_scheduler()
    assert calls["register"] == 2


def test_start_scheduler_failure_during_startup(monkeypatch):
    fake_scheduler = SimpleNamespace(running=False, start=lambda: (_ for _ in ()).throw(RuntimeError("start failed")))
    monkeypatch.setattr(core_scheduler, "scheduler", fake_scheduler)
    monkeypatch.setattr("app.scheduler.jobs.register_all_jobs", lambda _s: None)

    with pytest.raises(RuntimeError):
        core_scheduler.start_scheduler()
