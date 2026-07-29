import re
import zlib
from pathlib import Path

import tldextract  # type: ignore # noqa: E401
from ebooklib import epub
from flask import current_app

import app.utils.db as db

BOOK_ID_PATTERNS = (
    re.compile(r"_(\d{8,})$"),
    re.compile(r"/book/(\d{8,})"),
    re.compile(r"(\d{8,})"),
)


def extract_book_id(url=None):
    if url:
        for pattern in BOOK_ID_PATTERNS:
            m = pattern.search(url)
            if m:
                return m.group(1)
    return None


def epub_count_chapters(toc):
    total = 0
    for item in toc:
        if isinstance(item, tuple):
            section, children = item
            total += epub_count_chapters(children)
        else:
            if "volume" not in item.title.lower() and "chapter" in item.title.lower():
                total += 1
    return int(total)


def get_last_chapter_title(toc_item):
    if isinstance(toc_item, (list, tuple)):
        return get_last_chapter_title(toc_item[-1])
    return toc_item.title, toc_item.href


def extract_epub_cover(epub_path=None, getfrom="local", meta=None):
    """
    Extracts the cover image from an EPUB file local only.

    Parameters:
      epub_path (str): Relative path under LOCAL_EPUB_DIR
      getfrom (str): "local" or "online"

    Returns:
      str: Saved cover filename, or empty string on failure
    """

    if epub_path is None:
        raise ValueError("❌ ERROR extract_epub_cover: EPUB path is None.")

    if meta is None:
        raise ValueError(
            "❌ ERROR extract_epub_cover: EPUB Metadata is None. Not passed"
        )

    if getfrom == "online":
        raise ValueError("❌ ERROR extract_epub_cover: function is only for local")

    try:
        # -----------------------------
        # Paths & metadata
        # -----------------------------
        full_path = str(Path(db.get_value("LOCAL_EPUB_DIR") or "./") / epub_path)
        meta = get_epub_metadata(epub_path)  # RETURNS DICT
        cover_id = meta.get("cover_id", "nocover.webp")

        # Prepare cover output directory
        cover_dir = Path(db.get_value("COVER_PATH") or "./covers")
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
                current_app.logger.error(f"Error in reading epub: {str(e)}")
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
                raise ValueError("⚠️ No image found in EPUB.")

            cover_data = cover_item.get_content()

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
        raise ValueError(f"❌ extract_epub_cover error: {e}")


def extract_local_chap(epub_path=None):
    """
    Extracts the number of chapters from the table of contents of an EPUB file.

    Parameters:
    epub_path (str): The path to the EPUB file location.

    Returns:
    int: Number of chapters in the table of contents, or 0 if the path is invalid or there are no chapters.
    str: title of the last chapter
    str: file name of the last chapter
    """

    if epub_path is None:
        raise ValueError("Error: EPUB path is None.")

    try:
        epub_path = Path(db.get_value("LOCAL_EPUB_DIR") or "./") / epub_path
        if not epub_path.is_file():
            raise ValueError("Error: EPUB file doesn't exits.")

        # Read the EPUB file
        book = epub.read_epub(epub_path)
        if book is None:
            raise ValueError("Error: EPUB read is None.")

        # Check the length of the table of contents
        toc_len = epub_count_chapters(book.toc)

        # Get the title for the last chap
        last_chap_ti, last_chap_file = get_last_chapter_title(book.toc)

        if toc_len > 0:  # check for positive length and an int
            return toc_len, last_chap_ti, last_chap_file
        else:
            raise ValueError("No chapters found in the table of contents.")

    except Exception as e:
        with open("epub_error.txt", "a", encoding="utf-8") as f:
            f.write(f"{epub_path} : {e}\n")
        return None, None, None


