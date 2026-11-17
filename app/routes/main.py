import json
import logging
from queue import Empty

from flask import (
    Blueprint,
    Response,
    current_app,
    jsonify,
    make_response,
    render_template,
    request,
    send_from_directory,
    stream_with_context,
)
from flask_login import current_user, login_required

from app.auth import admin_required, editor_required
from app.constants import (
    SENSITIVE_SETTING_KEYS,
    SETTING_METADATA,
    AuthRole,
    DatabaseColumn,
)
from app.sync.job import SyncJob
from app.sync.metadata import FIELDS
from app.utils import db
from app.utils.filters import log_SpamFilter

main_bp = Blueprint("main", __name__)


def public_settings():
    """Settings safe to render in pages and API responses."""
    return {
        key: value
        for key, value in db.get_settings_dict().items()
        if key not in SENSITIVE_SETTING_KEYS
    }


NOVEL_EDITABLE_FIELDS = {
    "name",
    "url",
    "localchap",
    "onlinechap",
    "latestchaptime",
    "status",
    "source",
    "notes",
    "filepath",
    "author",
    "description",
    "tags",
    "characters",
    "online_characters",
    "cover_path",
    "local_lastchaptitle",
    "local_lastchapfile",
    "progress",
    "progress_updated",
    "epub_exists",
    "discord_channel_url",
}

NOVEL_INTEGER_FIELDS = {
    "localchap",
    "onlinechap",
    "characters",
    "online_characters",
    "progress",
}

NOVEL_BOOLEAN_FIELDS = {"epub_exists"}


def validate_novel_updates(payload):
    """
    Validate and coerce editable novel fields from a PATCH payload.

    Unknown keys are ignored for compatibility, but known keys must have the
    type the database expects. Raises ValueError with a user-facing message.
    """
    updates = {}

    for key, value in payload.items():
        if key not in NOVEL_EDITABLE_FIELDS:
            continue

        if key in NOVEL_INTEGER_FIELDS:
            if isinstance(value, bool):
                raise ValueError(f"'{key}' must be a number.")

            try:
                number = int(value)
            except (TypeError, ValueError):
                raise ValueError(f"'{key}' must be a number.") from None

            if number < 0:
                raise ValueError(f"'{key}' cannot be negative.")

            updates[key] = number
            continue

        if key in NOVEL_BOOLEAN_FIELDS:
            if isinstance(value, bool):
                updates[key] = int(value)
            elif value in (0, 1, "0", "1"):
                updates[key] = int(value)
            else:
                raise ValueError(f"'{key}' must be a boolean.")
            continue

        if value is not None and not isinstance(value, str):
            raise ValueError(f"'{key}' must be a string.")

        if key == "name" and (value is None or not value.strip()):
            raise ValueError("'name' cannot be empty.")

        updates[key] = value

    return updates


def build_library_novel(row, role=AuthRole.USER):
    """Shape one database row for the library API, including permissions."""
    can_edit = str(role) in {AuthRole.ADMIN, AuthRole.USER}
    can_admin = str(role) == AuthRole.ADMIN

    local_chapters = int(row["localchap"] or 0)
    online_chapters = int(row["onlinechap"] or 0)

    local_characters = int(row["characters"] or 0)
    online_characters = int(row["online_characters"] or 0)

    epub_exists = bool(row["epub_exists"])
    progress = int(row["progress"] or 0)

    return {
        "id": row["id"],
        "title": row["name"],
        "cover": {"url": row["cover_path"], "exists": bool(row["cover_path"])},
        "author": row["author"] or "",
        "description": row["description"] or "",
        "tags": row["tags"] or "",
        "source": {"name": row["source"], "url": row["url"]},
        "status": row["status"],
        "chapters": {
            "local": local_chapters,
            "online": online_chapters,
            "diff": max(0, online_chapters - local_chapters),
            "latest_title": row["local_lastchaptitle"] or "",
            "last_online_update": row["latestchaptime"],
            "last_sync": row["last_updated"],
        },
        "reading": {
            "chapter": progress,
            "unread": max(0, local_chapters - progress),
            "percent": round(100 * progress / local_chapters, 1)
            if local_chapters
            else 0,
        },
        "characters": {
            "local": local_characters,
            "online": online_characters,
            "new": max(0, online_characters - local_characters),
        },
        "epub": {
            "exists": epub_exists,
            "path": row["filepath"],
            "last_file": row["local_lastchapfile"],
        },
        "state": {
            "needs_update": online_chapters > local_chapters,
            "missing_epub": not epub_exists,
            "new_characters": online_characters > local_characters,
            "sync": ("online_ahead" if online_chapters > local_chapters else "synced"),
        },
        "permissions": {
            "can_read": epub_exists,
            "can_update": can_edit,
            "can_edit": can_edit,
            "can_delete": can_admin,
            "can_sync": can_admin,
            "can_import": can_admin,
        },
        "discord_channel_url": row["discord_channel_url"] or "",
    }


