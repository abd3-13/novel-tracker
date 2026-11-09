import pytest

from app.importer import scanner
from app.sync.services import EpubMetadata

pytestmark = pytest.mark.unit


def make_epub(tmp_path, name):
    path = tmp_path / name
    path.write_bytes(b"")
    return path


def metadata(**overrides):
    values = {
        "title": "Title",
        "author": "Author",
        "chapters": 3,
    }
    values.update(overrides)
    return EpubMetadata(**values)


def patch_database(monkeypatch, files=None, titles=None):
    monkeypatch.setattr(
        scanner.db,
        "get_db_filesNcover",
        lambda table: (set(files or ()), set()),
    )
    monkeypatch.setattr(
        scanner.db,
        "fetch_all",
        lambda *args, **kwargs: [(title,) for title in (titles or ())],
    )


def test_scan_skips_files_already_in_database(monkeypatch, tmp_path):
    make_epub(tmp_path, "known.epub")
    make_epub(tmp_path, "new.epub")

    monkeypatch.setattr(scanner, "_epub_dir", lambda: tmp_path)
    patch_database(monkeypatch, files={"known.epub"}, titles=["Other"])
    monkeypatch.setattr(
        scanner,
        "get_epub_metadata",
        lambda filename, strict=False: metadata(title="New Book"),
    )

    result = scanner.scan_library("novels")

    assert result["counts"] == {
        "total": 2,
        "known": 1,
        "new": 1,
        "already_exists": 0,
        "errors": 0,
    }
    assert [candidate["filename"] for candidate in result["candidates"]] == [
        "new.epub"
    ]


def test_scan_marks_duplicate_titles_as_already_existing(monkeypatch, tmp_path):
    make_epub(tmp_path, "duplicate.epub")

    monkeypatch.setattr(scanner, "_epub_dir", lambda: tmp_path)
    patch_database(monkeypatch, titles=["Duplicate Book"])
    monkeypatch.setattr(
        scanner,
        "get_epub_metadata",
        lambda filename, strict=False: metadata(title="Duplicate Book"),
    )

    result = scanner.scan_library("novels")

    candidate = result["candidates"][0]

    assert candidate["status"] == "already_exists"
    assert candidate["reason"] == "Title already exists in the library."
    assert result["counts"]["already_exists"] == 1


def test_scan_marks_later_duplicate_titles_in_the_same_scan(monkeypatch, tmp_path):
    make_epub(tmp_path, "first.epub")
    make_epub(tmp_path, "second.epub")

    monkeypatch.setattr(scanner, "_epub_dir", lambda: tmp_path)
    patch_database(monkeypatch)
    monkeypatch.setattr(
        scanner,
        "get_epub_metadata",
        lambda filename, strict=False: metadata(title="Same Book"),
    )

    result = scanner.scan_library("novels")

    statuses = {candidate["filename"]: candidate["status"] for candidate in result["candidates"]}

    assert statuses == {"first.epub": "new", "second.epub": "already_exists"}
    assert result["candidates"][1]["reason"] == "Duplicate title in this scan."


def test_scan_marks_unreadable_epubs_as_errors(monkeypatch, tmp_path):
    make_epub(tmp_path, "broken.epub")
    make_epub(tmp_path, "good.epub")

    monkeypatch.setattr(scanner, "_epub_dir", lambda: tmp_path)
    patch_database(monkeypatch)

    def read_metadata(filename, strict=False):
        if filename == "broken.epub":
            raise ValueError("bad zip")
        return metadata(title="Good Book")

    monkeypatch.setattr(scanner, "get_epub_metadata", read_metadata)

    result = scanner.scan_library("novels")

    assert result["counts"]["errors"] == 1
    assert result["counts"]["new"] == 1
    assert any(candidate["status"] == "error" for candidate in result["candidates"])
    assert any(candidate["status"] == "new" for candidate in result["candidates"])


def test_scan_ignores_non_epub_files(monkeypatch, tmp_path):
    make_epub(tmp_path, "book.EPUB")
    (tmp_path / "notes.txt").write_text("not an epub")

    monkeypatch.setattr(scanner, "_epub_dir", lambda: tmp_path)
    patch_database(monkeypatch)
    monkeypatch.setattr(
        scanner,
        "get_epub_metadata",
        lambda filename, strict=False: metadata(title="Book"),
    )

    result = scanner.scan_library("novels")

    assert result["counts"]["total"] == 1
    assert result["candidates"][0]["filename"] == "book.EPUB"


def test_scan_falls_back_to_filename_when_title_is_empty(monkeypatch, tmp_path):
    make_epub(tmp_path, "My Book.epub")

    monkeypatch.setattr(scanner, "_epub_dir", lambda: tmp_path)
    patch_database(monkeypatch)
    monkeypatch.setattr(
        scanner,
        "get_epub_metadata",
        lambda filename, strict=False: metadata(title=""),
    )

    result = scanner.scan_library("novels")

    assert result["candidates"][0]["title"] == "My Book"


def test_scan_raises_when_directory_is_missing(monkeypatch, tmp_path):
    monkeypatch.setattr(scanner, "_epub_dir", lambda: tmp_path / "missing")

    with pytest.raises(ValueError, match="Local EPUB directory not found"):
        scanner.scan_library("novels")


def test_iter_scan_library_emits_progress_then_done(monkeypatch, tmp_path):
    make_epub(tmp_path, "known.epub")
    make_epub(tmp_path, "new.epub")

    monkeypatch.setattr(scanner, "_epub_dir", lambda: tmp_path)
    patch_database(monkeypatch, files={"known.epub"})
    monkeypatch.setattr(
        scanner,
        "get_epub_metadata",
        lambda filename, strict=False: metadata(title="New Book"),
    )

    events = list(scanner.iter_scan_library("novels"))

    assert [event for event, _ in events] == [
        "progress",
        "progress",
        "progress",
        "done",
    ]
    assert events[0][1] == {"stage": "listing"}
    assert events[1][1] == {
        "stage": "checking",
        "total": 2,
        "known": 1,
        "new": 1,
    }
    assert events[2][1]["stage"] == "metadata"
    assert events[2][1]["filename"] == "new.epub"
    assert events[3][1]["counts"]["new"] == 1
