"""Storefront cart, checkout, and order confirmation pages."""
import json
import uuid
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from flask import Blueprint, current_app, jsonify, render_template, request

from service.jewelleryService import share_jewellery_data

from ..db import get_db
from ..identity import attach_visitor_cookie, get_or_create_visitor_id
from ..services.attribution import resolve_order_attribution, utc_now_iso

bp = Blueprint("store", __name__)

CATEGORY_MAP = {"earrings": "Earrings", "shades": "Shades"}


def _money_cents(value):
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        raise ValueError("Invalid product price")
    if not amount.is_finite() or amount < 0:
        raise ValueError("Invalid product price")
    return int((amount * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def _lookup_product(product_id):
    """Resolve a namespaced ID from the server-side product catalogue."""
    if not isinstance(product_id, str) or ":" not in product_id:
        return None
    category, raw_id = product_id.split(":", 1)
    category = category.lower().strip()
    if category not in CATEGORY_MAP or not raw_id.isdigit():
        return None
    data = share_jewellery_data()
    products = data.get(CATEGORY_MAP[category], [])
    product = next((item for item in products if str(item.get("id")) == raw_id), None)
    if not product:
        return None
    item = dict(product)
    item["product_id"] = f"{category}:{raw_id}"
    item["category"] = category
    item["price_cents"] = _money_cents(item.get("price"))
    return item


def _validate_try_on(db, visitor_id, product_id, try_on_id):
    """Only associate a try-on that was recorded for this visitor/product."""
    if not try_on_id:
        return None
    try:
        normalized = str(uuid.UUID(str(try_on_id)))
    except (ValueError, TypeError, AttributeError):
        return None
    row = db.execute(
        """SELECT 1 FROM product_interactions
           WHERE visitor_id = ? AND product_id = ?
             AND try_on_id = ? AND event_type = 'try_on_started'
           LIMIT 1""",
        (visitor_id, product_id, normalized),
    ).fetchone()
    return normalized if row else None


def record_purchase_events(db, order_id):
    """Write backend-generated purchase events for a paid order."""
    order = db.execute(
        "SELECT id, visitor_id, status, paid_at, is_test, payment_method FROM orders WHERE id = ?",
        (order_id,),
    ).fetchone()
    if not order or order["status"] != "paid" or not order["paid_at"]:
        return

    items = db.execute(
        "SELECT id, product_id, try_on_id, quantity, unit_price FROM order_items WHERE order_id = ?",
        (order_id,),
    ).fetchall()
    for item in items:
        # Deterministic ID prevents duplicate events if payment handling is retried.
        event_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"ahi-purchase:{order_id}:{item['id']}"))
        metadata = json.dumps({
            "quantity": item["quantity"],
            "paymentType": "demo" if order["is_test"] else order["payment_method"],
            "isTest": bool(order["is_test"]),
        })
        db.execute(
            """INSERT OR IGNORE INTO product_interactions
               (event_id, visitor_id, product_id, try_on_id, event_type,
                metadata, occurred_at, order_id)
               VALUES (?, ?, ?, ?, 'purchase', ?, ?, ?)""",
            (event_id, order["visitor_id"], item["product_id"], item["try_on_id"],
             metadata, order["paid_at"], order_id),
        )


@bp.get("/cart")
def cart_page():
    return render_template(
        "cart.html",
        demo_checkout_enabled=current_app.config.get("ENABLE_DEMO_CHECKOUT", False),
    )


@bp.get("/order-confirmation/<order_id>")
def order_confirmation_page(order_id):
    return render_template("order_confirmation.html", order_id=order_id)


