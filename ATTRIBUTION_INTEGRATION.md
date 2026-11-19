# Cart, checkout and admin analytics integration guide

This is an addition to the existing LUMIAR Flask monolith. Keep the existing root `app.py`, catalogue, templates, and AR files. The `ahi_attribution` package is registered into the same Flask app by `ahi_attribution.integration.register_attribution(app)`.

## New customer routes

- `GET /cart` — shopping bag and checkout form.
- `POST /api/store/checkout` — validates customer details and product IDs, looks prices up in `service/jewelleryService.py`, creates the order and order items.
- `GET /order-confirmation/<order_id>` — confirmation view scoped to the visitor cookie.
- `GET /api/store/orders/<order_id>` — limited order confirmation data for the matching visitor.

The cart is in `localStorage`, but the backend does not trust cart prices. Every line's price is calculated from the server-side catalogue. `try_on_id` is only retained if it matches a `try_on_started` record for the same visitor and product.

## New admin page and API

- `GET /admin/analytics` — admin dashboard shell.
- `GET /api/admin/analytics/overview` — views, try-on counts, order and revenue summary.
- `GET /api/admin/analytics/attribution?model=linear` — real/demo attribution and commission summary.
- `GET /api/admin/analytics/scale-friction` — product view, try-on-start and try-on-to-purchase measures.
- `GET /api/admin/orders` — recent order status and totals.
- Existing affiliate/link create and list endpoints are used by the dashboard's forms.

Admin APIs require `X-Admin-Key`. The browser dashboard asks the admin to enter the key and keeps it in session storage. Do not place the key in JavaScript source or expose it to customers.

## Demo/real purchase semantics

With `ENABLE_DEMO_CHECKOUT=true`, checkout automatically creates a synthetic paid order marked `is_test=1` and records a backend-generated purchase event. No payment is taken. Demo totals are shown separately from real revenue and commission.

With the setting disabled, checkout creates a pending request and does not create a paid purchase or attribution result. A trusted payment provider/order service must confirm payment before the app records `purchase` and resolves attribution.

`ENABLE_DEMO_PURCHASES` controls the older admin-key-protected demo-order endpoints and must be false in production. `ENABLE_DEMO_CHECKOUT` is a separate public prototype feature flag; turn it off after demos or when a real checkout is connected.

## SQLite schema changes

The database initializer adds customer/order/test columns to existing orders tables and migrates the old `product_interactions` CHECK constraint so backend-only `purchase` events can be stored while preserving existing view and try-on rows. Back up any existing SQLite file before first startup after this update.

## Product scale-friction interpretation

The dashboard compares product views with try-on starts and looks for `try_on_started` sessions that are linked by the same `try_on_id`, visitor, product and purchase window to a paid order. Since `try_on_completed` and `add_to_cart` aren't tracked, this is try-on-to-purchase analysis only. Low conversion does not prove scale confusion.
