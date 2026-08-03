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

import os
import sqlite3

from app.utils.tools import find_database_file, normalize_title

# ============================================================================
# Constants
# ============================================================================
DEFAULT_DB = find_database_file()
DEFAULT_TABLE = "novels"

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
    conn = sqlite3.connect(DEFAULT_DB)
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


def execute(query, params=(), *, commit=False, close=False):
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
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(query, params or ())
    if commit:
        conn.commit()
    if close:
        conn.close()
    return cur, conn


def fetch_one(query, params=()):
    """
    Execute a query and return one row.
    """
    cur, conn = execute(query, params)
    row = cur.fetchone()
    conn.close()
    return row


def fetch_all(query, params=(), close=False):
    """
    Execute a query and return all rows.
    """
    cur, conn = execute(query, params)
    rows = cur.fetchall()
    if close:
        conn.close()
        return rows
    return rows, cur, conn


# ============================================================================
# Database Initialization
# ============================================================================


def init_db():
    """
    Initialize the application database.
    Creates all required tables if they do not exist and inserts the
    default application settings.
    """
    conn = get_conn()
    cur = conn.cursor()
    # ------------------------------------------------------------------
    # Novels
    # ------------------------------------------------------------------
    cur.execute("""
    CREATE TABLE IF NOT EXISTS novels (
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
      progress_updated DATETIME
    )
  """)
    # ------------------------------------------------------------------
    # Settings
    # ------------------------------------------------------------------
    cur.execute("""
    CREATE TABLE IF NOT EXISTS settings (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      key TEXT NOT NULL UNIQUE,
      value TEXT
    )
  """)
    # ------------------------------------------------------------------
    # Default Settings
    # ------------------------------------------------------------------
    default_settings = {
        "DB_PATH": "my-novels.db",
        "ENDPOINT": "",
        "IMG_ENDPOINT": "",
        "USER_AGENT": "",
        "REFER_URL": "",
        "DELAY_FROM": "1",
        "DELAY_TO": "3",
        "LOCAL_EPUB_DIR": "novels/",
        "COVER_PATH": "static/img/cover/",
        "CHECK_ERROR_LINK": "1",
        "API_TIMEOUT": "10",
        "SECERT_KEY": "",
        "LAST_BULK_TIME": "",
        "UPDATE_LOCAL_ONLINE": "local",
        "EPUB_READER_FROM": "current",
        "MOON_PROGRESS_FILE": "/data/data/com.flyersoft.moonreaderp/shared_prefs/positions10.xml",
        "CHARAC_API": "https://idruid.webnovel.com/go/api/book-role",
    }
    for key, value in default_settings.items():
        cur.execute(
            """
      INSERT INTO settings(key, value)
      VALUES(?, ?)
      ON CONFLICT(key)
      DO UPDATE SET value = excluded.value
    """,
            (key, value),
        )
    conn.commit()
    conn.close()


def init_users_table():
    """
    Create the user table.
    """
    execute(
        """
    CREATE TABLE IF NOT EXISTS users (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      username TEXT UNIQUE NOT NULL,
      email TEXT,
      password_hash TEXT NOT NULL,
      role TEXT DEFAULT 'user',
      active INTEGER DEFAULT 1,
      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
  """,
        commit=True,
        close=True,
    )


# ============================================================================
# Settings API
# ============================================================================


def load_settings():
    """
    Load all application settings into memory.
    Returns
    -------
    dict
      Dictionary of setting key -> value.
    """
    print("RUN: load_settings()")
    conn = get_conn(row_factory=True)
    rows = conn.execute("SELECT key, value FROM settings").fetchall()
    conn.close()
    return {row["key"]: row["value"] for row in rows}


def get_settings_dict():
    """
    Return the cached settings dictionary.
    """
    return settings_dict


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
    return settings_dict.get(key, default)


def save_setting(key, value):
    """
    Save a setting.
    The in-memory cache is updated immediately before writing
    to the database.
    """
    if settings_dict.get(key) == value:
        return
    settings_dict[key] = value
    execute(
        "UPDATE settings SET value=? WHERE key=?", (value, key), commit=True, close=True
    )


# ============================================================================
# Novel CRUD
# ============================================================================


def get_table(table=DEFAULT_TABLE, role="user"):
    """
    Return all novels from a table.
    Parameters
    ----------
    table : Table name.
    role : Determines filtering.
    """
    if role == "admin":
        query = f"SELECT * FROM {table}"
    elif role == "demo":
        query = "SELECT * FROM demo_novels"
    else:
        query = f"SELECT * FROM {table} WHERE tags NOT LIKE '%nsfw%'"
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


def delete_novel(novel_id, table=DEFAULT_TABLE):
    """
    Delete one novel.
    """
    execute(f"DELETE FROM {table} WHERE id=?", (novel_id,), commit=True, close=True)


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
        "name": None,
        "url": None,
        "source": None,
        "localchap": 0,
        "onlinechap": 0,
        "status": None,
        "notes": "",
        "filepath": None,
        "latestchaptime": None,
        "author": None,
        "description": None,
        "cover_path": None,
        "local_lastchaptitle": None,
        "local_lastchapfile": None,
        "characters": 0,
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
    rows, _, _ = fetch_all(
        f"SELECT filepath, cover_path FROM {table} WHERE filepath IS NOT NULL OR cover_path IS NOT NULL ORDER BY filepath",
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
    epub_dir = get_value("LOCAL_EPUB_DIR")
    return {file for file in os.listdir(epub_dir) if file.lower().endswith(".epub")}


def get_cover_files():
    """
    Return all WebP covers inside the configured cover directory.
    """
    cover_dir = get_value("COVER_PATH")
    return {file for file in os.listdir(cover_dir) if file.lower().endswith(".webp")}


# ============================================================================
# Utility Helpers
# ============================================================================


def find_dup_title_db(input_title, table=DEFAULT_TABLE):
    """
    Search for a duplicate novel title using normalized titles.
    Returns
    -------
    dict | None
    """
    normalized = normalize_title(input_title)
    rows, _, _ = fetch_all(f"SELECT id, name FROM {table}", close=True)
    for novel_id, title in rows:
        if normalize_title(title) == normalized:
            return {"id": novel_id, "name": title}
    return None


# ============================================================================
# Module Initialization
# ============================================================================
settings_dict = load_settings()
if __name__ == "__main__":
    init_db()
    print("Database initialized.")
