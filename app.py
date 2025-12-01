#!/usr/bin/env python3
import re, logging
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from datetime import datetime
from scraper import extract_book_id, fetch_latest_chapter_webnovel, update_online_chapters_for_all, get_epub_metadata, extract_local_chap
from db import get_db_conn, get_settings_dict, save_setting, get_db_files, get_epub_files, get_cover_files
app = Flask(__name__)
app.secret_key = "supersecretkey12"  # for flash notifications

# Regular expression for the expected date format '%Y-%m-%d %H:%M:%S.%f'
DATE_FORMAT_REGEX = r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{1,}$'

# Remove some logs from repated spam of the log stream
SPAM_PATHS = ["/status", "/ping", "/health", "/static/img/cover"]

class log_SpamFilter(logging.Filter):
  def filter(self, record):
    return not any(p in record.getMessage() for p in SPAM_PATHS)

for logger_name in ['werkzeug', 'gunicorn.access', 'gunicorn.error']:
  logging.getLogger(logger_name).addFilter(log_SpamFilter())

# Custom filter to calculate the timedelta between two datetime strings
@app.template_filter()
def time_difference(latest_time_str):
  """Calculate the time difference from the latest time to now."""
  # Handle None input
  if latest_time_str is None:
    return " "  # Or return None
  
  # Validate the date format using regex
  if not re.match(DATE_FORMAT_REGEX, latest_time_str):
    return "Invalid date format"  # Or return None
  
  """Calculate the time difference from the latest time to now."""
  # Convert the latest_time_str to a datetime object
  latest_time = datetime.strptime(latest_time_str, '%Y-%m-%d %H:%M:%S.%f')
  now = datetime.now()
  
  # Calculate the difference
  delta = now - latest_time
  days = delta.days
    
  if days >= 1:
    return f"{days}" if days > 1 else "1"
  else:
    return "1"  # If less than a day ago

@app.route('/')
def index():
  conn = get_db_conn()
  cur = conn.cursor()
  cur.execute("SELECT id, name, url, localchap, onlinechap, latestchaptime, status, source, notes, filepath FROM novels ORDER BY id")
  novels = cur.fetchall()
  conn.close()
  settings_dict = get_settings_dict()
  return render_template('index.html', novels=novels, settings=settings_dict)

# Add this API endpoint to return JSON data for DataTables
@app.route('/api/novels')
def api_novels():
  conn = get_db_conn()
  cur = conn.cursor()
  cur.execute("SELECT id, name, url, localchap, onlinechap, latestchaptime, status, source, notes, filepath, epub_exists, author, description, cover_path FROM novels ORDER BY name")
  rows = cur.fetchall()
  conn.close()

  # Map rows into dicts for JSON. Use the existing time_difference filter to provide a human-friendly column
  novels = []
  for r in rows:
    novels.append({
      "id": r[0],
      "name": r[1],
      "url": r[2],
      "localchap": r[3],
      "onlinechap": r[4],
      "latestchaptime": r[5],
      "timeago": time_difference(r[5]) if r[5] else "",
      "status": r[6],
      "source": r[7],
      "notes": r[8],
      "filepath": r[9],
      "epubexists": r[10],
      "author": r[11],
      "description": r[12],
      "cover_path": r[13]
    })

  # Return wrapped in "data" because the DataTable below uses dataSrc: "data"
  return jsonify({"data": novels})

