from functools import wraps
from urllib.parse import urlsplit

from flask import (
    Blueprint,
    current_app,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import UserMixin, current_user, login_user, logout_user  # type: ignore
from werkzeug.security import check_password_hash

from app.constants import (
    AuthCategory,
    AuthField,
    AuthMessage,
    AuthResponseKey,
    AuthRole,
)
from app.utils import db

auth_bp = Blueprint("auth", __name__, url_prefix="")


class User(UserMixin):
    def __init__(self, id, username, role, active):
        self.id = id
        self.username = username
        self.role = role
        self.active = active

    @property
    def is_active(self):
        """Disabled accounts cannot keep an existing session alive."""
        return bool(self.active)


def load_user(user_id):

    row = db.fetch_one(
        "SELECT id, username, role, active FROM users WHERE id = ?", (user_id,)
    )
    if row and row[3]:
        return User(*row)
    return None


def safe_next_url(target):
    """Return a same-origin relative redirect target.

    ``next`` comes from the query string / login form, so it must never be
    allowed to point at another origin. Only absolute paths on this site are
    accepted; anything else falls back to the library.
    """
    fallback = url_for("main.index")

    if not target:
        return fallback

    target = target.strip()

    # Reject protocol-relative URLs (//host) and their backslash variants,
    # which browsers may normalize into a cross-origin request.
    if not target.startswith("/") or target.startswith(("//", "/\\")):
        return fallback

    parsed = urlsplit(target)

    if parsed.scheme or parsed.netloc:
        return fallback

    return target


def admin_required(view):
    """Require an authenticated administrator for a JSON endpoint."""

    @wraps(view)
    def wrapped(*args, **kwargs):
        if not current_user.is_authenticated:
            return jsonify(
                {
                    AuthResponseKey.SUCCESS: False,
                    AuthResponseKey.MESSAGE: AuthMessage.AUTH_FAILED_TITLE,
                    AuthResponseKey.CATEGORY: AuthCategory.ERROR,
                }
            ), 401

        if current_user.role != AuthRole.ADMIN:
            return jsonify(
                {
                    AuthResponseKey.SUCCESS: False,
                    AuthResponseKey.MESSAGE: AuthMessage.ADMIN_REQUIRED,
                    AuthResponseKey.CATEGORY: AuthCategory.ERROR,
                }
            ), 403

        return view(*args, **kwargs)

    return wrapped


@auth_bp.get("/login")
def login_page():

    if current_user.is_authenticated:
        return redirect(url_for("main.index"))

    return render_template(
        "login.html", next=request.args.get(AuthField.NEXT, "")
    )


@auth_bp.post("/login")
def login():

    username = request.form.get(AuthField.USERNAME, "").strip()
    password = request.form.get(AuthField.PASSWORD, "")

    user = db.fetch_one(
        "SELECT id, username, password_hash, role, active FROM users WHERE username = ?",
        (username,),
    )

    if not user or not check_password_hash(user[2], password):
        current_app.logger.warning("Failed login for '%s'", username)

        return jsonify(
            {
                AuthResponseKey.SUCCESS: False,
                AuthResponseKey.TITLE: AuthMessage.AUTH_FAILED_TITLE,
                AuthResponseKey.MESSAGE: AuthMessage.INVALID_CREDENTIALS,
                AuthResponseKey.CATEGORY: AuthCategory.ERROR,
            }
        ), 401

    if not user[4]:
        return jsonify(
            {
                AuthResponseKey.SUCCESS: False,
                AuthResponseKey.TITLE: AuthMessage.ACCOUNT_DISABLED_TITLE,
                AuthResponseKey.MESSAGE: AuthMessage.ACCOUNT_DISABLED,
                AuthResponseKey.CATEGORY: AuthCategory.WARNING,
            }
        ), 403

    login_user(User(user[0], user[1], user[3], user[4]))

    target = request.form.get(AuthField.NEXT) or request.args.get(AuthField.NEXT)

    return jsonify(
        {
            AuthResponseKey.SUCCESS: True,
            AuthResponseKey.REDIRECT: safe_next_url(target),
        }
    )


@auth_bp.route("/logout")
def logout():
    logout_user()
    return redirect(url_for("auth.login"))
