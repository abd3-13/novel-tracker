from app.constants import Event
from app.sync.runner import SyncRunner


def make_result(
    novel_id,
    updated=False,
    errors=None,
    warnings=None,
    title=None,
):
    result = {
        "id": novel_id,
        "updated": updated,
        "changes": {},
        "errors": errors or [],
        "warnings": warnings or [],
    }

    if title is not None:
        result["title"] = title

    return result


def test_error_result_contains_title():
    runner = SyncRunner()

    novel = {
        "id": 13,
        "name": "My Novel",
    }

    error = Exception("EPUB file not found")

    result = runner._error_result(novel, error)

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

    results = [
        make_result(
            1,
            updated=True,
            title="Updated Novel",
        ),
        make_result(
            2,
            warnings=["No EPUB file"],
            title="Warning Novel",
        ),
        make_result(
            3,
            errors=["EPUB file not found"],
            title="Failed Novel",
        ),
    ]

    summary = runner._on_finish(results)

    assert summary == {
        "total": 3,
        "updated": 1,
        "skipped": 1,
        "errors": 1,
        "warnings": 1,
    }


def test_finish_summary_counts_multiple_errors_and_warnings():
    runner = SyncRunner()

    results = [
        make_result(1, updated=True),
        make_result(2, errors=["error"]),
        make_result(3, errors=["error"]),
        make_result(4, warnings=["warning"]),
        make_result(5),
    ]

    summary = runner._on_finish(results)

    assert summary == {
        "total": 5,
        "updated": 1,
        "skipped": 1,
        "errors": 2,
        "warnings": 1,
    }


def test_finish_summary_empty_results():
    runner = SyncRunner()

    summary = runner._on_finish([])

    assert summary == {
        "total": 0,
        "updated": 0,
        "skipped": 0,
        "errors": 0,
        "warnings": 0,
    }


def test_event_handler_receives_sync_events():
    runner = SyncRunner()

    events = []

    class Job:
        event_handler = events.append

    runner._emit(
        Job(),
        Event.JOB_START,
        total=3,
    )

    assert len(events) == 1

    event = events[0]

    assert event.type == Event.JOB_START
    assert event.data == {
        "total": 3,
    }


def test_emit_does_nothing_without_handler():
    runner = SyncRunner()

    class Job:
        event_handler = None

    # Should not raise.
    runner._emit(
        Job(),
        Event.JOB_START,
        total=3,
    )
