import json
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_FLOOR

SUPPORTED_MODELS = {"first_touch", "last_touch", "linear"}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


def parse_timestamp(value: str) -> datetime:
    """Parse an ISO-8601 timestamp and normalize to UTC."""
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def calculate_attribution(touchpoints, model: str) -> list[dict]:
    """Calculate affiliate credit from chronologically sorted touchpoints.

    Policy:
    - first_touch: affiliate on the earliest eligible touchpoint gets 100%.
    - last_touch: affiliate on the latest eligible touchpoint gets 100%.
    - linear: distinct affiliates share credit equally, in first-seen order.

    Multiple visits from one affiliate do not give that affiliate extra weight
    under the linear model. The input is expected to be filtered to valid,
    eligible touchpoints for a single visitor and purchase.
    """
    if model not in SUPPORTED_MODELS:
        raise ValueError(f"Unsupported attribution model: {model}")

    events = sorted(
        touchpoints,
        key=lambda item: (
            parse_timestamp(item["occurred_at"]),
            item.get("id", 0),
        ),
    )
    if not events:
        return []

    if model == "first_touch":
        return [{
            "affiliate_id": events[0]["affiliate_id"],
            "weight": 1.0,
            "touchpoint_ids": [events[0]["id"]],
        }]

    if model == "last_touch":
        return [{
            "affiliate_id": events[-1]["affiliate_id"],
            "weight": 1.0,
            "touchpoint_ids": [events[-1]["id"]],
        }]

    # Linear: aggregate all touchpoint IDs per distinct affiliate.
    grouped = {}
    for event in events:
        affiliate_id = event["affiliate_id"]
        if affiliate_id is None:
            continue
        grouped.setdefault(affiliate_id, []).append(event["id"])

    if not grouped:
        return []

    weight = 1.0 / len(grouped)
    return [
        {
            "affiliate_id": affiliate_id,
            "weight": weight,
            "touchpoint_ids": ids,
        }
        for affiliate_id, ids in grouped.items()
    ]


def allocate_cents(total_cents: int, credits: list[dict]) -> list[int]:
    """Allocate integer cents by weight so allocations sum to the total.

    Any leftover cents are distributed deterministically to the credits with
    the largest fractional remainders. This avoids a one-cent rounding gap.
    """
    if not credits:
        return []
    total_weight = sum(Decimal(str(item["weight"])) for item in credits)
    if total_weight <= 0:
        raise ValueError("Attribution weights must sum to a positive value")

    exact = [
        Decimal(total_cents) * Decimal(str(item["weight"])) / total_weight
        for item in credits
    ]
    floors = [int(value.to_integral_value(rounding=ROUND_FLOOR)) for value in exact]
    remainder = total_cents - sum(floors)
    order = sorted(
        range(len(credits)),
        key=lambda index: (exact[index] - floors[index], -index),
        reverse=True,
    )
    for index in order[:remainder]:
        floors[index] += 1
    return floors


def _result_for_existing_run(db, run_row):
    results = db.execute(
        """SELECT ar.affiliate_id, a.name AS affiliate_name,
                  ar.credit_fraction, ar.attributed_revenue,
                  ar.commission_rate_applied, ar.commission_amount,
                  ar.touchpoint_ids_json
           FROM attribution_results ar
           JOIN affiliates a ON a.id = ar.affiliate_id
           WHERE ar.run_id = ? ORDER BY ar.affiliate_id""",
        (run_row["id"],),
    ).fetchall()
    return {
        "order_id": run_row["order_id"],
        "model": run_row["model"],
        "window_days": run_row["window_days"],
        "status": run_row["status"],
        "already_calculated": True,
        "credits": [
            {
                "affiliate_id": row["affiliate_id"],
                "affiliate_name": row["affiliate_name"],
                "credit_fraction": row["credit_fraction"],
                "attributed_revenue": row["attributed_revenue"],
                "commission_rate_applied": row["commission_rate_applied"],
                "commission_amount": row["commission_amount"],
                "touchpoint_ids": json.loads(row["touchpoint_ids_json"]),
            }
            for row in results
        ],
    }


