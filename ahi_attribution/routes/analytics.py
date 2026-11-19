"""Admin sales and product scale-friction reporting endpoints."""
from datetime import timedelta

from flask import Blueprint, jsonify, request

from ..auth import require_admin
from ..db import get_db
from ..services.attribution import parse_timestamp, utc_now_iso

bp = Blueprint("analytics", __name__)


def _range_from_request():
    """Optional ISO timestamps; defaults to the previous 30 days."""
    end_raw = request.args.get("to")
    start_raw = request.args.get("from")
    now = parse_timestamp(utc_now_iso())
    try:
        end = parse_timestamp(end_raw) if end_raw else now
        start = parse_timestamp(start_raw) if start_raw else end - timedelta(days=30)
    except (ValueError, TypeError, AttributeError):
        raise ValueError("from and to must be ISO-8601 timestamps")
    if start > end:
        raise ValueError("from must be earlier than or equal to to")
    return start.isoformat(), end.isoformat()


@bp.get("/api/admin/analytics/scale-friction")
@require_admin
def scale_friction_report():
    try:
        start, end = _range_from_request()
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    db = get_db()
    view_rows = db.execute(
        """SELECT product_id, visitor_id, COUNT(*) AS view_events
           FROM product_interactions
           WHERE event_type = 'product_view'
             AND datetime(occurred_at) >= datetime(?)
             AND datetime(occurred_at) <= datetime(?)
           GROUP BY product_id, visitor_id""",
        (start, end),
    ).fetchall()
    views_by_product = {}
    viewers_by_product = {}
    for row in view_rows:
        product_id = row["product_id"]
        views_by_product[product_id] = views_by_product.get(product_id, 0) + row["view_events"]
        viewers_by_product.setdefault(product_id, set()).add(row["visitor_id"])

    rows = db.execute(
        """WITH starts AS (
                SELECT product_id, visitor_id, try_on_id,
                       MIN(occurred_at) AS started_at
                FROM product_interactions
                WHERE event_type = 'try_on_started'
                  AND try_on_id IS NOT NULL
                  AND datetime(occurred_at) >= datetime(?)
                  AND datetime(occurred_at) <= datetime(?)
                GROUP BY product_id, visitor_id, try_on_id
            )
            SELECT
                starts.product_id,
                starts.visitor_id,
                starts.try_on_id,
                starts.started_at,
                CASE WHEN EXISTS (
                    SELECT 1
                    FROM order_items oi
                    JOIN orders o ON o.id = oi.order_id
                    WHERE oi.product_id = starts.product_id
                      AND oi.try_on_id = starts.try_on_id
                      AND o.visitor_id = starts.visitor_id
                      AND o.status = 'paid'
                      AND o.paid_at IS NOT NULL
                      AND datetime(o.paid_at) >= datetime(starts.started_at)
                      AND datetime(o.paid_at) <= datetime(starts.started_at, '+7 days')
                ) THEN 1 ELSE 0 END AS purchased,
                CASE WHEN EXISTS (
                    SELECT 1
                    FROM order_items oi
                    JOIN orders o ON o.id = oi.order_id
                    WHERE oi.product_id = starts.product_id
                      AND oi.try_on_id = starts.try_on_id
                      AND o.visitor_id = starts.visitor_id
                      AND o.status = 'paid'
                      AND o.is_test = 1
                      AND o.paid_at IS NOT NULL
                      AND datetime(o.paid_at) >= datetime(starts.started_at)
                      AND datetime(o.paid_at) <= datetime(starts.started_at, '+7 days')
                ) THEN 1 ELSE 0 END AS demo_purchased,
                CASE WHEN EXISTS (
                    SELECT 1
                    FROM order_items oi
                    JOIN orders o ON o.id = oi.order_id
                    WHERE oi.product_id = starts.product_id
                      AND oi.try_on_id = starts.try_on_id
                      AND o.visitor_id = starts.visitor_id
                      AND o.status = 'paid'
                      AND o.is_test = 0
                      AND o.paid_at IS NOT NULL
                      AND datetime(o.paid_at) >= datetime(starts.started_at)
                      AND datetime(o.paid_at) <= datetime(starts.started_at, '+7 days')
                ) THEN 1 ELSE 0 END AS real_purchased
            FROM starts""",
        (start, end),
    ).fetchall()

    grouped = {}
    for row in rows:
        item = grouped.setdefault(row["product_id"], {
            "starts": 0, "purchases": 0,
            "demo_purchases": 0, "real_purchases": 0,
            "try_on_visitors": set(),
        })
        item["starts"] += 1
        item["try_on_visitors"].add(row["visitor_id"])
        item["purchases"] += int(row["purchased"])
        item["demo_purchases"] += int(row["demo_purchased"])
        item["real_purchases"] += int(row["real_purchased"])

    for product_id in views_by_product:
        grouped.setdefault(product_id, {
            "starts": 0, "purchases": 0,
            "demo_purchases": 0, "real_purchases": 0,
            "try_on_visitors": set(),
        })

    products = []
    for product_id, metrics in grouped.items():
        starts = metrics["starts"]
        purchases = metrics["purchases"]
        views = views_by_product.get(product_id, 0)
        unique_viewers = len(viewers_by_product.get(product_id, set()))
        unique_try_on_visitors = len(metrics["try_on_visitors"])
        viewers_who_tried_on = len(
            metrics["try_on_visitors"] & viewers_by_product.get(product_id, set())
        )
        try_on_to_purchase = round(purchases / starts * 100, 2) if starts else 0.0
        # Visitor-level view-to-try-on rate; this cannot exceed 100% merely
        # because one person starts multiple try-on attempts.
        view_to_try_on = round(viewers_who_tried_on / unique_viewers * 100, 2) if unique_viewers else 0.0
        status = "insufficient_data" if starts < 30 else (
            "potential_friction" if try_on_to_purchase < 10 else "within_baseline"
        )
        products.append({
            "product_id": product_id,
            "product_views": views,
            "unique_product_viewers": unique_viewers,
            "unique_try_on_visitors": unique_try_on_visitors,
            "try_on_starts": starts,
            "purchasing_try_ons": purchases,
            "demo_purchasing_try_ons": metrics["demo_purchases"],
            "real_purchasing_try_ons": metrics["real_purchases"],
            "product_view_to_try_on_rate_percent": view_to_try_on,
            "try_on_to_purchase_rate_percent": try_on_to_purchase,
            "status": status,
        })

    products.sort(key=lambda item: (
        item["status"] != "potential_friction",
        item["try_on_to_purchase_rate_percent"],
    ))
    return jsonify({"from": start, "to": end, "products": products,
                    "purchase_window_days": 7,
                    "note": "View-to-try-on is based on unique visitors; try-on-to-purchase is based on distinct try-on sessions. Low conversion is a review signal, not proof of scale confusion."})


