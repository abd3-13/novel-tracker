from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class SyncEvent:
    type: str
    data: dict[str, Any]
