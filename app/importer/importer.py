"""
Import local EPUB files into the novel database.

Only files from the configured LOCAL_EPUB_DIR are importable. The importer
re-validates every filename and re-reads metadata from disk instead of
trusting the scan response.
"""

import os
import zlib
from pathlib import Path

from app.constants import DefaultValue, SettingKey
from app.sync.services import (
    build_novel_from_metadata,
    extract_epub_cover,
    get_epub_metadata,
)
from app.utils import db


def _epub_dir() -> Path:
    return Path(db.get_value(SettingKey.LOCAL_EPUB_DIR) or DefaultValue.CURRENT_DIR)


def _known_files(table: str) -> set[str]:
    epub_files, _ = db.get_db_filesNcover(table)
    return {os.path.basename(path).casefold() for path in epub_files if path}


def _resolve_file(filename: str) -> Path:
    """Validate a filename and return its path inside the EPUB directory."""
    name = Path(filename).name

    if not name or name != filename:
        raise ValueError("Invalid EPUB filename.")

    path = _epub_dir() / name

    if path.suffix.lower() != ".epub" or not path.is_file():
        raise FileNotFoundError(f"EPUB file not found: {name}")

    return path


def _cover_filename(meta, title: str) -> str:
    """Use the metadata cover id, or derive a stable one from the title."""
    if meta.cover_id:
        return meta.cover_id

    return f"{zlib.crc32(title.encode('utf-8'))}.webp"


def _result(filename: str, status: str, reason: str = "") -> dict:
    result = {"filename": filename, "status": status}

    if reason:
        result["reason"] = reason

    return result


def import_files(filenames: list[str], table: str) -> dict:
    """
    Import the selected EPUB filenames.

    Each file succeeds or fails independently. Files already recorded in the
    database, and files whose title already exists, are reported as skipped.
    """
    if not isinstance(filenames, list) or not filenames:
        raise ValueError("Select at least one EPUB to import.")

    if not all(isinstance(name, str) and name for name in filenames):
        raise ValueError("Invalid EPUB selection.")

    known_files = _known_files(table)

    results = []
    imported = 0
    skipped = 0
    failed = 0

    for filename in filenames:
        try:
            path = _resolve_file(filename)
        except (ValueError, FileNotFoundError) as exc:
            results.append(_result(filename, "failed", str(exc)))
            failed += 1
            continue

        if filename.casefold() in known_files:
            results.append(_result(filename, "skipped", "Already in database."))
            skipped += 1
            continue

        try:
            meta = get_epub_metadata(filename, strict=False)
        except Exception as exc:  # noqa: BLE001
            results.append(_result(filename, "failed", f"Could not read EPUB: {exc}"))
            failed += 1
            continue

        title = meta.title.strip() or path.stem

        if db.find_dup_title_db(title, table):
            results.append(_result(filename, "skipped", "Already exists in library."))
            skipped += 1
            continue

        cover_id = _cover_filename(meta, title)
        cover = extract_epub_cover(filename, cover_id=cover_id) or ""

        novel = build_novel_from_metadata(meta, filename, title=title, cover=cover)

        try:
            db.insert_novel(novel, table=table)
        except ValueError:
            # SQLite's UNIQUE(name) constraint is the final duplicate guard.
            results.append(_result(filename, "skipped", "Already exists in library."))
            skipped += 1
            continue
        except Exception as exc:  # noqa: BLE001
            results.append(_result(filename, "failed", f"Database insert failed: {exc}"))
            failed += 1
            continue

        results.append(_result(filename, "imported"))
        imported += 1

    return {
        "summary": {
            "requested": len(filenames),
            "imported": imported,
            "skipped": skipped,
            "failed": failed,
        },
        "results": results,
    }
