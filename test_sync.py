from app.sync.job import SyncSource
from tests.callbacks import print_events
from tests.harness import run_all_fields, run_sync_test

print("\n===== Synchronization Test: All Fields =====")
run_all_fields(
    SyncSource.LOCAL,
    ids=[13],
)

print("\n===== Synchronization Test: Specific Fields =====")
run_sync_test(
    source=SyncSource.LOCAL,
    ids=[13],
    fields=[
        "title",
        "author",
        "description",
    ],
    event_handler=print_events,
)
