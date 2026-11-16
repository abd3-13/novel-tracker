"""Development and administration CLI commands."""

import click
from flask import Flask
from werkzeug.security import generate_password_hash

from app.constants import AuthRole
from app.utils import db


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
        type=click.Choice([role.value for role in AuthRole]),
        default=AuthRole.USER.value,
        show_default=True,
        help="Account role.",
    )
    def create_user(username: str, password: str, email: str, role: str) -> None:
        """Create a user account."""
        username = username.strip()

        if not username:
            raise click.ClickException("Username cannot be empty.")

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
