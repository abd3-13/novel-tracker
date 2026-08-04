from app.constants import MetadataKey, Provider
from tests.callbacks import print_events
from tests.harness import run_sync_test

# print("\n===== Synchronization Test: All Fields =====")
# run_all_fields(
#    SyncSource.LOCAL,
#    ids=[13],
# )


print("\n===== Synchronization Test: Specific Fields =====")
run_sync_test(
    source=Provider.LOCAL,
    ids=[13],
    fields=[MetadataKey.TITLE, MetadataKey.AUTHOR, MetadataKey.DESCRIPTION],
    event_handler=print_events,
)
