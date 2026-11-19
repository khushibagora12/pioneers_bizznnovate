# Pioneers Bizznnovate — LUMIAR storefront, AR, cart and attribution analytics

This repository is a single Flask monolith. The existing jewellery catalogue and AR try-on are preserved, with a local cart, demo checkout/order records, multi-touch attribution, and an admin analytics dashboard added.

## Features

- Existing product catalogue and virtual try-on.
- Cart on the catalogue and try-on pages; cart persists in browser local storage.
- Checkout form captures delivery details and validates product IDs/prices on the Flask server.
- Demo checkout creates a clearly labelled test order and does not charge a payment method.
- Orders and order items preserve product IDs and `try_on_id` so purchases can be associated with try-on starts.
- Server-generated `purchase` interaction events; the browser cannot declare an order paid by submitting an analytics event.
- Referral links and click/touchpoint history.
- First-touch, last-touch and linear multi-touch attribution.
- Admin analytics page: `/admin/analytics`.
- Dashboard views for real vs demo revenue/commission, order status, affiliates/referral links, product views, try-on starts and try-on-to-purchase analysis.

## Local setup

```bash
python -m venv .venv
source .venv/bin/activate       # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env` and replace the development `ADMIN_API_KEY` and `PAYMENT_WEBHOOK_SECRET` with generated secrets. Never commit `.env`.

Start the single Flask app:

```bash
python app.py
```

Visit:

- Storefront: `http://localhost:5000/`
- Cart and checkout: `http://localhost:5000/cart`
- Admin sales/attribution/scale-friction dashboard: `http://localhost:5000/admin/analytics`
- Health endpoint: `http://localhost:5000/api/health`

In the admin page, enter `ADMIN_API_KEY` from your local `.env` and select **Connect dashboard**. From there you can register affiliates, create referral links, switch attribution models, review sales/orders, and inspect product-level try-on-to-purchase signals.

Seed sample affiliates and referral links in the same database:

```bash
python seed_demo.py
```

Then open `http://localhost:5000/r/demo-insta-a` and `http://localhost:5000/r/demo-blog-b` in the same browser profile. They record referral touchpoints and redirect to the actual AR product route.

## Demo checkout vs real checkout

The server defaults `ENABLE_DEMO_CHECKOUT` to `false` unless explicitly configured. In local `.env`, the example sets it to `true` for development. `ENABLE_DEMO_CHECKOUT=true` enables a simulated storefront checkout. Every such order is recorded with `is_test=1`; the UI explicitly tells the user no payment is collected, and the admin dashboard reports demo and real figures separately. This is only for prototypes, judging and local testing. It is not a payment gateway.

With `ENABLE_DEMO_CHECKOUT=false`, the checkout records a pending order request. It is not a paid purchase and is not attributed as revenue until a trusted payment/order integration confirms payment.

For a real shop, connect the existing checkout flow to a payment provider and call the internal payment-confirmation logic only after verifying the provider's webhook signature. Do not enable public simulated checkout for normal production sales.

## Admin dashboard

Open `/admin/analytics`, enter the `ADMIN_API_KEY` from `.env`/Render, and select **Connect dashboard**. The key is sent only in request headers and retained in the browser tab's session storage. All reporting and management APIs still require the key.

The admin page supports:

- Creating affiliate records with a commission rate.
- Creating and copying referral links.
- Choosing first-touch, last-touch or linear attribution for reporting.
- Reviewing credited real orders/revenue/commission separately from demo/test records.
- Reviewing recent orders and pending order requests (pending requests are not shown as paid revenue).
- Reviewing product views, try-on starts and purchases tied to the same `try_on_id`.
- Opening the admin page from the storefront header or footer.

Set only one attribution model as the official model for commission settlement. Other models are alternatives for analysis, not additional commissions.

## Tracking contract with the AR code

The frontend emits only:

- `product_view` when the selected product/try-on page loads successfully.
- `try_on_started` after camera and landmark setup succeeds, with a unique `tryOnId`.

The backend emits `purchase` when the order/payment flow marks an order paid. It is deliberately rejected by the public `/api/track/events` endpoint.

Cart line items carry the most recent matching `tryOnId` when one exists. The checkout backend verifies that the try-on ID was recorded for the same visitor and product before storing it on the order item. If a visitor adds an item without a try-on, it can still be ordered, but it will not count as a try-on-to-purchase conversion.

Product identifiers are namespaced (`earrings:1`, `shades:1`) because the existing catalogue uses numeric IDs that can overlap across categories.

## Render deployment

Continue deploying the existing GitHub repository and existing Render service; don't create a second app. Keep the current start command:

```bash
gunicorn app:app
```

Set environment variables in Render (don't upload `.env`):

```text
FLASK_ENV=production
FRONTEND_BASE_URL=https://ahi-jewelry.onrender.com
FRONTEND_ORIGIN=https://ahi-jewelry.onrender.com
BACKEND_PUBLIC_URL=https://ahi-jewelry.onrender.com
COOKIE_SECURE=true
ADMIN_API_KEY=<new strong secret>
PAYMENT_WEBHOOK_SECRET=<different new strong secret>
ENABLE_DEMO_PURCHASES=false
ENABLE_DEMO_CHECKOUT=true
```

`ENABLE_DEMO_CHECKOUT=true` is shown here only if you need a public demo checkout for a presentation. It creates only test records, but still allows people to generate test orders. Set it to `false` when connecting real payment processing or after the demo.

SQLite must live on persistent storage on Render. If you have attached a Render disk mounted at `/var/data`, configure:

```text
DATABASE_PATH=/var/data/ahi_tracking.db
```

Only use that path if the disk exists and is mounted there. SQLite on an ephemeral filesystem may be lost on restart/redeploy. If a persistent disk is unavailable or write concurrency grows, migrate to a hosted PostgreSQL database.

## Tests

Run:

```bash
python -m pytest -q
```

The tests cover the existing referral/attribution calculation paths. Also manually test the user journey: open a tracked link, try on a product, add it to the bag, submit the demo checkout, and verify the resulting test order and attribution in `/admin/analytics`.

## Analytics limitations

The current implementation has only product views, try-on starts and backend purchases. It does not record add-to-cart or try-on-completed events, by design. Consequently, it reports try-on-to-purchase association, not cart abandonment or AR completion rate. A low conversion rate is a signal for investigation, not proof of incorrect product scale.
