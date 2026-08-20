import threading

import pytest

from app.constants import Default, LogLevel, Provider, SyncMode
from app.sync.job import SyncJob


@pytest.fixture
def sync_job():
    def factory(**overrides):
        values = {
            "table": Default.DEMO_NOVEL_TABLE,
            "novels": [],
            "fields": [],
            "source": Provider.LOCAL,
            "mode": SyncMode.FILL_MISSING,
            "dry_run": True,
            "force": False,
            "options": {},
            "profile": "Test Synchronization",
            "log_level": LogLevel.SILENT,
        }
        values.update(overrides)
        return SyncJob(**values)

    return factory


@pytest.fixture
def event_collector():
    events = []

    def collect(event):
        events.append(event)

    collect.events = events
    return collect


@pytest.fixture
def novel_factory():
    def factory(novel_id=1, title=None, **values):
        novel = {
            "id": novel_id,
            "name": title or f"Novel {novel_id}",
        }
        novel.update(values)
        return novel

    return factory


@pytest.fixture
def cancellation_event():
    return threading.Event()


@pytest.fixture
def sync_manager():
    from app.sync.manager import SyncManager

    manager = SyncManager(max_workers=1)
    yield manager
    manager.executor.shutdown(wait=True)
