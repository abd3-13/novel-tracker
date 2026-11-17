"""Coverage for the account administration CLI commands."""

import pytest
from werkzeug.security import check_password_hash

from app import create_app
from app.constants import AuthRole
from app.utils import db

pytestmark = pytest.mark.integration

PASSWORD = "secret"


@pytest.fixture
def app(monkeypatch, tmp_path):
    monkeypatch.setattr(db, "DEFAULT_DB", str(tmp_path / "cli.db"))

    application = create_app()
    application.config.update(TESTING=True)

    yield application

    application.extensions["sync_manager"].executor.shutdown(wait=True)


@pytest.fixture
def runner(app):
    return app.test_cli_runner()


def user_row(username):
    return db.fetch_one(
        "SELECT username, email, password_hash, role, active FROM users "
        "WHERE username = ?",
        (username,),
        row_factory=True,
    )


def create(runner, username, role=AuthRole.USER.value, password=PASSWORD):
    result = runner.invoke(
        args=["create-user", username, "--password", password, "--role", role]
    )
    assert result.exit_code == 0, result.output
    return result


# ----------------------------------------------------------------------
# create-user
# ----------------------------------------------------------------------


def test_create_user_stores_a_password_hash(runner):
    create(runner, "boss", role=AuthRole.ADMIN.value)

    row = user_row("boss")

    assert row["role"] == AuthRole.ADMIN.value
    assert row["active"] == 1
    assert row["password_hash"] != PASSWORD
    assert check_password_hash(row["password_hash"], PASSWORD)


def test_create_user_stores_an_email(runner):
    result = runner.invoke(
        args=[
            "create-user",
            "reader",
            "--password",
            PASSWORD,
            "--email",
            "reader@example.test",
        ]
    )

    assert result.exit_code == 0, result.output
    assert user_row("reader")["email"] == "reader@example.test"


def test_create_user_rejects_duplicates(runner):
    create(runner, "reader")

    result = runner.invoke(
        args=["create-user", "reader", "--password", PASSWORD]
    )

    assert result.exit_code != 0
    assert "already exists" in result.output


@pytest.mark.parametrize("password", ("", "   "))
def test_create_user_rejects_empty_passwords(runner, password):
    result = runner.invoke(
        args=["create-user", "reader", "--password", password]
    )

    assert result.exit_code != 0
    assert "Password cannot be empty" in result.output
    assert user_row("reader") is None


def test_create_user_rejects_an_unknown_role(runner):
    result = runner.invoke(
        args=["create-user", "reader", "--password", PASSWORD, "--role", "root"]
    )

    assert result.exit_code == 2
    assert user_row("reader") is None


# ----------------------------------------------------------------------
# list-users
# ----------------------------------------------------------------------


def test_list_users_reports_an_empty_database(runner):
    result = runner.invoke(args=["list-users"])

    assert result.exit_code == 0
    assert "No users found." in result.output


def test_list_users_shows_accounts_and_status(runner):
    create(runner, "boss", role=AuthRole.ADMIN.value)
    create(runner, "reader")
    runner.invoke(args=["disable-user", "reader"])

    result = runner.invoke(args=["list-users"])

    assert result.exit_code == 0
    assert "USERNAME" in result.output
    assert "boss" in result.output
    assert "reader" in result.output
    assert "admin" in result.output
    assert "no" in result.output


# ----------------------------------------------------------------------
# reset-password
# ----------------------------------------------------------------------


def test_reset_password_replaces_the_hash(runner):
    create(runner, "reader")

    result = runner.invoke(
        args=["reset-password", "reader", "--password", "new-secret"]
    )

    assert result.exit_code == 0, result.output

    row = user_row("reader")
    assert check_password_hash(row["password_hash"], "new-secret")
    assert not check_password_hash(row["password_hash"], PASSWORD)


def test_reset_password_rejects_an_unknown_user(runner):
    result = runner.invoke(
        args=["reset-password", "ghost", "--password", "new-secret"]
    )

    assert result.exit_code != 0
    assert "does not exist" in result.output


