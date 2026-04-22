"""Analytics: period compare, budget status, net worth."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from finance_mcp.analytics.aggregations import (
    budget_status_for_month,
    compare_periods,
    net_worth,
)
from finance_mcp.storage.models import RawTransaction
from finance_mcp.storage.repository import Repository


def _seed_txns(repo: Repository, account_id: int, data: list[tuple[date, str, str, str]]) -> None:
    repo.bulk_insert_transactions(
        account_id,
        [
            RawTransaction(
                txn_date=d,
                amount=Decimal(amt),
                raw_description=desc,
                clean_merchant=merchant,
            )
            for d, amt, desc, merchant in data
        ],
    )


def test_compare_periods_by_category(repo: Repository) -> None:
    acct = repo.create_account(name="HDFC", type="savings", bank="HDFC")
    assert acct.id is not None

    # Jan: Swiggy 500 + Zomato 300 = 800 on Food Delivery.
    # Feb: Swiggy 200. Drop of 600 on Food Delivery.
    _seed_txns(
        repo,
        acct.id,
        [
            (date(2025, 1, 5), "-500", "UPI-SWIGGY-aa@ybl", "SWIGGY"),
            (date(2025, 1, 20), "-300", "UPI-ZOMATO-bb@ybl", "ZOMATO"),
            (date(2025, 2, 10), "-200", "UPI-SWIGGY-cc@ybl", "SWIGGY"),
        ],
    )
    rows = compare_periods(
        repo,
        period_a_start=date(2025, 1, 1),
        period_a_end=date(2025, 1, 31),
        period_b_start=date(2025, 2, 1),
        period_b_end=date(2025, 2, 28),
        group_by="category",
    )
    food = next(r for r in rows if r.group_key == "Food Delivery")
    assert food.period_a_total == -800
    assert food.period_b_total == -200
    assert food.delta == 600


def test_budget_status_for_month(repo: Repository) -> None:
    acct = repo.create_account(name="HDFC", type="savings", bank="HDFC")
    assert acct.id is not None
    food = repo.find_category_by_name("Food Delivery")
    assert food is not None and food.id is not None

    repo.upsert_budget(
        category_id=food.id,
        amount=1000,
        period="monthly",
        start_date=date(2025, 1, 1),
    )
    _seed_txns(
        repo,
        acct.id,
        [
            (date(2025, 1, 5), "-500", "UPI-SWIGGY-aa", "SWIGGY"),
            (date(2025, 1, 20), "-200", "UPI-ZOMATO-bb", "ZOMATO"),
        ],
    )
    rows = budget_status_for_month(repo, 2025, 1)
    assert len(rows) == 1
    b = rows[0]
    assert b.category_name == "Food Delivery"
    assert b.budgeted == 1000
    assert b.spent == 700
    assert b.remaining == 300
    assert 69 < b.utilization_pct < 71


def test_net_worth(repo: Repository) -> None:
    savings = repo.create_account(name="HDFC S", type="savings", bank="HDFC")
    card = repo.create_account(name="ICICI CC", type="credit_card", bank="ICICI")
    assert savings.id is not None and card.id is not None

    _seed_txns(
        repo,
        savings.id,
        [
            (date(2025, 1, 1), "100000", "NEFT CR-ACME SALARY", "SALARY"),
            (date(2025, 1, 10), "-15000", "NEFT-LANDLORD RENT", "RENT"),
        ],
    )
    _seed_txns(
        repo,
        card.id,
        [
            (date(2025, 1, 5), "-5000", "AMAZON INDIA", "AMAZON"),
            (date(2025, 1, 6), "-1000", "UBER INDIA", "UBER"),
        ],
    )
    nw = net_worth(repo, as_of=date(2025, 1, 31))
    assert nw.total_assets == 85000  # 100k - 15k rent
    assert nw.total_liabilities == 6000
    assert nw.net_worth == 79000
