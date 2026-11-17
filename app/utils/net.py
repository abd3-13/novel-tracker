"""HTTP helpers for external providers.

All outbound requests share one retry policy:

- Network errors and transient HTTP statuses are retried with exponential
  backoff, capped by ``max_delay``.
- Other 4xx responses are returned to the caller immediately; retrying them
  only wastes the provider's rate limit.
- ``Retry-After`` is honoured when the server sends it.
"""

from __future__ import annotations

import logging
import random
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any

from curl_cffi import requests

logger = logging.getLogger(__name__)

DEFAULT_RETRIES = 3
DEFAULT_INITIAL_DELAY = 2.0
MAX_DELAY = 30.0

RETRYABLE_STATUS = frozenset({408, 425, 429, 500, 502, 503, 504})


class HttpRequestError(RuntimeError):
    """Raised when a request still fails after its retry budget."""

    def __init__(self, message, *, url, status=None, attempts=0):
        super().__init__(message)
        self.url = url
        self.status = status
        self.attempts = attempts


def retry_after_seconds(response) -> float | None:
    """Return ``Retry-After`` in seconds, supporting delay and HTTP-date forms."""

    value = (response.headers.get("Retry-After") or "").strip()

    if not value:
        return None

    try:
        return max(0.0, float(value))
    except ValueError:
        pass

    try:
        when = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None

    if when.tzinfo is None:
        when = when.replace(tzinfo=timezone.utc)

    return max(0.0, (when - datetime.now(timezone.utc)).total_seconds())


def backoff_delay(attempt: int, initial: float, maximum: float) -> float:
    """Exponential backoff with a small amount of jitter, never above ``maximum``."""

    if initial <= 0:
        return 0.0

    delay = min(maximum, initial * (2 ** max(0, attempt - 1)))

    return min(maximum, delay * (0.8 + random.random() * 0.4))


def get(
    url: str,
    *,
    params: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    timeout: float = 10,
    retries: int = DEFAULT_RETRIES,
    initial_delay: float = DEFAULT_INITIAL_DELAY,
    max_delay: float = MAX_DELAY,
    session: requests.Session | None = None,
    impersonate: str | None = None,
) -> requests.Response:
    """GET ``url`` with bounded retries.

    The response is returned as-is, including non-retryable 4xx responses, so
    callers can decide how to report them.
    """

    retries = max(1, int(retries))
    own_session = session is None

    if own_session:
        session = requests.Session(impersonate=impersonate)

    last_error: Exception | None = None
    last_status: int | None = None

    try:
        for attempt in range(1, retries + 1):
            try:
                response = session.get(
                    url,
                    params=params,
                    headers=headers,
                    timeout=timeout,
                )
            except KeyboardInterrupt:
                raise
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                last_status = None

                if attempt == retries:
                    break

                delay = backoff_delay(attempt, initial_delay, max_delay)
                logger.warning(
                    "GET %s failed (attempt %d/%d): %s; retrying in %.1fs",
                    url,
                    attempt,
                    retries,
                    exc,
                    delay,
                )
                time.sleep(delay)
                continue

            if response.status_code in RETRYABLE_STATUS:
                last_error = None
                last_status = response.status_code

                if attempt == retries:
                    break

                delay = retry_after_seconds(response)
                if delay is None:
                    delay = backoff_delay(attempt, initial_delay, max_delay)
                delay = min(delay, max_delay)

                logger.warning(
                    "GET %s returned HTTP %s (attempt %d/%d); retrying in %.1fs",
                    url,
                    response.status_code,
                    attempt,
                    retries,
                    delay,
                )
                time.sleep(delay)
                continue

            return response
    finally:
        if own_session:
            session.close()

    if last_status is not None:
        raise HttpRequestError(
            f"GET {url} failed with HTTP {last_status} "
            f"after {retries} attempt(s)",
            url=url,
            status=last_status,
            attempts=retries,
        )

    raise HttpRequestError(
        f"GET {url} failed after {retries} attempt(s): {last_error}",
        url=url,
        attempts=retries,
    ) from last_error