def test_reset_password_rejects_an_empty_password(runner):
    create(runner, "reader")
    before = user_row("reader")["password_hash"]

    result = runner.invoke(args=["reset-password", "reader", "--password", " "])

    assert result.exit_code != 0
    assert "Password cannot be empty" in result.output
    assert user_row("reader")["password_hash"] == before


# ----------------------------------------------------------------------
# set-role
# ----------------------------------------------------------------------


def test_set_role_changes_the_role(runner):
    create(runner, "reader")

    result = runner.invoke(args=["set-role", "reader", "admin"])

    assert result.exit_code == 0, result.output
    assert user_row("reader")["role"] == AuthRole.ADMIN.value


def test_set_role_accepts_the_current_role(runner):
    create(runner, "reader")

    result = runner.invoke(args=["set-role", "reader", "user"])

    assert result.exit_code == 0
    assert "already has role" in result.output


def test_set_role_rejects_an_unknown_role(runner):
    create(runner, "reader")

    result = runner.invoke(args=["set-role", "reader", "root"])

    assert result.exit_code == 2
    assert user_row("reader")["role"] == AuthRole.USER.value


def test_set_role_rejects_an_unknown_user(runner):
    result = runner.invoke(args=["set-role", "ghost", "admin"])

    assert result.exit_code != 0
    assert "does not exist" in result.output


# ----------------------------------------------------------------------
# disable-user and enable-user
# ----------------------------------------------------------------------


def test_disable_user_blocks_the_account(runner):
    create(runner, "reader")

    result = runner.invoke(args=["disable-user", "reader"])

    assert result.exit_code == 0, result.output
    assert user_row("reader")["active"] == 0


def test_disable_user_is_idempotent(runner):
    create(runner, "reader")
    runner.invoke(args=["disable-user", "reader"])

    result = runner.invoke(args=["disable-user", "reader"])

    assert result.exit_code == 0
    assert "already disabled" in result.output


def test_enable_user_restores_the_account(runner):
    create(runner, "reader")
    runner.invoke(args=["disable-user", "reader"])

    result = runner.invoke(args=["enable-user", "reader"])

    assert result.exit_code == 0, result.output
    assert user_row("reader")["active"] == 1


def test_enable_user_is_idempotent(runner):
    create(runner, "reader")

    result = runner.invoke(args=["enable-user", "reader"])

    assert result.exit_code == 0
    assert "already enabled" in result.output


@pytest.mark.parametrize("command", ("disable-user", "enable-user"))
def test_user_state_commands_reject_an_unknown_user(runner, command):
    result = runner.invoke(args=[command, "ghost"])

    assert result.exit_code != 0
    assert "does not exist" in result.output


# ----------------------------------------------------------------------
# Administrator lock-out guard
# ----------------------------------------------------------------------


def test_cannot_disable_the_last_active_admin(runner):
    create(runner, "boss", role=AuthRole.ADMIN.value)

    result = runner.invoke(args=["disable-user", "boss"])

    assert result.exit_code != 0
    assert "last active administrator" in result.output
    assert user_row("boss")["active"] == 1


def test_cannot_demote_the_last_active_admin(runner):
    create(runner, "boss", role=AuthRole.ADMIN.value)

    result = runner.invoke(args=["set-role", "boss", "user"])

    assert result.exit_code != 0
    assert "last active administrator" in result.output
    assert user_row("boss")["role"] == AuthRole.ADMIN.value


def test_another_admin_allows_demotion(runner):
    create(runner, "boss", role=AuthRole.ADMIN.value)
    create(runner, "backup", role=AuthRole.ADMIN.value)

    result = runner.invoke(args=["set-role", "boss", "user"])

    assert result.exit_code == 0, result.output
    assert user_row("boss")["role"] == AuthRole.USER.value


def test_disabled_admin_is_not_counted_as_active(runner):
    create(runner, "boss", role=AuthRole.ADMIN.value)
    create(runner, "spare", role=AuthRole.ADMIN.value)
    runner.invoke(args=["disable-user", "spare"])

    # Only one active admin remains, so the guard applies again.
    result = runner.invoke(args=["disable-user", "boss"])

    assert result.exit_code != 0
    assert "last active administrator" in result.output
