from pathlib import Path

import pytest

from app.constants import DatabaseColumn, SyncAction, SyncMode
from app.sync.metadata import FIELDS, sync_cover_asset
from app.sync.webnovel import api

pytestmark = pytest.mark.unit


class FakeCollector:
    def __init__(self):
        self.updates = {}

    def set(self, key, value):
        self.updates[key] = value


class FakeProvider:
    def fetch_cover(self, overwrite=False):
        return "42.webp"


class FakeProviders:
    def get_provider(self, source):
        return FakeProvider()


class FakeJob:
    source = "local"
    mode = SyncMode.FILL_MISSING


class FakeContext:
    def __init__(self):
        self.collector = FakeCollector()
        self.providers = FakeProviders()
        self.job = FakeJob()
        self.events = []

    def emit(self, event, **data):
        self.events.append((event, data))


def test_sync_cover_asset_queues_cover_path():
    ctx = FakeContext()

    sync_cover_asset(ctx, FIELDS[SyncAction.FETCH_COVER])

    assert ctx.collector.updates == {DatabaseColumn.COVER: "42.webp"}


def test_online_cover_converts_the_downloaded_file(monkeypatch, tmp_path):
    monkeypatch.setattr(api, "_img_endpoint", lambda: "https://img.example")
    monkeypatch.setattr(api.db, "get_value", lambda key: str(tmp_path))

    seen = {}

    def fake_download(url, filename, folder, dry_run=False):
        (Path(folder) / filename).write_bytes(b"jpeg")
        return filename

    def fake_convert(image_path, overwrite=False):
        seen["image_path"] = image_path
        seen["overwrite"] = overwrite
        webp_path = Path(image_path).with_suffix(".webp")
        webp_path.write_bytes(b"webp")
        return webp_path

    monkeypatch.setattr(api, "download_image", fake_download)
    monkeypatch.setattr(api, "convert_to_webp", fake_convert)

    client = api.WebnovelClient()

    assert client.fetch_cover_image("42", overwrite=True) == "42.webp"
    assert seen["image_path"] == tmp_path / "42.cover"
    assert seen["overwrite"] is True


def test_online_cover_returns_none_when_conversion_fails(monkeypatch, tmp_path):
    monkeypatch.setattr(api, "_img_endpoint", lambda: "https://img.example")
    monkeypatch.setattr(api.db, "get_value", lambda key: str(tmp_path))
    monkeypatch.setattr(
        api,
        "download_image",
        lambda url, filename, folder, dry_run=False: filename,
    )
    monkeypatch.setattr(api, "convert_to_webp", lambda image_path, overwrite=False: None)

    assert api.WebnovelClient().fetch_cover_image("42") is None