def count_local_characters(epub_file=None):
    if epub_file is None:
        raise ValueError("Error: EPUB path is None.")

    try:
        epub_file = Path(db.get_value("LOCAL_EPUB_DIR") or "./") / epub_file
        if not epub_file.is_file():
            raise ValueError("Error: EPUB file doesn't exits.")
        count = 0
        # Read the EPUB file
        book = epub.read_epub(epub_file)
        if book is None:
            raise ValueError("Error: EPUB read is None.")

        for i in book.get_items():
            if i.get_name().lower().endswith("_chr.jpg"):
                count += 1
        current_app.logger.info(f" >> Counting Charaters: {count}")

    except Exception as e:
        with open("epub_error.txt", "a", encoding="utf-8") as f:
            f.write(f"count_local_characters: {epub_file} : {e}\n")
        return None
    return count


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
        "title": "",
        "identifiers": "",
    }

    try:
        full_path = str(Path(db.get_value("LOCAL_EPUB_DIR") or "./") / epub_path)
        book = epub.read_epub(full_path)

        url_list = book.get_metadata("DC", "source")
        author_list = book.get_metadata("DC", "creator")
        desc_list = book.get_metadata("DC", "description")
        title_list = book.get_metadata("DC", "title")
        identifiers = book.get_metadata("DC", "identifier")
        cover_filename = ""

        if url_list:
            data["url"] = url_list[0][0].strip()
        if author_list:
            data["author"] = author_list[0][0].strip()
        if desc_list:
            data["description"] = desc_list[0][0].strip()
        if title_list:
            data["title"] = title_list[0][0].strip()
        if identifiers:
            data["identifiers"] = identifiers[0][0].strip()

        if data["url"]:
            ext = tldextract.extract(data["url"])

            # Default source = domain
            source = ext.domain

            # WebNovel special handling
            if source == "webnovel":
                cover_filename = f"{extract_book_id(data['url'])}.webp"
            # Hosted platforms (blogspot.com, wordpress.com)
            elif source in ("blogspot", "wordpress", "law"):
                # Use subdomain as actual source/blog name
                source = ext.subdomain

                # fallback: safe filename from title
            if cover_filename == "":
                safe_title = zlib.crc32(data["title"].encode("utf-8"))
                cover_filename = f"{safe_title}.webp"

            data["source"] = source

        data["cover_id"] = str(cover_filename)

    except Exception as e:
        print(f"get_epub_metadata ERROR: {e}")
        raise ValueError(f"⚠️ Failed to read EPUB metadata: {e}")

    return data


def enrich_from_epubfile(novel, filename):
    local_chap, last_title, last_file = extract_local_chap(filename)
    if not local_chap:
        raise ValueError(f"Could not determine chapter count for {filename}")

    meta = get_epub_metadata(filename)

    novel.update(
        {
            "filepath": filename,
            "name": meta.get("title", "Unknown Title"),
            "url": meta.get("url", ""),
            "source": meta.get("source", "local"),
            "author": meta.get("author", ""),
            "description": meta.get("description", ""),
            "cover_path": meta.get("cover_id", ""),
            "localchap": local_chap,
            "local_lastchaptitle": last_title,
            "local_lastchapfile": last_file,
        }
    )


def import_epub_service(filename):
    """
    accept filename and process it for import to db

    Parameters:
    filename (str): filename of the said epub file

    Returns:
    dict: returns novel data
    """
    #  if db.get_db_file(filename):
    #    raise ValueError("EPUB: {filename} is already in DB")
    novel = db.build_base_novel()
    enrich_from_epubfile(novel, filename)
    book_id = extract_book_id(novel.get("url", ""))
    if book_id and db.get_value("UPDATE_LOCAL_ONLINE") == "online":
        # enrich_from_web(novel, book_id)
        print("Online provider clalled, enrich_from_web")
    return novel


def find_missing_epubs():
    missing = []

    rows, _, conn = db.fetch_all("SELECT id, name, filepath from novels", [])
    try:
        for book_id, name, path in rows:
            full_path = Path(db.get_value("LOCAL_EPUB_DIR") or "./") / path

            if not full_path.exists():
                missing.append({"id": book_id, "name": name, "path": str(full_path)})
    finally:
        conn.close()

    return missing
