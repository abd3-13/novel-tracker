import pytest

from app.sync.webnovel import api

pytestmark = pytest.mark.unit


class FakeResponse:
    def __init__(self, payload):
        self._payload = payload
        self.status_code = 200

    def json(self):
        return self._payload

    def raise_for_status(self):
        return None


@pytest.fixture
def settings(monkeypatch):
    values = {
        "ENDPOINT": "https://example.test/book/",
        "DELAY_FROM": "0",
        "DELAY_TO": "0",
        "API_TIMEOUT": "5",
    }

    monkeypatch.setattr(api.db, "get_value", lambda key: values.get(str(key)))
    monkeypatch.setattr(api.time, "sleep", lambda *_: None)


def test_fetch_latest_chapter_uses_the_client_session(settings, monkeypatch):
    captured = {}

    def fake_get(url, **kwargs):
        captured["url"] = url
        captured.update(kwargs)
        return FakeResponse(
            {
                "Data": {
                    "BookName": "Test Book",
                    "ChapterNum": 12,
                    "LastChapterTime": 1700000000000,
                    "AuthorInfo": {"AuthorName": "Author"},
                    "Description": "Description",
                }
            }
        )

    monkeypatch.setattr(api.net, "get", fake_get)

    client = api.WebnovelClient()
    info = client.fetch_latest_chapter("12345678")

    assert captured["url"] == "https://example.test/book/12345678"
    assert captured["session"] is client.session
    assert info.chapter == 12
    assert info.title == "Test Book"
    assert info.author == "Author"


def test_fetch_latest_chapter_wraps_network_failures(settings, monkeypatch):
    def fake_get(url, **kwargs):
        raise api.net.HttpRequestError("timed out", url=url, attempts=3)

    monkeypatch.setattr(api.net, "get", fake_get)

    client = api.WebnovelClient()

    with pytest.raises(api.NetworkError) as excinfo:
        client.fetch_latest_chapter("12345678")

    message = str(excinfo.value)
    assert "12345678" in message
    assert "timed out" in message