@app.route('/add', methods=['POST'])
def add():
  message = []
  status = "success"
  try:
    # --- Get form data with defaults ---
    name = request.form.get("name", "").strip()
    url = request.form.get("url", "").strip()
    source = request.form.get("source", "").strip().lower()
    local_chap = request.form.get("localchap", 0)
    online_chap = request.form.get("onlinechap", 0)
    status = request.form.get("status", "").strip()
    notes = request.form.get("notes", "").strip()

    # --- Validate required fields ---
    if not name or not url or not source:
      message.append("Missing required fields")

    latest_chap_time = None

    # --- Auto-fetch online chapter if source is webnovel ---
    if source == "webnovel":
      book_id = extract_book_id(url)
      if book_id:
        online_chap, latest_chap_time, author, desc, imgurl = fetch_latest_chapter_webnovel(book_id)
      else:
        message.append("Invalid Webnovel URL / Book ID")

    # --- Insert into database ---
    conn = get_db_conn()
    cur = conn.cursor()
    cur.execute("""
      INSERT INTO novels (name, url, source, localchap, onlinechap, status, notes, latestchaptime, author, description, cover_path)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (name, url, source, local_chap, online_chap, status, notes, latest_chap_time, author, desc, imgurl))
    conn.commit()
    conn.close()

    message.append(f"✅ Novel '{name}' added successfully")

  except Exception as e:
    message.append(str(e))
    status = "error"
  return jsonify({ "message": "\n".join(message), "status": status})

@app.route('/import-epub', methods=['POST'])
def import_epub():
  try:
    data = request.get_json(force=True)
    filename = data.get("filename")

    meta = get_epub_metadata(filename)
    name = meta.get("title", "Unknown Title")
    url = meta.get("source_url", "")
    source = meta.get("source", "local")
    local_chap = extract_local_chap(filename)
    online_chap, latest_chap_time, author, desc, imgurl = fetch_latest_chapter_webnovel(extract_book_id(url))
    status = "Ongoing" if int(time_difference(latest_chap_time)) <= 30 else "Hiatus"
    notes = ""

    if local_chap is None or local_chap == 0:
      raise ValueError(f"Could not determine chapter count for {filename}")

    conn = get_db_conn()
    cur = conn.cursor()

    cur.execute("""
      INSERT INTO novels 
      (name, url, source, localchap, onlinechap, status, notes, filepath, latestchaptime, author, description, cover_path)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
      name, url, source, local_chap, online_chap, status, notes, filename, latest_chap_time, author, desc, imgurl
    ))

    conn.commit()
    conn.close()

    return jsonify({
      "status": "success",
      "message": f"{name} imported successfully"
    })

  except Exception as e:
    print("Import EPUB error:", e)
    return jsonify({
      "status": "error",
      "message": str(e)
    }), 500

@app.route('/edit/<int:id>', methods=['POST'])
def edit(id):
  messages = []
  status = "success"
  
  # Get query parameters
  fields = {
    "name": request.form.get("name"),
    "url": request.form.get("url"),
    "localchap": request.form.get("localchap"),
    "onlinechap": request.form.get("onlinechap"),
    "source": request.form.get("source"),
    "status": request.form.get("status"),
    "notes": request.form.get("notes"),
    "filepath": request.form.get("filepath")
  }

  # Filter out None values
  updates = {k: v for k, v in fields.items() if v is not None}

  if not updates:
    messages.append("No updates provided.")

  # Dynamically build SQL SET clause
  set_clause = ", ".join([f"{k}=?" for k in updates.keys()])
  values = list(updates.values())
  values.append(id)  # for WHERE id=?

  # Update the database safely
  try:
    with get_db_conn() as conn:
      cur = conn.cursor()
      cur.execute(f"UPDATE novels SET {set_clause} WHERE id=?", values)
    messages.append(f"✅ Updated '{updates.get('name', 'the novel')}'.")
  except Exception as e:
    messages.append(str(e))
    status = "error"
  return jsonify({ "message": "\n".join(messages), "status": status})

@app.route('/get-from-epub')
def get_from_epub():
  get_param = request.args.get("get")
  epub = request.args.get("epub")

  # Set default values
  title = source = url = lchap = ochap = author = desc = None
  # Load metadata (returns url, source, author, description, cover_id, title)
  meta = get_epub_metadata(epub)

  if get_param == "title":
    title = meta.get("title")
  if get_param == "source":
    source = meta.get("source")
  if get_param == "url":
    url = meta.get("url")
  if get_param == "author":
    author = meta.get("author")
  if get_param == "desc":
    desc = meta.get("description")
  elif get_param == "all":
    title  = meta.get("title")
    url    = meta.get("url")
    source = meta.get("source")
    author = meta.get("author")
    desc   = meta.get("description")
    ochap, _, _, _, _ = fetch_latest_chapter_webnovel(extract_book_id(url))
    lchap = extract_local_chap(epub)

  return jsonify({
    "title": title,
    "source": source,
    "url": url,
    "author": author,
    "desc": desc,
    "lchap": lchap,
    "ochap": ochap
  })

@app.route('/delete/<int:id>', methods=['POST'])
def delete(id):
  name = request.form.get("name")

  try:
    conn = get_db_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM novels WHERE id=?", (id,))
    conn.commit()
    conn.close()

    return jsonify({"status": "success", "msg": f"🗑 '{name}' deleted."})

  except Exception as e:
    return jsonify({"status": "error", "msg": str(e)})
    
