import json
from types import SimpleNamespace

import pytest

from app.sync.webnovel import character_service
from app.sync.webnovel.api import CharacterInfo

pytestmark = pytest.mark.unit


class FakeClient:
    def get_character_list(self, book_id):
        return [
            SimpleNamespace(role_id="1", name="Alice"),
            SimpleNamespace(role_id="2", name="Bob"),
        ]

    def get_character_detail(self, book_id, role_id):
        if role_id == "2":
            return None
        return CharacterInfo(role_id=role_id, name="Alice")


def test_fetch_characters_writes_metadata_without_images(monkeypatch, tmp_path):
    monkeypatch.setattr(character_service, "_client", FakeClient())

    summary = character_service.fetch_characters(
        book_id="123", output_dir=tmp_path
    )

    assert summary["characters"] == 1
    assert summary["failed"] == 1

    characters = json.loads((tmp_path / "characters.json").read_text())
    assert characters == [
        {
            "role_id": "1",
            "name": "Alice",
            "nickname": None,
            "birthday": None,
            "height": None,
            "description": None,
            "data": None,
        }
    ]

    assert not [
        path for path in tmp_path.iterdir() if path.suffix in {".jpg", ".webp"}
    ]
