"""Attach AHI attribution and analytics routes to an existing Flask app.

This is designed for the LUMIAR monolith: do not create a second Flask app.
"""
import os
from pathlib import Path

from dotenv import load_dotenv

from .config import load_config
from .db import close_db, init_db


def register_attribution(app):
    """Initialize the tracking database and register its blueprints once."""
    load_dotenv()
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)

    settings = load_config(app.instance_path)

    # In this project, the storefront and API share one domain. Local defaults
    # must therefore point at the Flask server, not Vite's localhost:5173.
    if not os.getenv("FRONTEND_BASE_URL"):
        settings["FRONTEND_BASE_URL"] = "http://localhost:5000"
    if not os.getenv("FRONTEND_ORIGIN"):
        settings["FRONTEND_ORIGIN"] = "http://localhost:5000"
    if not os.getenv("BACKEND_PUBLIC_URL"):
        settings["BACKEND_PUBLIC_URL"] = "http://localhost:5000"

    # Don't overwrite settings that the parent application intentionally set.
    for key, value in settings.items():
        app.config.setdefault(key, value)

    init_db(app)

    if not app.extensions.get("ahi_attribution_teardown_registered"):
        app.teardown_appcontext(close_db)
        app.extensions["ahi_attribution_teardown_registered"] = True

    from .routes.referrals import bp as referrals_bp
    from .routes.tracking import bp as tracking_bp
    from .routes.admin import bp as admin_bp
    from .routes.analytics import bp as analytics_bp
    from .routes.orders import bp as orders_bp
    from .routes.store import bp as store_bp

    for blueprint in (
        referrals_bp,
        tracking_bp,
        admin_bp,
        analytics_bp,
        orders_bp,
        store_bp,
    ):
        if blueprint.name not in app.blueprints:
            app.register_blueprint(blueprint)

    # A health route for the shared monolith, unless it already exists.
    if "ahi_attribution_health" not in app.view_functions:
        def health():
            from flask import jsonify
            return jsonify({"status": "ok", "service": "ahi-jewellery-monolith"})

        app.add_url_rule(
            "/api/health",
            endpoint="ahi_attribution_health",
            view_func=health,
            methods=["GET"],
        )

    # Fail fast if production is explicitly enabled with unsafe demo settings.
    if os.getenv("FLASK_ENV", "").lower() == "production":
        if app.config["ADMIN_API_KEY"].startswith("replace-this"):
            raise RuntimeError("Set a strong ADMIN_API_KEY in production")
        if app.config["PAYMENT_WEBHOOK_SECRET"].startswith("replace-this"):
            raise RuntimeError("Set PAYMENT_WEBHOOK_SECRET in production")
        if app.config["ENABLE_DEMO_PURCHASES"]:
            raise RuntimeError("Set ENABLE_DEMO_PURCHASES=false in production")

    return app
