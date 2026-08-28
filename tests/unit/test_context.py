import pytest

from app.sync.context import SyncContext
from app.sync.events import SyncEvent

pytestmark = pytest.mark.unit


def test_context_initializes_with_defaults(sync_job, novel_factory):
    job = sync_job()
    novel = novel_factory()

    context = SyncContext(
        job=job,
        novel=novel,
    )

    assert context.job is job
    assert context.novel is novel
    assert context.providers is None
    assert context.collector is None
    assert context.logger is None
    assert context.state is None
    assert context.result is None
    assert context.cache == {}


def test_context_emit_adds_novel_information(
    sync_job,
    novel_factory,
    event_collector,
):
    job = sync_job(event_handler=event_collector)
    novel = novel_factory(42, "Test Novel")

    context = SyncContext(
        job=job,
        novel=novel,
    )

    context.emit(
        "field",
        field="author",
        value="John Doe",
    )

    assert len(event_collector.events) == 1

    event = event_collector.events[0]

    assert isinstance(event, SyncEvent)
    assert event.type == "field"
    assert event.data == {
        "field": "author",
        "value": "John Doe",
        "novel_id": 42,
        "novel": "Test Novel",
    }


def test_context_emit_preserves_explicit_novel_information(
    sync_job,
    novel_factory,
    event_collector,
):
    job = sync_job(event_handler=event_collector)
    novel = novel_factory(42, "Test Novel")

    context = SyncContext(
        job=job,
        novel=novel,
    )

    context.emit(
        "field",
        novel_id=999,
        novel="Wrong Novel",
    )

    event = event_collector.events[0]

    assert event.data["novel_id"] == 999
    assert event.data["novel"] == "Wrong Novel"


def test_context_emit_adds_novel_information_when_missing(
    sync_job,
    novel_factory,
    event_collector,
):
    job = sync_job(event_handler=event_collector)
    novel = novel_factory(42, "Test Novel")

    context = SyncContext(
        job=job,
        novel=novel,
    )

    context.emit("field", field="author")

    event = event_collector.events[0]

    assert event.data["novel_id"] == 42
    assert event.data["novel"] == "Test Novel"


def test_context_emit_without_handler_is_safe(sync_job, novel_factory):
    context = SyncContext(
        job=sync_job(event_handler=None),
        novel=novel_factory(),
    )

    context.emit("field", field="author")
