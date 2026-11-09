import logging
import os
import re
import xml.etree.ElementTree as ET
import zlib
from dataclasses import dataclass
from pathlib import Path

import tldextract
from ebooklib import epub

from app.constants import (
    AssetExtension,
    DefaultValue,
    MetadataKey,
    MetadataNamespace,
    Provider,
    SettingKey,
    SourceDomain,
    TocKeyword,
)
from app.utils import db
from app.utils.images import convert_to_webp, get_image_format
from app.utils.tools import normalize_filename

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

MOON_READER_PROGRESS_PATTERN = re.compile(r"(\d+)@.*?:([\d.]+)%")


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
    return Path(db.get_value(SettingKey.LOCAL_EPUB_DIR) or DefaultValue.CURRENT_DIR)


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
            if TocKeyword.CHAPTER in title and TocKeyword.VOLUME not in title:
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


def _cover_item(book):
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
    return cover_item


def _extract_cover_bytes(book) -> bytes | None:
    cover_item = _cover_item(book)
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


def _metadata_from_book(book, strict: bool = True) -> EpubMetadata:
    """Build EpubMetadata from an already-loaded ebooklib Book object (no re-read)."""

    def first(ns: str, key: str) -> str:
        vals = book.get_metadata(ns, key)
        return vals[0][0].strip() if vals else ""

    try:
        chap, last_title, last_file = extract_local_chap(book)
    except ValueError:
        if strict:
            raise
        chap, last_title, last_file = 0, "", ""

    meta = EpubMetadata(
        url=first(MetadataNamespace.DC, "source"),
        author=first(MetadataNamespace.DC, "creator"),
        description=first(MetadataNamespace.DC, "description"),
        title=first(MetadataNamespace.DC, "title"),
        identifiers=first(MetadataNamespace.DC, "identifier"),
        chapters=chap,
        last_file=last_file,
        last_title=last_title,
        characters=count_local_characters(book),
    )

    if meta.url:
        ext = tldextract.extract(meta.url)
        source = ext.domain
        cover_filename = ""

        # webnovel.com URLs embed a stable numeric book id -- use it directly
        # as the cover filename so re-imports of the same book overwrite
        # (rather than duplicate) the cached cover.
        if source == SourceDomain.WEBNOVEL:
            book_id = extract_book_id(meta.url)
            if book_id:
                cover_filename = f"{book_id}.webp"
        # Hosted blog platforms: the domain is just "blogspot"/"wordpress" for
        # every book, so use the subdomain (the actual site name) as source.
        elif source in (
            SourceDomain.BLOGSPOT,
            SourceDomain.WORDPRESS,
            SourceDomain.LAW,
        ):
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


def get_epub_metadata(epub_path: str, strict: bool = True) -> EpubMetadata:
    """Read an EPUB file from disk and extract its metadata."""
    book = _read_epub(epub_path)
    return _metadata_from_book(book, strict=strict)


def get_epub_cover_bytes(filename: str) -> tuple[bytes, str] | None:
    """
    Return the cover image bytes and media type for an EPUB in the configured
    EPUB directory, without writing anything to disk.
    """
    book = _read_epub(filename)
    cover_item = _cover_item(book)

    if cover_item is None:
        return None

    media_type = getattr(cover_item, "media_type", "") or "image/jpeg"

    return cover_item.get_content(), media_type


def extract_epub_cover(
    epub_path: str, cover_id: str | None = None, overwrite: bool = False
) -> str:
    """
    Extract the cover image from a local EPUB file,
    convert it to WebP when necessary, and save it.
    """

    logger.debug("Opening EPUB: %s", epub_path)

    book = _read_epub(epub_path)

    if cover_id is None:
        logger.debug("Reading EPUB metadata...")
        meta = _metadata_from_book(book)
        cover_id = meta.cover_id

    cover_id = cover_id or DefaultValue.NO_COVER

    # Metadata cover ids already carry a ".webp" suffix; keep the final
    # filename single-suffixed regardless of how the id was supplied.
    if cover_id.lower().endswith(".webp"):
        cover_id = cover_id[:-5]

    cover_dir = Path(
        db.get_value(SettingKey.COVER_PATH) or DefaultValue.CURRENT_COVER_DIR
    )
    cover_dir.mkdir(parents=True, exist_ok=True)

    # Final output is always WebP.
    cover_path = cover_dir / f"{cover_id}.webp"

    if cover_path.exists() and not overwrite:
        logger.debug("Cover already exists and overwite is False: %s", cover_path)
        return cover_path.name

    logger.debug("Extracting cover image...")
    cover_data = _extract_cover_bytes(book)

    if not cover_data:
        logger.warning("No cover image found in EPUB: %s", epub_path)
        return ""

    # Write extracted bytes to a temporary file.
    temp_path = cover_dir / f".{cover_id}.{AssetExtension.COVER}"

    try:
        temp_path.write_bytes(cover_data)

        # Determine the actual image format from its contents.
        image_format = get_image_format(temp_path)

        logger.debug("Extracted cover format: %s", image_format)

        # ---------------------------------------------------------
        # Already WebP
        # ---------------------------------------------------------
        if image_format == AssetExtension.WEBP:
            if cover_path.exists():
                if not overwrite:
                    temp_path.unlink(missing_ok=True)
                    return cover_path.name
                cover_path.unlink()

            temp_path.rename(cover_path)
            logger.info("Saved WebP cover: %s", cover_path)
            return cover_path.name

        # ---------------------------------------------------------
        # Convert non-WebP image
        # ---------------------------------------------------------
        converted_path = convert_to_webp(
            temp_path, quality=85, delete_original=True, overwrite=overwrite
        )

        if not converted_path:
            logger.error("Failed to convert cover to WebP: %s", epub_path)
            return ""

        # convert_to_webp keeps the temporary dot-prefixed name. Move the
        # converted image to the final cover path expected by the database.
        if converted_path != cover_path:
            cover_path.unlink(missing_ok=True)
            converted_path.rename(cover_path)

        logger.info("Converted and saved cover: %s", cover_path)
        return cover_path.name

    except Exception as exc:  # noqa: BLE001
        logger.error("Cover extraction failed: %s", exc)
        temp_path.unlink(missing_ok=True)
        return ""


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


