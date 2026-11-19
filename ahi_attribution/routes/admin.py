"""Protected attribution reports and the admin analytics UI shell."""
import json

from flask import Blueprint, current_app, jsonify, render_template, request

from ..auth import require_admin
from ..db import get_db

bp = Blueprint("admin", __name__)


@bp.get("/admin/analytics")
def analytics_dashboard_page():
    # The HTML shell contains no data. Every data endpoint still requires the
    # admin API key; the key is entered by an administrator at runtime.
    return render_template("admin_analytics.html")


@bp.get("/api/admin/analytics/attribution")
@require_admin
def attribution_report():
    model = request.args.get("model", "linear")
    if model not in {"first_touch", "last_touch", "linear"}:
        return jsonify({"error": "model must be first_touch, last_touch or linear"}), 400

    db = get_db()
    rows = db.execute(
        """SELECT a.id AS affiliate_id, a.code AS affiliate_code,
                  a.name AS affiliate_name,
                  COUNT(DISTINCT CASE WHEN o.is_test = 0 THEN r.order_id END) AS real_credited_orders,
                  COUNT(DISTINCT CASE WHEN o.is_test = 1 THEN r.order_id END) AS demo_credited_orders,
                  ROUND(SUM(CASE WHEN o.is_test = 0 THEN ar.attributed_revenue ELSE 0 END), 2) AS real_attributed_revenue,
                  ROUND(SUM(CASE WHEN o.is_test = 1 THEN ar.attributed_revenue ELSE 0 END), 2) AS demo_attributed_revenue,
                  ROUND(SUM(CASE WHEN o.is_test = 0 THEN ar.commission_amount ELSE 0 END), 2) AS real_commission,
                  ROUND(SUM(CASE WHEN o.is_test = 1 THEN ar.commission_amount ELSE 0 END), 2) AS demo_commission,
                  ROUND(SUM(ar.attributed_revenue), 2) AS attributed_revenue_all,
                  ROUND(SUM(ar.commission_amount), 2) AS commission_all
           FROM attribution_results ar
           JOIN affiliates a ON a.id = ar.affiliate_id
           JOIN attribution_runs r ON r.id = ar.run_id
           JOIN orders o ON o.id = r.order_id
           WHERE r.model = ? AND r.status = 'completed' AND o.status = 'paid'
           GROUP BY a.id, a.code, a.name
           ORDER BY attributed_revenue_all DESC""",
        (model,),
    ).fetchall()
    return jsonify({
        "model": model,
        "window_days_default": current_app.config["ATTRIBUTION_WINDOW_DAYS"],
        "affiliates": [dict(row) for row in rows],
        "note": "Demo/test orders are reported separately from real orders.",
    })


@bp.get("/api/admin/analytics/attribution/orders/<order_id>")
@require_admin
def order_attribution_report(order_id):
    model = request.args.get("model", "linear")
    if model not in {"first_touch", "last_touch", "linear"}:
        return jsonify({"error": "Invalid attribution model"}), 400
    db = get_db()
    run = db.execute(
        """SELECT * FROM attribution_runs WHERE order_id = ? AND model = ?""",
        (order_id, model),
    ).fetchone()
    if run is None:
        return jsonify({"error": "Attribution has not been calculated for this order/model"}), 404
    rows = db.execute(
        """SELECT a.id AS affiliate_id, a.name AS affiliate_name,
                  ar.credit_fraction, ar.attributed_revenue,
                  ar.commission_rate_applied, ar.commission_amount,
                  ar.touchpoint_ids_json
           FROM attribution_results ar
           JOIN affiliates a ON a.id = ar.affiliate_id
           WHERE ar.run_id = ? ORDER BY a.id""",
        (run["id"],),
    ).fetchall()
    return jsonify({
        "order_id": order_id,
        "model": model,
        "status": run["status"],
        "window_days": run["window_days"],
        "credits": [
            {
                "affiliate_id": row["affiliate_id"],
                "affiliate_name": row["affiliate_name"],
                "credit_fraction": row["credit_fraction"],
                "attributed_revenue": row["attributed_revenue"],
                "commission_rate_applied": row["commission_rate_applied"],
                "commission_amount": row["commission_amount"],
                "touchpoint_ids": json.loads(row["touchpoint_ids_json"]),
            }
            for row in rows
        ],
    })


@bp.get("/api/admin/orders")
@require_admin
def orders_report():
    db = get_db()
    rows = db.execute(
        """SELECT o.id, o.status, o.subtotal, o.currency, o.created_at,
                  o.paid_at, o.is_test, o.customer_name, o.payment_method,
                  COUNT(oi.id) AS line_count,
                  COALESCE(SUM(oi.quantity), 0) AS item_quantity
           FROM orders o
           LEFT JOIN order_items oi ON oi.order_id = o.id
           GROUP BY o.id
           ORDER BY o.created_at DESC
           LIMIT 100"""
    ).fetchall()
    return jsonify({"orders": [dict(row) for row in rows]})
