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


def _file_event(
    current: int,
    total: int,
    filename: str,
    result: dict,
    title: str = "",
) -> dict:
    """Build a progress event for one finished file."""
    event = {
        "current": current,
        "total": total,
        "filename": filename,
        "status": result["status"],
    }

    if result.get("reason"):
        event["reason"] = result["reason"]

    if title:
        event["title"] = title

    return event


def iter_import_files(filenames: list[str], table: str):
    """
    Import the selected EPUB filenames, yielding progress and the final result.

    Each file succeeds or fails independently. Files already recorded in the
    database, and files whose title already exists, are reported as skipped.

    Yields
    ------
    tuple[str, dict]
      ("start" | "file_start" | "stage" | "file_done" | "done", {...})
    """
    if not isinstance(filenames, list) or not filenames:
        raise ValueError("Select at least one EPUB to import.")

    if not all(isinstance(name, str) and name for name in filenames):
        raise ValueError("Invalid EPUB selection.")

    known_files = _known_files(table)
    total = len(filenames)

    results = []
    imported = 0
    skipped = 0
    failed = 0

    yield "start", {"total": total}

    for current, filename in enumerate(filenames, start=1):
        yield "file_start", {
            "current": current,
            "total": total,
            "filename": filename,
        }

        try:
            path = _resolve_file(filename)
        except (ValueError, FileNotFoundError) as exc:
            result = _result(filename, "failed", str(exc))
            results.append(result)
            failed += 1
            yield "file_done", _file_event(current, total, filename, result)
            continue

        if filename.casefold() in known_files:
            result = _result(filename, "skipped", "Already in database.")
            results.append(result)
            skipped += 1
            yield "file_done", _file_event(current, total, filename, result)
            continue

        yield "stage", {
            "stage": "metadata",
            "current": current,
            "total": total,
            "filename": filename,
        }

        try:
            meta = get_epub_metadata(filename, strict=False)
        except Exception as exc:  # noqa: BLE001
            result = _result(filename, "failed", f"Could not read EPUB: {exc}")
            results.append(result)
            failed += 1
            yield "file_done", _file_event(current, total, filename, result)
            continue

        title = meta.title.strip() or path.stem

        if db.find_dup_title_db(title, table):
            result = _result(filename, "skipped", "Already exists in library.")
            results.append(result)
            skipped += 1
            yield "file_done", _file_event(current, total, filename, result, title)
            continue

        yield "stage", {
            "stage": "cover",
            "current": current,
            "total": total,
            "filename": filename,
        }

        cover_id = _cover_filename(meta, title)
        cover = extract_epub_cover(filename, cover_id=cover_id) or ""

        novel = build_novel_from_metadata(meta, filename, title=title, cover=cover)

        yield "stage", {
            "stage": "insert",
            "current": current,
            "total": total,
            "filename": filename,
        }

        try:
            db.insert_novel(novel, table=table)
        except ValueError:
            # SQLite's UNIQUE(name) constraint is the final duplicate guard.
            result = _result(filename, "skipped", "Already exists in library.")
            results.append(result)
            skipped += 1
            yield "file_done", _file_event(current, total, filename, result, title)
            continue
        except Exception as exc:  # noqa: BLE001
            result = _result(filename, "failed", f"Database insert failed: {exc}")
            results.append(result)
            failed += 1
            yield "file_done", _file_event(current, total, filename, result, title)
            continue

        result = _result(filename, "imported")
        results.append(result)
        imported += 1
        yield "file_done", _file_event(current, total, filename, result, title)

    yield "done", {
        "summary": {
            "requested": total,
            "imported": imported,
            "skipped": skipped,
            "failed": failed,
        },
        "results": results,
    }


def import_files(filenames: list[str], table: str) -> dict:
    """Import the selected EPUB filenames and return the final summary."""
    for event, data in iter_import_files(filenames, table):
        if event == "done":
            return data

    raise RuntimeError("EPUB import did not produce a result.")
