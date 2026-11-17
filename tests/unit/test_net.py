from datetime import datetime, timedelta, timezone
from email.utils import format_datetime

import pytest

from app.utils import net

pytestmark = pytest.mark.unit


class FakeResponse:
    def __init__(self, status_code=200, payload=None, headers=None, content=b""):
        self.status_code = status_code
        self._payload = {} if payload is None else payload
        self.headers = headers or {}
        self.content = content

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class FakeSession:
    def __init__(self, outcomes):
        self.outcomes = list(outcomes)
        self.calls = []
        self.closed = False

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    def close(self):
        self.closed = True


@pytest.fixture
def sleeps(monkeypatch):
    recorded = []
    monkeypatch.setattr(net.time, "sleep", recorded.append)
    return recorded


def test_get_retries_transient_statuses_then_returns_success(sleeps):
    first = FakeResponse(503)
    second = FakeResponse(200, {"ok": True})
    session = FakeSession([first, second])

    response = net.get("https://example.test/api", session=session, retries=3)

    assert response is second
    assert len(session.calls) == 2
    assert len(sleeps) == 1


def test_get_does_not_retry_non_retryable_client_errors(sleeps):
    response = FakeResponse(404)
    session = FakeSession([response])

    result = net.get("https://example.test/api", session=session, retries=3)

    assert result is response
    assert len(session.calls) == 1
    assert sleeps == []


def test_get_raises_after_exhausting_retries(sleeps):
    session = FakeSession([FakeResponse(500), FakeResponse(502)])

    with pytest.raises(net.HttpRequestError) as excinfo:
        net.get("https://example.test/api", session=session, retries=2)

    assert excinfo.value.status == 502
    assert excinfo.value.attempts == 2
    assert len(session.calls) == 2


def test_get_retries_network_errors(sleeps):
    session = FakeSession([ConnectionError("boom"), FakeResponse(200, {"ok": True})])

    response = net.get("https://example.test/api", session=session, retries=2)

    assert response.status_code == 200
    assert len(session.calls) == 2

    failing = FakeSession([ConnectionError("boom")])

    with pytest.raises(net.HttpRequestError) as excinfo:
        net.get("https://example.test/api", session=failing, retries=1)

    assert "boom" in str(excinfo.value)


def test_get_honours_retry_after(sleeps):
    session = FakeSession(
        [FakeResponse(429, headers={"Retry-After": "7"}), FakeResponse(200)]
    )

    net.get("https://example.test/api", session=session, retries=2, max_delay=30)

    assert sleeps == [7.0]


def test_get_caps_retry_after(sleeps):
    session = FakeSession(
        [FakeResponse(503, headers={"Retry-After": "600"}), FakeResponse(200)]
    )

    net.get("https://example.test/api", session=session, retries=2, max_delay=5)

    assert sleeps == [5]


def test_get_creates_and_closes_its_own_session(sleeps, monkeypatch):
    instances = []
    response = FakeResponse(200)

    class Session(FakeSession):
        def __init__(self, outcomes=(), impersonate=None):
            super().__init__([response])
            instances.append((self, impersonate))

    monkeypatch.setattr(net.requests, "Session", Session)

    net.get("https://example.test/api", impersonate="chrome_android")

    assert len(instances) == 1
    session, impersonate = instances[0]
    assert impersonate == "chrome_android"
    assert session.closed is True


def test_backoff_delay_is_capped():
    for attempt in range(1, 10):
        assert net.backoff_delay(attempt, initial=2, maximum=5) <= 5


def test_retry_after_seconds_supports_http_dates():
    when = datetime.now(timezone.utc) + timedelta(seconds=30)
    response = FakeResponse(429, headers={"Retry-After": format_datetime(when)})

    delay = net.retry_after_seconds(response)

    assert delay is not None
    assert 25 <= delay <= 31


def test_retry_after_seconds_ignores_invalid_values():
    assert net.retry_after_seconds(FakeResponse(429)) is None
    assert (
        net.retry_after_seconds(FakeResponse(429, headers={"Retry-After": "soon"}))
        is None
    )
