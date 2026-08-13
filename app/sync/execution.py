import time
from dataclasses import dataclass, field
from queue import Queue
from typing import Any
from uuid import uuid4

from .events import SyncEvent


@dataclass(slots=True)
class SyncExecution:
    """
    Runtime state for a single synchronization job.

    SyncManager owns the execution lifecycle.
    SyncRunner/SyncEngine report progress through SyncEvent.
    """

    # Unique execution identifier
    job_id: str = field(default_factory=lambda: str(uuid4()))

    # Execution state
    status: str = "pending"

    # Timing
    start_time: float | None = None
    end_time: float | None = None

    # Final result
    result: dict[str, Any] | None = None

    # Fatal execution error
    error: str | None = None

    # Event stream
    events: Queue[SyncEvent | None] = field(default_factory=Queue)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self):
        """Mark execution as running."""

        self.status = "running"
        self.start_time = time.time()

    def finish(self, result: dict[str, Any] | None = None):
        """Mark execution as successfully completed."""

        self.result = result
        self.status = "finished"
        self.end_time = time.time()

    def fail(self, error: Exception | str):
        """Mark execution as failed."""

        self.error = str(error)
        self.status = "failed"
        self.end_time = time.time()

    # ------------------------------------------------------------------
    # Events
    # ------------------------------------------------------------------

    def emit(self, event: SyncEvent):
        """
        Add an event to the execution event stream.
        """

        self.events.put(event)

    def close_events(self):
        """
        Signal that no more events will be emitted.
        """

        self.events.put(None)

    # ------------------------------------------------------------------
    # State
    # ------------------------------------------------------------------

    @property
    def done(self) -> bool:
        """Whether execution has finished or failed."""

        return self.status in {"finished", "failed"}

    def snapshot(self) -> dict[str, Any]:
        """
        Return a serializable representation of the execution.
        """

        return {
            "job_id": self.job_id,
            "status": self.status,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "result": self.result,
            "error": self.error,
            "done": self.done,
        }