@bp.get("/api/admin/analytics/overview")
@require_admin
def overview_report():
    db = get_db()
    events = db.execute(
        """SELECT product_id,
                  SUM(CASE WHEN event_type = 'product_view' THEN 1 ELSE 0 END) AS product_views,
                  COUNT(DISTINCT CASE WHEN event_type = 'try_on_started' THEN try_on_id END) AS try_on_starts,
                  COUNT(DISTINCT CASE WHEN event_type = 'purchase' THEN order_id END) AS purchases
           FROM product_interactions
           GROUP BY product_id ORDER BY product_views DESC"""
    ).fetchall()
    touchpoint_count = db.execute(
        "SELECT COUNT(*) AS count FROM referral_touchpoints"
    ).fetchone()["count"]
    order_metrics = db.execute(
        """SELECT
             COUNT(*) AS total_orders,
             SUM(CASE WHEN status = 'paid' AND is_test = 0 THEN 1 ELSE 0 END) AS real_paid_orders,
             SUM(CASE WHEN status = 'paid' AND is_test = 1 THEN 1 ELSE 0 END) AS demo_paid_orders,
             SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) AS pending_orders,
             COALESCE(SUM(CASE WHEN status = 'paid' AND is_test = 0 THEN subtotal ELSE 0 END), 0) AS real_revenue,
             COALESCE(SUM(CASE WHEN status = 'paid' AND is_test = 1 THEN subtotal ELSE 0 END), 0) AS demo_revenue
           FROM orders"""
    ).fetchone()
    return jsonify({
        "referral_touchpoints": touchpoint_count,
        "total_orders": order_metrics["total_orders"] or 0,
        "real_paid_orders": order_metrics["real_paid_orders"] or 0,
        "demo_paid_orders": order_metrics["demo_paid_orders"] or 0,
        "pending_orders": order_metrics["pending_orders"] or 0,
        "real_revenue": round(order_metrics["real_revenue"] or 0, 2),
        "demo_revenue": round(order_metrics["demo_revenue"] or 0, 2),
        "product_events": [dict(row) for row in events],
    })
