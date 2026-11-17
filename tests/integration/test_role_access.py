"""Role-based access checks against a temporary database."""

import pytest
from werkzeug.security import generate_password_hash

from app import create_app
from app.utils import db

pytestmark = pytest.mark.integration

PASSWORD = "secret"


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setattr(db, "DEFAULT_DB", str(tmp_path / "roles.db"))

    app = create_app()
    app.config.update(TESTING=True)

    for username, role in (
        ("boss", "admin"),
        ("reader", "user"),
        ("guest", "demo"),
    ):
        db.execute(
            "INSERT INTO users (username, password_hash, role, active) "
            "VALUES (?, ?, ?, 1)",
            (username, generate_password_hash(PASSWORD), role),
            commit=True,
            close=True,
        )

    db.insert_novel(
        {
            "name": "Visible",
            "filepath": "Visible.epub",
            "epub_exists": 1,
        }
    )

    with app.test_client() as test_client:
        yield test_client


def login(client, username):
    client.get("/login")

    with client.session_transaction() as session:
        token = session["_csrf_token"]

    response = client.post(
        "/login",
        data={
            "username": username,
            "password": PASSWORD,
            "csrf_token": token,
        },
    )

    assert response.status_code == 200

    with client.session_transaction() as session:
        return session["_csrf_token"]


def test_demo_account_is_read_only(client):
    token = login(client, "guest")
    headers = {"X-CSRFToken": token}

    library = client.get("/api/v1/library").get_json()["data"]
    assert library[0]["permissions"] == {
        "can_read": True,
        "can_update": False,
        "can_edit": False,
        "can_delete": False,
        "can_sync": False,
        "can_import": False,
    }

    novel_id = library[0]["id"]

    assert client.patch(
        f"/api/v1/library/{novel_id}",
        json={"name": "Nope"},
        headers=headers,
    ).status_code == 403
    assert client.delete(
        f"/api/v1/library/{novel_id}", headers=headers
    ).status_code == 403
    assert client.post(
        "/api/v1/import/scan", json={}, headers=headers
    ).status_code == 403
    assert client.post(
        "/api/v1/sync", json={}, headers=headers
    ).status_code == 403

    assert db.get_novel(novel_id)["name"] == "Visible"


def test_regular_user_can_edit_but_not_delete_or_sync(client):
    token = login(client, "reader")
    headers = {"X-CSRFToken": token}

    library = client.get("/api/v1/library").get_json()["data"]
    novel_id = library[0]["id"]
    permissions = library[0]["permissions"]

    assert permissions["can_edit"] is True
    assert permissions["can_delete"] is False
    assert permissions["can_sync"] is False

    response = client.patch(
        f"/api/v1/library/{novel_id}",
        json={"name": "Renamed"},
        headers=headers,
    )

    assert response.status_code == 200
    assert db.get_novel(novel_id)["name"] == "Renamed"

    assert client.delete(
        f"/api/v1/library/{novel_id}", headers=headers
    ).status_code == 403
    assert client.delete(
        "/api/v1/library/missing-epub", headers=headers
    ).status_code == 403
    assert client.post(
        "/api/v1/sync", json={"novels": [novel_id]}, headers=headers
    ).status_code == 403
    assert db.get_novel(novel_id) is not None


def test_admin_can_delete_and_start_sync(client):
    token = login(client, "boss")
    headers = {"X-CSRFToken": token}

    library = client.get("/api/v1/library").get_json()["data"]
    novel_id = library[0]["id"]

    assert library[0]["permissions"]["can_delete"] is True
    assert library[0]["permissions"]["can_sync"] is True

    assert client.delete(
        "/api/v1/library/missing-epub", headers=headers
    ).status_code == 200

    response = client.post(
        "/api/v1/sync",
        json={"novels": [], "fields": []},
        headers=headers,
    )
    assert response.status_code == 202

    assert client.delete(
        f"/api/v1/library/{novel_id}", headers=headers
    ).status_code == 200
    assert db.get_novel(novel_id) is None
