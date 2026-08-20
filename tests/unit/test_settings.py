import json

from app.constants import SettingKey
from app.utils import db


def test_database_settings_include_overlay_metadata(monkeypatch, tmp_path):
    db_path = tmp_path / "settings.db"
    monkeypatch.setattr(db, "DEFAULT_DB", str(db_path))
    db.init_db()

    rows = db.list_setting_rows()
    keys = {row["key"] for row in rows}

    assert SettingKey.CARD_OVERLAY_METADATA in keys
    assert SettingKey.DB_PATH in keys


def test_save_overlay_metadata_persists_json(monkeypatch, tmp_path):
    db_path = tmp_path / "settings-overlays.db"
    monkeypatch.setattr(db, "DEFAULT_DB", str(db_path))
    db.init_db()

    value = ["characters", "progress", "chapter"]
    db.save_setting(SettingKey.CARD_OVERLAY_METADATA, json.dumps(value))

    assert json.loads(db.get_value(SettingKey.CARD_OVERLAY_METADATA, "[]")) == value
