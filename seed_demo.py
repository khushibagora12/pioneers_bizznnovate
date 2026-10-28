"""Seed local demo affiliates and referral links for the existing monolith."""
from app import app
from ahi_attribution.db import get_db
from ahi_attribution.services.attribution import utc_now_iso

SAMPLES = [
    {
        "affiliate_code": "creator-a",
        "name": "Demo Influencer A",
        "rate": 0.10,
        "link_code": "demo-insta-a",
        "source": "instagram",
        "campaign": "demo-campaign",
        "destination": "/try-on?category=earrings&product=1",
    },
    {
        "affiliate_code": "creator-b",
        "name": "Demo Influencer B",
        "rate": 0.10,
        "link_code": "demo-blog-b",
        "source": "jewellery-blog",
        "campaign": "demo-campaign",
        "destination": "/try-on?category=earrings&product=2",
    },
]

with app.app_context():
    db = get_db()
    for item in SAMPLES:
        db.execute(
            """INSERT INTO affiliates (code, name, commission_rate, active, created_at)
               VALUES (?, ?, ?, 1, ?)
               ON CONFLICT(code) DO UPDATE SET
                   name = excluded.name,
                   commission_rate = excluded.commission_rate,
                   active = 1""",
            (item["affiliate_code"], item["name"], item["rate"], utc_now_iso()),
        )
        affiliate = db.execute(
            "SELECT id FROM affiliates WHERE code = ?",
            (item["affiliate_code"],),
        ).fetchone()
        db.execute(
            """INSERT INTO referral_links
               (code, affiliate_id, source, campaign, destination_path,
                active, created_at)
               VALUES (?, ?, ?, ?, ?, 1, ?)
               ON CONFLICT(code) DO UPDATE SET
                   affiliate_id = excluded.affiliate_id,
                   source = excluded.source,
                   campaign = excluded.campaign,
                   destination_path = excluded.destination_path,
                   active = 1""",
            (
                item["link_code"], affiliate["id"], item["source"],
                item["campaign"], item["destination"], utc_now_iso(),
            ),
        )
    db.commit()

    print("Seeded sample affiliates and referral links into the monolith database.")
    print("Open both links in the same browser profile:")
    for item in SAMPLES:
        print(f"{app.config['BACKEND_PUBLIC_URL']}/r/{item['link_code']} -> {item['name']}")