@app.route('/updateall', methods=['POST'])
def updateall():
  onlinechap = request.form.get("onlinechap", 0)
  localchap = request.form.get("localchap", 0)
  limit = request.form["limit"]
  startId = request.form.get("startId", 1)
  title_opt = request.form.get("title", 0)
  url_opt = request.form.get("url", 0)
  audeco_opt = request.form.get("audeco", 0)
  check_epub = request.form.get("checkepub", 0)
  cover_opt = request.form.get("cover", 0)
  

  func_msg, msg_cat = update_online_chapters_for_all(int(onlinechap), int(localchap), int(startId), int(limit), int(title_opt), int(url_opt), int(audeco_opt), int(cover_opt), int(check_epub))
  # Default msg_cat to "message" if it is None

  if msg_cat is None:
    msg_cat = "message"

  return jsonify({
    "message": func_msg,
    "category": msg_cat
  })

@app.route('/update/<id>')
def update(id):
  messages = []
  status = "success"

  # --- Get params ---
  name = request.args.get("name", "")
  url = request.args.get("url", "")
  source = request.args.get("source", "")
  local_chap = float(request.args.get("local_chap", 0))
  online_chap = float(request.args.get("online_chap", 0))
  epub_file = request.args.get("filepath", "")

  if not source or not url:
    return jsonify({"status": "error", "msg": "Missing parameters"})

  # --- Values to compare/update ---
  updated_fields = {}   # final dict to be written to DB
  change_log = []     # human readable messages

  # ------------------------------------------------
  # 1) Extract online data (depends on source)
  # ------------------------------------------------
  func_online_chap = online_chap
  latest_chap_time = None
  author = desc = imgurl = None

  if source.lower() == "webnovel":
    book_id = extract_book_id(url)
    if book_id:
      func_online_chap, latest_chap_time, author, desc, imgurl = \
        fetch_latest_chapter_webnovel(book_id)
    else:
      messages.append("Invalid book ID")
  else:
    messages.append("Unsupported source (offline mode)")

  # ------------------------------------------------
  # 2) Extract local chapter from EPUB
  # ------------------------------------------------
  func_local_chap = float(extract_local_chap(epub_file) or 0)

  # ------------------------------------------------
  # 3) Build list of fields that changed
  # ------------------------------------------------
  # Format: field_name : (old_value, new_value)
  potential_updates = {
    "onlinechap": (online_chap, func_online_chap),
    "localchap": (local_chap, func_local_chap),
    "latestchaptime": (None, latest_chap_time),  # always trust API time
    "author": (None, author),
    "description": (None, desc),
    "cover_path": (None, imgurl)
  }

  for field, (old, new) in potential_updates.items():
    if new is None:
      continue  # skip missing values
    if str(old) != str(new):
      updated_fields[field] = new
      change_log.append(f"Updated {field}: {old} → {new}")

  # ------------------------------------------------
  # 4) Commit only if there are changes
  # ------------------------------------------------
  if updated_fields:
    try:
      conn = get_db_conn()
      cur = conn.cursor()

      # dynamic SQL for updates
      set_clause = ", ".join(f"{k}=?" for k in updated_fields.keys())
      sql = f"UPDATE novels SET {set_clause} WHERE id=?"
      params = list(updated_fields.values()) + [id]

      cur.execute(sql, params)
      conn.commit()
      conn.close()

      messages.append(f"✅ '{name}' updated:")
      messages.extend(change_log)

    except Exception as e:
      status = "error"
      messages.append(str(e))
  else:
    messages.append(f"No changes detected for '{name}'. Up to date.")

  return jsonify({
    "status": status,
    "message": "\n".join(messages)
  })

@app.route('/settings', methods=['GET', 'POST'])
def settings():
  if request.method == 'POST':
    # Save the form data
    for key, value in request.form.items():
      save_setting(key, value)  # your function to save to DB
  return redirect(url_for('index'))

@app.route("/scan-unrecorded")
def scan_unrecorded():
  db_epub_files, db_cover_files = get_db_files()
  folder_files = get_epub_files()
  cover_files = get_cover_files()

  unrecorded = sorted(folder_files - db_epub_files)
  unrecorded_covers = sorted(cover_files - db_cover_files)

  return jsonify({
    "total_unrecorded": len(unrecorded),
    "total_unrecorded_covers": len(unrecorded_covers),
    "files": unrecorded,
    "covers": unrecorded_covers
  })
  
@app.route('/status')
def status():
  return "", 200

if __name__ == '__main__':
  app.run(host="0.0.0.0", port=5000, debug=True)
