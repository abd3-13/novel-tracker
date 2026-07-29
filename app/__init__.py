from flask import Flask
from flask_login import LoginManager
from app.routes.main import main_bp
from app.utils.filters import time_difference
from app.state import BulkState
from app.worker import start_worker
from app.auth import load_user, auth_bp
import os

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

  # App-level state
  app.bulk_state = BulkState()
  
  start_worker(app)
  return app

@login_manager.user_loader
def user_loader(user_id):
    return load_user(user_id)
