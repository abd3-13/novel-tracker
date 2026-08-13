import os

from flask import Flask
from flask_login import LoginManager

from app.auth import auth_bp, load_user
from app.routes.main import main_bp
from app.sync.manager import SyncManager
from app.utils.filters import time_difference

login_manager = LoginManager()


def create_app():
    app = Flask(__name__)
    app.secret_key = os.environ.get("SECRET_KEY", "devkey")

    # Initialize login manager
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"  # blueprint.endpoint

    # Register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)

    # Register template filters
    app.add_template_filter(time_difference, name="time_difference")

    app.extensions["sync_manager"] = SyncManager()

    return app


@login_manager.user_loader
def user_loader(user_id):
    return load_user(user_id)
