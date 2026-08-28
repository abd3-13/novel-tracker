import pytest

from app.sync.collector import SyncCollector

pytestmark = pytest.mark.unit


def test_collector_starts_empty():
    collector = SyncCollector()

    assert collector.changed() is False
    assert len(collector) == 0
    assert collector.as_dict() == {}


def test_collector_set_and_get():
    collector = SyncCollector()

    collector.set("author", "John Doe")

    assert collector.get("author") == "John Doe"
    assert collector.has("author") is True
    assert collector.changed() is True
    assert len(collector) == 1


def test_collector_get_returns_default():
    collector = SyncCollector()

    assert collector.get("author") is None
    assert collector.get("author", "Unknown") == "Unknown"


def test_collector_replaces_existing_value():
    collector = SyncCollector()

    collector.set("author", "John Doe")
    collector.set("author", "Jane Doe")

    assert collector.get("author") == "Jane Doe"
    assert len(collector) == 1


def test_collector_remove():
    collector = SyncCollector()

    collector.set("author", "John Doe")
    collector.remove("author")

    assert collector.has("author") is False
    assert collector.changed() is False


def test_collector_remove_missing_value_is_safe():
    collector = SyncCollector()

    collector.remove("author")

    assert collector.changed() is False


def test_collector_clear():
    collector = SyncCollector()

    collector.set("author", "John Doe")
    collector.set("description", "A novel")

    collector.clear()

    assert collector.changed() is False
    assert len(collector) == 0
    assert collector.as_dict() == {}


def test_collector_items():
    collector = SyncCollector()

    collector.set("author", "John Doe")
    collector.set("description", "A novel")

    assert dict(collector.items()) == {
        "author": "John Doe",
        "description": "A novel",
    }


def test_collector_as_dict_returns_copy():
    collector = SyncCollector()
    collector.set("author", "John Doe")

    values = collector.as_dict()
    values["author"] = "Changed"

    assert collector.get("author") == "John Doe"


def test_collector_supports_contains():
    collector = SyncCollector()

    collector.set("author", "John Doe")

    assert "author" in collector
    assert "description" not in collector
