"""Recurring-charge detection tests."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from finance_mcp.analytics.recurring import detect_recurring
from finance_mcp.storage.models import RawTransaction
from finance_mcp.storage.repository import Repository


def _seed_monthly(
    repo: Repository, account_id: int, merchant: str, amount: str, months: int
) -> None:
    start = date(2025, 1, 8)
    rows: list[RawTransaction] = []
    for i in range(months):
        d = date(start.year, start.month + i if start.month + i <= 12 else (start.month + i) - 12,
                 start.day)
        rows.append(
            RawTransaction(
                txn_date=d,
                amount=Decimal(amount),
                raw_description=f"ACH D-{merchant}",
                clean_merchant=merchant,
            )
        )
    repo.bulk_insert_transactions(account_id, rows)


def test_detects_monthly_subscription(repo: Repository) -> None:
    acct = repo.create_account(name="HDFC", type="savings", bank="HDFC")
    assert acct.id is not None
    _seed_monthly(repo, acct.id, "NETFLIX", "-649.00", months=6)

    # Pretend "today" is mid-July so a 7-month lookback covers Jan-Jun.
    today = date(2025, 7, 15)
    out = detect_recurring(repo, min_occurrences=3, lookback_months=7, today=today)
    hits = [r for r in out if r.merchant == "NETFLIX"]
    assert len(hits) == 1
    r = hits[0]
    assert r.occurrences == 6
    assert 25 <= r.cadence_days <= 35
    assert abs(r.avg_amount - 649.0) < 0.01


def test_ignores_one_off_purchases(repo: Repository) -> None:
    acct = repo.create_account(name="HDFC", type="savings", bank="HDFC")
    assert acct.id is not None
    # Two Amazon purchases 2 days apart — not recurring.
    repo.bulk_insert_transactions(
        acct.id,
        [
            RawTransaction(
                txn_date=date(2025, 5, 1),
                amount=Decimal("-2500"),
                raw_description="POS AMAZON INDIA",
                clean_merchant="AMAZON INDIA",
            ),
            RawTransaction(
                txn_date=date(2025, 5, 3),
                amount=Decimal("-1200"),
                raw_description="POS AMAZON INDIA",
                clean_merchant="AMAZON INDIA",
            ),
        ],
    )
    today = date(2025, 6, 1)
    out = detect_recurring(repo, min_occurrences=3, today=today)
    assert all(r.merchant != "AMAZON INDIA" for r in out)


def test_irregular_gaps_rejected(repo: Repository) -> None:
    acct = repo.create_account(name="HDFC", type="savings", bank="HDFC")
    assert acct.id is not None
    base = date(2025, 1, 1)
    offsets = [0, 5, 40, 45, 120]  # wildly inconsistent
    rows = [
        RawTransaction(
            txn_date=base + timedelta(days=o),
            amount=Decimal("-100"),
            raw_description="UPI-RANDOM",
            clean_merchant="RANDOM",
        )
        for o in offsets
    ]
    repo.bulk_insert_transactions(acct.id, rows)
    today = date(2025, 6, 1)
    out = detect_recurring(repo, min_occurrences=3, today=today)
    assert all(r.merchant != "RANDOM" for r in out)
