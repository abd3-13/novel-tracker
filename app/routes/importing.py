"""Routes for scanning and importing local EPUB files."""

import json
from pathlib import Path

from flask import (
    Blueprint,
    Response,
    current_app,
    jsonify,
    request,
    stream_with_context,
)
from flask_login import current_user, login_required

from app.constants import AuthRole
from app.importer.importer import import_files, iter_import_files
from app.importer.scanner import iter_scan_library
from app.sync.services import get_epub_cover_bytes
from app.utils import db

import_bp = Blueprint("importing", __name__)


def _import_table():
    """Return the writable table for the current user, or None if not allowed.

    Importing writes new rows and reads the server's EPUB directory, so it is
    restricted to administrators. Regular users and the demo account cannot
    import.
    """
    if str(current_user.role) != AuthRole.ADMIN:
        return None

    return db.get_user_table(current_user)


def _forbidden():
    return jsonify(
        {
            "success": False,
            "message": "Import is not available for this account.",
            "category": "warning",
        }
    ), 403


def _json_payload():
    """Return the request body when it is a JSON object, otherwise ``None``."""
    payload = request.get_json(silent=True)

    return payload if isinstance(payload, dict) else None


def _invalid_body():
    return jsonify(
        {
            "success": False,
            "message": "Request body must be a JSON object.",
            "category": "warning",
        }
    ), 400


@import_bp.get("/api/v1/import/scan/events")
@login_required
def api_import_scan_events():
    table = _import_table()

    if table is None:
        return _forbidden()

    def event_stream():
        try:
            for event, data in iter_scan_library(table):
                yield f"event: {event}\ndata: {json.dumps(data)}\n\n"
        except ValueError as exc:
            current_app.logger.warning(f"Import scan failed: {exc!s}")
            yield f"event: scan_error\ndata: {json.dumps({'message': str(exc)})}\n\n"
        except Exception as exc:  # noqa: BLE001
            current_app.logger.exception(f"Failed to scan EPUB directory: {exc!s}")
            yield (
                "event: scan_error\ndata: "
                f"{json.dumps({'message': 'Failed to scan EPUB directory.'})}\n\n"
            )

    return Response(
        stream_with_context(event_stream()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@import_bp.post("/api/v1/import")
@login_required
def api_import_files():
    table = _import_table()

    if table is None:
        return _forbidden()

    payload = _json_payload()

    if payload is None:
        return _invalid_body()

    filenames = payload.get("filenames")

    if not isinstance(filenames, list) or not filenames:
        return jsonify(
            {
                "success": False,
                "message": "Select at least one EPUB to import.",
                "category": "warning",
            }
        ), 400

    if not all(isinstance(name, str) and name for name in filenames):
        return jsonify(
            {
                "success": False,
                "message": "Invalid EPUB selection.",
                "category": "warning",
            }
        ), 400

    try:
        result = import_files(filenames, table)
    except ValueError as exc:
        current_app.logger.warning(f"Import failed: {exc!s}")
        return jsonify(
            {
                "success": False,
                "message": str(exc),
                "category": "warning",
            }
        ), 400
    except Exception as exc:  # noqa: BLE001
        current_app.logger.error(f"Failed to import EPUBs: {exc!s}")
        return jsonify(
            {
                "success": False,
                "message": "Failed to import EPUBs.",
                "category": "error",
            }
        ), 500

    return jsonify({"success": True, **result})


@import_bp.post("/api/v1/import/events")
@login_required
def api_import_files_events():
    table = _import_table()

    if table is None:
        return _forbidden()

    payload = _json_payload()

    if payload is None:
        return _invalid_body()

    filenames = payload.get("filenames")

    if not isinstance(filenames, list) or not filenames:
        return jsonify(
            {
                "success": False,
                "message": "Select at least one EPUB to import.",
                "category": "warning",
            }
        ), 400

    if not all(isinstance(name, str) and name for name in filenames):
        return jsonify(
            {
                "success": False,
                "message": "Invalid EPUB selection.",
                "category": "warning",
            }
        ), 400

    def event_stream():
        try:
            for event, data in iter_import_files(filenames, table):
                yield json.dumps({"event": event, "data": data}) + "\n"
        except ValueError as exc:
            current_app.logger.warning(f"Import failed: {exc!s}")
            yield json.dumps(
                {"event": "error", "data": {"message": str(exc)}}
            ) + "\n"
        except Exception as exc:  # noqa: BLE001
            current_app.logger.exception(f"Failed to import EPUBs: {exc!s}")
            yield json.dumps(
                {"event": "error", "data": {"message": "Failed to import EPUBs."}}
            ) + "\n"

    return Response(
        stream_with_context(event_stream()),
        mimetype="application/x-ndjson",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@import_bp.get("/api/v1/import/cover")
@login_required
def api_import_cover():
    if _import_table() is None:
        return _forbidden()

    filename = request.args.get("filename", "")

    if Path(filename).name != filename or not filename.lower().endswith(".epub"):
        return "", 400

    try:
        cover = get_epub_cover_bytes(filename)
    except FileNotFoundError:
        return "", 404
    except Exception as exc:  # noqa: BLE001
        current_app.logger.error(f"Failed to read EPUB cover: {exc!s}")
        return "", 404

    if cover is None:
        return "", 404

    data, media_type = cover

    response = Response(data, mimetype=media_type)
    response.headers["Cache-Control"] = "no-store"

    return response
