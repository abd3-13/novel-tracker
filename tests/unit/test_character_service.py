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


class FailingListClient:
    def get_character_list(self, book_id):
        raise RuntimeError("network down")


def test_character_list_failure_is_wrapped(monkeypatch, tmp_path):
    monkeypatch.setattr(character_service, "_client", FailingListClient())

    with pytest.raises(character_service.CharacterFetchError) as excinfo:
        character_service.fetch_characters(book_id="123", output_dir=tmp_path)

    assert "network down" in str(excinfo.value)


class FlakyDetailClient:
    def __init__(self):
        self.calls = 0

    def get_character_list(self, book_id):
        return [
            SimpleNamespace(role_id="1", name="Alice"),
            SimpleNamespace(role_id="2", name="Bob"),
        ]

    def get_character_detail(self, book_id, role_id):
        self.calls += 1
        if role_id == "2":
            raise RuntimeError("detail unavailable")
        return CharacterInfo(role_id=role_id, name="Alice")


def test_detail_exception_marks_only_that_character_failed(monkeypatch, tmp_path):
    client = FlakyDetailClient()
    monkeypatch.setattr(character_service, "_client", client)

    summary = character_service.fetch_characters(book_id="123", output_dir=tmp_path)

    assert summary["characters"] == 1
    assert summary["failed"] == 1

    # One initial call per character plus MAX_RETRY retries for the failing one.
    assert client.calls == 2 + character_service.MAX_RETRY


class RecoveringDetailClient:
    def __init__(self, failures):
        self.failures = failures
        self.calls = 0

    def get_character_list(self, book_id):
        return [SimpleNamespace(role_id="1", name="Alice")]

    def get_character_detail(self, book_id, role_id):
        self.calls += 1
        if self.calls <= self.failures:
            raise RuntimeError("temporarily unavailable")
        return CharacterInfo(role_id=role_id, name="Alice")


def test_failed_detail_is_retried(monkeypatch, tmp_path):
    client = RecoveringDetailClient(failures=2)
    monkeypatch.setattr(character_service, "_client", client)

    summary = character_service.fetch_characters(book_id="123", output_dir=tmp_path)

    assert summary["characters"] == 1
    assert summary["failed"] == 0
    assert client.calls == 3
