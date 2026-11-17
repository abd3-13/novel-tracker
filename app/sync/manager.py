from concurrent.futures import ThreadPoolExecutor
from threading import Lock

from .execution import SyncExecution
from .runner import SyncRunner


class SyncManager:
    """
    Manages background synchronization executions.

    Finished executions are kept briefly so late status/event requests can
    still read their snapshot. ``max_finished`` bounds that retention so a
    long-running server does not grow without limit.
    """

    def __init__(self, max_workers=2, max_finished=20):
        self.executor = ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix="sync",
        )

        self.executions = {}
        self.lock = Lock()
        self.max_finished = max_finished

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start(self, job):
        """
        Start a synchronization job in the background.
        """

        execution = SyncExecution()

        # Route SyncRunner events into this execution.
        job.event_handler = execution.emit

        with self.lock:
            self.executions[execution.job_id] = execution

        self.executor.submit(
            self._run,
            execution,
            job,
        )

        return execution

    def _prune_finished(self):
        """
        Drop the oldest finished executions beyond ``max_finished``.

        Running jobs are never removed. Callers hold ``self.lock``.
        """

        finished = [e for e in self.executions.values() if e.done]
        excess = len(finished) - self.max_finished

        if excess <= 0:
            return

        finished.sort(key=lambda execution: execution.end_time or 0)

        for execution in finished[:excess]:
            self.executions.pop(execution.job_id, None)

    def get(self, job_id):
        """
        Get an execution by ID.
        """

        with self.lock:
            return self.executions.get(job_id)

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    def _run(self, execution, job):
        """
        Execute the synchronization in the background.
        """

        execution.start()

        try:
            runner = SyncRunner()

            result = runner.run(job, is_cancelled=execution.is_cancelled)

            if execution.is_cancelled():
                execution.cancelled(result)
            else:
                execution.finish(result)

        except Exception as exc:  # noqa: BLE001
            execution.fail(exc)

        finally:
            execution.close_events()

            with self.lock:
                self._prune_finished()

    def cancel(self, job_id):
        """
        Request cancellation of an execution.
        """

        execution = self.get(job_id)

        if execution is None:
            return None

        if execution.done:
            return execution

        execution.cancel()

        return execution
