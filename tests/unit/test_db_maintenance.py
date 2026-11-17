import sqlite3

import pytest

from app.utils import db

pytestmark = pytest.mark.unit


def test_backup_database_writes_a_readable_copy(monkeypatch, tmp_path):
    live = tmp_path / "live.db"
    monkeypatch.setattr(db, "DEFAULT_DB", str(live))

    db.init_db()
    db.insert_novel({"name": "Backed Up", "filepath": "Backed Up.epub"})

    destination = db.backup_database(tmp_path / "backups" / "copy.db")

    assert destination.exists()

    copy = sqlite3.connect(destination)
    try:
        rows = copy.execute("SELECT name FROM novels").fetchall()
    finally:
        copy.close()

    assert rows == [("Backed Up",)]


def test_check_integrity_passes_on_a_fresh_database(monkeypatch, tmp_path):
    monkeypatch.setattr(db, "DEFAULT_DB", str(tmp_path / "fresh.db"))

    db.init_db()

    result, foreign_keys = db.check_integrity()

    assert result == "ok"
    assert foreign_keys == []
