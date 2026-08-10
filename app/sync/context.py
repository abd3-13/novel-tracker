from dataclasses import dataclass, field
from typing import Any

from .events import SyncEvent
from .job import SyncJob


@dataclass(slots=True)
class SyncContext:
    """
    Runtime context for synchronizing a single novel.

    This object is created by the SyncEngine and passed to every
    metadata handler. It contains everything needed during execution.
    """

    # Sync request
    job: SyncJob

    # Current novel (database row)
    novel: dict

    # Provider manager
    providers: Any = None

    # Database update collector
    collector: Any = None

    # Runtime services
    logger: Any = None
    state: Any = None

    # Per-novel synchronization result
    result: Any = None

    # Shared temporary cache
    cache: dict = field(default_factory=dict)

    def emit(self, event: str, **data):
        """
        Emit an event for the current synchronization.
        """
        

        if self.job.event_handler:
            self.job.event_handler(SyncEvent(type=event, data=data))
