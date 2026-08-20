import pytest

from app.sync.execution import SyncExecution


pytestmark = pytest.mark.unit


def test_execution_starts_as_pending():
    execution = SyncExecution()

    assert execution.status == "pending"
    assert execution.done is False
    assert execution.cancelling is False


def test_execution_lifecycle_to_finished():
    execution = SyncExecution()

    execution.start()
    assert execution.status == "running"
    assert execution.start_time is not None

    result = {"summary": {"total": 1}}
    execution.finish(result)

    assert execution.status == "finished"
    assert execution.result == result
    assert execution.end_time is not None
    assert execution.done is True


def test_execution_cancel_requests_cooperative_cancellation():
    execution = SyncExecution()
    execution.start()

    execution.cancel()

    assert execution.status == "cancelling"
    assert execution.is_cancelled() is True
    assert execution.cancelling is True
    assert execution.done is False


def test_execution_cancelled_finalizes_result():
    execution = SyncExecution()
    execution.start()

    result = {"summary": {"cancelled": True}}
    execution.cancelled(result)

    assert execution.status == "cancelled"
    assert execution.result == result
    assert execution.end_time is not None
    assert execution.done is True


def test_execution_snapshot_is_serializable():
    execution = SyncExecution()
    execution.start()
    execution.cancel()

    snapshot = execution.snapshot()

    assert snapshot["job_id"] == execution.job_id
    assert snapshot["status"] == "cancelling"
    assert snapshot["done"] is False
    assert snapshot["cancelling"] is True
