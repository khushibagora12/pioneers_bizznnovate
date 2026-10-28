import sqlite3
from pathlib import Path

from flask import current_app, g

_CONNECTION_KEY = "ahi_attribution_db"


def get_db() -> sqlite3.Connection:
    """Return a request-scoped SQLite connection for attribution only."""
    connection = g.get(_CONNECTION_KEY)
    if connection is None:
        db_path = current_app.config["DATABASE"]
        if db_path != ":memory:":
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(db_path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 10000")
        if db_path != ":memory:":
            connection.execute("PRAGMA journal_mode = WAL")
        setattr(g, _CONNECTION_KEY, connection)
    return connection


def close_db(_error=None) -> None:
    connection = g.pop(_CONNECTION_KEY, None)
    if connection is not None:
        connection.close()


def _columns(connection, table_name):
    return {row["name"] for row in connection.execute(f"PRAGMA table_info({table_name})")}


def _migrate_orders(connection):
    """Add checkout/customer fields to existing development databases."""
    existing = _columns(connection, "orders")
    additions = {
        "is_test": "INTEGER NOT NULL DEFAULT 0 CHECK (is_test IN (0, 1))",
        "customer_name": "TEXT",
        "customer_email": "TEXT",
        "customer_phone": "TEXT",
        "shipping_address": "TEXT",
        "payment_method": "TEXT NOT NULL DEFAULT 'unconfigured'",
    }
    for name, definition in additions.items():
        if name not in existing:
            connection.execute(f"ALTER TABLE orders ADD COLUMN {name} {definition}")


def _migrate_interactions(connection):
    """Ensure purchase events can be stored, preserving existing event rows."""
    table = connection.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='product_interactions'"
    ).fetchone()
    columns = _columns(connection, "product_interactions")
    schema_sql = (table["sql"] or "").lower() if table else ""
    if "purchase" in schema_sql and "order_id" in columns:
        return

    # Old schema had a CHECK constraint allowing only product_view and
    # try_on_started. Rebuild the table to add backend-only purchase events.
    for index_name in (
        "idx_interactions_product_event_time",
        "idx_interactions_visitor_time",
        "idx_interactions_try_on",
        "idx_interactions_order",
    ):
        connection.execute(f"DROP INDEX IF EXISTS {index_name}")

    connection.execute("ALTER TABLE product_interactions RENAME TO product_interactions_legacy")
    connection.execute("""
        CREATE TABLE product_interactions (
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
        )
    """)
    connection.execute("""
        INSERT INTO product_interactions
            (id, event_id, visitor_id, session_id, product_id, try_on_id,
             event_type, metadata, occurred_at, order_id)
        SELECT id, event_id, visitor_id, session_id, product_id, try_on_id,
               event_type, metadata, occurred_at, NULL
        FROM product_interactions_legacy
    """)
    connection.execute("DROP TABLE product_interactions_legacy")
    connection.execute("CREATE INDEX idx_interactions_product_event_time ON product_interactions(product_id, event_type, occurred_at)")
    connection.execute("CREATE INDEX idx_interactions_visitor_time ON product_interactions(visitor_id, occurred_at)")
    connection.execute("CREATE INDEX idx_interactions_try_on ON product_interactions(try_on_id)")
    connection.execute("CREATE INDEX idx_interactions_order ON product_interactions(order_id, event_type)")


def init_db(app) -> None:
    """Create missing tables and migrate an existing SQLite database safely."""
    db_path = app.config["DATABASE"]
    if db_path != ":memory:":
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(db_path, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        schema_path = Path(__file__).with_name("schema.sql")
        connection.executescript(schema_path.read_text(encoding="utf-8"))
        _migrate_orders(connection)
        _migrate_interactions(connection)
        connection.execute("CREATE INDEX IF NOT EXISTS idx_interactions_order ON product_interactions(order_id, event_type)")
        connection.commit()
    finally:
        connection.close()
