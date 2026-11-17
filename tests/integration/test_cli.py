"""Coverage for the account administration CLI commands."""

import sqlite3

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


# ----------------------------------------------------------------------
# Database maintenance
# ----------------------------------------------------------------------


def add_novel(table="novels", **values):
    values.setdefault("name", "Book")
    values.setdefault("filepath", "Book.epub")

    db.insert_novel(values, table=table)

    return db.fetch_one(
        f"SELECT id FROM {table} WHERE name = ?", (values["name"],)
    )[0]


def test_backup_db_writes_a_readable_snapshot(runner, tmp_path):
    add_novel(name="Kept")

    destination = tmp_path / "snapshot.db"
    result = runner.invoke(args=["backup-db", "--output", str(destination)])

    assert result.exit_code == 0, result.output
    assert str(destination) in result.output

    copy = sqlite3.connect(destination)
    try:
        rows = copy.execute("SELECT name FROM novels").fetchall()
    finally:
        copy.close()

    assert rows == [("Kept",)]


def test_backup_db_defaults_to_the_backups_directory(runner, tmp_path):
    result = runner.invoke(args=["backup-db"])

    assert result.exit_code == 0, result.output

    snapshots = list((tmp_path / "backups").glob("cli-*.db"))
    assert len(snapshots) == 1


def test_backup_db_refuses_to_overwrite(runner, tmp_path):
    destination = tmp_path / "snapshot.db"
    destination.write_bytes(b"existing")

    result = runner.invoke(args=["backup-db", "--output", str(destination)])

    assert result.exit_code != 0
    assert "Refusing to overwrite" in result.output
    assert destination.read_bytes() == b"existing"


def test_backup_db_requires_an_existing_database(runner, monkeypatch, tmp_path):
    monkeypatch.setattr(db, "DEFAULT_DB", str(tmp_path / "missing.db"))

    result = runner.invoke(args=["backup-db"])

    assert result.exit_code != 0
    assert "Database not found" in result.output


def test_integrity_check_passes_on_a_healthy_database(runner):
    result = runner.invoke(args=["integrity-check"])

    assert result.exit_code == 0, result.output
    assert "Integrity check passed" in result.output


def test_integrity_check_fails_on_a_corrupt_file(runner, monkeypatch, tmp_path):
    corrupt = tmp_path / "corrupt.db"
    corrupt.write_bytes(b"this is not a sqlite database")
    monkeypatch.setattr(db, "DEFAULT_DB", str(corrupt))

    result = runner.invoke(args=["integrity-check"])

    assert result.exit_code != 0
    assert "Integrity check failed" in result.output


def test_integrity_check_requires_an_existing_database(
    runner, monkeypatch, tmp_path
):
    monkeypatch.setattr(db, "DEFAULT_DB", str(tmp_path / "missing.db"))

    result = runner.invoke(args=["integrity-check"])

    assert result.exit_code != 0
    assert "Database not found" in result.output


def test_restore_novel_brings_back_a_deleted_row(runner):
    novel_id = add_novel(name="Comeback")
    db.soft_delete_novels(novel_id)
    assert db.get_novel(novel_id) is None

    result = runner.invoke(args=["restore-novel", str(novel_id)])

    assert result.exit_code == 0, result.output
    assert db.get_novel(novel_id)["name"] == "Comeback"


def test_restore_novel_rejects_a_row_that_is_not_deleted(runner):
    novel_id = add_novel(name="Active")

    result = runner.invoke(args=["restore-novel", str(novel_id)])

    assert result.exit_code != 0
    assert "is not deleted" in result.output


def test_restore_novel_rejects_an_unknown_id(runner):
    result = runner.invoke(args=["restore-novel", "999999"])

    assert result.exit_code != 0
    assert "is not deleted" in result.output


def test_restore_novel_supports_the_demo_table(runner):
    novel_id = add_novel(table="demo_novels", name="Demo Book")
    db.soft_delete_novels(novel_id, table="demo_novels")

    result = runner.invoke(
        args=["restore-novel", str(novel_id), "--table", "demo_novels"]
    )

    assert result.exit_code == 0, result.output
    assert db.get_novel(novel_id, table="demo_novels") is not None


def test_list_deleted_novels_reports_an_empty_table(runner):
    result = runner.invoke(args=["list-deleted-novels"])

    assert result.exit_code == 0
    assert "No deleted novels." in result.output


def test_list_deleted_novels_shows_ids_and_titles(runner):
    novel_id = add_novel(name="Hidden")
    add_novel(name="Visible")
    db.soft_delete_novels(novel_id)

    result = runner.invoke(args=["list-deleted-novels"])

    assert result.exit_code == 0
    assert "Hidden" in result.output
    assert str(novel_id) in result.output
    assert "Visible" not in result.output


def test_backup_db_reports_a_corrupt_source(runner, monkeypatch, tmp_path):
    corrupt = tmp_path / "corrupt.db"
    corrupt.write_bytes(b"this is not a sqlite database")
    monkeypatch.setattr(db, "DEFAULT_DB", str(corrupt))

    result = runner.invoke(args=["backup-db"])

    assert result.exit_code != 0
    assert "Backup failed" in result.output


def test_a_corrupt_database_still_allows_maintenance_commands(
    monkeypatch, tmp_path
):
    corrupt = tmp_path / "corrupt.db"
    corrupt.write_bytes(b"this is not a sqlite database")
    monkeypatch.setattr(db, "DEFAULT_DB", str(corrupt))

    application = create_app()
    application.config.update(TESTING=True)

    try:
        assert isinstance(
            application.extensions["db_init_error"], sqlite3.DatabaseError
        )

        result = application.test_cli_runner().invoke(args=["integrity-check"])

        assert result.exit_code != 0
        assert "Integrity check failed" in result.output
    finally:
        application.extensions["sync_manager"].executor.shutdown(wait=True)