@bp.post("/api/store/checkout")
def checkout():
    """Create an order using server-side catalogue prices.

    If ENABLE_DEMO_CHECKOUT is enabled, this creates a clearly labelled test
    purchase without charging a payment method. Otherwise it records a pending
    order request; real payment integration must confirm payment separately.
    """
    data = request.get_json(silent=True) or {}
    items = data.get("items")
    customer_name = str(data.get("customerName", "")).strip()
    customer_email = str(data.get("customerEmail", "")).strip()
    customer_phone = str(data.get("customerPhone", "")).strip()
    shipping_address = str(data.get("shippingAddress", "")).strip()

    if not isinstance(items, list) or not items or len(items) > 30:
        return jsonify({"error": "Your cart must contain between 1 and 30 line items."}), 400
    if not customer_name or len(customer_name) > 160:
        return jsonify({"error": "Enter a valid full name."}), 400
    if "@" not in customer_email or len(customer_email) > 254:
        return jsonify({"error": "Enter a valid email address."}), 400
    digits = "".join(ch for ch in customer_phone if ch.isdigit())
    if len(digits) < 7 or len(digits) > 15:
        return jsonify({"error": "Enter a valid phone number."}), 400
    if len(shipping_address) < 8 or len(shipping_address) > 1000:
        return jsonify({"error": "Enter a complete shipping address."}), 400

    visitor_id, is_new = get_or_create_visitor_id()
    db = get_db()
    normalized = []
    total_cents = 0
    merged = {}

    # Validate catalogue IDs, cap quantities, and ignore client-sent prices.
    for raw in items:
        if not isinstance(raw, dict):
            return jsonify({"error": "Invalid cart item."}), 400
        product_id = str(raw.get("productId", ""))
        product = _lookup_product(product_id)
        if not product:
            return jsonify({"error": f"Product not found: {product_id}"}), 400
        quantity = raw.get("quantity", 1)
        if not isinstance(quantity, int) or isinstance(quantity, bool) or not 1 <= quantity <= 10:
            return jsonify({"error": "Each product quantity must be between 1 and 10."}), 400
        try_on_id = _validate_try_on(db, visitor_id, product_id, raw.get("tryOnId"))
        # Keep distinct try-on IDs as distinct order lines so a specific try-on
        # can be associated with the purchased item; combine only identical keys.
        key = (product_id, try_on_id)
        if key not in merged:
            merged[key] = {"product": product, "quantity": 0, "try_on_id": try_on_id}
        merged[key]["quantity"] += quantity
        if merged[key]["quantity"] > 10:
            return jsonify({"error": "Maximum quantity per product/try-on is 10."}), 400

    for item in merged.values():
        product = item["product"]
        item["unit_price"] = product["price_cents"] / 100
        total_cents += product["price_cents"] * item["quantity"]
        normalized.append(item)

    is_demo = bool(current_app.config.get("ENABLE_DEMO_CHECKOUT", False))
    order_id = str(uuid.uuid4())
    created_at = utc_now_iso()
    status = "paid" if is_demo else "pending"
    paid_at = created_at if is_demo else None
    payment_method = "demo-no-charge" if is_demo else "not-configured"

    try:
        db.execute("BEGIN IMMEDIATE")
        db.execute(
            """INSERT INTO orders
               (id, visitor_id, status, subtotal, currency, created_at, paid_at,
                is_test, customer_name, customer_email, customer_phone,
                shipping_address, payment_method)
               VALUES (?, ?, ?, ?, 'INR', ?, ?, ?, ?, ?, ?, ?, ?)""",
            (order_id, visitor_id, status, total_cents / 100, created_at, paid_at,
             1 if is_demo else 0, customer_name, customer_email, customer_phone,
             shipping_address, payment_method),
        )
        for item in normalized:
            db.execute(
                """INSERT INTO order_items
                   (order_id, product_id, try_on_id, quantity, unit_price)
                   VALUES (?, ?, ?, ?, ?)""",
                (order_id, item["product"]["product_id"], item["try_on_id"],
                 item["quantity"], item["unit_price"]),
            )
        if is_demo:
            record_purchase_events(db, order_id)
        db.commit()
    except Exception:
        db.rollback()
        current_app.logger.exception("Could not create storefront order")
        return jsonify({"error": "We could not place your order. Please try again."}), 500

    attribution = None
    if is_demo:
        try:
            attribution = resolve_order_attribution(
                db, order_id, model="linear",
                window_days=current_app.config["ATTRIBUTION_WINDOW_DAYS"],
            )
        except Exception:
            current_app.logger.exception("Order placed but attribution calculation failed")

    response = jsonify({
        "order_id": order_id,
        "status": status,
        "subtotal": total_cents / 100,
        "currency": "INR",
        "demo_order": is_demo,
        "message": (
            "Demo checkout complete. No real payment was taken."
            if is_demo else
            "Order request received. Online payment is not configured; this order is awaiting confirmation."
        ),
        "attribution": attribution,
    })
    response.status_code = 201
    if is_new:
        attach_visitor_cookie(response, visitor_id)
    return response


@bp.get("/api/store/orders/<order_id>")
def get_order_status(order_id):
    """Public confirmation only; do not return addresses or payment secrets."""
    visitor_id, is_new = get_or_create_visitor_id()
    order = get_db().execute(
        """SELECT id, status, subtotal, currency, created_at,
                  paid_at, is_test FROM orders WHERE id = ? AND visitor_id = ?""",
        (order_id, visitor_id),
    ).fetchone()
    if not order:
        return jsonify({"error": "Order not found"}), 404
    rows = get_db().execute(
        """SELECT product_id, quantity, unit_price FROM order_items
           WHERE order_id = ? ORDER BY id""",
        (order_id,),
    ).fetchall()
    response = jsonify({"order": dict(order), "items": [dict(row) for row in rows]})
    if is_new:
        attach_visitor_cookie(response, visitor_id)
    return response
