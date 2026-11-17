"""End-to-end coverage for the HTTP layer.

These tests drive the real Flask application against a temporary database so
they exercise routing, CSRF, authentication, validation, and response shapes
together, the way a browser does.
"""

import json
import re

import pytest
from werkzeug.security import generate_password_hash

from app import create_app
from app.constants import AuthRole, SettingKey
from app.utils import db

from tests.support.wait import wait_for

pytestmark = pytest.mark.integration

PASSWORD = "secret"
PASSWORD_HASH = generate_password_hash(PASSWORD, method="pbkdf2:sha256:1000")


@pytest.fixture
def app(monkeypatch, tmp_path):
    monkeypatch.setattr(db, "DEFAULT_DB", str(tmp_path / "web.db"))

    application = create_app()
    application.config.update(TESTING=True)

    for username, role, active in (
        ("boss", AuthRole.ADMIN, 1),
        ("reader", AuthRole.USER, 1),
        ("demo", AuthRole.DEMO, 1),
        ("disabled", AuthRole.USER, 0),
    ):
        db.execute(
            "INSERT INTO users (username, password_hash, role, active) "
            "VALUES (?, ?, ?, ?)",
            (username, PASSWORD_HASH, role, active),
            commit=True,
            close=True,
        )

    yield application

    application.extensions["sync_manager"].executor.shutdown(wait=True)


@pytest.fixture
def client(app):
    with app.test_client() as test_client:
        yield test_client


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------


def csrf_token(client):
    client.get("/login")

    with client.session_transaction() as session:
        return session["_csrf_token"]


def login(client, username="reader", password=PASSWORD, next_url=None):
    token = csrf_token(client)
    data = {
        "username": username,
        "password": password,
        "csrf_token": token,
    }

    if next_url is not None:
        data["next"] = next_url

    return client.post("/login", data=data)


def login_ok(client, username="reader"):
    response = login(client, username)
    assert response.status_code == 200

    body = response.get_json()
    assert body["success"] is True

    return body


def add_novel(table="novels", **values):
    values.setdefault("name", "Book")
    values.setdefault("filepath", "Book.epub")
    values.setdefault("epub_exists", 1)

    db.insert_novel(values, table=table)

    row = db.fetch_one(
        f"SELECT id FROM {table} WHERE name = ?", (values["name"],)
    )
    return row[0]


def set_epub_dir(path):
    db.save_setting(SettingKey.LOCAL_EPUB_DIR, str(path))


# ----------------------------------------------------------------------
# Authentication
# ----------------------------------------------------------------------


def test_login_form_carries_a_csrf_token(client):
    html = client.get("/login").get_data(as_text=True)

    match = re.search(r'name="csrf_token" value="([^"]+)"', html)
    assert match is not None

    with client.session_transaction() as session:
        assert session["_csrf_token"] == match.group(1)


def test_form_login_works_without_javascript(client):
    html = client.get("/login").get_data(as_text=True)
    token = re.search(r'name="csrf_token" value="([^"]+)"', html).group(1)

    response = client.post(
        "/login",
        data={
            "username": "reader",
            "password": PASSWORD,
            "csrf_token": token,
        },
    )

    assert response.status_code == 200

    body = response.get_json()
    assert body["success"] is True
    assert body["redirect"] == "/"


def test_login_rejects_wrong_password(client):
    response = login(client, password="wrong")

    assert response.status_code == 401
    assert response.get_json()["message"] == "Invalid username or password."


def test_login_rejects_disabled_account(client):
    response = login(client, "disabled")

    assert response.status_code == 403
    assert response.get_json()["message"] == "Your account has been disabled."


@pytest.mark.parametrize(
    ("target", "expected"),
    (
        ("https://evil.test/steal", "/"),
        ("//evil.test/steal", "/"),
        ("/\\evil.test/steal", "/"),
        ("/api/v1/library", "/api/v1/library"),
        ("", "/"),
    ),
)
def test_login_redirect_is_same_origin(client, target, expected):
    login_ok(client)

    token = csrf_token(client)
    response = client.post(
        "/login",
        data={
            "username": "reader",
            "password": PASSWORD,
            "csrf_token": token,
            "next": target,
        },
    )

    assert response.status_code == 200
    assert response.get_json()["redirect"] == expected


