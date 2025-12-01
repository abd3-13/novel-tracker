import random, requests, re, time, threading, tldextract, zlib
from db import get_db_conn, get_value 
from datetime import datetime
from ebooklib import epub
from pathlib import Path
from functools import wraps

# Create a lock
lock = threading.Lock()

def timer(func):
  @wraps(func)
  def wrapper(*args, **kwargs):
    start = time.perf_counter()
    result = func(*args, **kwargs)
    end = time.perf_counter()
    print(f"{func.__name__} took {end - start:.4f} seconds")
    return result
  return wrapper

def epub_count_chapters(toc):
  total = 0
  for item in toc:
    if isinstance(item, tuple):
      section, children = item
      total += epub_count_chapters(children)
    else:
      if 'volume' not in item.title.lower() and 'chapter' in item.title.lower():
        total += 1
  return total

def extract_epub_cover(epub_path=None, getfrom="local", meta=None):
  """
  Extracts the cover image from an EPUB file OR downloads it from Webnovel.

  Parameters:
    epub_path (str): Relative path under LOCAL_EPUB_DIR
    getfrom (str): "local" or "online"

  Returns:
    str: Saved cover filename, or empty string on failure
  """

  if epub_path is None:
    print("❌ ERROR: EPUB path is None.")
    return ""
  if meta is None:
    print("❌ ERROR: EPUB Metadata is None. Not passed")
    return ""
  try:
    # -----------------------------
    # Paths & metadata
    # -----------------------------
    full_path = str(Path(get_value("LOCAL_EPUB_DIR")) / epub_path)
    #meta = get_epub_metadata(epub_path)  # RETURNS DICT
    src = meta.get("source", "")
    url = meta.get("url", "")
    cover_id = meta.get("cover_id", "nocover.webp")

    # Prepare cover output directory
    cover_dir = Path(get_value("COVER_PATH"))
    cover_dir.mkdir(parents=True, exist_ok=True)

    cover_path = cover_dir / cover_id

    # If already exists, return it immediately
    if cover_path.exists():
      return str(cover_id)

    cover_data = None  # data that will be written

    # ========================================================
    # 1) FETCH COVER LOCALLY FROM EPUB
    # ========================================================
    if getfrom == "local":
      try:
        book = epub.read_epub(full_path)
      except Exception as e:
        raise

      cover_item = None

      # First: Try official EPUB "cover" (type 10)
      for item in book.get_items():
        if item.get_type() == 10:
          cover_item = item
          break

      # If not found, fallback: first image
      if cover_item is None:
        for item in book.get_items():
          if item.get_type() == 1:
            cover_item = item
            break

      if cover_item is None:
        print("⚠️ No image found in EPUB.")
        raise

      cover_data = cover_item.get_content()

    # ========================================================
    # 2) FETCH COVER ONLINE (WEBNOVEL ONLY)
    # ========================================================
    else:
      print("🌐 ONLINE COVER REQUEST...")

      # Only Webnovel has predictable image URL
      if src == "webnovel":
        book_id = extract_book_id(url)
        if not book_id:
          return extract_epub_cover(epub_path, "local", meta)

        img_url = f"{get_value('IMG_ENDPOINT')}{book_id}/180.jpg"
        print(f"➡️ Downloading Webnovel image: {img_url}")

        try:
          response = requests.get(img_url, timeout=int(get_value("API_TIMEOUT")))
          if response.ok:
            cover_data = response.content
          else:
            return extract_epub_cover(epub_path, "local", meta)

        except Exception as e:
          return extract_epub_cover(epub_path, "local", meta)

      else:
        # No online source → fallback
        return extract_epub_cover(epub_path, "local", meta)

    # ========================================================
    # 3) WRITE FILE
    # ========================================================
    if cover_data:
      with open(cover_path, "wb") as f:
        f.write(cover_data)
      return str(cover_id)

    print("⚠️ No cover_data found, returning empty.")
    return ""

  except Exception as e:
    print(f"❌ extract_epub_cover error: {e}")
    return ""

def extract_local_chap(epub_path=None):
  """
  Extracts the number of chapters from the table of contents of an EPUB file.
  
  Parameters:
  epub_path (str): The path to the EPUB file location.

  Returns:
  int: Number of chapters in the table of contents, or 0 if the path is invalid or there are no chapters.
  """

  if epub_path is None:
    print("Error: EPUB path is None.")
    return 0

  try:
    epub_path = str(Path(get_value("LOCAL_EPUB_DIR")) / epub_path)
    # Read the EPUB file
    book = epub.read_epub(epub_path)

    
    # Check the length of the table of contents
    toc_len = epub_count_chapters(book.toc)

    if toc_len > 0:  # check for positive length and an int
      return toc_len
    else:
      print("No chapters found in the table of contents.")
      return 0

  except Exception as e:
    print(f"error in processing the EPUB: {e}")
    with open("epub_error.txt", "a", encoding="utf-8") as f:
      f.write(f"{epub_path}\n")
    return None