for logger_name in ["werkzeug", "gunicorn.access", "gunicorn.error"]:
    logging.getLogger(logger_name).addFilter(log_SpamFilter())


@main_bp.route("/")
@login_required
def index():
    return render_template(
        "library.html",
        settings=public_settings(),
        settings_metadata=SETTING_METADATA,
        current_username=current_user.username,
        current_role=current_user.role,
    )

@main_bp.route('/status')
def status():
  return "", 200


@main_bp.route("/api/v1/library")
@login_required
def api_library():

    rows = db.get_table(current_user)

    library = [
        build_library_novel(row, current_user.role) for row in rows
    ]

    return jsonify({"data": library})


@main_bp.route("/api/v1/library/missing-epub", methods=["DELETE"])
@admin_required
def api_delete_missing_epubs():
    table = db.get_user_table(current_user)

    try:
        count = db.delete_missing_epub_novels(table=table)
    except Exception as e:
        current_app.logger.error(f"Failed to clean up missing EPUB records: {e!s}")
        return jsonify(
            {
                "success": False,
                "message": f"Failed to clean up missing EPUB records. {e!s}",
                "category": "error",
            }
        ), 500

    if count == 0:
        message = "No missing EPUB records to clean up."
    else:
        message = (
            f"{count} missing EPUB record{'s' if count != 1 else ''} flagged as deleted."
        )

    return jsonify(
        {
            "success": True,
            "message": message,
            "category": "success",
            "data": {"deleted": count},
        }
    )


def _library_novel(novel_id):
    """Return the writable table and the visible novel row (or ``None``)."""
    table = db.get_user_table(current_user)

    return table, db.get_novel(novel_id, table=table, user=current_user)


def _novel_not_found(novel_id):
    return jsonify(
        {
            "success": False,
            "message": f"Novel with ID {novel_id} was not found.",
            "category": "warning",
        }
    ), 404


@main_bp.get("/api/v1/library/<int:novel_id>")
@login_required
def api_library_novel(novel_id):
    _, row = _library_novel(novel_id)

    if row is None:
        return _novel_not_found(novel_id)

    return jsonify(
        {
            "success": True,
            "data": dict(row),
        }
    )


@main_bp.delete("/api/v1/library/<int:novel_id>")
@admin_required
def api_delete_library_novel(novel_id):
    table, row = _library_novel(novel_id)

    if row is None:
        return _novel_not_found(novel_id)

    try:
        db.delete_novels(novel_id, table=table)
    except Exception as e:
        current_app.logger.error(f"Failed to delete novel with ID {novel_id}: {e!s}")
        return jsonify(
            {
                "success": False,
                "message": f"Failed to delete novel with ID {novel_id}. {e!s}",
                "category": "error",
            }
        ), 500

    return jsonify(
        {
            "success": True,
            "message": f"Novel with ID {novel_id} deleted.",
            "category": "success",
        }
    )