def test_authenticated_login_page_redirects_to_library(client):
    login_ok(client)

    response = client.get("/login")

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/")


def test_logout_clears_the_session(client):
    login_ok(client)

    response = client.get("/logout")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]

    assert client.get("/api/v1/library").status_code == 302


def test_protected_page_redirects_to_login(client):
    response = client.get("/")

    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_status_endpoint_is_public(client):
    response = client.get("/status")

    assert response.status_code == 200
    assert response.get_data() == b""


# ----------------------------------------------------------------------
# CSRF and response headers
# ----------------------------------------------------------------------


def test_unsafe_request_without_csrf_is_rejected(client):
    login_ok(client, "boss")

    response = client.post(
        "/api/v1/settings", json={"key": "USER_AGENT", "value": "agent"}
    )

    assert response.status_code == 400
    assert "CSRF" in response.get_json()["message"]


def test_unsafe_request_with_wrong_csrf_is_rejected(client):
    login_ok(client, "boss")

    response = client.post(
        "/api/v1/settings",
        json={"key": "USER_AGENT", "value": "agent"},
        headers={"X-CSRFToken": "not-the-token"},
    )

    assert response.status_code == 400


def test_csrf_token_is_accepted_in_the_json_body(client):
    login_ok(client, "boss")
    token = csrf_token(client)

    response = client.post(
        "/api/v1/settings",
        json={
            "csrf_token": token,
            "key": "USER_AGENT",
            "value": "agent",
        },
    )

    assert response.status_code == 200
    assert response.get_json()["success"] is True


@pytest.mark.parametrize("path", ("/status", "/does-not-exist"))
def test_security_headers_are_always_set(client, path):
    response = client.get(path)

    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "SAMEORIGIN"
    assert response.headers["Referrer-Policy"] == "same-origin"


# ----------------------------------------------------------------------
# Library API
# ----------------------------------------------------------------------


def test_library_shapes_a_novel(client):
    add_novel(
        name="Visible",
        filepath="Visible.epub",
        author="A. Writer",
        description="Description",
        tags="fantasy",
        cover_path="cover.webp",
        localchap=10,
        onlinechap=12,
        characters=3,
        online_characters=5,
        progress=7,
        local_lastchaptitle="Chapter 10",
        local_lastchapfile="chapter10.xhtml",
        discord_channel_url="https://discord.test/invite",
    )

    login_ok(client)

    data = client.get("/api/v1/library").get_json()["data"]

    assert len(data) == 1
    novel = data[0]

    assert novel["title"] == "Visible"
    assert novel["cover"] == {"url": "cover.webp", "exists": True}
    assert novel["author"] == "A. Writer"
    assert novel["tags"] == "fantasy"
    assert novel["chapters"] == {
        "local": 10,
        "online": 12,
        "diff": 2,
        "latest_title": "Chapter 10",
        "last_online_update": None,
        "last_sync": None,
    }
    assert novel["reading"] == {"chapter": 7, "unread": 3, "percent": 70.0}
    assert novel["characters"] == {"local": 3, "online": 5, "new": 2}
    assert novel["epub"] == {
        "exists": True,
        "path": "Visible.epub",
        "last_file": "chapter10.xhtml",
    }
    assert novel["state"] == {
        "needs_update": True,
        "missing_epub": False,
        "new_characters": True,
        "sync": "online_ahead",
    }
    assert novel["permissions"] == {
        "can_read": True,
        "can_update": True,
        "can_edit": True,
        "can_delete": False,
        "can_sync": False,
        "can_import": False,
    }
    assert novel["discord_channel_url"] == "https://discord.test/invite"


def test_library_hides_soft_deleted_novels(client):
    add_novel(name="Gone", is_deleted=1)

    login_ok(client, "boss")

    assert client.get("/api/v1/library").get_json()["data"] == []


def test_library_hides_nsfw_from_regular_users(client):
    safe_id = add_novel(name="Safe")
    nsfw_id = add_novel(name="Secret", tags="NSFW")

    login_ok(client)

    library = client.get("/api/v1/library").get_json()["data"]

    assert [novel["id"] for novel in library] == [safe_id]
    assert client.get(f"/api/v1/library/{nsfw_id}").status_code == 404

    client.get("/logout")
    login_ok(client, "boss")

    library = client.get("/api/v1/library").get_json()["data"]

    assert {novel["id"] for novel in library} == {safe_id, nsfw_id}
    assert client.get(f"/api/v1/library/{nsfw_id}").status_code == 200


