import hmac
from functools import wraps

from flask import current_app, jsonify, request


def require_admin(view_function):
    """Protect admin routes with an API key for this MVP.

    Replace this with your real user/session authentication before production.
    """
    @wraps(view_function)
    def wrapped(*args, **kwargs):
        expected = current_app.config.get("ADMIN_API_KEY", "")
        supplied = request.headers.get("X-Admin-Key", "")
        if not expected or not hmac.compare_digest(supplied, expected):
            return jsonify({"error": "Admin authentication required"}), 401
        return view_function(*args, **kwargs)

    return wrapped


def require_payment_secret(view_function):
    """Protect internal payment confirmation endpoint.

    In production, use the payment provider's documented webhook signature
    verification rather than relying on a generic shared secret alone.
    """
    @wraps(view_function)
    def wrapped(*args, **kwargs):
        expected = current_app.config.get("PAYMENT_WEBHOOK_SECRET", "")
        supplied = request.headers.get("X-Payment-Webhook-Secret", "")
        if not expected or not hmac.compare_digest(supplied, expected):
            return jsonify({"error": "Invalid payment webhook secret"}), 401
        return view_function(*args, **kwargs)

    return wrapped
