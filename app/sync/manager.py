from concurrent.futures import ThreadPoolExecutor
from threading import Lock

from .execution import SyncExecution
from .runner import SyncRunner


class SyncManager:
    """
    Manages background synchronization executions.
    """

    def __init__(self, max_workers=2):
        self.executor = ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix="sync",
        )

        self.executions = {}
        self.lock = Lock()

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

            result = runner.run(job)

            execution.finish(result)

        except Exception as exc:  # noqa: BLE001
            execution.fail(exc)

        finally:
            execution.close_events()
