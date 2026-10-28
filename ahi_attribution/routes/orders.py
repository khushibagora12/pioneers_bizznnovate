import uuid
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from flask import Blueprint, current_app, jsonify, request

from ..auth import require_admin, require_payment_secret
from ..db import get_db
from ..identity import attach_visitor_cookie, get_or_create_visitor_id
from ..services.attribution import resolve_order_attribution, utc_now_iso

bp = Blueprint("orders", __name__)


def _money_to_cents(value):
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        raise ValueError("subtotal must be a valid amount")
    if not amount.is_finite() or amount < 0:
        raise ValueError("subtotal must be a finite non-negative amount")
    return int((amount * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def _record_payment_and_resolve(db, order_id, model):
    order = db.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
    if order is None:
        raise LookupError("Order not found")

    if order["status"] == "refunded":
        raise ValueError("Cannot attribute a refunded order as paid")
    if order["status"] == "cancelled":
        raise ValueError("Cannot pay a cancelled order")

    if order["status"] != "paid":
        paid_at = utc_now_iso()
        db.execute(
            "UPDATE orders SET status = 'paid', paid_at = ? WHERE id = ?",
            (paid_at, order_id),
        )
        db.commit()

    # Purchases are recorded only by the trusted order/payment flow, not by
    # accepting a browser-supplied `purchase` analytics event.
    from .store import record_purchase_events
    record_purchase_events(db, order_id)
    db.commit()

    result = resolve_order_attribution(
        db,
        order_id=order_id,
        model=model,
        window_days=current_app.config["ATTRIBUTION_WINDOW_DAYS"],
    )
    return result


@bp.post("/api/demo/orders")
@require_admin
def create_demo_order():
    """Create a PENDING demo order for local/testing use only."""
    if not current_app.config["ENABLE_DEMO_PURCHASES"]:
        return jsonify({"error": "Demo purchase endpoints are disabled"}), 404

    data = request.get_json(silent=True) or {}
    currency = str(data.get("currency", "INR")).upper()
    if len(currency) != 3 or not currency.isalpha():
        return jsonify({"error": "currency must be a 3-letter code"}), 400

    # This demo-only endpoint can accept item data so the product analytics
    # report can link a tryOnId to a purchased product. A real checkout must
    # calculate prices from the server-side product catalogue instead.
    items = data.get("items")
    normalized_items = []
    if items is not None:
        if not isinstance(items, list) or not items:
            return jsonify({"error": "items must be a non-empty array"}), 400
        cents = 0
        for item in items:
            if not isinstance(item, dict):
                return jsonify({"error": "each item must be an object"}), 400
            product_id = str(item.get("productId", "")).strip()
            try_on_id = item.get("tryOnId")
            quantity = item.get("quantity", 1)
            if not product_id or len(product_id) > 100:
                return jsonify({"error": "each item needs a valid productId"}), 400
            if not isinstance(quantity, int) or isinstance(quantity, bool) or quantity < 1:
                return jsonify({"error": "quantity must be a positive integer"}), 400
            if try_on_id:
                try:
                    try_on_id = str(uuid.UUID(try_on_id))
                except (ValueError, TypeError, AttributeError):
                    return jsonify({"error": "tryOnId must be a UUID"}), 400
            try:
                unit_cents = _money_to_cents(item.get("unitPrice"))
            except ValueError as exc:
                return jsonify({"error": str(exc)}), 400
            cents += unit_cents * quantity
            normalized_items.append((product_id, try_on_id, quantity, unit_cents / 100))
    else:
        try:
            cents = _money_to_cents(data.get("subtotal"))
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400

    visitor_id, is_new = get_or_create_visitor_id()
    order_id = str(uuid.uuid4())
    now = utc_now_iso()
    db = get_db()
    db.execute(
        """INSERT INTO orders
           (id, visitor_id, status, subtotal, currency, created_at, paid_at,
            is_test, payment_method)
           VALUES (?, ?, 'pending', ?, ?, ?, NULL, 1, 'demo-admin')""",
        (order_id, visitor_id, cents / 100, currency, now),
    )
    for product_id, try_on_id, quantity, unit_price in normalized_items:
        db.execute(
            """INSERT INTO order_items
               (order_id, product_id, try_on_id, quantity, unit_price)
               VALUES (?, ?, ?, ?, ?)""",
            (order_id, product_id, try_on_id, quantity, unit_price),
        )
    db.commit()
    response = jsonify({
        "order_id": order_id,
        "status": "pending",
        "subtotal": cents / 100,
        "currency": currency,
        "test_order": True,
    })
    response.status_code = 201
    if is_new:
        attach_visitor_cookie(response, visitor_id)
    return response


@bp.post("/api/demo/orders/<order_id>/mark-paid")
@require_admin
def mark_demo_order_paid(order_id):
    """Mark a demo order paid; never enable this route in production."""
    if not current_app.config["ENABLE_DEMO_PURCHASES"]:
        return jsonify({"error": "Demo purchase endpoints are disabled"}), 404
    model = (request.get_json(silent=True) or {}).get("model", "linear")
    db = get_db()
    try:
        result = _record_payment_and_resolve(db, order_id, model)
    except LookupError as exc:
        return jsonify({"error": str(exc)}), 404
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception:
        current_app.logger.exception("Could not resolve demo purchase")
        return jsonify({"error": "Attribution calculation failed"}), 500
    return jsonify({"test_order": True, "attribution": result})


@bp.post("/api/internal/orders/<order_id>/payment-confirmed")
@require_payment_secret
def confirm_payment_from_trusted_backend(order_id):
    """Integration point for a trusted payment service.

    Verify the payment provider's real webhook signature in the relevant
    checkout integration before calling this function/route. The shared-secret
    example is only a generic protected integration point, not a substitute
    for provider-specific signature verification.
    """
    model = (request.get_json(silent=True) or {}).get("model", "linear")
    db = get_db()
    try:
        result = _record_payment_and_resolve(db, order_id, model)
    except LookupError as exc:
        return jsonify({"error": str(exc)}), 404
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception:
        current_app.logger.exception("Payment confirmation/attribution failed")
        return jsonify({"error": "Payment confirmation processing failed"}), 500
    return jsonify({"attribution": result})
