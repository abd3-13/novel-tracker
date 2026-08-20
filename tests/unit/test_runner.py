import threading

import pytest

from app.constants import Event
from app.sync.runner import SyncRunner

from tests.support.fakes import BlockingEngine, RecordingEngine


pytestmark = pytest.mark.unit


def test_error_result_contains_title(novel_factory):
    runner = SyncRunner()
    novel = novel_factory(13, "My Novel")

    result = runner._error_result(novel, Exception("EPUB file not found"))

    assert result == {
        "id": 13,
        "title": "My Novel",
        "updated": False,
        "changes": {},
        "errors": ["EPUB file not found"],
        "warnings": [],
    }


def test_finish_summary_counts_results():
    runner = SyncRunner()
    runner.logger = runner.logger or __import__("app.sync.logger", fromlist=["SyncLogger"]).SyncLogger()

    results = [
        {"id": 1, "updated": True, "errors": [], "warnings": []},
        {"id": 2, "updated": False, "errors": [], "warnings": ["warning"]},
        {"id": 3, "updated": False, "errors": ["error"], "warnings": []},
    ]

    assert runner._on_finish(results) == {
        "total": 3,
        "updated": 1,
        "skipped": 1,
        "errors": 1,
        "warnings": 1,
    }


def test_emit_sends_typed_event(event_collector):
    runner = SyncRunner()

    class Job:
        event_handler = event_collector

    runner._emit(Job(), Event.JOB_START, total=3)

    assert len(event_collector.events) == 1
    assert event_collector.events[0].type == Event.JOB_START
    assert event_collector.events[0].data == {"total": 3}


def test_emit_is_safe_without_handler():
    runner = SyncRunner()

    class Job:
        event_handler = None

    runner._emit(Job(), Event.JOB_START, total=3)


def test_runner_stops_after_current_novel_when_cancelled(sync_job, novel_factory):
    runner = SyncRunner()
    engine = BlockingEngine()
    runner.engine = engine

    novels = [novel_factory(1), novel_factory(2), novel_factory(3)]
    cancel = threading.Event()

    result_holder = {}

    def run():
        result_holder["result"] = runner.run(
            sync_job(novels=[1, 2, 3]),
            is_cancelled=cancel.is_set,
        )

    thread = threading.Thread(target=run)
    thread.start()

    assert engine.first_started.wait(timeout=2)

    cancel.set()
    engine.release_first.set()

    thread.join(timeout=5)

    assert not thread.is_alive()
    assert engine.processed == [1]
    assert result_holder["result"]["summary"] == {
        "total": 1,
        "updated": 0,
        "skipped": 1,
        "errors": 0,
        "warnings": 0,
        "cancelled": True,
    }


def test_runner_processes_all_novels_without_cancellation(sync_job, novel_factory):
    runner = SyncRunner()
    engine = RecordingEngine()
    runner.engine = engine

    novels = [novel_factory(1), novel_factory(2), novel_factory(3)]

    runner._select = lambda job: novels

    result = runner.run(sync_job(novels=[1, 2, 3]))

    assert engine.processed == [1, 2, 3]
    assert result["summary"]["cancelled"] is False
    assert result["summary"]["total"] == 3
