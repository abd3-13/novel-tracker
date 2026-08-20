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

from app.constants import AuthCategory, AuthField, AuthMessage, AuthResponseKey
from app.utils import db

auth_bp = Blueprint("auth", __name__, url_prefix="")


class User(UserMixin):
    def __init__(self, id, username, role, active):
        self.id = id
        self.username = username
        self.role = role
        self.active = active


def load_user(user_id):

    row = db.fetch_one(
        "SELECT id, username, role, active FROM users WHERE id = ?", (user_id,)
    )
    if row:
        return User(*row)
    return None


@auth_bp.get("/login")
def login_page():

    if current_user.is_authenticated:
        return redirect(url_for("main.index"))

    return render_template("login.html")


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

    return jsonify(
        {
            AuthResponseKey.SUCCESS: True,
            AuthResponseKey.REDIRECT: request.args.get(AuthField.NEXT)
            or url_for("main.index"),
        }
    )


@auth_bp.route("/logout")
def logout():
    logout_user()
    return redirect(url_for("auth.login"))
