"""
Database layer for Novel Tracker.
Responsibilities
----------------
- SQLite connection management
- Database initialization
- Settings storage
- Novel CRUD operations
- File helper queries
- General database utilities
Higher-level business logic belongs elsewhere.
"""

import json
import os
import sqlite3
from pathlib import Path

from app.config import DATABASE_PATH
from app.constants import SETTING_METADATA, Default, MetadataKey, SettingKey
from app.utils.tools import normalize_title

# ============================================================================
# Constants
# ============================================================================
DEFAULT_DB = str(DATABASE_PATH)
DEFAULT_TABLE = Default.NOVEL_TABLE

# ============================================================================
# Connection Helpers
# ============================================================================


def get_conn(row_factory=False):
    """
    Create a SQLite connection.

    Parameters
    ----------
    row_factory
      When True, rows are returned as sqlite3.Row objects.

    Returns
    -------
    sqlite3.Connection
    """
    Path(DEFAULT_DB).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DEFAULT_DB)
    conn.execute("PRAGMA busy_timeout = 5000")
    # WAL is persistent per database file and is enabled in init_db(). NORMAL
    # sync is the safe companion setting: durable against app crashes, and
    # fast enough for background sync writes.
    conn.execute("PRAGMA synchronous = NORMAL")
    if row_factory:
        conn.row_factory = sqlite3.Row
    return conn


def commit(conn):
    """
    Commit changes and close the connection.
    """
    if conn:
        conn.commit()
        conn.close()


# ============================================================================
# Generic SQL Helpers
# ============================================================================


def execute(query, params=(), *, commit=False, close=False, row_factory=False):
    """
    Execute a SQL statement.

    Parameters
    ----------
    query : SQL query.
    params : SQL parameters.
    commit : Commit transaction.
    close : Close connection afterwards.

    Returns
    -------
    (cursor, connection)
    """
    conn = get_conn(row_factory=row_factory)
    cur = conn.cursor()
    cur.execute(query, params or ())
    if commit:
        conn.commit()
    if close:
        conn.close()
    return cur, conn


def fetch_one(query, params=(), row_factory=False):
    """
    Execute a query and return one row.
    """
    cur, conn = execute(query, params, row_factory=row_factory)
    row = cur.fetchone()
    conn.close()
    return row


def fetch_all(query, params=(), close=False, row_factory=False):
    """
    Execute a query and return all rows.
    """
    cur, conn = execute(query, params, row_factory=row_factory)
    rows = cur.fetchall()
    if close:
        conn.close()
        return rows
    return rows, cur, conn


# ============================================================================
# Database Initialization
# ============================================================================


NOVEL_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS {table} (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL UNIQUE,
  url TEXT,
  localchap INTEGER DEFAULT 0,
  onlinechap INTEGER DEFAULT 0,
  latestchaptime TEXT,
  status TEXT,
  source TEXT,
  notes TEXT,
  filepath TEXT,
  created_time DATETIME DEFAULT CURRENT_TIMESTAMP,
  last_updated TEXT,
  updated_count INTEGER DEFAULT 0,
  epub_exists INTEGER,
  author TEXT,
  description TEXT,
  tags TEXT,
  characters INTEGER NOT NULL DEFAULT 0,
  online_characters INTEGER NOT NULL DEFAULT 0,
  cover_path TEXT,
  local_lastchaptitle TEXT,
  local_lastchapfile TEXT,
  progress INTEGER NOT NULL DEFAULT 0,
  progress_updated DATETIME,
  discord_channel_url TEXT,
  is_deleted INTEGER NOT NULL DEFAULT 0
)
"""

SETTINGS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS settings (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  key TEXT NOT NULL UNIQUE,
  value TEXT
)
"""

USERS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  username TEXT UNIQUE NOT NULL,
  email TEXT,
  password_hash TEXT NOT NULL,
  role TEXT DEFAULT 'user',
  active INTEGER DEFAULT 1,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
