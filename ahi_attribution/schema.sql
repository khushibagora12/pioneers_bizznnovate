PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS affiliates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    commission_rate REAL NOT NULL DEFAULT 0.10
        CHECK (commission_rate >= 0 AND commission_rate <= 1),
    active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0, 1)),
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS referral_links (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT UNIQUE NOT NULL,
    affiliate_id INTEGER NOT NULL,
    source TEXT NOT NULL,
    campaign TEXT,
    destination_path TEXT NOT NULL,
    active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0, 1)),
    created_at TEXT NOT NULL,
    FOREIGN KEY (affiliate_id) REFERENCES affiliates(id)
);

CREATE TABLE IF NOT EXISTS referral_touchpoints (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id TEXT UNIQUE NOT NULL,
    visitor_id TEXT NOT NULL,
    session_id TEXT,
    referral_link_id INTEGER,
    affiliate_id INTEGER,
    source TEXT,
    campaign TEXT,
    occurred_at TEXT NOT NULL,
    FOREIGN KEY (referral_link_id) REFERENCES referral_links(id),
    FOREIGN KEY (affiliate_id) REFERENCES affiliates(id)
);

CREATE INDEX IF NOT EXISTS idx_touchpoints_visitor_time
    ON referral_touchpoints(visitor_id, occurred_at, id);
CREATE INDEX IF NOT EXISTS idx_touchpoints_affiliate
    ON referral_touchpoints(affiliate_id, occurred_at);

-- Only product_view and try_on_started are accepted from the browser.
-- Purchase events are inserted by the trusted order/payment backend.
CREATE TABLE IF NOT EXISTS product_interactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id TEXT UNIQUE NOT NULL,
    visitor_id TEXT NOT NULL,
    session_id TEXT,
    product_id TEXT NOT NULL,
    try_on_id TEXT,
    event_type TEXT NOT NULL CHECK (
        event_type IN ('product_view', 'try_on_started', 'purchase')
    ),
    metadata TEXT NOT NULL DEFAULT '{}',
    occurred_at TEXT NOT NULL,
    order_id TEXT,
    FOREIGN KEY (order_id) REFERENCES orders(id)
);

CREATE INDEX IF NOT EXISTS idx_interactions_product_event_time
    ON product_interactions(product_id, event_type, occurred_at);
CREATE INDEX IF NOT EXISTS idx_interactions_visitor_time
    ON product_interactions(visitor_id, occurred_at);
CREATE INDEX IF NOT EXISTS idx_interactions_try_on
    ON product_interactions(try_on_id);

CREATE TABLE IF NOT EXISTS orders (
    id TEXT PRIMARY KEY,
    visitor_id TEXT NOT NULL,
    status TEXT NOT NULL CHECK (
        status IN ('pending', 'paid', 'cancelled', 'refunded')
    ),
    subtotal REAL NOT NULL CHECK (subtotal >= 0),
    currency TEXT NOT NULL DEFAULT 'INR',
    created_at TEXT NOT NULL,
    paid_at TEXT,
    is_test INTEGER NOT NULL DEFAULT 0 CHECK (is_test IN (0, 1)),
    customer_name TEXT,
    customer_email TEXT,
    customer_phone TEXT,
    shipping_address TEXT,
    payment_method TEXT NOT NULL DEFAULT 'unconfigured'
);

CREATE INDEX IF NOT EXISTS idx_orders_visitor_paid
    ON orders(visitor_id, status, paid_at);

CREATE TABLE IF NOT EXISTS order_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id TEXT NOT NULL,
    product_id TEXT NOT NULL,
    try_on_id TEXT,
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    unit_price REAL NOT NULL CHECK (unit_price >= 0),
    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_order_items_product_tryon
    ON order_items(product_id, try_on_id);

-- One run per order/model. This lets us remember no-touchpoint results too.
CREATE TABLE IF NOT EXISTS attribution_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id TEXT NOT NULL,
    model TEXT NOT NULL CHECK (
        model IN ('first_touch', 'last_touch', 'linear')
    ),
    window_days INTEGER NOT NULL,
    status TEXT NOT NULL CHECK (
        status IN ('completed', 'no_touchpoints')
    ),
    calculated_at TEXT NOT NULL,
    UNIQUE(order_id, model),
    FOREIGN KEY (order_id) REFERENCES orders(id)
);

CREATE TABLE IF NOT EXISTS attribution_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER NOT NULL,
    affiliate_id INTEGER NOT NULL,
    credit_fraction REAL NOT NULL CHECK (
        credit_fraction >= 0 AND credit_fraction <= 1
    ),
    attributed_revenue REAL NOT NULL CHECK (attributed_revenue >= 0),
    commission_rate_applied REAL NOT NULL CHECK (
        commission_rate_applied >= 0 AND commission_rate_applied <= 1
    ),
    commission_amount REAL NOT NULL CHECK (commission_amount >= 0),
    touchpoint_ids_json TEXT NOT NULL DEFAULT '[]',
    FOREIGN KEY (run_id) REFERENCES attribution_runs(id) ON DELETE CASCADE,
    FOREIGN KEY (affiliate_id) REFERENCES affiliates(id),
    UNIQUE(run_id, affiliate_id)
);

CREATE INDEX IF NOT EXISTS idx_attribution_model_affiliate
    ON attribution_results(run_id, affiliate_id);
