import pytest

from app.sync.events import SyncEvent

pytestmark = pytest.mark.unit


def test_sync_event_stores_type_and_data():
    event = SyncEvent(
        type="field",
        data={
            "field": "author",
            "value": "John Doe",
        },
    )

    assert event.type == "field"
    assert event.data == {
        "field": "author",
        "value": "John Doe",
    }


def test_sync_event_accepts_empty_data():
    event = SyncEvent(
        type="job_start",
        data={},
    )

    assert event.type == "job_start"
    assert event.data == {}
