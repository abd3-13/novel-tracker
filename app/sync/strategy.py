from typing import Any

from app.constants import SyncErrorMessage, SyncMode


class SyncStrategy:
    """
    Determines whether a metadata value should be updated.
    """

    @staticmethod
    def is_empty(value: Any) -> bool:
        """
        Returns True if a value is considered empty.
        """
        return value in (None, "", [], {}, ())

    @classmethod
    def should_update(cls, mode: str, current: Any, new: Any) -> bool:
        """
        Determine whether the current value should be replaced
        with the new value according to the selected sync mode.
        """

        # Never overwrite with nothing
        if new is None:
            return False

        match mode:
            case SyncMode.OVERWRITE:
                return True

            case SyncMode.FILL_MISSING | SyncMode.SKIP_EXISTING:
                return cls.is_empty(current)

            case SyncMode.ONLY_CHANGED:
                return current != new

            case _:
                raise ValueError(SyncErrorMessage.UNKNOWN_MODE.format(mode=mode))
