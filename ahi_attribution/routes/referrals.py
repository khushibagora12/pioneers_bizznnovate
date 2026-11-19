import secrets
import uuid
from urllib.parse import urlparse

from flask import Blueprint, current_app, jsonify, redirect, request

from ..auth import require_admin
from ..db import get_db
from ..identity import attach_visitor_cookie, get_or_create_visitor_id
from ..services.attribution import utc_now_iso

bp = Blueprint("referrals", __name__)


def is_safe_destination_path(value: str) -> bool:
    """Only permit local absolute paths, never external redirect URLs."""
    if not isinstance(value, str) or not value.startswith("/") or value.startswith("//"):
        return False
    parsed = urlparse(value)
    return not parsed.scheme and not parsed.netloc and "\\" not in value


@bp.post("/api/admin/affiliates")
@require_admin
def create_affiliate():
    data = request.get_json(silent=True) or {}
    code = str(data.get("code", "")).strip()
    name = str(data.get("name", "")).strip()
    try:
        commission_rate = float(data.get("commission_rate", 0.10))
    except (TypeError, ValueError):
        return jsonify({"error": "commission_rate must be a number"}), 400

    if not code or not name:
        return jsonify({"error": "code and name are required"}), 400
    if len(code) > 80 or len(name) > 200:
        return jsonify({"error": "code or name is too long"}), 400
    if not 0 <= commission_rate <= 1:
        return jsonify({"error": "commission_rate must be between 0 and 1"}), 400

    db = get_db()
    try:
        cursor = db.execute(
            """INSERT INTO affiliates
               (code, name, commission_rate, created_at)
               VALUES (?, ?, ?, ?)""",
            (code, name, commission_rate, utc_now_iso()),
        )
        db.commit()
    except Exception as exc:
        db.rollback()
        if "UNIQUE constraint failed" in str(exc):
            return jsonify({"error": "Affiliate code already exists"}), 409
        raise

    return jsonify({
        "id": cursor.lastrowid,
        "code": code,
        "name": name,
        "commission_rate": commission_rate,
    }), 201


@bp.get("/api/admin/affiliates")
@require_admin
def list_affiliates():
    rows = get_db().execute(
        """SELECT id, code, name, commission_rate, active, created_at
           FROM affiliates ORDER BY id"""
    ).fetchall()
    return jsonify({"affiliates": [dict(row) for row in rows]})


@bp.post("/api/admin/referral-links")
@require_admin
def create_referral_link():
    data = request.get_json(silent=True) or {}
    affiliate_id = data.get("affiliate_id")
    source = str(data.get("source", "")).strip()
    campaign = str(data.get("campaign", "")).strip() or None
    destination = data.get("destination_path", "/products")

    try:
        affiliate_id = int(affiliate_id)
    except (TypeError, ValueError):
        return jsonify({"error": "affiliate_id must be an integer"}), 400

    if not source or len(source) > 100:
        return jsonify({"error": "source is required and must be <= 100 chars"}), 400
    if campaign is not None and len(campaign) > 200:
        return jsonify({"error": "campaign must be <= 200 chars"}), 400
    if not is_safe_destination_path(destination):
        return jsonify({"error": "destination_path must be a safe local path"}), 400

    db = get_db()
    affiliate = db.execute(
        "SELECT id FROM affiliates WHERE id = ? AND active = 1",
        (affiliate_id,),
    ).fetchone()
    if affiliate is None:
        return jsonify({"error": "Active affiliate not found"}), 404

    # Random code avoids exposing sequential database IDs in public links.
    code = secrets.token_urlsafe(9).replace("-", "x").replace("_", "y")
    cursor = db.execute(
        """INSERT INTO referral_links
           (code, affiliate_id, source, campaign, destination_path, created_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (code, affiliate_id, source, campaign, destination, utc_now_iso()),
    )
    db.commit()

    backend_url = current_app.config["BACKEND_PUBLIC_URL"]
    return jsonify({
        "id": cursor.lastrowid,
        "code": code,
        "affiliate_id": affiliate_id,
        "source": source,
        "campaign": campaign,
        "destination_path": destination,
        "referral_url": f"{backend_url}/r/{code}",
    }), 201


@bp.get("/api/admin/referral-links")
@require_admin
def list_referral_links():
    rows = get_db().execute(
        """SELECT rl.id, rl.code, rl.affiliate_id, a.name AS affiliate_name,
                  rl.source, rl.campaign, rl.destination_path,
                  rl.active, rl.created_at
           FROM referral_links rl
           JOIN affiliates a ON a.id = rl.affiliate_id
           ORDER BY rl.id DESC"""
    ).fetchall()
    items = []
    backend_url = current_app.config["BACKEND_PUBLIC_URL"]
    for row in rows:
        item = dict(row)
        item["referral_url"] = f"{backend_url}/r/{row['code']}"
        items.append(item)
    return jsonify({"referral_links": items})


@bp.get("/r/<code>")
def referral_redirect(code):
    db = get_db()
    link = db.execute(
        """SELECT rl.*, a.active AS affiliate_active
           FROM referral_links rl
           JOIN affiliates a ON a.id = rl.affiliate_id
           WHERE rl.code = ? AND rl.active = 1 AND a.active = 1""",
        (code,),
    ).fetchone()

    if link is None:
        return jsonify({"error": "Referral link not found or inactive"}), 404

    visitor_id, is_new = get_or_create_visitor_id()
    # A GET to /r/<code> is treated as a referral click/landing request.
    # Social preview bots may also request URLs; filter known bots if accurate
    # human-click reporting is important to your campaign.
    db.execute(
        """INSERT INTO referral_touchpoints
           (event_id, visitor_id, referral_link_id, affiliate_id,
            source, campaign, occurred_at)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (
            str(uuid.uuid4()), visitor_id, link["id"], link["affiliate_id"],
            link["source"], link["campaign"], utc_now_iso(),
        ),
    )
    db.commit()

    response = redirect(
        current_app.config["FRONTEND_BASE_URL"] + link["destination_path"],
        code=302,
    )
    if is_new:
        attach_visitor_cookie(response, visitor_id)
    return response
