import os
from pathlib import Path

from flask import Flask, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

from .config import load_config
from .db import close_db, init_db


def create_app(test_config=None):
    load_dotenv()
    app = Flask(__name__, instance_relative_config=True)
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    app.config.update(load_config(app.instance_path))
    if test_config:
        app.config.update(test_config)

    CORS(
        app,
        origins=[app.config["FRONTEND_ORIGIN"]],
        supports_credentials=True,
    )

    init_db(app)
    app.teardown_appcontext(close_db)

    from .routes.referrals import bp as referrals_bp
    from .routes.tracking import bp as tracking_bp
    from .routes.admin import bp as admin_bp
    from .routes.analytics import bp as analytics_bp
    from .routes.orders import bp as orders_bp

    app.register_blueprint(referrals_bp)
    app.register_blueprint(tracking_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(analytics_bp)
    app.register_blueprint(orders_bp)

    @app.get("/api/health")
    def health():
        return jsonify({"status": "ok"})

    # Avoid accidentally running with demo secrets in a production deployment.
    if os.getenv("FLASK_ENV", "development").lower() == "production":
        if app.config["ADMIN_API_KEY"].startswith("replace-this"):
            raise RuntimeError("Set a strong ADMIN_API_KEY in production")
        if app.config["PAYMENT_WEBHOOK_SECRET"].startswith("replace-this"):
            raise RuntimeError("Set PAYMENT_WEBHOOK_SECRET in production")
        if app.config["ENABLE_DEMO_PURCHASES"]:
            raise RuntimeError("Disable ENABLE_DEMO_PURCHASES in production")

    return app
