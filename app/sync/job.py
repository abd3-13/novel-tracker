from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from app.constants import Default, LogLevel, Provider, SyncMode


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
    def from_dict(cls, data: dict[str, Any]) -> "SyncJob":
        if not isinstance(data, dict):
            raise TypeError("Sync job must be an object.")

        source = data.get("source", Provider.LOCAL)
        mode = data.get("mode", SyncMode.FILL_MISSING)
        fields = data.get("fields", [])
        table = data.get("table", Default.NOVEL_TABLE)

        try:
            source = Provider(source)
        except ValueError:
            raise ValueError(f"Invalid sync source: {source}") from None

        try:
            mode = SyncMode(mode)
        except ValueError:
            raise ValueError(f"Invalid sync mode: {mode}") from None

        if not isinstance(fields, list):
            raise TypeError("Sync fields must be a list.")

        if not all(isinstance(value, str) for value in fields):
            raise ValueError("Sync fields must contain strings.")

        novels = data.get("novels", [])

        if not isinstance(novels, list):
            raise TypeError("Novels must be a list.")

        if not all(isinstance(value, int) for value in novels):
            raise ValueError("Novel IDs must be integers.")

        return cls(
            table=table,
            novels=novels,
            fields=fields,
            source=source,
            mode=mode,
            dry_run=bool(data.get("dry_run", False)),
            force=bool(data.get("force", False)),
        )
