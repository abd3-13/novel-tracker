import pytest

from app.utils import db

pytestmark = pytest.mark.unit


def test_get_db_files_ncover_reads_rows_returned_by_fetch_all(monkeypatch):
    rows = [
        ("Text/one.epub", "covers/one.webp"),
        ("Text/two.epub", "covers/two.webp"),
        ("Text/three.epub", "covers/three.webp"),
        ("Text/four.epub", None),
    ]

    monkeypatch.setattr(db, "fetch_all", lambda *args, **kwargs: rows)

    epub_files, cover_files = db.get_db_filesNcover("novels")

    assert epub_files == {"one.epub", "two.epub", "three.epub", "four.epub"}
    assert cover_files == {"one.webp", "two.webp", "three.webp"}


def test_find_dup_title_db_reads_rows_returned_by_fetch_all(monkeypatch):
    monkeypatch.setattr(
        db,
        "fetch_all",
        lambda *args, **kwargs: [(1, "Some Book"), (2, "Another Book")],
    )

    assert db.find_dup_title_db("Some Book", "novels") == {
        "id": 1,
        "name": "Some Book",
    }
    assert db.find_dup_title_db("Missing Book", "novels") is None