def build_novel_from_metadata(
    meta: EpubMetadata,
    filename: str,
    title: str | None = None,
    cover: str | None = None,
) -> dict:
    """Build a novel dict ready for DB insertion from extracted EPUB metadata."""
    novel = db.build_base_novel()
    novel.update(
        {
            MetadataKey.FILEPATH: filename,
            MetadataKey.TITLE: title or meta.title or DefaultValue.UNKNOWN_TITLE,
            MetadataKey.URL: meta.url or None,
            MetadataKey.SOURCE: meta.source or Provider.LOCAL,
            MetadataKey.AUTHOR: meta.author or None,
            MetadataKey.DESCRIPTION: meta.description or None,
            MetadataKey.COVER: (cover if cover is not None else meta.cover_id) or None,
            MetadataKey.LOCAL_CHAPTERS: meta.chapters,
            MetadataKey.LOCAL_LAST_TITLE: meta.last_title or None,
            MetadataKey.LOCAL_LAST_FILE: meta.last_file or None,
            MetadataKey.CHARACTERS: meta.characters,
            MetadataKey.ONLINE_CHAPTERS: 0,
            MetadataKey.ONLINE_CHARACTERS: 0,
            MetadataKey.PROGRESS: 0,
            MetadataKey.EPUB_EXISTS: True,
            "notes": "",
            "tags": "",
        }
    )
    return novel


def import_epub_service(filename: str) -> dict:
    """Process an EPUB file into a novel dict ready for DB insertion."""
    meta = get_epub_metadata(filename, strict=False)
    return build_novel_from_metadata(meta, filename)


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


# =============================================================================
# Moon+ Reader Progress
# =============================================================================


@dataclass(slots=True)
class ReadingProgress:
    """
    Reading progress for a single EPUB.
    """

    chapter: int | None = None


_progress_cache: dict[str, ReadingProgress] | None = None
_progress_source: str | None = None
_progress_mtime: int | None = None


def _load_progress(xml_path: str | None) -> dict[str, ReadingProgress]:
    """
    Load and cache the Moon+ Reader progress database.
    """

    global _progress_cache
    global _progress_source
    global _progress_mtime

    xml_file = Path(xml_path) if xml_path else None

    if xml_file is None:
        logger.warning("Moon+ Reader XML path not configured.")
        _progress_cache = {}
        _progress_source = xml_path
        _progress_mtime = None
        return _progress_cache

    if not xml_file.exists():
        logger.warning("Moon+ Reader XML not found: %s", xml_file)
        _progress_cache = {}
        _progress_source = xml_path
        _progress_mtime = None
        return _progress_cache

    mtime = xml_file.stat().st_mtime_ns

    if (
        _progress_cache is not None
        and _progress_source == xml_path
        and _progress_mtime == mtime
    ):
        logger.debug("Using cached Moon+ Reader progress.")
        return _progress_cache

    logger.info("Loading Moon+ Reader progress...")

    progress: dict[str, ReadingProgress] = {}

    tree = ET.parse(xml_file)
    root = tree.getroot()

    for node in root.findall("string"):
        full_path = node.attrib.get("name", "")

        value = (node.text or "").strip()

        filename = normalize_filename(os.path.basename(full_path))

        match = MOON_READER_PROGRESS_PATTERN.match(value)

        if not match:
            continue

        progress[filename] = ReadingProgress(chapter=int(match.group(1)))

    logger.info("Loaded Moon+ Reader progress for %d books.", len(progress))

    _progress_cache = progress
    _progress_source = xml_path
    _progress_mtime = mtime

    return progress


def get_moonreader_progress(
    epub_filename: str,
    xml_path: str | None = None,
) -> ReadingProgress:
    """
    Return the reading progress for a single EPUB.

    Progress is cached after the first XML parse.
    """

    if xml_path is None:
        xml_path = db.get_value(SettingKey.MOON_PROGRESS_FILE) or ""

    filename = normalize_filename(epub_filename)

    progress = _load_progress(xml_path)
    print(
        f"Moon+ Reader Progress cache: {len(progress)} entries loaded from {xml_path}"
    )
    print(f"Full progress cache: {progress}")
    print(f"Looking up progress for filename: {filename}")

    result = progress.get(filename)

    if result is None:
        logger.debug("No Moon+ Reader progress found for '%s'.", filename)
        return ReadingProgress()

    logger.debug("Moon+ Reader progress: %s -> chapter %d", filename, result.chapter)

    return result
