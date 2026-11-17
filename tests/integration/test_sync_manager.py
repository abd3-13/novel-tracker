import pytest

from app.sync.execution import SyncExecution
from app.sync.manager import SyncManager
from app.sync.runner import SyncRunner

from tests.support.fakes import BlockingEngine
from tests.support.wait import wait_for


pytestmark = pytest.mark.integration


def test_manager_cancels_running_job_after_current_novel(
    monkeypatch,
    sync_job,
    novel_factory,
    sync_manager,
):
    engine = BlockingEngine()
    novels = [novel_factory(1), novel_factory(2), novel_factory(3)]

    original_init = SyncRunner.__init__

    def test_init(self):
        original_init(self)
        self.engine = engine

    monkeypatch.setattr(SyncRunner, "__init__", test_init)
    monkeypatch.setattr(SyncRunner, "_select", lambda self, job: novels)

    execution = sync_manager.start(sync_job(novels=[1, 2, 3]))

    assert engine.first_started.wait(timeout=2)
    assert execution.status in {"running", "cancelling"}

    sync_manager.cancel(execution.job_id)

    assert execution.cancelling is True
    assert execution.status == "cancelling"

    engine.release_first.set()

    wait_for(lambda: execution.done)

    assert execution.status == "cancelled"
    assert execution.result["summary"]["cancelled"] is True
    assert engine.processed == [1]


def test_manager_cancel_unknown_job_returns_none(sync_manager):
    assert sync_manager.cancel("does-not-exist") is None


def test_manager_prunes_the_oldest_finished_executions(
    monkeypatch,
    sync_job,
):
    def test_init(self):
        self.engine = None
        self.logger = None

    monkeypatch.setattr(SyncRunner, "__init__", test_init)
    monkeypatch.setattr(SyncRunner, "_select", lambda self, job: [])

    manager = SyncManager(max_workers=1, max_finished=1)

    try:
        first = manager.start(sync_job())
        wait_for(lambda: first.done)

        second = manager.start(sync_job())
        wait_for(lambda: second.done)
        wait_for(lambda: first.job_id not in manager.executions)

        assert second.job_id in manager.executions
        assert len(manager.executions) == 1
    finally:
        manager.executor.shutdown(wait=True)


def test_manager_never_prunes_running_executions(sync_manager):
    running = SyncExecution()
    running.start()

    finished = SyncExecution()
    finished.finish()

    sync_manager.max_finished = 0

    with sync_manager.lock:
        sync_manager.executions = {
            running.job_id: running,
            finished.job_id: finished,
        }
        sync_manager._prune_finished()

    assert running.job_id in sync_manager.executions
    assert finished.job_id not in sync_manager.executions


def test_manager_cancel_finished_job_does_not_change_status(
    monkeypatch,
    sync_job,
    novel_factory,
    sync_manager,
):
    engine = BlockingEngine()
    engine.release_first.set()
    novels = [novel_factory(1)]

    def test_init(self):
        self.engine = engine
        self.logger = None

    monkeypatch.setattr(SyncRunner, "__init__", test_init)
    monkeypatch.setattr(SyncRunner, "_select", lambda self, job: novels)

    execution = sync_manager.start(sync_job(novels=[1]))

    wait_for(lambda: execution.done)

    assert execution.status == "finished"

    returned = sync_manager.cancel(execution.job_id)

    assert returned is execution
    assert execution.status == "finished"
    assert execution.cancelling is False
