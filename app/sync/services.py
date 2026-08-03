import logging
import re
import zlib
from dataclasses import dataclass
from pathlib import Path

import tldextract
from ebooklib import epub

from app.utils import db

logger = logging.getLogger(__name__)

# ebooklib item type constants (avoiding the ebooklib.epub export names since
# they've moved between versions; these ints are stable across the lib).
_ITEM_TYPE_COVER = 10
_ITEM_TYPE_IMAGE = 1

# Tried in order, most specific first. The last pattern is a bare "8+ digits
# anywhere" catch-all, so it only gets a chance if the URL doesn't match the
# more precise "_<id>" suffix or "/book/<id>" path shapes.
BOOK_ID_PATTERNS = (
    re.compile(r"_(\d{8,})$"),
    re.compile(r"/book/(\d{8,})"),
    re.compile(r"(\d{8,})"),
)


def extract_book_id(url: str | None = None) -> str | None:
    """Extract a numeric book id (8+ digits) from a URL, trying patterns in priority order."""
    if not url:
        return None
    for pattern in BOOK_ID_PATTERNS:
        m = pattern.search(url)
        if m:
            return m.group(1)
    return None


def _epub_dir() -> Path:
    return Path(db.get_value("LOCAL_EPUB_DIR") or "./")


def _resolve_epub_path(filename: str) -> Path:
    path = _epub_dir() / filename
    if not path.is_file():
        raise FileNotFoundError(f"EPUB file not found: {path}")
    return path


def _read_epub(filename: str):
    """
    Resolve path and parse the EPUB in one step, with a consistent error type.

    Single choke point for opening a book. Every public function below calls
    this exactly once per invocation -- callers that need chapters, metadata,
    AND a cover (e.g. enrich_from_epubfile) parse the file once and reuse the
    resulting `book` object, instead of each concern re-reading the EPUB.
    """
    full_path = _resolve_epub_path(filename)
    try:
        return epub.read_epub(str(full_path))
    except Exception as e:
        raise ValueError(f"Failed to read EPUB '{filename}': {e}") from e


def _count_chapters(toc) -> int:
    """
    Recursively count TOC entries whose title contains 'chapter' but not 'volume'.

    ebooklib's `book.toc` is a nested structure: each entry is either a
    Link/Section leaf, or a (Section, [children]) tuple for a subsection.
    We recurse into tuples and only count leaves. This is a substring match
    on the title text (not a structural "is this a chapter node" check), so
    it's only as reliable as the source EPUB's TOC labeling.
    """
    total = 0
    for item in toc:
        if isinstance(item, tuple):
            _, children = item
            total += _count_chapters(children)
        else:
            title = item.title.lower()
            if "chapter" in title and "volume" not in title:
                total += 1
    return total


def _last_chapter(toc_item):
    """
    Descend into nested TOC lists/tuples to find the final (title, href) leaf.

    Always follows the LAST entry at each level, so this assumes the TOC is
    in reading order and the last leaf under the last branch is truly the
    most recent chapter -- not guaranteed if a book's TOC has trailing
    non-chapter sections (afterword, glossary, etc.) ordered after the story.
    """
    if isinstance(toc_item, (list, tuple)):
        if not toc_item:
            raise ValueError("Empty TOC section, cannot resolve last chapter.")
        return _last_chapter(toc_item[-1])
    return toc_item.title, toc_item.href


def _extract_cover_bytes(book) -> bytes | None:
    """
    Prefer the EPUB's officially declared cover item; fall back to the first
    image in the manifest if the book doesn't declare one properly (common
    in scraped/converted EPUBs).
    """
    cover_item = next(
        (i for i in book.get_items() if i.get_type() == _ITEM_TYPE_COVER), None
    )
    if cover_item is None:
        cover_item = next(
            (i for i in book.get_items() if i.get_type() == _ITEM_TYPE_IMAGE), None
        )
    return cover_item.get_content() if cover_item else None


@dataclass
class EpubMetadata:
    url: str = ""
    source: str = ""
    author: str = ""
    description: str = ""
    cover_id: str = ""
    title: str = ""
    identifiers: str = ""
    chapters: int = 0
    last_title: str = ""
    last_file: str = ""
    characters: int = 0