@main_bp.patch("/api/v1/library/<int:novel_id>")
@editor_required
def api_update_library_novel(novel_id):
    table, row = _library_novel(novel_id)

    if row is None:
        return _novel_not_found(novel_id)

    payload = request.get_json(silent=True)

    if not isinstance(payload, dict):
        return jsonify(
            {
                "success": False,
                "message": "Request body must be a JSON object.",
                "category": "warning",
            }
        ), 400

    try:
        updates = validate_novel_updates(payload)
    except ValueError as exc:
        return jsonify(
            {
                "success": False,
                "message": str(exc),
                "category": "warning",
            }
        ), 400

    if not updates:
        return jsonify(
            {
                "success": False,
                "message": "No editable fields were provided.",
                "category": "warning",
            }
        ), 400

    try:
        db.update_novel(novel_id, updates, table=table)

    except Exception as e:
        current_app.logger.error(f"Failed to update novel with ID {novel_id}: {e!s}")
        return jsonify(
            {
                "success": False,
                "message": f"Failed to update novel with ID {novel_id}. {e!s}",
                "category": "error",
            }
        ), 500

    updated = db.get_novel(novel_id, table=table, user=current_user)

    return jsonify(
        {
            "success": True,
            "message": f"Novel with ID {novel_id} updated.",
            "category": "success",
            "data": dict(updated),
        }
    )


@main_bp.get("/api/v1/settings")
@login_required
def api_get_settings():
    metadata = {
        key: {"key": key, **definition}
        for key, definition in SETTING_METADATA.items()
    }

    return jsonify(
        {
            "data": public_settings(),
            "metadata": metadata,
        }
    )


@main_bp.post("/api/v1/settings")
@admin_required
def api_save_setting():
    payload = request.get_json(silent=True) or {}

    key = payload.get("key")
    value = payload.get("value")

    if not key:
        return jsonify(
            {
                "success": False,
                "message": "Setting key is required.",
                "category": "warning",
            }
        ), 400

    metadata = SETTING_METADATA.get(key)

    if metadata is None:
        return jsonify(
            {
                "success": False,
                "message": f"Unknown setting: {key}.",
                "category": "warning",
            }
        ), 400

    if metadata.get("readonly"):
        return jsonify(
            {
                "success": False,
                "message": f"Setting '{key}' is read-only.",
                "category": "warning",
            }
        ), 400

    try:
        normalized_value = db.normalize_setting_value(value, metadata)
    except ValueError as exc:
        return jsonify(
            {
                "success": False,
                "message": str(exc),
                "category": "warning",
            }
        ), 400

    db.save_setting(key, normalized_value)

    return jsonify(
        {
            "success": True,
            "message": "Setting saved.",
            "category": "success",
            "data": {
                key: db.get_value(key),
            },
        }
    )


@main_bp.route("/api/v1/sync/registry")
@login_required
def api_sync_registry():
    return jsonify(
        [
            field.to_ui()
            for field in sorted(FIELDS.values(), key=lambda f: f.order)
            if field.visible and field.enabled
        ]
    )


@main_bp.route("/api/v1/sync", methods=["POST"])
@admin_required
def api_sync():
    try:
        data = request.get_json(silent=True)

        if data is None:
            raise ValueError("Invalid or missing JSON payload")

        job = SyncJob.from_dict(
            data,
            table=db.get_user_table(current_user),
        )

        job.include_nsfw = current_user.role == AuthRole.ADMIN

        sync_manager = current_app.extensions["sync_manager"]

        execution = sync_manager.start(job)

        return jsonify(
            {
                "success": True,
                "message": "Synchronization started.",
                "category": "success",
                "job_id": execution.job_id,
            }
        ), 202

    except ValueError as exc:
        return jsonify(
            {
                "success": False,
                "message": str(exc),
                "category": "warning",
            }
        ), 400

    except Exception as exc:  # noqa: BLE001
        current_app.logger.error(f"Failed to start synchronization: {exc}")

        return jsonify(
            {
                "success": False,
                "message": "Failed to start synchronization.",
                "category": "error",
            }
        ), 500


