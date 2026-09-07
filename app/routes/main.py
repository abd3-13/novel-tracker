import json
import logging

from flask import (
    Blueprint,
    Response,
    current_app,
    jsonify,
    render_template,
    request,
    stream_with_context,
)
from flask_login import current_user, login_required

from app.constants import SETTING_METADATA
from app.sync.job import SyncJob
from app.sync.metadata import FIELDS
from app.utils import db
from app.utils.filters import log_SpamFilter

main_bp = Blueprint("main", __name__)

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


def build_library_novel(row):
    local_chapters = int(row[3] or 0)
    online_chapters = int(row[4] or 0)

    local_characters = int(row[22] or 0)
    online_characters = int(row[23] or 0)

    epub_exists = bool(row[13])

    return {
        "id": row[0],
        "title": row[1],
        "cover": {"url": row[17], "exists": bool(row[17])},
        "author": row[14] or "",
        "description": row[15] or "",
        "tags": row[16] or "",
        "source": {"name": row[7], "url": row[2]},
        "status": row[6],
        "chapters": {
            "local": local_chapters,
            "online": online_chapters,
            "diff": max(0, online_chapters - local_chapters),
            "latest_title": row[18] or "",
            "last_online_update": row[5],
            "last_sync": row[11],
        },
        "reading": {
            "chapter": int(row[20] or 0),
            "unread": max(0, local_chapters - int(row[20] or 0)),
            "percent": round(100 * int(row[20] or 0) / local_chapters, 1)
            if local_chapters
            else 0,
        },
        "characters": {
            "local": local_characters,
            "online": online_characters,
            "new": max(0, online_characters - local_characters),
        },
        "epub": {"exists": epub_exists, "path": row[9], "last_file": row[19]},
        "state": {
            "needs_update": online_chapters > local_chapters,
            "missing_epub": not epub_exists,
            "new_characters": online_characters > local_characters,
            "sync": ("online_ahead" if online_chapters > local_chapters else "synced"),
        },
        "permissions": {
            "can_read": epub_exists,
            "can_update": True,
            "can_edit": True,
            "can_delete": True,
        },
        "discord_channel_url": row[24] or "",
    }


for logger_name in ["werkzeug", "gunicorn.access", "gunicorn.error"]:
    logging.getLogger(logger_name).addFilter(log_SpamFilter())


@main_bp.route("/")
@login_required
def index():
    settings = db.get_settings_dict()

    return render_template(
        "library.html", settings=settings, settings_metadata=SETTING_METADATA
    )


@main_bp.route("/api/v1/library")
@login_required
def api_library():

    rows = db.get_table(current_user)

    library = [build_library_novel(row) for row in rows]

    return jsonify({"data": library})


@main_bp.route("/api/v1/library/<int:novel_id>", methods=["GET", "PATCH"])
@login_required
def api_library_novel(novel_id):
    table = db.get_user_table(current_user)
    row = db.get_novel(novel_id, table=table)

    if row is None:
        return jsonify(
            {
                "success": False,
                "message": f"Novel with ID {novel_id} was not found.",
                "category": "warning",
            }
        ), 404

    if request.method == "GET":
        return jsonify(
            {
                "success": True,
                "data": dict(row),
            }
        )

    payload = request.get_json(silent=True) or {}

    updates = {
        key: value for key, value in payload.items() if key in NOVEL_EDITABLE_FIELDS
    }

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
        print(f"Failed to update novel with ID {novel_id}: {e!s}")
        return jsonify(
            {
                "success": False,
                "message": f"Failed to update novel with ID {novel_id}. {e!s}",
                "category": "error",
            }
        ), 500

    updated = db.get_novel(novel_id, table=table)

    return jsonify(
        {
            "success": True,
            "message": f"Novel with ID {novel_id} updated.",
            "category": "success",
            "data": dict(updated),
        }
    )


@main_bp.route("/api/v1/settings")
@login_required
def api_settings():
    settings = db.get_settings_dict()

    metadata = {
        key: {
            "key": key,
            **definition,
        }
        for key, definition in SETTING_METADATA.items()
    }

    return jsonify(
        {
            "data": settings,
            "metadata": metadata,
        }
    )


@main_bp.route("/api/v1/settings", methods=["POST"])
@login_required
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
@login_required
def api_sync():
    try:
        data = request.get_json(silent=True)

        if data is None:
            raise ValueError("Invalid or missing JSON payload")

        job = SyncJob.from_dict(
            data,
            table=db.get_user_table(current_user),
        )

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
        print(f"Failed to start synchronization: {exc}")

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
@login_required
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

    def event_stream():
        while True:
            event = execution.events.get()

            # No more events
            if event is None:
                yield (f"event: done\ndata: {json.dumps(execution.snapshot())}\n\n")
                break

            yield (f"event: {event.type}\ndata: {json.dumps(event.data)}\n\n")

    return Response(
        stream_with_context(event_stream()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )
