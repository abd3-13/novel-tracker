from concurrent.futures import ThreadPoolExecutor
from threading import Lock

from .events import SyncEvent
from .job import SyncExecution
from .runner import SyncRunner


class SyncManager:
    """
    Manages running synchronization jobs.

    Responsibilities:
    - Create synchronization executions
    - Run SyncRunner in the background
    - Store execution state
    - Collect synchronization events
    - Expose execution state to the API
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
        Create and start a synchronization execution.
        """

        execution = SyncExecution()

        job.event_handler = lambda event: self._handle_event(
            execution,
            event,
        )

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
        Return an execution by ID.
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

        execution.status = "running"

        try:
            runner = SyncRunner()

            result = runner.run(job)

            execution.result = result
            execution.status = "finished"

        except Exception as exc:  # noqa: BLE001
            execution.error = str(exc)
            execution.status = "failed"

        finally:
            # Signal that no more events will be produced.
            execution.events.put(None)

    # ------------------------------------------------------------------
    # Events
    # ------------------------------------------------------------------

    def _handle_event(self, execution, event: SyncEvent):
        """
        Store a synchronization event for consumers.
        """

        execution.events.put(event)
