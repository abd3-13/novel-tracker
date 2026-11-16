import secrets

from flask import Flask
from flask_login import LoginManager

from app.auth import auth_bp, load_user
from app.cli import register_cli
from app.config import Config
from app.routes.importing import import_bp
from app.routes.main import main_bp
from app.security import init_security
from app.sync.manager import SyncManager
from app.utils import db
from app.utils.filters import time_difference

login_manager = LoginManager()


def create_app(config_object=Config):
    app = Flask(__name__)
    app.config.from_object(config_object)

    if not app.config.get("SECRET_KEY"):
        if app.config.get("ENV") == "production":
            raise RuntimeError(
                "SECRET_KEY must be set when APP_ENV=production. "
                "Generate one with: python -c 'import secrets; print(secrets.token_urlsafe(48))'"
            )

        # Ephemeral development key: safe by default, but sessions reset on
        # restart. Set SECRET_KEY to keep sessions across restarts.
        app.secret_key = secrets.token_urlsafe(48)
        app.logger.warning(
            "SECRET_KEY is not set; using an ephemeral development key. "
            "Sessions will be invalidated when the process restarts."
        )

    # Initialize login manager
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"  # blueprint.endpoint

    init_security(app)

    # Create missing tables before any request can read settings or novels.
    # Both operations are idempotent and never overwrite existing rows.
    db.init_db()
    db.ensure_schema()

    # Register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(import_bp)

    register_cli(app)

    # Register template filters
    app.add_template_filter(time_difference, name="time_difference")

    @app.after_request
    def add_security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
        response.headers.setdefault("Referrer-Policy", "same-origin")
        return response

    app.extensions["sync_manager"] = SyncManager()

    return app


@login_manager.user_loader
def user_loader(user_id):
    return load_user(user_id)
