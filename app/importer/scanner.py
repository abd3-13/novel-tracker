"""
Scan the configured local EPUB directory for novels that are not in the database.

The scanner is intentionally read-only: it never writes files or database rows.
Importing happens in app.importer.importer.
"""

import os
from pathlib import Path
from typing import Any

from app.constants import DefaultValue, SettingKey
from app.sync.services import get_epub_metadata
from app.utils import db
from app.utils.tools import normalize_title


def _epub_dir() -> Path:
    return Path(db.get_value(SettingKey.LOCAL_EPUB_DIR) or DefaultValue.CURRENT_DIR)


def _known_files(table: str) -> set[str]:
    """Return filenames already referenced by the database, case-insensitively."""
    epub_files, _ = db.get_db_filesNcover(table)
    return {os.path.basename(path).casefold() for path in epub_files if path}


def _known_titles(table: str) -> set[str]:
    """Return normalized titles already present in the database."""
    rows = db.fetch_all(f"SELECT name FROM {table}", close=True)
    return {normalize_title(name) for (name,) in rows if name}


def _candidate(
    path: Path,
    status: str,
    *,
    meta: Any = None,
    title: str = "",
    reason: str = "",
) -> dict:
    title = title or (meta.title.strip() if meta and meta.title else "") or path.stem

    return {
        "filename": path.name,
        "status": status,
        "title": title,
        "author": meta.author if meta else "",
        "description": meta.description if meta else "",
        "source": meta.source if meta else "",
        "url": meta.url if meta else "",
        "chapters": meta.chapters if meta else 0,
        "last_title": meta.last_title if meta else "",
        "last_file": meta.last_file if meta else "",
        "characters": meta.characters if meta else 0,
        "cover_id": meta.cover_id if meta else "",
        "reason": reason,
    }


def iter_scan_library(table: str):
    """
    Scan the configured EPUB directory, yielding progress and the final result.

    Yields
    ------
    tuple[str, dict]
      ("progress", {...}) while working, then ("done", result) exactly once.
    """
    epub_dir = _epub_dir()

    if not epub_dir.is_dir():
        raise ValueError(f"Local EPUB directory not found: {epub_dir}")

    yield "progress", {"stage": "listing"}

    try:
        files = sorted(
            (
                path
                for path in epub_dir.iterdir()
                if path.is_file() and path.suffix.lower() == ".epub"
            ),
            key=lambda path: path.name.casefold(),
        )
    except OSError as exc:
        raise ValueError(f"Unable to read EPUB directory: {epub_dir}") from exc

    known_files = _known_files(table)
    new_files = [path for path in files if path.name.casefold() not in known_files]
    known_count = len(files) - len(new_files)

    yield "progress", {
        "stage": "checking",
        "total": len(files),
        "known": known_count,
        "new": len(new_files),
    }

    db_titles = _known_titles(table)
    seen_titles = set(db_titles)

    candidates = []
    live = {"new": 0, "already_exists": 0, "errors": 0}

    for current, path in enumerate(new_files, start=1):
        yield "progress", {
            "stage": "metadata",
            "current": current,
            "total": len(new_files),
            "filename": path.name,
            **live,
        }

        try:
            meta = get_epub_metadata(path.name, strict=False)
        except Exception as exc:  # noqa: BLE001
            candidates.append(
                _candidate(path, "error", reason=f"Could not read EPUB: {exc}")
            )
            live["errors"] += 1
            continue

        title = meta.title.strip() or path.stem
        normalized_title = normalize_title(title)

        if normalized_title in seen_titles:
            reason = (
                "Title already exists in the library."
                if normalized_title in db_titles
                else "Duplicate title in this scan."
            )
            candidates.append(
                _candidate(
                    path,
                    "already_exists",
                    meta=meta,
                    title=title,
                    reason=reason,
                )
            )
            live["already_exists"] += 1
            continue

        seen_titles.add(normalized_title)
        candidates.append(_candidate(path, "new", meta=meta, title=title))
        live["new"] += 1

    counts = {
        "total": len(files),
        "known": known_count,
        **live,
    }

    yield "done", {
        "directory": str(epub_dir),
        "candidates": candidates,
        "counts": counts,
    }


def scan_library(table: str) -> dict:
    """
    Scan the configured EPUB directory and return the final Candidates result.

    Files whose names are already recorded in the database are skipped.
    New files are parsed for local metadata; files whose normalized title
    already exists in the database are returned with status "already_exists".
    """
    for event, data in iter_scan_library(table):
        if event == "done":
            return data

    raise RuntimeError("EPUB scan did not produce a result.")