def get_epub_metadata(epub_path):
  """
  Extract metadata from a local EPUB file.
  Returns a dictionary with keys:
  url, source, author, description, cover_id, title
  """
  data = {
    "url": "",
    "source": "",
    "author": "",
    "description": "",
    "cover_id": "",
    "title": ""
  }

  try:
    full_path = str(Path(get_value("LOCAL_EPUB_DIR")) / epub_path)
    book = epub.read_epub(full_path)

    url_list = book.get_metadata('DC', 'source')
    author_list = book.get_metadata('DC', 'creator')
    desc_list = book.get_metadata('DC', 'description')
    title_list = book.get_metadata('DC', 'title')

    if url_list: data["url"] = url_list[0][0].strip()
    if author_list: data["author"] = author_list[0][0].strip()
    if desc_list: data["description"] = desc_list[0][0].strip()
    if title_list: data["title"] = title_list[0][0].strip()

    if data["url"]:
      data["source"] = tldextract.extract(data["url"]).domain
      if data["source"] == "webnovel":
        cover_filename = f"{extract_book_id(data['url'])}.webp" 
      else:
        # fallback: safe filename from title 
        safe_title = zlib.crc32(data["title"].encode("utf-8"))
        cover_filename = f"{safe_title}.webp"
      
    data["cover_id"] = str(cover_filename)

  except Exception as e:
    print(f"⚠️ Failed to read EPUB metadata: {e}")
    raise

  return data

def extract_book_id(url):
  """
  Extracts the Webnovel book ID from a given URL.

  Parameters:
  url (str): The URL string from which to extract the book ID.

  Returns:
  str: The extracted book ID if found, or None if not found.
  """
  # Define patterns to search for book ID
  patterns = [
    r'_(\d{8,})$',  # Match book IDs after an underscore at the end
    r'/book/(\d{8,})',  # Match book IDs in '/book/' path
    r'(\d{8,})'  # Match any sequence of digits of length 8 or more
  ]

  for pattern in patterns:
    match = re.search(pattern, url)
    if match:
      return match.group(1)

  return None

def fetch_latest_chapter_webnovel(book_id):
  """
  Fetches the latest chapter number and last chapter time from the Webnovel mobile API.

  Parameters:
  book_id (str): The ID of the book to fetch data for.

  Returns:
  tuple: (chapter_num, last_chapter_time, author, description, image_url)
  All fields may be None if an error occurs.
  """
  if book_id is None:
    return None, None, None, None
  endpoint = f'{get_value("ENDPOINT")}{book_id}'
  headers = {
    "User-Agent": f"{get_value("USER_AGENT")}",
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://android.webnovel.com",
  }

  try:
    # polite delay to avoid hammering server
    # Random delay between 1 and 3 seconds, make random to avoid being flagged 
    # Delay only after actual processing
    time.sleep(random.uniform(float(get_value("DELAY_FROM")), float(get_value("DELAY_TO"))))
    
    resp = requests.get(endpoint, headers=headers, timeout=int(get_value("API_TIMEOUT")))
    resp.raise_for_status()  # Raise an error for HTTP error responses

    # Extract relevant data from the response JSON
    # Extracting ChapterNum and LastChapterTime
    json_data = resp.json()
    data = json_data.get("Data", {})
    
    chapter_num = data.get("ChapterNum")
    last_chapter_time = data.get("LastChapterTime")
    book_desc = data.get("Description") or ""
    book_author = data.get("AuthorInfo", {}).get("AuthorName") or "Unknown"

    # Convert epoch time to formatted string
    if last_chapter_time is not None:
      last_chapter_time = datetime.fromtimestamp(last_chapter_time / 1000).strftime('%Y-%m-%d %H:%M:%S.%f')
    else:
      last_chapter_time = None

    return chapter_num, last_chapter_time, book_author, book_desc
  
  except Exception as e:
    print(f"fetch_latest_chapter_webnovel error: {e}")
    raise
    return None, None, None, None