"""

DEFAULT_SETTINGS = {
    SettingKey.DB_PATH: "my-novels.db",
    SettingKey.ENDPOINT: "",
    SettingKey.IMG_ENDPOINT: "",
    SettingKey.USER_AGENT: "",
    SettingKey.REFER_URL: "",
    SettingKey.DELAY_FROM: "1",
    SettingKey.DELAY_TO: "3",
    SettingKey.LOCAL_EPUB_DIR: "novels/",
    SettingKey.COVER_PATH: "static/img/cover/",
    SettingKey.CHECK_ERROR_LINK: "1",
    SettingKey.API_TIMEOUT: "10",
    SettingKey.LAST_BULK_TIME: "",
    SettingKey.UPDATE_LOCAL_ONLINE: "local",
    SettingKey.EPUB_READER_FROM: "true",
    SettingKey.MOON_PROGRESS_FILE: "/data/data/com.flyersoft.moonreaderp/shared_prefs/positions10.xml",
    SettingKey.CHARAC_API: "https://idruid.webnovel.com/go/api/book-role",
}

_settings_cache: dict[str, str] | None = None


def init_db():
    """
    Create every application table and insert default settings.

    This is idempotent: existing rows are preserved, including settings.
    Call it from the app factory or the ``init-db`` CLI command.
    """
    global _settings_cache

    conn = get_conn()
    try:
        cur = conn.cursor()

        # Allow readers (library pages, SSE status) to keep working while a
        # background sync writes. The setting is stored in the database file,
        # so this only takes effect once per database.
        cur.execute("PRAGMA journal_mode = WAL")

        for table in (Default.NOVEL_TABLE, Default.DEMO_NOVEL_TABLE):
            cur.execute(NOVEL_TABLE_SQL.format(table=table))

        cur.execute(SETTINGS_TABLE_SQL)
        cur.execute(USERS_TABLE_SQL)

        for key, value in DEFAULT_SETTINGS.items():
            cur.execute(
                "INSERT INTO settings(key, value) VALUES(?, ?) "
                "ON CONFLICT(key) DO NOTHING",
                (key, value),
            )

        conn.commit()
    finally:
        conn.close()

    _settings_cache = None


def ensure_schema():
    """
    Apply lightweight, additive schema migrations.

    Existing databases are upgraded in place so the application does not need
    a separate migration tool. Only columns that are safe to append are added
    here; existing column order is preserved because some query builders still
    read rows by position.
    """
    conn = get_conn()
    cur = conn.cursor()

    tables = {
        row[0]
        for row in cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }

    for table in (Default.NOVEL_TABLE, Default.DEMO_NOVEL_TABLE):
        if table not in tables:
            continue

        columns = {row[1] for row in cur.execute(f"PRAGMA table_info({table})")}

        if "is_deleted" not in columns:
            cur.execute(
                f"ALTER TABLE {table} ADD COLUMN is_deleted INTEGER NOT NULL DEFAULT 0"
            )

    conn.commit()
    conn.close()


def init_users_table():
    """
    Create the user table.
    """
    execute(USERS_TABLE_SQL, commit=True, close=True)


# ============================================================================
# Settings API
# ============================================================================


def load_settings():
    """
    Load all application settings from the database.

    Returns
    -------
    dict
      Dictionary of setting key -> value.
    """
    conn = get_conn(row_factory=True)
    try:
        rows = conn.execute("SELECT key, value FROM settings").fetchall()
    finally:
        conn.close()
    return {row["key"]: row["value"] for row in rows}


def list_setting_rows():
    """Return all settings rows as dictionaries, ordered by key."""
    conn = get_conn(row_factory=True)
    rows = conn.execute("SELECT key, value FROM settings ORDER BY key").fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_settings_dict():
    """
    Return the cached settings dictionary, loading it on first use.
    """
    global _settings_cache

    if _settings_cache is None:
        _settings_cache = load_settings()

    return _settings_cache


def get_setting_metadata(key):
    metadata = SETTING_METADATA.get(key)

    if metadata is None:
        return {
            "label": key.replace("_", " ").title(),
            "description": "",
            "type": "string",
            "group": "Other",
            "icon": "settings",
        }

    return {
        "key": key,
        **metadata,
    }


def get_all_setting_metadata():
    return {
        key: {
            "key": key,
            **metadata,
        }
        for key, metadata in SETTING_METADATA.items()
    }


def get_value(key, default=None):
    """
    Return a setting value.
    Parameters
    ----------
    key
      Setting key.
    default
      Returned when the key is not found.
    """
    return get_settings_dict().get(key, default)


def save_setting(key, value):
    """
    Save a setting.

    The in-memory cache is updated immediately before writing to the database.
    Unknown keys are inserted so newly added settings persist without a manual
    schema migration.
    """
    if not isinstance(value, str):
        value = json.dumps(value)

    settings = get_settings_dict()

    if settings.get(key) == value:
        return

    settings[key] = value

    execute(
        "INSERT INTO settings(key, value) VALUES(?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (key, value),
        commit=True,
        close=True,
    )


def normalize_setting_value(value, metadata):
    setting_type = metadata.get("type", "string")

    if setting_type == "boolean":
        if isinstance(value, bool):
            return "1" if value else "0"

        if str(value).lower() in {"1", "true", "yes", "on"}:
            return "1"

        if str(value).lower() in {"0", "false", "no", "off"}:
            return "0"

        raise ValueError("Value must be a boolean.")

    if setting_type == "number":
        try:
            number = int(value)
        except (TypeError, ValueError):
            raise ValueError("Value must be a number.") from None

        minimum = metadata.get("min")
        maximum = metadata.get("max")

        if minimum is not None and number < minimum:
            raise ValueError(f"Value must be at least {minimum}.")

        if maximum is not None and number > maximum:
            raise ValueError(f"Value must be at most {maximum}.")

        return str(number)

    if setting_type == "choice":
        options = metadata.get("options", [])
        allowed_values = {option["value"] for option in options}

        if value not in allowed_values:
            raise ValueError("Invalid setting choice.")

        return str(value)

    if setting_type in {"string", "url", "path", "password"}:
        if value is None:
            return ""

        if not isinstance(value, str):
            raise ValueError("Value must be a string.")

        return value

    raise ValueError(f"Unsupported setting type: {setting_type}.")


# ============================================================================
# Novel CRUD
# ============================================================================


NSFW_VISIBILITY_SQL = "(tags IS NULL OR LOWER(tags) NOT LIKE '%nsfw%')"


def _visibility_filter(role):
    """SQL fragment that hides NSFW-tagged novels from non-administrators."""
    if role == "admin":
        return ""

    # NULL tags are safe; compare case-insensitively because imported tag
    # values are not normalized.
    return f" AND {NSFW_VISIBILITY_SQL}"


def get_table(user):
    """
    Return all active novels from a table, based on user and role.

    Soft-deleted rows are never returned to the application, and NSFW-tagged
    novels are only visible to administrators.
    """
    table = get_user_table(user)
    query = (
        f"SELECT * FROM {table} "
        "WHERE COALESCE(is_deleted, 0) = 0"
        f"{_visibility_filter(user.role)}"
    )

    return fetch_all(query, close=True)


def insert_novel(data, table=DEFAULT_TABLE):
    """
    Insert a novel.
    """
    if not data:
        raise ValueError("No data provided.")
    columns = ", ".join(data.keys())
    placeholders = ", ".join("?" for _ in data)
    query = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"
    try:
        execute(query, tuple(data.values()), commit=True, close=True)
    except sqlite3.IntegrityError as e:
        raise ValueError(str(e))
    return True


def update_novel(novel_id, updates, table=DEFAULT_TABLE):
    """
    Update a novel.
    """
    if not updates:
        return False
    set_clause = ", ".join(f"{column}=?" for column in updates)
    values = list(updates.values())
    values.append(novel_id)
    query = f"UPDATE {table} SET {set_clause} WHERE id=?"
    execute(query, tuple(values), commit=True, close=True)
    return True


def delete_novels(ids, table=DEFAULT_TABLE):
    """
    Delete multiple novels.
    Parameters
    ----------
    ids
      Comma-separated SQL ids.
      Example:
        "1,2,3"
    """
    execute(f"DELETE FROM {table} WHERE id IN ({ids})", commit=True, close=True)


def delete_missing_epub_novels(table=DEFAULT_TABLE):
    """
    Flag every active novel whose EPUB is missing as deleted.

    The rows stay in the database (so they can be inspected or recovered) but
    are skipped everywhere the application reads novels.
    Returns
    -------
    int
      Number of rows flagged in this call.
    """
    cur, _ = execute(
        f"""
        UPDATE {table}
        SET is_deleted = 1
        WHERE COALESCE(is_deleted, 0) = 0
          AND COALESCE(epub_exists, 0) = 0
        """,
        commit=True,
        close=True,
    )
    return max(cur.rowcount, 0)


def get_novel(
    novel_id, table=DEFAULT_TABLE, column="*", row_factory=True, user=None
):
    """
    Return one active novel by ID.

    When ``user`` is provided, NSFW-tagged novels are hidden from
    non-administrators, matching the library list.
    """
    visibility = _visibility_filter(user.role) if user is not None else ""

    return fetch_one(
        f"SELECT {column} FROM {table} "
        "WHERE id=? AND COALESCE(is_deleted, 0) = 0"
        f"{visibility}",
        (novel_id,),
        row_factory=row_factory,
    )


def get_db_file(filename, table=DEFAULT_TABLE):
    """
    Return an EPUB already present in the database.
    """
    if not filename:
        return None
    return fetch_one(f"SELECT filepath FROM {table} WHERE filepath=?", (filename,))


def build_base_novel():
    """
    Build an empty novel dictionary used during import.
    """
    return {
        MetadataKey.TITLE: None,
        MetadataKey.URL: None,
        MetadataKey.SOURCE: None,
        MetadataKey.LOCAL_CHAPTERS: 0,
        MetadataKey.ONLINE_CHAPTERS: 0,
        MetadataKey.STATUS: None,
        "notes": "",
        MetadataKey.FILEPATH: None,
        MetadataKey.LATEST_CHAPTER_TIME: None,
        MetadataKey.AUTHOR: None,
        MetadataKey.DESCRIPTION: None,
        MetadataKey.COVER: None,
        MetadataKey.LOCAL_LAST_TITLE: None,
        MetadataKey.LOCAL_LAST_FILE: None,
        MetadataKey.CHARACTERS: 0,
    }


# ============================================================================
# File Helpers
# ============================================================================


def get_db_filesNcover(table=DEFAULT_TABLE):
    """
    Return all EPUB filenames and cover filenames currently referenced by the database.
    Returns
    -------
    tuple[set, set]
      (epub filenames, cover filenames)
    """
    rows = fetch_all(
        f"SELECT filepath, cover_path FROM {table} "
        "WHERE COALESCE(is_deleted, 0) = 0 "
        "AND (filepath IS NOT NULL OR cover_path IS NOT NULL) "
        "ORDER BY filepath",
        close=True,
    )
    epub_files = set()
    cover_files = set()
    for filepath, cover in rows:
        if filepath:
            epub_files.add(os.path.basename(filepath))
        if cover:
            cover_files.add(os.path.basename(cover))
    return epub_files, cover_files


def get_epub_files():
    """
    Return all EPUB filenames inside the configured EPUB directory.
    """
    epub_dir = get_value(SettingKey.LOCAL_EPUB_DIR)
    return {file for file in os.listdir(epub_dir) if file.lower().endswith(".epub")}


def get_cover_files():
    """
    Return all WebP covers inside the configured cover directory.
    """
    cover_dir = get_value(SettingKey.COVER_PATH)
    return {file for file in os.listdir(cover_dir) if file.lower().endswith(".webp")}


# ============================================================================
# Utility Helpers
# ============================================================================


def find_dup_title_db(input_title, table=DEFAULT_TABLE):
    """
    Search for an active duplicate novel title using normalized titles.
    Returns
    -------
    dict | None
    """
    normalized = normalize_title(input_title)
    rows = fetch_all(
        f"SELECT id, name FROM {table} WHERE COALESCE(is_deleted, 0) = 0",
        close=True,
    )
    for novel_id, title in rows:
        if normalize_title(title) == normalized:
            return {"id": novel_id, "name": title}
    return None


def find_deleted_dup_title_db(input_title, table=DEFAULT_TABLE):
    """
    Search for a soft-deleted novel with the same normalized title.

    Importing a book whose row was previously flagged as deleted restores
    that row instead of failing on the UNIQUE(name) constraint.
    Returns
    -------
    dict | None
    """
    normalized = normalize_title(input_title)
    rows = fetch_all(
        f"SELECT id, name FROM {table} WHERE COALESCE(is_deleted, 0) = 1",
        close=True,
    )
    for novel_id, title in rows:
        if normalize_title(title) == normalized:
            return {"id": novel_id, "name": title}
    return None


def get_user_table(user):
    if user.username == "demo":
        return Default.DEMO_NOVEL_TABLE

    return Default.NOVEL_TABLE


# ============================================================================
# Module entry point
# ============================================================================

if __name__ == "__main__":
    init_db()
    ensure_schema()
    print(f"Database initialized: {DEFAULT_DB}")
