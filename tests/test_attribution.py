import pytest

from ahi_attribution.services.attribution import (
    allocate_cents,
    calculate_attribution,
)


TOUCHPOINTS = [
    {"id": 1, "affiliate_id": 10, "occurred_at": "2026-10-23T10:00:00+00:00"},
    {"id": 2, "affiliate_id": 20, "occurred_at": "2026-10-23T11:00:00+00:00"},
]


def test_first_touch_assigns_all_credit_to_earliest_affiliate():
    result = calculate_attribution(TOUCHPOINTS, "first_touch")
    assert result == [{"affiliate_id": 10, "weight": 1.0, "touchpoint_ids": [1]}]


def test_last_touch_assigns_all_credit_to_latest_affiliate():
    result = calculate_attribution(TOUCHPOINTS, "last_touch")
    assert result == [{"affiliate_id": 20, "weight": 1.0, "touchpoint_ids": [2]}]


def test_linear_splits_credit_between_distinct_affiliates():
    result = calculate_attribution(TOUCHPOINTS, "linear")
    assert [item["weight"] for item in result] == [0.5, 0.5]
    assert sum(item["weight"] for item in result) == pytest.approx(1.0)


def test_linear_does_not_give_extra_weight_for_repeated_affiliate_clicks():
    repeated = [
        {"id": 1, "affiliate_id": 10, "occurred_at": "2026-10-23T10:00:00+00:00"},
        {"id": 2, "affiliate_id": 10, "occurred_at": "2026-10-23T10:30:00+00:00"},
        {"id": 3, "affiliate_id": 20, "occurred_at": "2026-10-23T11:00:00+00:00"},
    ]
    result = calculate_attribution(repeated, "linear")
    assert [item["affiliate_id"] for item in result] == [10, 20]
    assert [item["weight"] for item in result] == [0.5, 0.5]
    assert result[0]["touchpoint_ids"] == [1, 2]


def test_empty_touchpoints_returns_empty_results():
    assert calculate_attribution([], "linear") == []


def test_unknown_model_is_rejected():
    with pytest.raises(ValueError):
        calculate_attribution(TOUCHPOINTS, "random")


def test_cents_allocation_sums_exactly():
    credits = [
        {"affiliate_id": 1, "weight": 1 / 3},
        {"affiliate_id": 2, "weight": 1 / 3},
        {"affiliate_id": 3, "weight": 1 / 3},
    ]
    allocated = allocate_cents(10000, credits)
    assert sum(allocated) == 10000
