import os
from pathlib import Path


def load_config(instance_path: str) -> dict:
    """Read configuration from environment variables with dev defaults."""
    database_path = os.getenv(
        "DATABASE_PATH",
        str(Path(instance_path) / "ahi_tracking.db"),
    )
    return {
        "DATABASE": database_path,
        "FRONTEND_ORIGIN": os.getenv(
            "FRONTEND_ORIGIN", "http://localhost:5000"
        ).rstrip("/"),
        "FRONTEND_BASE_URL": os.getenv(
            "FRONTEND_BASE_URL", "http://localhost:5000"
        ).rstrip("/"),
        "BACKEND_PUBLIC_URL": os.getenv(
            "BACKEND_PUBLIC_URL", "http://localhost:5000"
        ).rstrip("/"),
        "COOKIE_SECURE": os.getenv("COOKIE_SECURE", "false").lower()
        in {"1", "true", "yes"},
        "ADMIN_API_KEY": os.getenv(
            "ADMIN_API_KEY", "replace-this-development-key"
        ),
        "PAYMENT_WEBHOOK_SECRET": os.getenv(
            "PAYMENT_WEBHOOK_SECRET", "replace-this-payment-webhook-secret"
        ),
        "ATTRIBUTION_WINDOW_DAYS": int(
            os.getenv("ATTRIBUTION_WINDOW_DAYS", "30")
        ),
        "ENABLE_DEMO_PURCHASES": os.getenv(
            "ENABLE_DEMO_PURCHASES", "false"
        ).lower() in {"1", "true", "yes"},
        # Public demo checkout creates clearly marked synthetic test orders.
        # It defaults off in production and never charges a payment method.
        # Safe by default. Enable explicitly only for local/judging demos.
        "ENABLE_DEMO_CHECKOUT": os.getenv(
            "ENABLE_DEMO_CHECKOUT", "false"
        ).lower() in {"1", "true", "yes"},
        "JSON_SORT_KEYS": False,
    }
