import uuid

import pytest

from ahi_attribution import create_app
from ahi_attribution.db import get_db


@pytest.fixture()
def app(tmp_path):
    app = create_app({
        "TESTING": True,
        "DATABASE": str(tmp_path / "test.db"),
        "FRONTEND_ORIGIN": "http://localhost:5173",
        "FRONTEND_BASE_URL": "http://localhost:5173",
        "BACKEND_PUBLIC_URL": "http://localhost:5000",
        "ADMIN_API_KEY": "test-admin-key",
        "PAYMENT_WEBHOOK_SECRET": "test-payment-secret",
        "ATTRIBUTION_WINDOW_DAYS": 30,
        "ENABLE_DEMO_PURCHASES": True,
        "COOKIE_SECURE": False,
    })
    yield app


@pytest.fixture()
def client(app):
    return app.test_client()


def admin_headers():
    return {"X-Admin-Key": "test-admin-key"}


def create_affiliate(client, code, name):
    response = client.post(
        "/api/admin/affiliates",
        headers=admin_headers(),
        json={"code": code, "name": name, "commission_rate": 0.10},
    )
    assert response.status_code == 201, response.get_json()
    return response.get_json()["id"]


def create_link(client, affiliate_id, source, destination="/products/earring-001"):
    response = client.post(
        "/api/admin/referral-links",
        headers=admin_headers(),
        json={
            "affiliate_id": affiliate_id,
            "source": source,
            "campaign": "pytest",
            "destination_path": destination,
        },
    )
    assert response.status_code == 201, response.get_json()
    return response.get_json()["code"]


def test_health(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.get_json()["status"] == "ok"


def test_admin_routes_require_key(client):
    response = client.post(
        "/api/admin/affiliates",
        json={"code": "x", "name": "X"},
    )
    assert response.status_code == 401


def test_referral_journey_and_linear_attribution(client, app):
    affiliate_a = create_affiliate(client, "a", "Influencer A")
    affiliate_b = create_affiliate(client, "b", "Influencer B")
    code_a = create_link(client, affiliate_a, "instagram")
    code_b = create_link(client, affiliate_b, "blog")

    # The same test client retains the same first-party visitor cookie.
    visit_a = client.get(f"/r/{code_a}")
    assert visit_a.status_code == 302
    visit_b = client.get(f"/r/{code_b}")
    assert visit_b.status_code == 302

    # Insert a paid demo order for the same visitor, then resolve it.
    created = client.post(
        "/api/demo/orders",
        headers=admin_headers(),
        json={"subtotal": "2000.00", "currency": "INR"},
    )
    assert created.status_code == 201, created.get_json()
    order_id = created.get_json()["order_id"]

    paid = client.post(
        f"/api/demo/orders/{order_id}/mark-paid",
        headers=admin_headers(),
        json={"model": "linear"},
    )
    assert paid.status_code == 200, paid.get_json()
    credits = paid.get_json()["attribution"]["credits"]
    assert len(credits) == 2
    assert sum(row["credit_fraction"] for row in credits) == pytest.approx(1.0)
    assert sum(row["attributed_revenue"] for row in credits) == pytest.approx(2000.0)
    assert sum(row["commission_amount"] for row in credits) == pytest.approx(200.0)

    report = client.get(
        "/api/admin/analytics/attribution?model=linear",
        headers=admin_headers(),
    )
    assert report.status_code == 200
    assert len(report.get_json()["affiliates"]) == 2


def test_tracking_accepts_only_product_view_and_try_on_started(client):
    payload = {
        "eventId": str(uuid.uuid4()),
        "eventType": "product_view",
        "productId": "earring-001",
    }
    response = client.post("/api/track/events", json=payload)
    assert response.status_code == 201

    bad = client.post("/api/track/events", json={
        "eventId": str(uuid.uuid4()),
        "eventType": "purchase",
        "productId": "earring-001",
    })
    assert bad.status_code == 400


def test_scale_report_counts_try_on_to_purchase(client, app):
    # Set up a visitor via a tracked product event, then insert an attributed
    # try-on and matching paid order directly to test the reporting relation.
    visitor_id = str(uuid.uuid4())
    try_on_id = str(uuid.uuid4())
    event_id = str(uuid.uuid4())

    with app.app_context():
        db = get_db()
        db.execute(
            """INSERT INTO product_interactions
               (event_id, visitor_id, product_id, try_on_id, event_type,
                metadata, occurred_at)
               VALUES (?, ?, ?, ?, 'try_on_started', '{}', ?)""",
            (event_id, visitor_id, "earring-001", try_on_id, "2026-10-23T10:00:00+00:00"),
        )
        db.execute(
            """INSERT INTO orders
               (id, visitor_id, status, subtotal, currency, created_at, paid_at)
               VALUES (?, ?, 'paid', 1000, 'INR', ?, ?)""",
            ("test-order-1", visitor_id, "2026-10-23T11:00:00+00:00", "2026-10-23T11:00:00+00:00"),
        )
        db.execute(
            """INSERT INTO order_items
               (order_id, product_id, try_on_id, quantity, unit_price)
               VALUES (?, ?, ?, 1, 1000)""",
            ("test-order-1", "earring-001", try_on_id),
        )
        db.commit()

    response = client.get(
        "/api/admin/analytics/scale-friction",
        headers=admin_headers(),
    )
    assert response.status_code == 200
    product = response.get_json()["products"][0]
    assert product["try_on_starts"] == 1
    assert product["purchasing_try_ons"] == 1
    assert product["try_on_to_purchase_rate_percent"] == 100.0
