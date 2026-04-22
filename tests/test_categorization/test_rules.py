"""Tests for rule seeding, user-rule precedence, and manual-override protection."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from finance_mcp.categorization.default_rules import DEFAULT_RULES
from finance_mcp.categorization.rules import create_user_rule, seed_default_rules
from finance_mcp.errors import CategoryNotFoundError
from finance_mcp.storage.models import RawTransaction
from finance_mcp.storage.repository import Repository


def test_default_rules_seeded_on_init(repo: Repository) -> None:
    # init_db already runs seed; we expect all default rules persisted.
    assert repo.count_rules() == len(DEFAULT_RULES)


def test_seeding_is_idempotent(repo: Repository) -> None:
    before = repo.count_rules()
    inserted = seed_default_rules(repo)
    assert inserted == 0
    assert repo.count_rules() == before


def test_at_least_30_default_rules() -> None:
    assert len(DEFAULT_RULES) >= 30


def test_user_rule_overrides_default_at_same_priority(repo: Repository) -> None:
    # Default says SWIGGY → Food Delivery. User redirects to Groceries.
    groceries = repo.find_category_by_name("Groceries")
    assert groceries is not None and groceries.id is not None

    create_user_rule(
        repo,
        pattern="SWIGGY",
        category_name="Groceries",
        priority=50,
    )

    # A fresh transaction should land in Groceries.
    acc = repo.create_account(name="HDFC Test", type="savings", bank="HDFC")
    assert acc.id is not None
    raw = RawTransaction(
        txn_date=date(2025, 1, 10),
        amount=Decimal("-400"),
        raw_description="UPI-SWIGGY-swiggy@axl-112233445566",
        clean_merchant="SWIGGY",
    )
    inserted, _ = repo.bulk_insert_transactions(acc.id, [raw])
    assert inserted == 1
    txn = repo.list_transactions(account_id=acc.id)[0]
    assert txn.category_id == groceries.id
    assert txn.category_source == "rule"


def test_rule_for_missing_category_raises(repo: Repository) -> None:
    with pytest.raises(CategoryNotFoundError):
        create_user_rule(repo, pattern="FOO", category_name="NoSuchCategory")


def test_auto_categorize_fills_food_delivery(repo: Repository) -> None:
    acc = repo.create_account(name="HDFC X", type="savings", bank="HDFC")
    assert acc.id is not None
    raw = RawTransaction(
        txn_date=date(2025, 2, 1),
        amount=Decimal("-300"),
        raw_description="UPI-ZOMATO-zomato@ybl-112233",
        clean_merchant="ZOMATO",
    )
    repo.bulk_insert_transactions(acc.id, [raw])
    txn = repo.list_transactions(account_id=acc.id)[0]
    food_delivery = repo.find_category_by_name("Food Delivery")
    assert food_delivery is not None
    assert txn.category_id == food_delivery.id
    assert txn.category_source == "rule"


def test_manual_override_not_replaced_by_rule(repo: Repository) -> None:
    acc = repo.create_account(name="HDFC M", type="savings", bank="HDFC")
    assert acc.id is not None
    raw = RawTransaction(
        txn_date=date(2025, 3, 1),
        amount=Decimal("-300"),
        raw_description="UPI-ZOMATO-zomato@ybl-112233",
        clean_merchant="ZOMATO",
    )
    repo.bulk_insert_transactions(acc.id, [raw])
    txn = repo.list_transactions(account_id=acc.id)[0]
    assert txn.id is not None

    # User manually moves the txn to Restaurants.
    restaurants = repo.find_category_by_name("Restaurants")
    assert restaurants is not None and restaurants.id is not None
    repo.set_transaction_category(txn.id, restaurants.id, source="manual")

    # A subsequent rule-based reassignment attempt must be rejected.
    food_delivery = repo.find_category_by_name("Food Delivery")
    assert food_delivery is not None and food_delivery.id is not None
    updated = repo.set_transaction_category(txn.id, food_delivery.id, source="rule")
    assert updated.category_id == restaurants.id
    assert updated.category_source == "manual"


def test_list_rules_ordered_by_priority_then_user(repo: Repository) -> None:
    rules = repo.list_rules()
    prios = [r.priority for r in rules]
    assert prios == sorted(prios)


def test_delete_rule(repo: Repository) -> None:
    # Add then delete a user rule.
    rule = create_user_rule(repo, pattern="TESTDEL", category_name="General")
    assert rule.id is not None
    affected = repo.delete_rule(rule.id)
    assert affected == 1
    with pytest.raises(KeyError):
        repo.get_rule(rule.id)


def test_list_rules_user_only(repo: Repository) -> None:
    create_user_rule(repo, pattern="MYRULE", category_name="General")
    user_rules = repo.list_rules(user_only=True)
    assert len(user_rules) == 1
    assert user_rules[0].pattern == "MYRULE"
    assert user_rules[0].is_user_defined is True