def _metadata_from_book(book) -> EpubMetadata:
    """Build EpubMetadata from an already-loaded ebooklib Book object (no re-read)."""

    def first(ns: str, key: str) -> str:
        vals = book.get_metadata(ns, key)
        return vals[0][0].strip() if vals else ""

    chap, last_title, last_file = extract_local_chap(book)

    meta = EpubMetadata(
        url=first("DC", "source"),
        author=first("DC", "creator"),
        description=first("DC", "description"),
        title=first("DC", "title"),
        identifiers=first("DC", "identifier"),
        chapters=chap,
        last_file=last_title,
        last_title=last_file,
        characters=count_local_characters(book),
    )

    if meta.url:
        ext = tldextract.extract(meta.url)
        source = ext.domain
        cover_filename = ""

        # webnovel.com URLs embed a stable numeric book id -- use it directly
        # as the cover filename so re-imports of the same book overwrite
        # (rather than duplicate) the cached cover.
        if source == "webnovel":
            book_id = extract_book_id(meta.url)
            if book_id:
                cover_filename = f"{book_id}.webp"
        # Hosted blog platforms: the domain is just "blogspot"/"wordpress" for
        # every book, so use the subdomain (the actual site name) as source.
        elif source in ("blogspot", "wordpress", "law"):
            source = ext.subdomain

        # No stable id available (unknown source, or webnovel URL didn't
        # match) -- derive a deterministic filename from the title so the
        # same book always maps to the same cover file.
        if not cover_filename:
            safe_title = zlib.crc32(meta.title.encode("utf-8"))
            cover_filename = f"{safe_title}.webp"

        meta.source = source
        meta.cover_id = cover_filename

    return meta


def get_epub_metadata(epub_path: str) -> EpubMetadata:
    """Read an EPUB file from disk and extract its metadata."""
    book = _read_epub(epub_path)
    return _metadata_from_book(book)


def extract_epub_cover(epub_path: str, meta: EpubMetadata | None = None) -> str:
    """
    Extract and save the cover image from a local EPUB file.
    If `meta` is provided (e.g. already fetched by the caller), it's reused
    instead of re-parsing the EPUB for metadata.
    Returns the saved cover filename, or "" if no image was found.
    """
    book = _read_epub(epub_path)

    if meta is None:
        meta = _metadata_from_book(book)

    cover_id = meta.cover_id or "nocover.webp"
    cover_dir = Path(db.get_value("COVER_PATH") or "./covers")
    cover_dir.mkdir(parents=True, exist_ok=True)
    cover_path = cover_dir / cover_id

    # cover_id is deterministic per book (see _metadata_from_book), so if the
    # file's already on disk we can skip re-extracting/re-writing it.
    if cover_path.exists():
        return cover_id

    cover_data = _extract_cover_bytes(book)
    if not cover_data:
        logger.warning("No cover image found in EPUB: %s", epub_path)
        return ""

    cover_path.write_bytes(cover_data)
    return cover_id


def extract_local_chap(book):
    """Read chapter count and last-chapter info from an EPUB's table of contents."""

    count = _count_chapters(book.toc)
    if count <= 0:
        raise ValueError("No chapters found in TOC")

    last_title, last_file = _last_chapter(book.toc)
    return count, last_title, last_file


def count_local_characters(book) -> int:
    """Count items in the EPUB whose filename ends with '_chr.jpg' (character images)."""
    return sum(1 for i in book.get_items() if i.get_name().lower().endswith("_chr.jpg"))


def import_epub_service(filename: str) -> dict:
    """Process an EPUB file into a novel dict ready for DB insertion."""
    novel = db.build_base_novel()
    meta = get_epub_metadata(filename)
    novel.update(
        {
            "filepath": filename,
            "name": meta.title or "Unknown Title",
            "url": meta.url,
            "source": meta.source or "local",
            "author": meta.author,
            "description": meta.description,
            "cover_path": meta.cover_id,
            "localchap": meta.chapters,
            "local_lastchaptitle": meta.last_title,
            "local_lastchapfile": meta.last_file,
            "characters": meta.characters,
        }
    )

    # TODO: add online metadata fetch if "sync from" setting is "online"
    # book_id = meta.cover_id.suffix(".webp")
    # if book_id and db.get_value("UPDATE_LOCAL_ONLINE") == "online":
    #    logger.info("Online enrichment requested for book_id=%s (not yet implemented)", book_id)

    return novel


def find_missing_epubs() -> list:
    """
    Return novels whose on-disk EPUB file is missing.

    Scales as: 1 directory walk (O(files on disk)) + N in-memory set lookups
    (O(rows)), instead of N separate stat() syscalls. Worth it once the
    library is large enough that N individual filesystem round-trips cost
    more than one walk -- which is true for any non-trivial catalog.

    Assumes `filepath` in the DB is stored relative to LOCAL_EPUB_DIR with
    forward-slash separators (matches how the rest of this module writes
    paths). If that ever changes, the set comparison below needs to change
    with it.
    """
    epub_dir = _epub_dir()
    on_disk = {
        p.relative_to(epub_dir).as_posix() for p in epub_dir.rglob("*") if p.is_file()
    }

    missing = []
    rows, _, conn = db.fetch_all("SELECT id, name, filepath from novels", [])
    try:
        for book_id, name, path in rows:
            if path not in on_disk:
                missing.append(
                    {"id": book_id, "name": name, "path": str(epub_dir / path)}
                )
    finally:
        conn.close()
    return missing
