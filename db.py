import sqlite3, os

def find_database_file(filename="my-novels.db"):
  # Scan the current directory for the specified database file
  for root, dirs, files in os.walk(os.getcwd()):
    if filename in files:
      return filename
  return None  # Return None if not found

DEFAULT_DB = find_database_file() or "my-novels.db"

def get_db_conn():
  conn = sqlite3.connect(DEFAULT_DB)
  return conn

def init_db():
  conn = get_db_conn()
  c = conn.cursor()

  # Main novels table
  c.execute('''
    CREATE TABLE IF NOT EXISTS novels (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      name TEXT NOT NULL,
      url TEXT,
      author TEXT,
      description TEXT,
      tags TEXT,
      cover_path TEXT,
      localchap REAL DEFAULT 0,
      onlinechap REAL DEFAULT 0,
      latestchaptime TEXT,
      status TEXT,
      source TEXT,
      notes TEXT,
      filepath TEXT,
      epub_exists TEXT,
      created_time DATETIME DEFAULT CURRENT_TIMESTAMP,
      last_updated TEXT,
      updated_count INTEGER DEFAULT 0
    )
  ''')

  # Add trigger for changes on novel row
  c.execute('''
    CREATE TRIGGER insert_Timestamp_Trigger
    AFTER UPDATE ON novels
    BEGIN
       UPDATE novels SET last_updated =STRFTIME('%Y-%m-%d %H:%M:%f', 'NOW'), updated_count=updated_count+1 WHERE id = NEW.id;
    END;
  ''')

  # Settings table
  c.execute('''
    CREATE TABLE IF NOT EXISTS settings (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      key TEXT NOT NULL UNIQUE,
      value TEXT
    )
  ''')
  
    # Default settings dictionary
  default_settings = {
    "DB_PATH": "my-novels.db",
    "ENDPOINT": "",
    "IMG_ENDPOINT": "",
    "USER_AGENT": "",
    "DELAY_FROM": "1",
    "DELAY_TO": "3",
    "LOCAL_EPUB_DIR": "novels/",
    "COVER_PATH": "static/img/cover/",
    "CHECK_ERROR_LINK": "1",
    "API_TIMEOUT": "10",
    "SECERT_KEY": "",
    "LAST_BULK_TIME": "",
  }

  # Insert or replace defaults
  for key, value in default_settings.items():
    conn.execute("""
      INSERT INTO settings (key, value)
      VALUES (?, ?)
      ON CONFLICT(key) DO UPDATE SET value=excluded.value
    """, (key, value))

  conn.commit()
  conn.close()

def load_settings():
  """Load all settings into a dictionary."""
  print("RUN: load_Settings()")
  conn = get_db_conn()
  conn.row_factory = sqlite3.Row  # Allows for dictionary-like access to rows
  settings = conn.execute('SELECT key, value FROM settings').fetchall()
  conn.close()
  return {setting['key']: setting['value'] for setting in settings}

def get_settings_dict():
  return settings_dict

def get_value(key):
  """Fetch the value from the settings dictionary."""
  return settings_dict.get(key)

def save_setting(key, value):
  """Set the value from the settings dictionary."""
  settings_dict[key] = value
  conn = get_db_conn()
  cur = conn.cursor()
  cur.execute("UPDATE settings SET value=? WHERE key=?", (value, key))
  conn.commit()
  conn.close()
  return
  
def get_db_files():
    conn = get_db_conn()
    cursor = conn.cursor()

    # Return BOTH filepath + cover_path
    cursor.execute("""
        SELECT filepath, cover_path
        FROM novels
        WHERE filepath IS NOT NULL OR cover_path IS NOT NULL
        ORDER BY filepath
    """)

    rows = cursor.fetchall()
    conn.close()

    filepaths = set()
    covers = set()

    for fp, cp in rows:
        if fp:
            filepaths.add(os.path.basename(fp))
        if cp:
            covers.add(os.path.basename(cp))

    return filepaths, covers

def get_epub_files():
  return {
    f for f in os.listdir(get_value("LOCAL_EPUB_DIR"))
    if f.lower().endswith(".epub")
  }

def get_cover_files():
  return {
    f for f in os.listdir(get_value("COVER_PATH"))
    if f.lower().endswith(".webp")
  }

global settings_dict
settings_dict = {}
settings_dict = load_settings() 

if __name__ == "__main__":
  init_db()
  print("Database initialized.")

