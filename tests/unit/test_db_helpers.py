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


def test_get_table_excludes_soft_deleted_novels(monkeypatch):
    captured = {}

    class User:
        role = "admin"

    def fake_fetch_all(query, **kwargs):
        captured["query"] = query
        return []

    monkeypatch.setattr(db, "get_user_table", lambda user: "novels")
    monkeypatch.setattr(db, "fetch_all", fake_fetch_all)

    assert db.get_table(User()) == []
    assert "COALESCE(is_deleted, 0) = 0" in captured["query"]


def test_delete_missing_epub_novels_flags_only_missing_active_rows(monkeypatch):
    captured = {}

    class Cursor:
        rowcount = 3

    def fake_execute(query, params=(), **kwargs):
        captured["query"] = query
        captured["params"] = params
        return Cursor(), None

    monkeypatch.setattr(db, "execute", fake_execute)

    assert db.delete_missing_epub_novels("novels") == 3
    assert "SET is_deleted = 1" in captured["query"]
    assert "COALESCE(epub_exists, 0) = 0" in captured["query"]
    assert "COALESCE(is_deleted, 0) = 0" in captured["query"]
