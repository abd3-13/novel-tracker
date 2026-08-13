from collections.abc import Callable
from dataclasses import dataclass, field
from queue import Queue
from typing import Any
from uuid import uuid4

from app.constants import Default, LogLevel, Provider, SyncMode
from app.sync.metadata import FIELDS


@dataclass
class SyncExecution:
    """
    Runtime state for a synchronization job.
    """

    job_id: str = field(default_factory=lambda: str(uuid4()))

    status: str = "pending"

    result: dict[str, Any] | None = None

    events: Queue = field(default_factory=Queue)

    error: str | None = None


@dataclass(slots=True)
class SyncJob:
    """
    Describes a synchronization request.

    This object contains no execution logic.
    It simply tells the SyncEngine what should be synchronized.
    """

    # Database table
    table: str = Default.NOVEL_TABLE

    # Novels to process
    novels: list[int] = field(default_factory=list)

    # Metadata fields to synchronize
    fields: list[str] = field(default_factory=list)

    # Preferred metadata source
    source: str = Provider.LOCAL

    # Update strategy
    mode: str = SyncMode.FILL_MISSING

    # Optional behavior
    dry_run: bool = False
    force: bool = False

    # Optional filters
    options: dict[str, Any] = field(default_factory=dict)

    # Display name (UI / logging)
    profile: str = "Synchronization"

    # Logging level
    log_level: LogLevel = LogLevel.NORMAL

    # Event callbacks
    event_handler: Callable | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any], table: str | None = None) -> "SyncJob":
        if not isinstance(data, dict):
            raise TypeError("Sync job must be an object.")

        source = data.get("source", Provider.LOCAL)
        mode = data.get("mode", SyncMode.FILL_MISSING)
        fields = data.get("fields", [])
        dry_run = data.get("dry_run", False)
        force = data.get("force", False)

        try:
            source = Provider(source)
        except ValueError:
            raise ValueError(f"Invalid sync source: {source}") from None

        try:
            mode = SyncMode(mode)
        except ValueError:
            raise ValueError(f"Invalid sync mode: {mode}") from None

        unknown = [value for value in fields if value not in FIELDS]

        if unknown:
            raise ValueError(f"Unknown metadata fields: {', '.join(unknown)}")

        if not isinstance(fields, list):
            raise TypeError("Sync fields must be a list.")

        if not all(isinstance(value, str) for value in fields):
            raise ValueError("Sync fields must contain strings.")

        novels = data.get("novels", [])

        if not isinstance(novels, list):
            raise TypeError("Novels must be a list.")

        if not all(isinstance(value, int) for value in novels):
            raise ValueError("Novel IDs must be integers.")

        if not isinstance(dry_run, bool):
            raise TypeError("dry_run must be a boolean.")

        if not isinstance(force, bool):
            raise TypeError("force must be a boolean.")

        return cls(
            table=table or Default.NOVEL_TABLE,
            novels=novels,
            fields=fields,
            source=source,
            mode=mode,
            dry_run=dry_run,
            force=force,
        )