def test_library_novel_missing_returns_404(client):
    login_ok(client)

    response = client.get("/api/v1/library/999999")

    assert response.status_code == 404
    assert response.get_json()["success"] is False


def test_patch_requires_a_json_object(client):
    novel_id = add_novel()
    login_ok(client)

    response = client.patch(
        f"/api/v1/library/{novel_id}",
        json=[],
        headers={"X-CSRFToken": csrf_token(client)},
    )

    assert response.status_code == 400
    assert "JSON object" in response.get_json()["message"]


@pytest.mark.parametrize(
    ("payload", "message"),
    (
        ({"localchap": -1}, "cannot be negative"),
        ({"localchap": "abc"}, "must be a number"),
        ({"localchap": True}, "must be a number"),
        ({"epub_exists": "sometimes"}, "must be a boolean"),
        ({"name": "   "}, "cannot be empty"),
        ({"author": 5}, "must be a string"),
    ),
)
def test_patch_validates_values(client, payload, message):
    novel_id = add_novel()
    login_ok(client)

    response = client.patch(
        f"/api/v1/library/{novel_id}",
        json=payload,
        headers={"X-CSRFToken": csrf_token(client)},
    )

    assert response.status_code == 400
    assert message in response.get_json()["message"]


def test_patch_rejects_payload_without_editable_fields(client):
    novel_id = add_novel()
    login_ok(client)

    response = client.patch(
        f"/api/v1/library/{novel_id}",
        json={"unknown": "value"},
        headers={"X-CSRFToken": csrf_token(client)},
    )

    assert response.status_code == 400
    assert "No editable fields" in response.get_json()["message"]


def test_patch_updates_and_returns_the_novel(client):
    novel_id = add_novel(name="Before")
    login_ok(client)

    response = client.patch(
        f"/api/v1/library/{novel_id}",
        json={"name": "After", "localchap": "4", "notes": "note"},
        headers={"X-CSRFToken": csrf_token(client)},
    )

    assert response.status_code == 200

    data = response.get_json()["data"]
    assert data["name"] == "After"
    assert data["localchap"] == 4
    assert data["notes"] == "note"


def test_delete_removes_the_novel_for_an_admin(client):
    novel_id = add_novel()
    login_ok(client, "boss")

    response = client.delete(
        f"/api/v1/library/{novel_id}",
        headers={"X-CSRFToken": csrf_token(client)},
    )

    assert response.status_code == 200
    assert db.get_novel(novel_id) is None


def test_missing_epub_cleanup_flags_rows(client):
    novel_id = add_novel(name="Missing", filepath="gone.epub", epub_exists=0)
    login_ok(client, "boss")

    response = client.delete(
        "/api/v1/library/missing-epub",
        headers={"X-CSRFToken": csrf_token(client)},
    )

    assert response.status_code == 200
    assert response.get_json()["data"]["deleted"] == 1

    row = db.fetch_one(
        "SELECT is_deleted FROM novels WHERE id = ?", (novel_id,)
    )
    assert row[0] == 1
    assert client.get("/api/v1/library").get_json()["data"] == []


def test_missing_epub_cleanup_reports_when_nothing_matches(client):
    login_ok(client, "boss")

    response = client.delete(
        "/api/v1/library/missing-epub",
        headers={"X-CSRFToken": csrf_token(client)},
    )

    assert response.status_code == 200
    assert response.get_json()["data"]["deleted"] == 0
    assert "No missing EPUB" in response.get_json()["message"]


# ----------------------------------------------------------------------
# Settings API
# ----------------------------------------------------------------------


def test_settings_hide_sensitive_values(client):
    db.save_setting(SettingKey.SECRETS_KEY, "top-secret")
    db.save_setting(SettingKey.USER_AGENT, "agent")

    login_ok(client)

    payload = client.get("/api/v1/settings").get_json()

    assert SettingKey.SECRETS_KEY.value not in payload["data"]
    assert "top-secret" not in json.dumps(payload)
    assert payload["data"][SettingKey.USER_AGENT.value] == "agent"

    html = client.get("/").get_data(as_text=True)
    assert "top-secret" not in html
    assert "agent" in html


