from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class SyncCollector:
    """
    Collects database updates for a single novel.

    Metadata handlers only register changes here.
    The SyncEngine is responsible for committing them.
    """

    _updates: dict[str, Any] = field(default_factory=dict)

    def set(self, column: str, value: Any) -> None:
        """Queue or replace a column update."""
        self._updates[column] = value

    def get(self, column: str, default: Any = None) -> Any:
        """Return a queued value."""
        return self._updates.get(column, default)

    def has(self, column: str) -> bool:
        """Check if a column has a pending update."""
        return column in self._updates

    def changed(self) -> bool:
        """True if any updates are queued."""
        return bool(self._updates)

    def remove(self, column: str) -> None:
        """Remove a queued update."""
        self._updates.pop(column, None)

    def clear(self) -> None:
        """Discard all queued updates."""
        self._updates.clear()

    def items(self):
        """Iterate over queued updates."""
        return self._updates.items()

    def as_dict(self) -> dict[str, Any]:
        """Return a copy of all queued updates."""
        return dict(self._updates)

    def __len__(self) -> int:
        return len(self._updates)

    def __contains__(self, column: str) -> bool:
        return column in self._updates
