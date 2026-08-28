import pytest

from app.constants import Event, Provider, SyncMode
from app.sync.collector import SyncCollector
from app.sync.context import SyncContext
from app.sync.metadata import FIELDS, generic_sync

pytestmark = pytest.mark.unit


class FakeLogger:
    def __init__(self):
        self.fields = []
        self.debug_messages = []

    def field(self, field, current, new, should_update):
        self.fields.append(
            {
                "field": field,
                "current": current,
                "new": new,
                "should_update": should_update,
            }
        )

    def debug(self, message):
        self.debug_messages.append(message)


class FakeProviders:
    def __init__(self, values):
        self.values = values

    def get_value(self, source, field):
        key = field.sources[source]
        return self.values[key]


def make_context(
    *,
    current=None,
    new="new value",
    mode=SyncMode.FILL_MISSING,
    event_handler=None,
):
    field = FIELDS["author"]

    job = type(
        "Job",
        (),
        {
            "source": Provider.LOCAL,
            "mode": mode,
            "event_handler": event_handler,
        },
    )()

    novel = {
        "id": 1,
        "name": "Test Novel",
        "author": current,
    }

    return (
        SyncContext(
            job=job,
            novel=novel,
            providers=FakeProviders(
                {
                    "author": new,
                }
            ),
            collector=SyncCollector(),
            logger=FakeLogger(),
        ),
        field,
    )


def test_generic_sync_queues_missing_value(event_collector):
    context, field = make_context(
        current=None,
        new="John Doe",
        event_handler=event_collector,
    )

    generic_sync(context, field)

    assert context.collector.as_dict() == {
        "author": "John Doe",
    }


def test_generic_sync_does_not_overwrite_existing_value():
    context, field = make_context(
        current="Existing Author",
        new="New Author",
    )

    generic_sync(context, field)

    assert context.collector.as_dict() == {}


def test_generic_sync_overwrite_mode_replaces_existing_value():
    context, field = make_context(
        current="Existing Author",
        new="New Author",
        mode=SyncMode.OVERWRITE,
    )

    generic_sync(context, field)

    assert context.collector.as_dict() == {
        "author": "New Author",
    }


def test_generic_sync_does_not_queue_none():
    context, field = make_context(
        current=None,
        new=None,
        mode=SyncMode.OVERWRITE,
    )

    generic_sync(context, field)

    assert context.collector.as_dict() == {}


def test_generic_sync_emits_field_event(event_collector):
    context, field = make_context(
        current=None,
        new="John Doe",
        event_handler=event_collector,
    )

    generic_sync(context, field)

    assert len(event_collector.events) == 1

    event = event_collector.events[0]

    assert event.type == Event.FIELD
    assert event.data["field"] == "author"
    assert event.data["name"] == field.name
    assert event.data["value"] == "John Doe"
    assert event.data["should_update"] is True


def test_generic_sync_emits_skip_event_information(event_collector):
    context, field = make_context(
        current="Existing Author",
        new="New Author",
        event_handler=event_collector,
    )

    generic_sync(context, field)

    event = event_collector.events[0]

    assert event.type == Event.FIELD
    assert event.data["should_update"] is False
    assert context.collector.as_dict() == {}


def test_metadata_fields_have_synchronizers():
    assert FIELDS

    for field in FIELDS.values():
        assert field.column
        assert field.name
        assert field.group
        assert field.synchronizer is not None


def test_metadata_field_ui_representation():
    field = FIELDS["author"]

    result = field.to_ui()

    assert result["id"] == field.column
    assert result["name"] == field.name
    assert result["description"] == field.description
    assert result["icon"] == field.icon
    assert result["default"] == field.default
    assert result["providers"] == list(field.sources)