def test_settings_reject_non_object_body(client):
    login_ok(client, "boss")

    response = client.post(
        "/api/v1/settings",
        json=[],
        headers={"X-CSRFToken": csrf_token(client)},
    )

    assert response.status_code == 400
    assert "JSON object" in response.get_json()["message"]


def test_settings_require_a_key(client):
    login_ok(client, "boss")

    response = client.post(
        "/api/v1/settings",
        json={"value": "x"},
        headers={"X-CSRFToken": csrf_token(client)},
    )

    assert response.status_code == 400
    assert "key is required" in response.get_json()["message"]


def test_settings_reject_unknown_key(client):
    login_ok(client, "boss")

    response = client.post(
        "/api/v1/settings",
        json={"key": "NOT_A_SETTING", "value": "x"},
        headers={"X-CSRFToken": csrf_token(client)},
    )

    assert response.status_code == 400
    assert "Unknown setting" in response.get_json()["message"]


def test_settings_reject_readonly_key(client):
    login_ok(client, "boss")

    response = client.post(
        "/api/v1/settings",
        json={"key": SettingKey.LAST_BULK_TIME.value, "value": "now"},
        headers={"X-CSRFToken": csrf_token(client)},
    )

    assert response.status_code == 400
    assert "read-only" in response.get_json()["message"]


def test_settings_require_admin(client):
    login_ok(client)

    response = client.post(
        "/api/v1/settings",
        json={"key": SettingKey.USER_AGENT.value, "value": "agent"},
        headers={"X-CSRFToken": csrf_token(client)},
    )

    assert response.status_code == 403


@pytest.mark.parametrize(
    ("key", "value", "stored"),
    (
        (SettingKey.DELAY_FROM.value, "5", "5"),
        (SettingKey.CHECK_ERROR_LINK.value, True, "1"),
        (SettingKey.UPDATE_LOCAL_ONLINE.value, "online", "online"),
    ),
)
def test_settings_normalize_values(client, key, value, stored):
    login_ok(client, "boss")

    response = client.post(
        "/api/v1/settings",
        json={"key": key, "value": value},
        headers={"X-CSRFToken": csrf_token(client)},
    )

    assert response.status_code == 200
    assert response.get_json()["data"][key] == stored
    assert db.get_value(key) == stored


@pytest.mark.parametrize("value", ("abc", "-1", "301"))
def test_settings_validate_number_bounds(client, value):
    login_ok(client, "boss")

    response = client.post(
        "/api/v1/settings",
        json={"key": SettingKey.DELAY_FROM.value, "value": value},
        headers={"X-CSRFToken": csrf_token(client)},
    )

    assert response.status_code == 400


@pytest.mark.parametrize(
    ("key", "value"),
    (
        (SettingKey.CHECK_ERROR_LINK.value, "maybe"),
        (SettingKey.UPDATE_LOCAL_ONLINE.value, "both"),
    ),
)
def test_settings_reject_invalid_typed_values(client, key, value):
    login_ok(client, "boss")

    response = client.post(
        "/api/v1/settings",
        json={"key": key, "value": value},
        headers={"X-CSRFToken": csrf_token(client)},
    )

    assert response.status_code == 400


# ----------------------------------------------------------------------
# Synchronization API
# ----------------------------------------------------------------------


def test_sync_registry_requires_login(client):
    assert client.get("/api/v1/sync/registry").status_code == 302


def test_sync_registry_lists_enabled_fields(client):
    login_ok(client)

    fields = client.get("/api/v1/sync/registry").get_json()

    assert fields
    assert all({"id", "name"} <= set(field) for field in fields)


def test_sync_rejects_non_object_payload(client):
    login_ok(client, "boss")

    response = client.post(
        "/api/v1/sync",
        json=[],
        headers={"X-CSRFToken": csrf_token(client)},
    )

    assert response.status_code == 400
    assert "object" in response.get_json()["message"]


def test_sync_rejects_unknown_source(client):
    login_ok(client, "boss")

    response = client.post(
        "/api/v1/sync",
        json={"source": "not-a-source"},
        headers={"X-CSRFToken": csrf_token(client)},
    )

    assert response.status_code == 400
    assert "Invalid sync source" in response.get_json()["message"]


