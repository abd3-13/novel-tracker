import zlib

import pytest

from app.importer import importer
from app.sync.services import EpubMetadata, build_novel_from_metadata

pytestmark = pytest.mark.unit


def make_epub(tmp_path, name="book.epub"):
    path = tmp_path / name
    path.write_bytes(b"")
    return path


def metadata(**overrides):
    values = {
        "title": "Book",
        "author": "Author",
        "chapters": 3,
    }
    values.update(overrides)
    return EpubMetadata(**values)


def patch_import(monkeypatch, tmp_path, **overrides):
    settings = {
        "_epub_dir": lambda: tmp_path,
        "_known_files": lambda table: set(),
        "get_epub_metadata": lambda filename, strict=False: metadata(),
        "extract_epub_cover": lambda filename, cover_id=None: "cover.webp",
    }
    settings.update(overrides)

    for name, value in settings.items():
        monkeypatch.setattr(importer, name, value)

    monkeypatch.setattr(importer.db, "find_dup_title_db", lambda title, table: None)


def test_import_inserts_new_novel(monkeypatch, tmp_path):
    make_epub(tmp_path)
    inserted = {}

    patch_import(monkeypatch, tmp_path)
    monkeypatch.setattr(
        importer.db,
        "insert_novel",
        lambda data, table: inserted.update(data) or True,
    )

    result = importer.import_files(["book.epub"], "novels")

    assert result["summary"] == {
        "requested": 1,
        "imported": 1,
        "skipped": 0,
        "failed": 0,
    }
    assert inserted["name"] == "Book"
    assert inserted["filepath"] == "book.epub"
    assert inserted["cover_path"] == "cover.webp"
    assert inserted["localchap"] == 3
    assert inserted["epub_exists"] is True


def test_import_skips_files_already_in_database(monkeypatch, tmp_path):
    make_epub(tmp_path)

    patch_import(
        monkeypatch,
        tmp_path,
        _known_files=lambda table: {"book.epub"},
    )
    monkeypatch.setattr(
        importer.db,
        "insert_novel",
        lambda data, table: pytest.fail("should not insert"),
    )

    result = importer.import_files(["book.epub"], "novels")

    assert result["summary"]["skipped"] == 1
    assert result["results"][0]["reason"] == "Already in database."


def test_import_skips_duplicate_titles(monkeypatch, tmp_path):
    make_epub(tmp_path)

    patch_import(monkeypatch, tmp_path)
    monkeypatch.setattr(
        importer.db,
        "find_dup_title_db",
        lambda title, table: {"id": 1, "name": title},
    )
    monkeypatch.setattr(
        importer.db,
        "insert_novel",
        lambda data, table: pytest.fail("should not insert"),
    )

    result = importer.import_files(["book.epub"], "novels")

    assert result["summary"]["skipped"] == 1
    assert result["results"][0]["reason"] == "Already exists in library."


def test_import_rejects_filenames_outside_the_epub_directory(monkeypatch, tmp_path):
    patch_import(monkeypatch, tmp_path)

    result = importer.import_files(["../book.epub"], "novels")

    assert result["summary"]["failed"] == 1
    assert result["results"][0]["reason"] == "Invalid EPUB filename."


def test_import_marks_unreadable_epubs_as_failed(monkeypatch, tmp_path):
    make_epub(tmp_path)

    def fail(filename, strict=False):
        raise ValueError("bad zip")

    patch_import(monkeypatch, tmp_path, get_epub_metadata=fail)
    monkeypatch.setattr(
        importer.db,
        "insert_novel",
        lambda data, table: pytest.fail("should not insert"),
    )

    result = importer.import_files(["book.epub"], "novels")

    assert result["summary"]["failed"] == 1
    assert "Could not read EPUB" in result["results"][0]["reason"]


def test_import_treats_database_unique_errors_as_skipped(monkeypatch, tmp_path):
    make_epub(tmp_path)

    patch_import(monkeypatch, tmp_path)

    def insert(data, table):
        raise ValueError("UNIQUE constraint failed: novels.name")

    monkeypatch.setattr(importer.db, "insert_novel", insert)

    result = importer.import_files(["book.epub"], "novels")

    assert result["summary"]["skipped"] == 1
    assert result["results"][0]["reason"] == "Already exists in library."


def test_import_requires_a_non_empty_selection():
    with pytest.raises(ValueError, match="Select at least one EPUB"):
        importer.import_files([], "novels")


def test_cover_filename_falls_back_to_title_hash():
    meta = metadata(cover_id="")

    assert importer._cover_filename(meta, "Book") == f"{zlib.crc32(b'Book')}.webp"


def test_build_novel_from_metadata_uses_explicit_title_and_cover():
    novel = build_novel_from_metadata(
        metadata(title="Metadata Title", cover_id="meta.webp"),
        "file.epub",
        title="Chosen Title",
        cover="chosen.webp",
    )

    assert novel["name"] == "Chosen Title"
    assert novel["cover_path"] == "chosen.webp"
    assert novel["filepath"] == "file.epub"
    assert novel["epub_exists"] is True


def test_iter_import_files_emits_progress_then_done(monkeypatch, tmp_path):
    make_epub(tmp_path, "one.epub")
    make_epub(tmp_path, "two.epub")

    patch_import(monkeypatch, tmp_path)
    monkeypatch.setattr(importer.db, "insert_novel", lambda data, table: True)

    events = list(
        importer.iter_import_files(
            ["one.epub", "../bad.epub", "two.epub"], "novels"
        )
    )

    names = [event for event, _ in events]

    assert names[0] == "start"
    assert names[-1] == "done"
    assert "file_start" in names
    assert "stage" in names
    assert "file_done" in names

    statuses = [
        data["status"] for event, data in events if event == "file_done"
    ]

    assert statuses == ["imported", "failed", "imported"]
    assert events[-1][1]["summary"] == {
        "requested": 3,
        "imported": 2,
        "skipped": 0,
        "failed": 1,
    }


def test_iter_import_files_reports_skipped_files(monkeypatch, tmp_path):
    make_epub(tmp_path)

    patch_import(
        monkeypatch,
        tmp_path,
        _known_files=lambda table: {"book.epub"},
    )

    events = list(importer.iter_import_files(["book.epub"], "novels"))
    file_done = next(data for event, data in events if event == "file_done")

    assert file_done["status"] == "skipped"
    assert file_done["reason"] == "Already in database."
