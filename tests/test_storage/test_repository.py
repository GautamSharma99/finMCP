"""Tests for the repository layer."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from finance_mcp.errors import (
    AccountNotFoundError,
    CategoryNotFoundError,
    DuplicateTransactionError,
)
from finance_mcp.storage.models import RawTransaction
from finance_mcp.storage.repository import Repository, compute_dedup_hash

# --- Seeding ---------------------------------------------------------------


def test_default_categories_seeded(repo: Repository) -> None:
    names = {c.name for c in repo.list_categories()}
    # Spot-check that top-level + a few leaves from PRD §4.3 are present.
    assert {"Income", "Salary", "Food & Dining", "Food Delivery", "Uncategorized"} <= names


def test_category_tree_has_parents_and_children(repo: Repository) -> None:
    cats = repo.list_categories()
    by_name = {c.name: c for c in cats}
    food = by_name["Food & Dining"]
    delivery = by_name["Food Delivery"]
    assert food.parent_id is None
    assert delivery.parent_id == food.id


def test_find_category_by_name_case_insensitive(repo: Repository) -> None:
    cat = repo.find_category_by_name("food delivery")
    assert cat is not None
    assert cat.name == "Food Delivery"


def test_find_category_by_name_missing(repo: Repository) -> None:
    assert repo.find_category_by_name("does-not-exist") is None


# --- Accounts --------------------------------------------------------------


def test_create_and_get_account(repo: Repository) -> None:
    acc = repo.create_account(name="HDFC Savings - 1234", type="savings", bank="HDFC")
    assert acc.id is not None
    fetched = repo.get_account(acc.id)
    assert fetched.name == "HDFC Savings - 1234"
    assert fetched.type == "savings"
    assert fetched.currency == "INR"


def test_get_account_missing_raises(repo: Repository) -> None:
    with pytest.raises(AccountNotFoundError):
        repo.get_account(9999)


def test_get_category_missing_raises(repo: Repository) -> None:
    with pytest.raises(CategoryNotFoundError):
        repo.get_category(9999)


def test_account_name_unique(repo: Repository) -> None:
    repo.create_account(name="Dup", type="savings")
    with pytest.raises(Exception):  # IntegrityError subclass  # noqa: B017
        repo.create_account(name="Dup", type="savings")


def test_get_account_by_name(repo: Repository) -> None:
    repo.create_account(name="ICICI CC", type="credit_card", bank="ICICI")
    found = repo.get_account_by_name("ICICI CC")
    assert found is not None and found.type == "credit_card"
    assert repo.get_account_by_name("nope") is None


def test_list_accounts_ordered(repo: Repository) -> None:
    a1 = repo.create_account(name="A", type="savings")
    a2 = repo.create_account(name="B", type="credit_card")
    ids = [a.id for a in repo.list_accounts()]
    assert ids == [a1.id, a2.id]


# --- Categories ------------------------------------------------------------


def test_create_custom_category(repo: Repository) -> None:
    parent = repo.find_category_by_name("Shopping")
    assert parent is not None
    new = repo.create_category(name="Hobbies", parent_id=parent.id)
    assert new.parent_id == parent.id
    assert repo.find_category_by_name("Hobbies") is not None


# --- Dedup hash ------------------------------------------------------------


def test_dedup_hash_stable_and_sensitive() -> None:
    h1 = compute_dedup_hash(1, date(2025, 1, 10), Decimal("-250.00"), "UPI-SWIGGY-abc")
    h2 = compute_dedup_hash(1, date(2025, 1, 10), Decimal("-250.00"), "  UPI-SWIGGY-abc  ")
    h3 = compute_dedup_hash(1, date(2025, 1, 10), Decimal("-250.01"), "UPI-SWIGGY-abc")
    assert len(h1) == 16
    assert h1 == h2, "whitespace normalization should produce same hash"
    assert h1 != h3, "amount differences must change the hash"


# --- Transactions ----------------------------------------------------------


@pytest.fixture
def account_id(repo: Repository) -> int:
    acc = repo.create_account(name="HDFC Savings - Test", type="savings", bank="HDFC")
    assert acc.id is not None
    return acc.id


def _make_raw(
    amount: str = "-250.00",
    desc: str = "UPI-SWIGGY-swiggy@axl",
    day: int = 10,
) -> RawTransaction:
    return RawTransaction(
        txn_date=date(2025, 1, day),
        amount=Decimal(amount),
        raw_description=desc,
        clean_merchant="SWIGGY",
        running_balance=Decimal("12345.67"),
    )


def test_insert_and_get_transaction(repo: Repository, account_id: int) -> None:
    cat = repo.find_category_by_name("Food Delivery")
    assert cat is not None and cat.id is not None
    txn = repo.insert_transaction(
        account_id, _make_raw(), category_id=cat.id, category_source="rule"
    )
    assert txn.id is not None
    fetched = repo.get_transaction(txn.id)
    assert fetched.amount == Decimal("-250.00")
    assert fetched.category_id == cat.id
    assert fetched.category_source == "rule"
    assert fetched.dedup_hash == txn.dedup_hash


def test_duplicate_transaction_raises(repo: Repository, account_id: int) -> None:
    repo.insert_transaction(account_id, _make_raw())
    with pytest.raises(DuplicateTransactionError):
        repo.insert_transaction(account_id, _make_raw())


def test_bulk_insert_counts_duplicates(repo: Repository, account_id: int) -> None:
    rows = [_make_raw(day=10), _make_raw(day=11), _make_raw(day=10)]  # dup on day=10
    inserted, skipped = repo.bulk_insert_transactions(account_id, rows)
    assert (inserted, skipped) == (2, 1)
    assert repo.count_transactions(account_id) == 2


def test_list_and_count_transactions(repo: Repository, account_id: int) -> None:
    for day in (1, 5, 10):
        repo.insert_transaction(account_id, _make_raw(day=day))
    assert repo.count_transactions() == 3
    listed = repo.list_transactions(account_id=account_id)
    # Ordered by txn_date desc
    assert [t.txn_date.day for t in listed] == [10, 5, 1]


def test_set_transaction_category(repo: Repository, account_id: int) -> None:
    txn = repo.insert_transaction(account_id, _make_raw())
    food = repo.find_category_by_name("Food Delivery")
    assert txn.id is not None and food is not None and food.id is not None
    updated = repo.set_transaction_category(txn.id, food.id, source="manual")
    assert updated.category_id == food.id
    assert updated.category_source == "manual"


def test_foreign_key_cascade_on_account_delete(repo: Repository, account_id: int) -> None:
    repo.insert_transaction(account_id, _make_raw())
    # Delete account; ON DELETE CASCADE should remove transactions too.
    repo.connection.execute("DELETE FROM accounts WHERE id = ?", (account_id,))
    assert repo.count_transactions(account_id) == 0
