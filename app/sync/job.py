from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from app.constants import LogLevel, Provider, SyncMode


@dataclass(slots=True)
class SyncJob:
    """
    Describes a synchronization request.

    This object contains no execution logic.
    It simply tells the SyncEngine what should be synchronized.
    """

    # Database table
    table: str = "novels"

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
