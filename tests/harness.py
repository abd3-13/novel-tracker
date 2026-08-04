from app.sync.job import (
    SyncJob,
    SyncMode,
    SyncSource,
)
from app.sync.logger import LogLevel
from app.sync.runner import SyncRunner

from .callbacks import quiet
from .report import TestReport


def run_sync_test(
    *,
    source=SyncSource.LOCAL,
    fields=None,
    ids=None,
    table="demo_novels",
    mode=SyncMode.FILL_MISSING,
    dry_run=True,
    force=False,
    options=None,
    log_level=LogLevel.DEBUG,
    event_handler=quiet,
):

    fields = fields or []

    ids = ids or []

    options = options or {}

    print("\n===== Synchronization Test =====")

    print(f"Source   : {source}")
    print(f"Fields   : {fields}")
    print(f"Mode     : {mode}")
    print(f"Dry Run  : {dry_run}")
    print(f"IDs      : {ids if ids else 'ALL'}")

    report = TestReport()

    job = SyncJob(
        table=table,
        novels=ids,
        fields=fields,
        source=source,
        mode=mode,
        dry_run=dry_run,
        force=force,
        options=options,
        log_level=log_level,
        event_handler=event_handler,
    )

    runner = SyncRunner()

    results = runner.run(job)

    report.finish(results)

    print("\n===== Results =====")

    for result in results:
        print(result)

    return results


def run_all_fields(source, **kwargs):

    from app.sync.metadata import FIELDS

    return run_sync_test(
        source=source,
        fields=list(FIELDS.keys()),
        **kwargs,
    )