def resolve_order_attribution(
    db,
    order_id: str,
    model: str = "linear",
    window_days: int = 30,
) -> dict:
    """Resolve attribution for an already-paid order and persist the result.

    Call this only after your trusted order/payment flow has verified payment.
    One run is stored per (order_id, model), including a no-touchpoints result.
    """
    if model not in SUPPORTED_MODELS:
        raise ValueError(f"Unsupported attribution model: {model}")
    if not isinstance(window_days, int) or isinstance(window_days, bool) or window_days < 1:
        raise ValueError("window_days must be a positive integer")

    # Reserve the write transaction so two concurrent requests don't create
    # two attribution runs for the same order and model.
    db.execute("BEGIN IMMEDIATE")
    try:
        order = db.execute(
            """SELECT id, visitor_id, status, subtotal, paid_at
               FROM orders WHERE id = ?""",
            (order_id,),
        ).fetchone()
        if order is None:
            raise ValueError("Order not found")
        if order["status"] != "paid" or not order["paid_at"]:
            raise ValueError("Order must be confirmed as paid")

        existing = db.execute(
            "SELECT * FROM attribution_runs WHERE order_id = ? AND model = ?",
            (order_id, model),
        ).fetchone()
        if existing:
            result = _result_for_existing_run(db, existing)
            db.commit()
            return result

        paid_at = parse_timestamp(order["paid_at"])
        cutoff = paid_at - timedelta(days=window_days)
        raw_touchpoints = db.execute(
            """SELECT id, affiliate_id, occurred_at
               FROM referral_touchpoints
               WHERE visitor_id = ? AND affiliate_id IS NOT NULL
               ORDER BY occurred_at ASC, id ASC""",
            (order["visitor_id"],),
        ).fetchall()

        # Use parsed datetimes for robust timezone/window comparisons. Store
        # timestamps in UTC throughout the app.
        touchpoints = []
        for row in raw_touchpoints:
            occurred_at = parse_timestamp(row["occurred_at"])
            if cutoff <= occurred_at <= paid_at:
                touchpoints.append(dict(row))

        # Keep each touchpoint's affiliate history even if an affiliate is
        # deactivated after the referral occurred; don't erase historical credit.
        credits = calculate_attribution(touchpoints, model)
        calculated_at = utc_now_iso()
        status = "completed" if credits else "no_touchpoints"
        cursor = db.execute(
            """INSERT INTO attribution_runs
               (order_id, model, window_days, status, calculated_at)
               VALUES (?, ?, ?, ?, ?)""",
            (order_id, model, window_days, status, calculated_at),
        )
        run_id = cursor.lastrowid

        if not credits:
            db.commit()
            return {
                "order_id": order_id,
                "model": model,
                "window_days": window_days,
                "status": "no_touchpoints",
                "already_calculated": False,
                "credits": [],
            }

        # This MVP attributes the full order subtotal. For production, align
        # the revenue basis with business policy (discounts, tax, shipping,
        # refunds) and snapshot the applicable commission rules.
        total_cents = int(
            (Decimal(str(order["subtotal"])) * 100).quantize(Decimal("1"))
        )
        allocated_cents = allocate_cents(total_cents, credits)

        saved_credits = []
        for credit, revenue_cents in zip(credits, allocated_cents):
            affiliate = db.execute(
                "SELECT id, name, commission_rate FROM affiliates WHERE id = ?",
                (credit["affiliate_id"],),
            ).fetchone()
            if affiliate is None:
                raise ValueError("Affiliate referenced by a touchpoint was not found")

            revenue = (Decimal(revenue_cents) / 100).quantize(Decimal("0.01"))
            rate = Decimal(str(affiliate["commission_rate"]))
            commission = (revenue * rate).quantize(Decimal("0.01"))

            db.execute(
                """INSERT INTO attribution_results
                   (run_id, affiliate_id, credit_fraction,
                    attributed_revenue, commission_rate_applied,
                    commission_amount, touchpoint_ids_json)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    run_id,
                    affiliate["id"],
                    credit["weight"],
                    float(revenue),
                    float(rate),
                    float(commission),
                    json.dumps(credit["touchpoint_ids"]),
                ),
            )
            saved_credits.append({
                "affiliate_id": affiliate["id"],
                "affiliate_name": affiliate["name"],
                "credit_fraction": credit["weight"],
                "attributed_revenue": float(revenue),
                "commission_rate_applied": float(rate),
                "commission_amount": float(commission),
                "touchpoint_ids": credit["touchpoint_ids"],
            })

        db.commit()
        return {
            "order_id": order_id,
            "model": model,
            "window_days": window_days,
            "status": "completed",
            "already_calculated": False,
            "credits": saved_credits,
        }
    except Exception:
        db.rollback()
        raise
