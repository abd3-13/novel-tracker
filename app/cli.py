"""Development and administration CLI commands."""

import click
from flask import Flask
from werkzeug.security import generate_password_hash

from app.constants import AuthRole
from app.utils import db

ROLES = [role.value for role in AuthRole]


def _require_password(password: str) -> str:
    """Reject passwords that would leave an account trivially accessible."""
    if not password or not password.strip():
        raise click.ClickException("Password cannot be empty.")

    return password


def _require_user(username: str):
    """Return the user row for ``username`` or fail the command."""
    db.init_users_table()

    username = username.strip()

    if not username:
        raise click.ClickException("Username cannot be empty.")

    row = db.fetch_one(
        "SELECT id, username, email, role, active, created_at "
        "FROM users WHERE username = ?",
        (username,),
        row_factory=True,
    )

    if row is None:
        raise click.ClickException(f"User '{username}' does not exist.")

    return row


def _active_admin_count() -> int:
    row = db.fetch_one(
        "SELECT COUNT(*) FROM users WHERE role = ? AND active = 1",
        (AuthRole.ADMIN.value,),
    )
    return row[0]


def _guard_last_admin(row, action: str) -> None:
    """Refuse to lock every administrator out of the application."""
    is_admin = str(row["role"]) == AuthRole.ADMIN
    is_active = bool(row["active"])

    if is_admin and is_active and _active_admin_count() <= 1:
        raise click.ClickException(
            f"Cannot {action} the last active administrator."
        )


def _format_users(rows) -> str:
    headers = ("ID", "USERNAME", "EMAIL", "ROLE", "ACTIVE", "CREATED")
    body = [
        (
            str(row["id"]),
            row["username"],
            row["email"] or "",
            str(row["role"]),
            "yes" if row["active"] else "no",
            row["created_at"] or "",
        )
        for row in rows
    ]

    widths = [
        max(len(header), *(len(line[index]) for line in body))
        for index, header in enumerate(headers)
    ]

    lines = ["  ".join(header.ljust(width) for header, width in zip(headers, widths))]

    for line in body:
        lines.append(
            "  ".join(cell.ljust(width) for cell, width in zip(line, widths))
        )

    return "\n".join(line.rstrip() for line in lines)


def register_cli(app: Flask) -> None:
    """Register ``flask`` commands on the application."""

    @app.cli.command("init-db")
    def init_db_command() -> None:
        """Create missing tables and insert default settings."""
        db.init_db()
        db.ensure_schema()
        click.echo(f"Database initialized: {db.DEFAULT_DB}")

    @app.cli.command("create-user")
    @click.argument("username")
    @click.option(
        "--password",
        prompt=True,
        hide_input=True,
        confirmation_prompt=True,
        help="Password for the new account (prompted when omitted).",
    )
    @click.option("--email", default="", help="Optional email address.")
    @click.option(
        "--role",
        type=click.Choice(ROLES),
        default=AuthRole.USER.value,
        show_default=True,
        help="Account role.",
    )
    def create_user(username: str, password: str, email: str, role: str) -> None:
        """Create a user account."""
        username = username.strip()

        if not username:
            raise click.ClickException("Username cannot be empty.")

        _require_password(password)

        db.init_users_table()

        if db.fetch_one("SELECT id FROM users WHERE username = ?", (username,)):
            raise click.ClickException(f"User '{username}' already exists.")

        db.execute(
            "INSERT INTO users (username, email, password_hash, role, active) "
            "VALUES (?, ?, ?, ?, 1)",
            (username, email.strip(), generate_password_hash(password), role),
            commit=True,
            close=True,
        )

        click.echo(f"Created user '{username}' with role '{role}'.")

    @app.cli.command("list-users")
    def list_users() -> None:
        """List every user account."""
        db.init_users_table()

        rows = db.fetch_all(
            "SELECT id, username, email, role, active, created_at "
            "FROM users ORDER BY username",
            close=True,
            row_factory=True,
        )

        if not rows:
            click.echo("No users found.")
            return

        click.echo(_format_users(rows))

    @app.cli.command("reset-password")
    @click.argument("username")
    @click.option(
        "--password",
        prompt=True,
        hide_input=True,
        confirmation_prompt=True,
        help="New password (prompted when omitted).",
    )
    def reset_password(username: str, password: str) -> None:
        """Set a new password for an account."""
        row = _require_user(username)
        _require_password(password)

        db.execute(
            "UPDATE users SET password_hash = ? WHERE id = ?",
            (generate_password_hash(password), row["id"]),
            commit=True,
            close=True,
        )

        click.echo(f"Password updated for '{row['username']}'.")

    @app.cli.command("set-role")
    @click.argument("username")
    @click.argument("role", type=click.Choice(ROLES))
    def set_role(username: str, role: str) -> None:
        """Change an account's role."""
        row = _require_user(username)

        if str(row["role"]) == role:
            click.echo(f"'{row['username']}' already has role '{role}'.")
            return

        if role != AuthRole.ADMIN:
            _guard_last_admin(row, "demote")

        db.execute(
            "UPDATE users SET role = ? WHERE id = ?",
            (role, row["id"]),
            commit=True,
            close=True,
        )

        click.echo(f"Changed role for '{row['username']}' to '{role}'.")

    @app.cli.command("disable-user")
    @click.argument("username")
    def disable_user(username: str) -> None:
        """Disable an account so it cannot sign in."""
        row = _require_user(username)

        if not row["active"]:
            click.echo(f"'{row['username']}' is already disabled.")
            return

        _guard_last_admin(row, "disable")

        db.execute(
            "UPDATE users SET active = 0 WHERE id = ?",
            (row["id"],),
            commit=True,
            close=True,
        )

        click.echo(f"Disabled user '{row['username']}'.")

    @app.cli.command("enable-user")
    @click.argument("username")
    def enable_user(username: str) -> None:
        """Re-enable a disabled account."""
        row = _require_user(username)

        if row["active"]:
            click.echo(f"'{row['username']}' is already enabled.")
            return

        db.execute(
            "UPDATE users SET active = 1 WHERE id = ?",
            (row["id"],),
            commit=True,
            close=True,
        )

        click.echo(f"Enabled user '{row['username']}'.")