def test_sync_start_and_status(client, app):
    login_ok(client, "boss")

    response = client.post(
        "/api/v1/sync",
        json={"novels": [999999], "fields": [], "dry_run": True},
        headers={"X-CSRFToken": csrf_token(client)},
    )

    assert response.status_code == 202
    job_id = response.get_json()["job_id"]

    manager = app.extensions["sync_manager"]
    execution = manager.get(job_id)
    assert execution is not None

    wait_for(lambda: execution.done)

    status = client.get(f"/api/v1/sync/{job_id}")
    assert status.status_code == 200

    snapshot = status.get_json()["execution"]
    assert snapshot["status"] == "finished"
    assert snapshot["result"]["summary"]["total"] == 0


def test_sync_status_unknown_job(client):
    login_ok(client)

    assert client.get("/api/v1/sync/does-not-exist").status_code == 404


def test_sync_cancel_unknown_job(client):
    login_ok(client, "boss")

    response = client.post(
        "/api/v1/sync/does-not-exist/cancel",
        headers={"X-CSRFToken": csrf_token(client)},
    )

    assert response.status_code == 404


# ----------------------------------------------------------------------
# EPUB serving
# ----------------------------------------------------------------------


def test_epub_requires_login(client):
    assert client.get("/api/v1/epub/1").status_code == 302


def test_epub_serves_the_configured_file(client, tmp_path):
    epub_dir = tmp_path / "books"
    epub_dir.mkdir()
    (epub_dir / "Book.epub").write_bytes(b"PK-test")

    set_epub_dir(epub_dir)
    novel_id = add_novel(name="Book", filepath="Book.epub")
    login_ok(client)

    response = client.get(f"/api/v1/epub/{novel_id}")

    assert response.status_code == 200
    assert response.get_data() == b"PK-test"
    assert response.headers["Content-Type"] == "application/epub+zip"
    assert "no-store" in response.headers["Cache-Control"]


def test_epub_missing_file_returns_json_404(client, tmp_path):
    set_epub_dir(tmp_path)
    novel_id = add_novel(name="Book", filepath="Missing.epub")
    login_ok(client)

    response = client.get(f"/api/v1/epub/{novel_id}")

    assert response.status_code == 404
    assert response.is_json
    assert response.get_json()["message"] == "EPUB file was not found."


def test_epub_rejects_path_traversal(client, tmp_path):
    epub_dir = tmp_path / "books"
    epub_dir.mkdir()
    (tmp_path / "secret.epub").write_bytes(b"secret")

    set_epub_dir(epub_dir)
    novel_id = add_novel(name="Book", filepath="../secret.epub")
    login_ok(client)

    response = client.get(f"/api/v1/epub/{novel_id}")

    assert response.status_code == 404
    assert response.is_json
    assert b"secret" not in response.get_data()


def test_epub_requires_a_filepath(client):
    novel_id = add_novel(name="Book", filepath=None)
    login_ok(client)

    response = client.get(f"/api/v1/epub/{novel_id}")

    assert response.status_code == 404
    assert "not configured" in response.get_json()["message"]


def test_epub_hides_nsfw_from_regular_users(client, tmp_path):
    set_epub_dir(tmp_path)
    novel_id = add_novel(name="Secret", tags="NSFW")
    login_ok(client)

    assert client.get(f"/api/v1/epub/{novel_id}").status_code == 404


# ----------------------------------------------------------------------
# Import API
# ----------------------------------------------------------------------


@pytest.mark.parametrize("path", ("/api/v1/import", "/api/v1/import/events"))
def test_import_rejects_non_object_body(client, path):
    login_ok(client, "boss")

    response = client.post(
        path,
        json=[],
        headers={"X-CSRFToken": csrf_token(client)},
    )

    assert response.status_code == 400
    assert "JSON object" in response.get_json()["message"]


@pytest.mark.parametrize("filenames", ([], [""], [1]))
def test_import_requires_valid_filenames(client, filenames):
    login_ok(client, "boss")

    response = client.post(
        "/api/v1/import",
        json={"filenames": filenames},
        headers={"X-CSRFToken": csrf_token(client)},
    )

    assert response.status_code == 400


