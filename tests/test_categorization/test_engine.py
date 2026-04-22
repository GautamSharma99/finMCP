"""Tests for the pure categorization engine (PRD §8.1)."""

from __future__ import annotations

from datetime import datetime

from finance_mcp.categorization.engine import categorize
from finance_mcp.storage.models import Rule


def _rule(
    id: int,
    pattern: str,
    category_id: int,
    priority: int = 50,
    user: bool = False,
    match_type: str = "contains",
) -> Rule:
    return Rule(
        id=id,
        pattern=pattern,
        match_type=match_type,
        category_id=category_id,
        priority=priority,
        is_user_defined=user,
        created_at=datetime(2025, 1, 1),
    )


def test_no_match_returns_none() -> None:
    rules = [_rule(1, "SWIGGY", category_id=10)]
    assert categorize("COFFEE SHOP", "COFFEE SHOP DOWNTOWN", rules) is None


def test_basic_contains_match() -> None:
    rules = [_rule(1, "SWIGGY", category_id=10)]
    match = categorize("SWIGGY", "UPI-SWIGGY-...", rules)
    assert match is not None and match.category_id == 10


def test_priority_orders_by_number() -> None:
    # Two rules match; lower priority number should win.
    rules = [
        _rule(1, "SWIGGY", category_id=10, priority=60),
        _rule(2, "SWIGGY", category_id=20, priority=30),
    ]
    match = categorize("SWIGGY", "UPI-SWIGGY", rules)
    assert match is not None and match.category_id == 20


def test_user_rule_beats_default_at_same_priority() -> None:
    rules = [
        _rule(1, "SWIGGY", category_id=10, priority=50, user=False),
        _rule(2, "SWIGGY", category_id=99, priority=50, user=True),
    ]
    match = categorize("SWIGGY", "UPI-SWIGGY", rules)
    assert match is not None and match.category_id == 99


def test_falls_back_to_raw_description() -> None:
    rules = [_rule(1, "NETFLIX", category_id=77)]
    # clean_merchant empty; match should come from raw_description.
    match = categorize("", "ACH D-NETFLIX SUBSCRIPTION", rules)
    assert match is not None and match.category_id == 77


def test_specific_before_generic_when_priority_set() -> None:
    # "SWIGGY INSTAMART" → Groceries (priority 30);
    # "SWIGGY" → Food Delivery (priority 50). Both match the instamart text,
    # but the more specific (lower priority number) wins.
    rules = [
        _rule(1, "SWIGGY", category_id=10, priority=50),
        _rule(2, "SWIGGY INSTAMART", category_id=20, priority=30),
    ]
    match = categorize("SWIGGY INSTAMART", "UPI-SWIGGY INSTAMART-...", rules)
    assert match is not None and match.category_id == 20


def test_regex_match_type() -> None:
    rules = [_rule(1, r"^UBER\b", category_id=55, match_type="regex")]
    match = categorize("UBER INDIA SYSTEMS", "POS UBER INDIA SYSTEMS", rules)
    assert match is not None and match.category_id == 55


def test_invalid_regex_does_not_crash() -> None:
    rules = [_rule(1, r"[unterminated", category_id=1, match_type="regex")]
    assert categorize("X", "Y", rules) is None


def test_exact_match() -> None:
    rules = [_rule(1, "AMAZON", category_id=9, match_type="exact")]
    # Substring is not an exact match.
    assert categorize("AMAZON INDIA", "amazon india", rules) is None
    assert categorize("AMAZON", "AMAZON", rules) is not None