@main_bp.route("/api/v1/sync/<job_id>", methods=["GET"])
@login_required
def api_sync_status(job_id):
    sync_manager = current_app.extensions["sync_manager"]

    execution = sync_manager.get(job_id)

    if execution is None:
        return jsonify(
            {
                "success": False,
                "message": "Synchronization job not found.",
                "category": "warning",
            }
        ), 404

    return jsonify(
        {
            "success": True,
            "execution": execution.snapshot(),
        }
    )


@main_bp.route("/api/v1/sync/<job_id>/cancel", methods=["POST"])
@admin_required
def api_sync_cancel(job_id):
    sync_manager = current_app.extensions["sync_manager"]

    execution = sync_manager.cancel(job_id)

    if execution is None:
        return jsonify(
            {
                "success": False,
                "message": "Synchronization job not found.",
                "category": "warning",
            }
        ), 404

    if execution.done:
        return jsonify(
            {
                "success": False,
                "message": "Synchronization has already finished.",
                "category": "warning",
                "execution": execution.snapshot(),
            }
        ), 409

    return jsonify(
        {
            "success": True,
            "message": "Synchronization cancellation requested.",
            "category": "success",
            "execution": execution.snapshot(),
        }
    )


def _sync_event_stream(execution, timeout=15):
    """Yield SSE frames for one synchronization execution."""
    events = execution.subscribe()

    try:
        while True:
            try:
                event = events.get(timeout=timeout)
            except Empty:
                if execution.done:
                    yield f"event: done\ndata: {json.dumps(execution.snapshot())}\n\n"
                    break

                yield ": keep-alive\n\n"
                continue

            # No more events
            if event is None:
                yield f"event: done\ndata: {json.dumps(execution.snapshot())}\n\n"
                break

            try:
                data = json.dumps(event.data)
            except (TypeError, ValueError):
                current_app.logger.exception(
                    "Failed to serialize synchronization event '%s'.", event.type
                )
                payload = {
                    "message": "Failed to serialize synchronization event.",
                    "event": event.type,
                }

                yield f"event: error\ndata: {json.dumps(payload)}\n\n"
                break

            yield f"event: {event.type}\ndata: {data}\n\n"
    finally:
        execution.unsubscribe(events)


@main_bp.route("/api/v1/sync/<job_id>/events", methods=["GET"])
@login_required
def api_sync_events(job_id):
    sync_manager = current_app.extensions["sync_manager"]

    execution = sync_manager.get(job_id)

    if execution is None:
        return jsonify(
            {
                "success": False,
                "message": "Synchronization job not found.",
                "category": "warning",
            }
        ), 404

    return Response(
        stream_with_context(_sync_event_stream(execution)),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@main_bp.route("/api/v1/epub/<int:novelID>")
@login_required
def serve_epub(novelID):
    epub_dir = db.get_value("LOCAL_EPUB_DIR") or "./"

    filename = db.get_novel(
        novelID,
        db.get_user_table(current_user),
        DatabaseColumn.FILEPATH.value,
        row_factory=False,
        user=current_user,
    )

    if isinstance(filename, (tuple, list)):
        filename = filename[0] if filename else None

    if not filename:
        return jsonify(
            {
                "success": False,
                "message": "EPUB file is not configured for this novel.",
                "category": "warning",
            }
        ), 404

    try:
        response = make_response(send_from_directory(epub_dir, filename))
    except FileNotFoundError:
        return jsonify(
            {
                "success": False,
                "message": "EPUB file was not found.",
                "category": "warning",
            }
        ), 404

    response.headers["Content-Type"] = "application/epub+zip"
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"

    return response
