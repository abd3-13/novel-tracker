"""Application configuration.

Values are read from the environment so deployments can override them
without editing code. Development keeps working with sensible defaults,
while production refuses to start without an explicit secret key.
"""

import os
from datetime import timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.environ.get("NOVEL_DATA_DIR", BASE_DIR / "data"))
DATABASE_PATH = Path(os.environ.get("DATABASE_PATH", DATA_DIR / "my-novels.db"))

ENV = os.environ.get("APP_ENV", "development").strip().lower()


def _env_flag(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


class Config:
    """Default application configuration."""

    ENV = ENV
    DEBUG = False if ENV == "production" else _env_flag("FLASK_DEBUG")
    TESTING = False

    # No default on purpose: create_app() either requires this in production
    # or generates an ephemeral key for local development.
    SECRET_KEY = os.environ.get("SECRET_KEY")

    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = _env_flag("SESSION_COOKIE_SECURE", ENV == "production")
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)

    # JSON payloads and imported metadata never need to be this large.
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024