def test_import_reports_a_missing_file(client, tmp_path):
    set_epub_dir(tmp_path)
    login_ok(client, "boss")

    response = client.post(
        "/api/v1/import",
        json={"filenames": ["missing.epub"]},
        headers={"X-CSRFToken": csrf_token(client)},
    )

    assert response.status_code == 200

    body = response.get_json()
    assert body["success"] is True
    assert body["summary"]["failed"] == 1
    assert body["results"][0]["status"] == "failed"


def test_import_rejects_traversal_filename(client, tmp_path):
    set_epub_dir(tmp_path)
    login_ok(client, "boss")

    response = client.post(
        "/api/v1/import",
        json={"filenames": ["../outside.epub"]},
        headers={"X-CSRFToken": csrf_token(client)},
    )

    assert response.status_code == 200

    body = response.get_json()
    assert body["summary"]["failed"] == 1
    assert "Invalid EPUB filename" in body["results"][0]["reason"]
    assert client.get("/api/v1/library").get_json()["data"] == []


def test_scan_events_reports_a_missing_directory(client, tmp_path):
    set_epub_dir(tmp_path / "does-not-exist")
    login_ok(client, "boss")

    response = client.get("/api/v1/import/scan/events")

    assert response.status_code == 200
    assert response.mimetype == "text/event-stream"

    body = response.get_data(as_text=True)
    assert "event: scan_error" in body
    assert "Local EPUB directory not found" in body


def test_scan_events_streams_progress_and_done(client, tmp_path):
    (tmp_path / "broken.epub").write_bytes(b"not really an epub")

    set_epub_dir(tmp_path)
    login_ok(client, "boss")

    response = client.get("/api/v1/import/scan/events")

    assert response.status_code == 200

    body = response.get_data(as_text=True)
    assert "event: progress" in body
    assert "event: done" in body
    assert "candidates" in body


def test_import_cover_validates_the_filename(client, tmp_path):
    set_epub_dir(tmp_path)
    login_ok(client, "boss")

    assert (
        client.get("/api/v1/import/cover?filename=../book.epub").status_code
        == 400
    )
    assert (
        client.get("/api/v1/import/cover?filename=book.txt").status_code == 400
    )


def test_import_cover_missing_file_returns_404(client, tmp_path):
    set_epub_dir(tmp_path)
    login_ok(client, "boss")

    assert (
        client.get("/api/v1/import/cover?filename=missing.epub").status_code
        == 404
    )


def test_import_endpoints_are_forbidden_for_regular_users(client, tmp_path):
    set_epub_dir(tmp_path)
    login_ok(client)

    response = client.post(
        "/api/v1/import",
        json={"filenames": ["book.epub"]},
        headers={"X-CSRFToken": csrf_token(client)},
    )
    assert response.status_code == 403

    assert client.get("/api/v1/import/scan/events").status_code == 403
    assert (
        client.get("/api/v1/import/cover?filename=book.epub").status_code == 403
    )


def test_sync_events_unknown_job(client):
    login_ok(client)

    assert client.get("/api/v1/sync/does-not-exist/events").status_code == 404


def test_sync_events_stream_the_final_snapshot(client, app):
    login_ok(client, "boss")

    response = client.post(
        "/api/v1/sync",
        json={"novels": [999999], "fields": [], "dry_run": True},
        headers={"X-CSRFToken": csrf_token(client)},
    )
    job_id = response.get_json()["job_id"]

    execution = app.extensions["sync_manager"].get(job_id)
    wait_for(lambda: execution.done)

    stream = client.get(f"/api/v1/sync/{job_id}/events")

    assert stream.status_code == 200
    assert stream.mimetype == "text/event-stream"

    body = stream.get_data(as_text=True)
    assert "event: done" in body
    assert '"status": "finished"' in body


def test_import_events_stream_ndjson(client, tmp_path):
    set_epub_dir(tmp_path)
    login_ok(client, "boss")

    response = client.post(
        "/api/v1/import/events",
        json={"filenames": ["missing.epub"]},
        headers={"X-CSRFToken": csrf_token(client)},
    )

    assert response.status_code == 200
    assert response.mimetype == "application/x-ndjson"

    events = [
        json.loads(line)
        for line in response.get_data(as_text=True).splitlines()
        if line.strip()
    ]

    assert [event["event"] for event in events][-2:] == ["file_done", "done"]
    assert events[-2]["data"]["status"] == "failed"
