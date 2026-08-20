"""
Shared constants.

These define the common vocabulary used throughout the
Codebase.

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


class AuthField(StrEnum):
    USERNAME = "username"
    PASSWORD = "password"
    NEXT = "next"
    ROLE = "role"
    ACTIVE = "active"


class AuthRole(StrEnum):
    ADMIN = "admin"
    USER = "user"
    DEMO = "demo"


class AuthMessage(StrEnum):
    AUTH_FAILED_TITLE = "Authentication Failed"
    INVALID_CREDENTIALS = "Invalid username or password."
    ACCOUNT_DISABLED_TITLE = "Account Disabled"
    ACCOUNT_DISABLED = "Your account has been disabled."


class AuthCategory(StrEnum):
    ERROR = "error"
    WARNING = "warning"


class AuthResponseKey(StrEnum):
    SUCCESS = "success"
    TITLE = "title"
    MESSAGE = "message"
    CATEGORY = "category"
    REDIRECT = "redirect"


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


# =============================================================================
# Settings
# =============================================================================


class SettingKey(StrEnum):
    """Canonical application setting names used across the codebase."""

    DB_PATH = "DB_PATH"
    ENDPOINT = "ENDPOINT"
    IMG_ENDPOINT = "IMG_ENDPOINT"
    USER_AGENT = "USER_AGENT"
    REFER_URL = "REFER_URL"
    DELAY_FROM = "DELAY_FROM"
    DELAY_TO = "DELAY_TO"
    LOCAL_EPUB_DIR = "LOCAL_EPUB_DIR"
    COVER_PATH = "COVER_PATH"
    CHECK_ERROR_LINK = "CHECK_ERROR_LINK"
    API_TIMEOUT = "API_TIMEOUT"
    SECRETS_KEY = "SECERT_KEY"
    LAST_BULK_TIME = "LAST_BULK_TIME"
    UPDATE_LOCAL_ONLINE = "UPDATE_LOCAL_ONLINE"
    EPUB_READER_FROM = "EPUB_READER_FROM"
    MOON_PROGRESS_FILE = "MOON_PROGRESS_FILE"
    CHARAC_API = "CHARAC_API"


# =============================================================================
# Metadata namespaces and source vocabularies
# =============================================================================


class MetadataNamespace(StrEnum):
    """Common metadata namespaces used when parsing metadata from sources."""

    DC = "DC"


class SourceDomain(StrEnum):
    """Known external source domains."""

    WEBNOVEL = "webnovel"
    BLOGSPOT = "blogspot"
    WORDPRESS = "wordpress"
    LAW = "law"


class TocKeyword(StrEnum):
    """Keywords used to classify EPUB table-of-contents entries."""

    CHAPTER = "chapter"
    VOLUME = "volume"


class AssetExtension(StrEnum):
    """Generated or extracted asset formats."""

    WEBP = "WEBP"
    COVER = "cover"
    NO_COVER = "nocover"


class DefaultValue(StrEnum):
    """Default and fallback values used across the app."""

    CURRENT_DIR = "./"
    CURRENT_COVER_DIR = "./covers"
    UNKNOWN_TITLE = "Unknown Title"
    UNKNOWN_TEXT = "Unknown"
    ONGOING = "Ongoing"
    HIATUS = "Hiatus"
    NO_COVER = "nocover"


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


class SyncResultKey(StrEnum):
    ID = "id"
    TITLE = "title"
    UPDATED = "updated"
    CHANGES = "changes"
    ERRORS = "errors"
    WARNINGS = "warnings"


class SyncJobKey(StrEnum):
    SOURCE = "source"
    MODE = "mode"
    DRY_RUN = "dry_run"
    FORCE = "force"
    FIELDS = "fields"
    NOVELS = "novels"


class SyncJobOptionKey(StrEnum):
    SOURCE = "source"
    STATUS = "status"
    WHERE = "where"
    PARAMS = "params"


class SyncSummaryKey(StrEnum):
    TOTAL = "total"
    UPDATED = "updated"
    SKIPPED = "skipped"
    ERRORS = "errors"
    WARNINGS = "warnings"
    CANCELLED = "cancelled"


class SyncErrorMessage(StrEnum):
    UNKNOWN_MODE = "Unknown sync mode: {mode}"
    UNKNOWN_SOURCE = "Unknown sync source: {source}"


class WebnovelHeader(StrEnum):
    USER_AGENT = "User-Agent"
    ACCEPT = "Accept"
    REFERER = "Referer"
    ARCANE = "arcane"
    CONTENT_TYPE = "Content-Type"


class WebnovelJsonKey(StrEnum):
    DATA = "Data"
    MESSAGE = "Message"
    SUCCESS = "Success"
    BOOK_ID = "bookId"
    ROLE_ID = "RoleId"
    NAME = "Name"
    BOOK_NAME = "BookName"
    AUTHOR_INFO = "AuthorInfo"
    AUTHOR_NAME = "AuthorName"
    DESCRIPTION = "Description"
    CHAPTER_NUM = "ChapterNum"
    LAST_CHAPTER_TIME = "LastChapterTime"
    DESIGN_IMAGE = "DesignImage"
    NICKNAME = "NickName"
    HEIGHT = "Height"
    BIRTHDAY = "Birthday"
    ITEMS = "Items"
    ROLE_ID_FIELD = "roleId"
    BOOK_ID_FIELD = "bookId"


class WebnovelErrorMessage(StrEnum):
    BOOK_ID_REQUIRED = "Book ID is required to fetch characters."
    BOOK_ID_EMPTY = "book_id cannot be empty"
    MISSING_RESPONSE_DATA = "Missing 'Data' in API response."
    NO_CHARACTER_LIST = "Unable to retrieve character list for {book_id}"


class WebnovelSummaryKey(StrEnum):
    STATUS = "status"
    BOOK_ID = "book_id"
    CHARACTERS = "characters"
    DOWNLOADED = "downloaded"
    FAILED = "failed"
    OUTPUT_DIR = "output_dir"
    MSG = "msg"


class WebnovelSummaryStatus(StrEnum):
    SUCCESS = "success"
    PARTIAL = "partial"


class MetadataGroup(StrEnum):
    BASIC = "Basic"
    CHAPTERS = "Chapters"
    COVER = "Cover"
    CHARACTERS = "Characters"
    STATUS = "Status"
    FILE = "File"


class MetadataLabel(StrEnum):
    TITLE = "Title"
    URL = "URL"
    AUTHOR = "Author"
    DESCRIPTION = "Description"
    SOURCE = "Source"
    LOCAL_CHAPTERS = "Local Chapters"
    ONLINE_CHAPTERS = "Online Chapters"
    LATEST_CHAPTER_TIME = "Latest Chapter Time"
    LOCAL_LAST_TITLE = "Last Chapter Title"
    LOCAL_LAST_FILE = "Last Chapter File"
    COVER = "Cover"
    FETCH_COVER = "Fetch Cover"
    CHARACTERS = "Characters"
    ONLINE_CHARACTERS = "Online Characters"
    FETCH_CHARACTERS = "Fetch Characters"
    STATUS = "Status"
    PROGRESS = "Reading Progress"
    FILEPATH = "EPUB File"
    EPUB_EXISTS = "EPUB Exists"


class MetadataDescription(StrEnum):
    TITLE = "Novel title."
    URL = "Original novel website address."
    AUTHOR = "Novel author."
    DESCRIPTION = "Synopsis or summary."
    SOURCE = "Metadata provider or website."
    LOCAL_CHAPTERS = "Number of chapters stored in the EPUB."
    ONLINE_CHAPTERS = "Latest chapter count available online."
    LATEST_CHAPTER_TIME = "Publication time of the latest online chapter."
    LOCAL_LAST_TITLE = "Title of the last chapter in the EPUB."
    LOCAL_LAST_FILE = "Internal EPUB file for the last chapter."
    COVER = "Stored cover image."
    FETCH_COVER = "Download a fresh cover image."
    CHARACTERS = "Stored character list."
    ONLINE_CHARACTERS = "Characters available from the online provider."
    FETCH_CHARACTERS = "Download character images and metadata."
    STATUS = "Publication status of the novel."
    PROGRESS = "Reading progress imported from Moon+ Reader."
    FILEPATH = "Path to the EPUB file."
    EPUB_EXISTS = "Whether the EPUB file exists on disk."


class MetadataIcon(StrEnum):
    BOOK = "book"
    LINK = "link"
    USER = "user"
    ALIGN_LEFT = "align-left"
    WORLD = "world"
    BOOKS = "books"
    CLOUD = "cloud"
    CLOCK = "clock"
    BOOK_2 = "book-2"
    FILE_TEXT = "file-text"
    PHOTO = "photo"
    DOWNLOAD = "download"
    USERS = "users"
    USERS_GROUP = "users-group"
    USER_DOWN = "user-down"
    CIRCLE_CHECK = "circle-check"
    PROGRESS = "progress"
    FILE = "file"
    FILE_CHECK = "file-check"


class ExecutionStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    FINISHED = "finished"
    FAILED = "failed"
    CANCELLED = "cancelled"
    CANCELLING = "cancelling"


class ExecutionSnapshotKey(StrEnum):
    JOB_ID = "job_id"
    STATUS = "status"
    START_TIME = "start_time"
    END_TIME = "end_time"
    RESULT = "result"
    ERROR = "error"
    DONE = "done"
    CANCELLING = "cancelling"


SYNC_METADATA = {
    "title": {
        "label": "Title",
        "group": "General",
        "provider": [Provider.LOCAL, Provider.ONLINE],
        "keys": [MetadataKey.TITLE],
        "default": True,
    },
    "author": {
        "label": "Author",
        "group": "General",
        "provider": [Provider.LOCAL, Provider.ONLINE],
        "keys": [MetadataKey.AUTHOR],
        "default": True,
    },
    "cover": {
        "label": "Cover",
        "group": "Assets",
        "provider": [Provider.ONLINE],
        "asset": Asset.COVER,
        "default": True,
    },
    "chapters": {
        "label": "Chapters",
        "group": "Content",
        "provider": [Provider.LOCAL, Provider.ONLINE],
        "keys": [
            MetadataKey.LOCAL_CHAPTERS,
            MetadataKey.ONLINE_CHAPTERS,
            MetadataKey.LOCAL_LAST_TITLE,
            MetadataKey.LOCAL_LAST_FILE,
            MetadataKey.LATEST_CHAPTER_TIME,
        ],
        "default": True,
    },
}

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