@timer
def update_online_chapters_for_all(onlinechap=0, localchap=0, startId=1, limit=None, gettitle=0, geturl=0, get_audecco=0, cover=0, check_epub=0):

  with lock:  # Only one thread will execute this block at a time
    upall_err_cnt = 0
    check_epub_err_cnt = 0
    messages = []
    status = "success"
    flags = [onlinechap, localchap, gettitle, geturl, get_audecco, cover, check_epub]

    if all(f == 0 for f in flags):
      return "Chapters are not selected", "error"
    query = "SELECT id, name, url, onlinechap, localchap, filepath, author, description, cover_path FROM novels"
    params = []
    
    if startId > 1:
      query += " WHERE id >= ?"
      params.append(startId)
    
    if limit is not None and limit >= 1:
      query += " LIMIT ?"
      params.append(limit)

    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute(query, params)
    books = cursor.fetchall()

    print(f">> Updating {len(books)} novels from id {startId}, Limited to {limit}")

    for book_id, name, url, db_online_chap, db_local_chap, epub_loc, db_author, db_desc, db_coverpath in books:
      try:
        set_parts = []
        values = []

        if any([gettitle == 1, geturl == 1, get_audecco == 1, cover == 1, onlinechap == 1]): 
          # Load metadata (returns url, source, author, description, cover_id, title)
          meta = get_epub_metadata(epub_loc)

        # ========= ONLINE =========
        if onlinechap == 1 and url and "webnovel.com" in url:
          ext_id = extract_book_id(url)

          if not ext_id:
            messages.append(f"⚠️ Could not extract bookId for {name}")
            continue

          latest_chap, latest_chap_time, author, desc = fetch_latest_chapter_webnovel(ext_id)
          imgurl = extract_epub_cover(epub_loc, "online", meta)

          if latest_chap is None:
            continue

          if db_online_chap is None or latest_chap > db_online_chap:
            set_parts.append("onlinechap = ?")
            values.append(latest_chap)

          if latest_chap_time:
            set_parts.append("latestchaptime = ?")
            values.append(latest_chap_time)
            
          if author:
            set_parts.append("author = ?")
            values.append(author)
            
          if desc:
            set_parts.append("description = ?")
            values.append(desc)
            
          if imgurl:
            set_parts.append("cover_path = ?")
            values.append(imgurl)
        elif onlinechap == 1 and "webnovel.com" not in url:
          extract_epub_cover(epub_loc, "local", meta)
          set_parts.append("author = ?, description = ?, cover_path = ?")
          values.append(meta.get("author") or "")
          values.append(meta.get("description") or "")
          values.append(meta.get("cover_id") or "")

        # ========= LOCAL =========
        if localchap == 1 and epub_loc:
          extracted_local = extract_local_chap(epub_loc)

          if extracted_local > 0 and extracted_local > db_local_chap:
            set_parts.append("localchap = ?")
            values.append(extracted_local)

          print(f"{name}: extracted {extracted_local}, in DB {db_local_chap}")
        
        # ========= TITLE ==========
        if gettitle == 1 and epub_loc:
          epub_title = meta.get("title")
          if epub_title:
            set_parts.append("name = ?")
            values.append(epub_title)

        # ========= URL ==========
        if geturl == 1 and epub_loc:
          epub_url = meta.get("url")
          if epub_url:
            set_parts.append("url = ?")
            values.append(epub_url)

        # ========= Cover File  =========
        if cover == 1 and onlinechap == 0 and epub_loc:
          extract_epub_cover(epub_loc, "local", meta)

        # ==== Author, Desc, cover =======
        if get_audecco == 1 and epub_loc:
          set_parts.append("author = ?, description = ?, cover_path = ?")
          values.append(meta.get("author") or "")
          values.append(meta.get("description") or "")
          values.append(meta.get("cover_id") or "")
        # ========= CHECK EXIST ==========
        if check_epub == 1:
          epubpath = Path(get_value('LOCAL_EPUB_DIR')) / epub_loc
          set_parts.append("epub_exists = ?")
          if epubpath.exists():
            values.append("1")
          else:
            values.append("0")
            check_epub_err_cnt += 1

        # ========= EXECUTE =========
        if set_parts:
          values.append(book_id)
          cursor.execute(f"UPDATE novels SET {', '.join(set_parts)} WHERE id = ?", values)
        

      except Exception as e:
        messages.append(f"⚠️ Error processing {name}: {e}")
        upall_err_cnt += 1
        continue

    if onlinechap == 1: conn.execute("UPDATE settings SET value=? where key='LAST_BULK_TIME'", (datetime.now(), ))
    conn.commit()
    conn.close()
    
   
    if upall_err_cnt > 0:
      messages.append(f"{upall_err_cnt} update errors")
      status = "error"
    
    if check_epub_err_cnt > 0:
      messages.append(f"{check_epub_err_cnt} epub files missing")
      status = "error"
    
    if not messages:
      return "✅ Done Bulk updating Novels", "success"
    
    return "\n".join(messages), status
