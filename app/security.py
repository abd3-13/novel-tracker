"""Request security helpers.

The application is a server-rendered Flask app with a JSON API, so it does
not depend on Flask-WTF. This module provides a small, dependency-free CSRF
guard: a per-session token rendered into pages and echoed back by the
JavaScript API on every state-changing request.
"""

import hmac
import secrets

from flask import Flask, jsonify, request, session

CSRF_SESSION_KEY = "_csrf_token"
CSRF_HEADER = "X-CSRFToken"
CSRF_FORM_FIELD = "csrf_token"
CSRF_ERROR_MESSAGE = "Invalid or missing CSRF token."

UNSAFE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})


def get_csrf_token() -> str:
    """Return the current session's CSRF token, creating it on first use."""
    token = session.get(CSRF_SESSION_KEY)

    if not token:
        token = secrets.token_urlsafe(32)
        session[CSRF_SESSION_KEY] = token

    return token


def _submitted_token() -> str:
    token = request.headers.get(CSRF_HEADER)

    if token:
        return token

    token = request.form.get(CSRF_FORM_FIELD)

    if token:
        return token

    payload = request.get_json(silent=True)

    if isinstance(payload, dict):
        return payload.get(CSRF_FORM_FIELD) or ""

    return ""


def init_security(app: Flask) -> None:
    """Register CSRF protection and expose ``csrf_token()`` to templates."""
    app.jinja_env.globals["csrf_token"] = get_csrf_token

    @app.before_request
    def protect_from_csrf():
        if request.method not in UNSAFE_METHODS:
            return None

        expected = session.get(CSRF_SESSION_KEY)
        submitted = _submitted_token()

        if not expected or not submitted or not hmac.compare_digest(expected, submitted):
            app.logger.warning(
                "Rejected %s %s: missing or invalid CSRF token",
                request.method,
                request.path,
            )
            return jsonify(
                {
                    "success": False,
                    "message": CSRF_ERROR_MESSAGE,
                    "category": "error",
                }
            ), 400

        return None
