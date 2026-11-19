import json
import uuid

from flask import Blueprint, jsonify, make_response, request

from ..db import get_db
from ..identity import attach_visitor_cookie, get_or_create_visitor_id
from ..services.attribution import utc_now_iso

bp = Blueprint("tracking", __name__)
ALLOWED_EVENTS = {"product_view", "try_on_started"}


def _is_uuid(value) -> bool:
    try:
        uuid.UUID(str(value))
        return True
    except (ValueError, TypeError, AttributeError):
        return False


@bp.post("/api/track/events")
def record_product_event():
    data = request.get_json(silent=True) or {}
    event_id = data.get("eventId")
    event_type = data.get("eventType")
    product_id = data.get("productId")
    try_on_id = data.get("tryOnId")
    session_id = data.get("sessionId")
    metadata = data.get("metadata", {})

    if not _is_uuid(event_id):
        return jsonify({"error": "eventId must be a valid UUID"}), 400
    if event_type not in ALLOWED_EVENTS:
        return jsonify({
            "error": "eventType must be product_view or try_on_started"
        }), 400
    if not isinstance(product_id, str) or not product_id.strip() or len(product_id) > 100:
        return jsonify({"error": "A valid productId is required"}), 400
    if event_type == "try_on_started" and not _is_uuid(try_on_id):
        return jsonify({
            "error": "tryOnId must be a UUID for try_on_started"
        }), 400
    if metadata is None:
        metadata = {}
    if not isinstance(metadata, dict):
        return jsonify({"error": "metadata must be a JSON object"}), 400
    if len(json.dumps(metadata)) > 4000:
        return jsonify({"error": "metadata is too large"}), 400
    if session_id is not None and (not isinstance(session_id, str) or len(session_id) > 100):
        return jsonify({"error": "sessionId must be a string <= 100 chars"}), 400

    visitor_id, is_new = get_or_create_visitor_id()
    db = get_db()
    try:
        db.execute(
            """INSERT INTO product_interactions
               (event_id, visitor_id, session_id, product_id, try_on_id,
                event_type, metadata, occurred_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                str(uuid.UUID(event_id)), visitor_id, session_id,
                product_id.strip(), str(uuid.UUID(try_on_id)) if try_on_id else None,
                event_type, json.dumps(metadata), utc_now_iso(),
            ),
        )
        db.commit()
        response = make_response(jsonify({"recorded": True}), 201)
    except Exception as exc:
        db.rollback()
        if "UNIQUE constraint failed" in str(exc):
            response = make_response(jsonify({"recorded": True, "duplicate": True}), 200)
        else:
            raise

    if is_new:
        attach_visitor_cookie(response, visitor_id)
    return response
