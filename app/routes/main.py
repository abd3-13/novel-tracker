import logging

from flask import Blueprint, jsonify, render_template, request
from flask_login import current_user, login_required

from app.sync.job import SyncJob
from app.sync.metadata import FIELDS
from app.sync.runner import SyncRunner
from app.utils import db
from app.utils.filters import log_SpamFilter

main_bp = Blueprint("main", __name__)


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
    }


for logger_name in ["werkzeug", "gunicorn.access", "gunicorn.error"]:
    logging.getLogger(logger_name).addFilter(log_SpamFilter())


@main_bp.route("/")
@login_required
def index():
    settings = db.get_settings_dict()

    return render_template("library.html", settings=settings)


@main_bp.route("/library")
@login_required
def library():
    settings = db.get_settings_dict()

    return render_template("library.html", settings=settings)


@main_bp.route("/api/v1/library")
@login_required
def api_library():

    rows = db.get_table(current_user)

    library = [build_library_novel(row) for row in rows]

    return jsonify({"data": library})


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

        runner = SyncRunner()

        result = runner.run(job)

    except ValueError as exc:
        return jsonify(
            {
                "success": False,
                "message": str(exc),
                "category": "warning",
            }
        ), 400

    except Exception as exc:  # noqa: BLE001
        print(f"Synchronization failed: {exc}")

        return jsonify(
            {
                "success": False,
                "message": "Synchronization failed.",
                "category": "error",
            }
        ), 500

    summary = result["summary"]

    if summary["errors"] > 0:
        category = "error"

        message = (
            f"Synchronization completed with "
            f"{summary['errors']} error"
            f"{'s' if summary['errors'] != 1 else ''}."
        )

    elif summary["warnings"] > 0:
        category = "warning"

        message = (
            f"Synchronization completed with "
            f"{summary['warnings']} warning"
            f"{'s' if summary['warnings'] != 1 else ''}."
        )

    else:
        category = "success"

        message = "Synchronization completed successfully."

    return jsonify(
        {
            "success": True,
            "message": message,
            "category": category,
            "summary": summary,
            "results": result["results"],
        }
    )
