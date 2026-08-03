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

    def run(self, job):
        """
        Execute a synchronization job.
        """
        self.logger = SyncLogger(level=job.log_level)

        novels = self._select(job)

        total = len(novels)

        self._emit(job, "job_start", total=total)

        results = []

        self._on_start(total)

        for current, novel in enumerate(novels, start=1):
            self._on_progress(current, total, novel)
            self._emit(
                job, "novel_start", current=current, total=total, novel=novel["name"]
            )

            try:
                result = self.engine.run(job, novel)

            except Exception as e:  # noqa: BLE001
                self.logger.error(f"{novel['name']}: {e}")
                result = self._error_result(novel, e)

            results.append(result)
            self._emit(job, "novel_finish", current=current, total=total, result=result)

        self._on_finish(results)
        self._emit(job, "job_finish", results=results)

        return results

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

        selector = BulkSelector(
            table=job.table,
        )

        # Explicit IDs
        if job.novels:
            return selector.ids(job.novels)

        # Filter by source
        if "source" in job.options:
            return selector.source(
                job.options["source"],
            )

        # Filter by status
        if "status" in job.options:
            return selector.status(
                job.options["status"],
            )

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
        Called after synchronization completes.
        """

        updated = sum(1 for r in results if r and "error" not in r and r)

        failed = sum(1 for r in results if r and "error" in r)

        skipped = len(results) - updated - failed

        assert self.logger is not None
        self.logger.summary(
            processed=len(results), updated=updated, skipped=skipped, errors=failed
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _error_result(self, novel, error):
        """
        Convert an exception into a result object.
        """

        return {
            "id": novel["id"],
            "title": novel["name"],
            "error": str(error),
        }

    def _emit(self, job, event_type: str, **data):
        """
        Emit an event to the registered callback.
        """

        if job.event_handler is None:
            return

        job.event_handler(SyncEvent(type=event_type, data=data))
