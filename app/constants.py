"""
Shared synchronization constants.

These define the common vocabulary used throughout the
synchronization engine.

They are intentionally limited to identifiers that are shared
between multiple modules.
"""

from enum import StrEnum


# =============================================================================
# Defaults
# =============================================================================
class Default(StrEnum):
    NOVEL_TABLE = "novels"
    DEMO_NOVEL_TABLE = "demo_novels"


# =============================================================================
# Providers
# =============================================================================


class Provider(StrEnum):
    """
    Metadata provider identifiers.
    """

    LOCAL = "local"
    ONLINE = "online"


# =============================================================================
# Assets
# =============================================================================


class Asset(StrEnum):
    """
    Downloadable / generated assets.
    """

    COVER = "cover"
    CHARACTERS = "characters"


# =============================================================================
# Events
# =============================================================================


class Event(StrEnum):
    """
    Synchronization events.
    """

    JOB_START = "job_start"
    JOB_FINISH = "job_finish"

    NOVEL_START = "novel_start"
    NOVEL_FINISH = "novel_finish"

    STAGE = "stage"
    FIELD = "field"
    ASSET = "asset"

    WARNING = "warning"
    ERROR = "error"


# =============================================================================
# Stages
# =============================================================================


class Stage(StrEnum):
    """
    Synchronization pipeline stages.
    """

    PROVIDERS = "providers"
    METADATA = "metadata"
    COMMIT = "commit"
    DONE = "done"


# =============================================================================
# Metadata Keys
# =============================================================================


class MetadataKey(StrEnum):
    """
    Canonical metadata identifiers. Same as the DB column names(in db.py), used to avoid hardcoding strings throughout the codebase.
    """

    ID = "id"

    TITLE = "name"
    AUTHOR = "author"
    DESCRIPTION = "description"

    URL = "url"
    SOURCE = "source"
    STATUS = "status"

    LOCAL_CHAPTERS = "localchap"
    LOCAL_LAST_TITLE = "local_lastchaptitle"
    LOCAL_LAST_FILE = "local_lastchapfile"

    ONLINE_CHAPTERS = "onlinechap"
    LATEST_CHAPTER_TIME = "latestchaptime"

    PROGRESS = "progress"

    COVER = "cover_path"

    CHARACTERS = "characters"
    ONLINE_CHARACTERS = "online_characters"

    FILEPATH = "filepath"
    EPUB_EXISTS = "epub_exists"


DatabaseColumn = MetadataKey


# ==============================================================================
# Synchronization
# ==============================================================================


class SyncMode(StrEnum):
    OVERWRITE = "overwrite"
    FILL_MISSING = "fill_missing"
    SKIP_EXISTING = "skip_existing"
    ONLY_CHANGED = "only_changed"


class SyncAction(StrEnum):
    UPDATE = "update"
    SKIP = "skip"
    DELETE = "delete"
    CREATE = "create"
    FETCH_COVER = "fetch_cover"
    FETCH_CHARACTERS = "fetch_characters"


# =============================================================================
# Log Levels
# =============================================================================


class LogLevel(StrEnum):
    """
    Synchronization logging levels.
    """

    SILENT = "silent"
    NORMAL = "normal"
    DEBUG = "debug"
