import time
from dataclasses import dataclass, field
from queue import Queue
from threading import Event, Lock
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

    job_id: str = field(default_factory=lambda: str(uuid4()))

    status: str = "pending"

    start_time: float | None = None
    end_time: float | None = None

    result: dict[str, Any] | None = None

    error: str | None = None

    events: Queue[SyncEvent | None] = field(default_factory=Queue)

    cancel_event: Event = field(default_factory=Event)
    lock: Lock = field(default_factory=Lock)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self):
        """Mark execution as running."""

        with self.lock:
            self.status = "running"
            self.start_time = time.time()

    def finish(self, result: dict[str, Any] | None = None):
        """Mark execution as successfully completed."""

        with self.lock:
            self.result = result
            self.status = "finished"
            self.end_time = time.time()

    def fail(self, error: Exception | str):
        """Mark execution as failed."""

        with self.lock:
            self.error = str(error)
            self.status = "failed"
            self.end_time = time.time()

    def cancel(self):
        """
        Request cancellation.

        This does not forcibly terminate the worker thread.
        """

        self.cancel_event.set()

        with self.lock:
            if self.status == "running":
                self.status = "cancelling"

    def is_cancelled(self) -> bool:
        """Return whether cancellation was requested."""

        return self.cancel_event.is_set()

    def cancelled(self, result: dict[str, Any] | None = None):
        """Mark execution as cancelled."""

        with self.lock:
            self.result = result
            self.status = "cancelled"
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
        """Whether execution has finished."""

        return self.status in {"finished", "failed", "cancelled"}

    @property
    def cancelling(self) -> bool:
        """Whether cancellation has been requested."""

        return self.cancel_event.is_set()

    # ------------------------------------------------------------------
    # Snapshot
    # ------------------------------------------------------------------

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
            "cancelling": self.cancelling,
        }


class SyncCancelled(Exception):
    """Raised when synchronization cancellation was requested."""
