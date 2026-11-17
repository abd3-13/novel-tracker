import pytest
from PIL import Image

from app.utils import images
from app.utils.images import convert_to_webp

pytestmark = pytest.mark.unit


def test_convert_to_webp_creates_missing_output(tmp_path):
    source = tmp_path / ".cover.jpg"
    Image.new("RGB", (8, 12), "red").save(source, "JPEG")

    result = convert_to_webp(source)

    assert result is not None
    assert result.is_file()
    assert result.suffix == ".webp"


class FakeResponse:
    def __init__(self, content=b"image", status_code=200):
        self.content = content
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


def test_download_image_writes_the_response(tmp_path, monkeypatch):
    calls = []

    def fake_get(url, **kwargs):
        calls.append((url, kwargs))
        return FakeResponse(b"bytes")

    monkeypatch.setattr(images.net, "get", fake_get)

    filename = images.download_image(
        "https://example.test/cover.jpg", "cover.jpg", tmp_path
    )

    assert filename == "cover.jpg"
    assert (tmp_path / "cover.jpg").read_bytes() == b"bytes"
    assert calls[0][1]["impersonate"] == "chrome_android"


def test_download_image_returns_none_when_every_attempt_fails(tmp_path, monkeypatch):
    def fake_get(url, **kwargs):
        raise images.net.HttpRequestError("boom", url=url, attempts=3)

    monkeypatch.setattr(images.net, "get", fake_get)

    assert (
        images.download_image("https://example.test/cover.jpg", "cover.jpg", tmp_path)
        is None
    )
    assert not (tmp_path / "cover.jpg").exists()


def test_download_image_keeps_an_existing_file(tmp_path, monkeypatch):
    existing = tmp_path / "cover.jpg"
    existing.write_bytes(b"old")

    def fake_get(url, **kwargs):
        raise AssertionError("existing files must not be downloaded again")

    monkeypatch.setattr(images.net, "get", fake_get)

    assert (
        images.download_image("https://example.test/cover.jpg", "cover.jpg", tmp_path)
        == "cover.jpg"
    )
    assert existing.read_bytes() == b"old"


def test_download_image_dry_run_does_not_write(tmp_path, monkeypatch):
    monkeypatch.setattr(
        images.net,
        "get",
        lambda *args, **kwargs: pytest.fail("dry run must not request the URL"),
    )

    assert (
        images.download_image(
            "https://example.test/cover.jpg",
            "cover.jpg",
            tmp_path,
            dry_run=True,
        )
        == "cover.jpg"
    )
    assert not (tmp_path / "cover.jpg").exists()
