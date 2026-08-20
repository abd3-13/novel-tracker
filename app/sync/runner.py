"""
Bulk synchronization runner.

Responsibilities

- Select novels to synchronize
- Execute SyncEngine
- Track progress
- Collect results
- Handle per-novel failures

This class contains no synchronization logic.
"""

from app.constants import Event, MetadataKey
from app.utils import db

from .engine import SyncEngine
from .events import SyncEvent
from .logger import SyncLogger  # type: ignore
from .selector import BulkSelector


class SyncRunner:
    """
    Executes synchronization jobs.
    """

    def __init__(self):

        self.engine = SyncEngine(db)
        self.logger = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(self, job, is_cancelled=None):
        """
        Execute a synchronization job.
        """
        self.logger = SyncLogger(level=job.log_level)

        novels = self._select(job)

        total = len(novels)

        self._emit(job, Event.JOB_START, total=total)

        results = []

        self._on_start(total)

        for current, novel in enumerate(novels, start=1):
            if is_cancelled and is_cancelled():
                break
            self._on_progress(current, total, novel)
            self._emit(
                job,
                Event.NOVEL_START,
                current=current,
                total=total,
                novel=novel["name"],
            )

            try:
                result = self.engine.run(job, novel)

            except Exception as e:  # noqa: BLE001
                self.logger.error(f"{novel['name']}: {e}")
                result = self._error_result(novel, e)

            results.append(result)
            self._emit(
                job, Event.NOVEL_FINISH, current=current, total=total, result=result
            )

            if is_cancelled and is_cancelled():
                break
        cancelled = bool(is_cancelled and is_cancelled())
        summary: dict[str, int | bool] = self._on_finish(results)
        summary["cancelled"] = cancelled
        self._emit(job, Event.JOB_FINISH, results=results, summary=summary)

        return {
            "summary": summary,
            "results": results,
        }

    def preview(self, job):
        """
        Return novels that would be synchronized.
        """

        return self._select(job)

    # ------------------------------------------------------------------
    # Selection
    # ------------------------------------------------------------------

    def _select(self, job):
        """
        Select novels according to the SyncJob.
        """

        selector = BulkSelector(table=job.table)

        # Explicit IDs
        if job.novels:
            return selector.ids(job.novels)

        # Filter by source
        if "source" in job.options:
            return selector.column(MetadataKey.SOURCE, job.options["source"])

        # Filter by status
        if "status" in job.options:
            return selector.column(MetadataKey.STATUS, job.options["status"])

        # Custom WHERE clause
        if "where" in job.options:
            return selector.where(
                job.options["where"],
                job.options.get("params", ()),
            )

        # Default
        return selector.all()

    # ------------------------------------------------------------------
    # Progress
    # ------------------------------------------------------------------

    def _on_start(self, total):
        """
        Called before synchronization begins.
        """

        assert self.logger is not None
        self.logger.info(f"\nStarting synchronization ({total} novels)\n")

    def _on_progress(self, current, total, novel):
        """
        Called before synchronizing a novel.
        """

        assert self.logger is not None
        self.logger.progress(current, total, novel["name"])

    def _on_finish(self, results):
        """
        Build synchronization summary after all novels are processed.
        """

        processed = len(results)

        updated = sum(1 for r in results if r and r.get("updated"))

        errors = sum(1 for r in results if r and r.get("errors"))

        skipped = sum(
            1 for r in results if r and not r.get("updated") and not r.get("errors")
        )

        warnings = sum(1 for r in results if r and r.get("warnings"))

        summary = {
            "total": processed,
            "updated": updated,
            "skipped": skipped,
            "errors": errors,
            "warnings": warnings,
        }

        assert self.logger is not None

        self.logger.summary(
            processed=processed,
            updated=updated,
            skipped=skipped,
            errors=errors,
            warnings=warnings,
        )

        return summary

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _error_result(self, novel, error):
        """
        Convert an exception into a result object.
        """

        return {
            "id": novel[MetadataKey.ID],
            "title": novel[MetadataKey.TITLE],
            "updated": False,
            "changes": {},
            "errors": [str(error)],
            "warnings": [],
        }

    def _emit(self, job, event_type: str, **data):
        """
        Emit an event to the registered callback.
        """

        if job.event_handler is None:
            return

        job.event_handler(SyncEvent(type=event_type, data=data))
