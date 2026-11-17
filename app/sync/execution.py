import time
from dataclasses import dataclass, field
from queue import Queue
from threading import Event, Lock
from typing import Any
from uuid import uuid4

from app.constants import ExecutionSnapshotKey, ExecutionStatus

from .events import SyncEvent


@dataclass(slots=True)
class SyncExecution:
    """
    Runtime state for a single synchronization job.

    SyncManager owns the execution lifecycle.
    SyncRunner/SyncEngine report progress through SyncEvent.
    """

    job_id: str = field(default_factory=lambda: str(uuid4()))

    status: str = ExecutionStatus.PENDING

    start_time: float | None = None
    end_time: float | None = None

    result: dict[str, Any] | None = None

    error: str | None = None

    # One queue per connected client. Emitted events are broadcast to all of
    # them, so several tabs can watch the same job without stealing events.
    subscribers: list[Queue[SyncEvent | None]] = field(default_factory=list)
    events_closed: bool = False

    cancel_event: Event = field(default_factory=Event)
    lock: Lock = field(default_factory=Lock)
    events_lock: Lock = field(default_factory=Lock)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self):
        """Mark execution as running."""

        with self.lock:
            self.status = ExecutionStatus.RUNNING
            self.start_time = time.time()

    def finish(self, result: dict[str, Any] | None = None):
        """Mark execution as successfully completed."""

        with self.lock:
            self.result = result
            self.status = ExecutionStatus.FINISHED
            self.end_time = time.time()

    def fail(self, error: Exception | str):
        """Mark execution as failed."""

        with self.lock:
            self.error = str(error)
            self.status = ExecutionStatus.FAILED
            self.end_time = time.time()

    def cancel(self):
        """
        Request cancellation.

        This does not forcibly terminate the worker thread.
        """

        self.cancel_event.set()

        with self.lock:
            if self.status == ExecutionStatus.RUNNING:
                self.status = ExecutionStatus.CANCELLING

    def is_cancelled(self) -> bool:
        """Return whether cancellation was requested."""

        return self.cancel_event.is_set()

    def cancelled(self, result: dict[str, Any] | None = None):
        """Mark execution as cancelled."""

        with self.lock:
            self.result = result
            self.status = ExecutionStatus.CANCELLED
            self.end_time = time.time()

    # ------------------------------------------------------------------
    # Events
    # ------------------------------------------------------------------

    def emit(self, event: SyncEvent):
        """
        Broadcast an event to every connected client.
        """

        with self.events_lock:
            subscribers = list(self.subscribers)

        for subscriber in subscribers:
            subscriber.put(event)

    def subscribe(self) -> Queue[SyncEvent | None]:
        """
        Register a client and return its private event queue.

        A client that connects after the stream closed receives ``None``
        immediately, so it can render the final snapshot and disconnect.
        """

        queue: Queue[SyncEvent | None] = Queue()

        with self.events_lock:
            if self.events_closed:
                queue.put(None)
            else:
                self.subscribers.append(queue)

        return queue

    def unsubscribe(self, queue: Queue[SyncEvent | None]) -> None:
        """Remove a disconnected client."""

        with self.events_lock:
            if queue in self.subscribers:
                self.subscribers.remove(queue)

    def close_events(self):
        """
        Signal that no more events will be emitted.
        """

        with self.events_lock:
            self.events_closed = True
            subscribers = self.subscribers
            self.subscribers = []

        for subscriber in subscribers:
            subscriber.put(None)

    # ------------------------------------------------------------------
    # State
    # ------------------------------------------------------------------

    @property
    def done(self) -> bool:
        """Whether execution has finished."""

        return self.status in {
            ExecutionStatus.FINISHED,
            ExecutionStatus.FAILED,
            ExecutionStatus.CANCELLED,
        }

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
            ExecutionSnapshotKey.JOB_ID: self.job_id,
            ExecutionSnapshotKey.STATUS: self.status,
            ExecutionSnapshotKey.START_TIME: self.start_time,
            ExecutionSnapshotKey.END_TIME: self.end_time,
            ExecutionSnapshotKey.RESULT: self.result,
            ExecutionSnapshotKey.ERROR: self.error,
            ExecutionSnapshotKey.DONE: self.done,
            ExecutionSnapshotKey.CANCELLING: self.cancelling,
        }


class SyncCancelled(Exception):
    """Raised when synchronization cancellation was requested."""
