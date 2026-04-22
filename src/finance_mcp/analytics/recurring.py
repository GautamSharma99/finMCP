"""Subscription / recurring-charge detection.

A merchant is flagged recurring if:

- It has at least ``min_occurrences`` debit transactions in the
  lookback window, AND
- The median gap between consecutive charges is 20-370 days
  (weekly/monthly/quarterly/yearly), AND
- The gaps are reasonably consistent (coefficient of variation ≤ 0.5).
"""

from __future__ import annotations

import statistics
from datetime import date, timedelta
from decimal import Decimal
from typing import NamedTuple

from finance_mcp.storage.models import RecurringTxn
from finance_mcp.storage.repository import Repository


class _Stats(NamedTuple):
    cadence: int
    mean_gap: float
    cv: float


def _cadence_stats(sorted_dates: list[date]) -> _Stats | None:
    if len(sorted_dates) < 2:
        return None
    gaps = [
        (sorted_dates[i] - sorted_dates[i - 1]).days for i in range(1, len(sorted_dates))
    ]
    gaps = [g for g in gaps if g > 0]
    if not gaps:
        return None
    mean = statistics.fmean(gaps)
    cadence = round(statistics.median(gaps))
    cv = statistics.pstdev(gaps) / mean if mean > 0 else 1.0
    return _Stats(cadence=cadence, mean_gap=mean, cv=cv)


def detect_recurring(
    repo: Repository,
    min_occurrences: int = 3,
    lookback_months: int = 6,
    today: date | None = None,
) -> list[RecurringTxn]:
    """Detect recurring merchants from transaction history."""
    today = today or date.today()
    lookback_start = today - timedelta(days=lookback_months * 31)

    out: list[RecurringTxn] = []
    for merchant, dates, amounts, cat_id in repo.merchant_history(
        min_occurrences=min_occurrences,
        lookback_start=lookback_start,
    ):
        sorted_pairs = sorted(zip(dates, amounts, strict=True), key=lambda p: p[0])
        dates_sorted = [p[0] for p in sorted_pairs]
        amounts_sorted = [p[1] for p in sorted_pairs]

        stats = _cadence_stats(dates_sorted)
        if stats is None:
            continue
        if not (20 <= stats.cadence <= 370):
            continue
        if stats.cv > 0.5:
            continue

        avg = abs(sum(amounts_sorted, Decimal("0"))) / Decimal(len(amounts_sorted))
        category_name = None
        if cat_id is not None:
            try:
                category_name = repo.get_category(cat_id).name
            except Exception:
                category_name = None

        out.append(
            RecurringTxn(
                merchant=merchant,
                avg_amount=float(avg),
                cadence_days=stats.cadence,
                occurrences=len(dates_sorted),
                last_seen=dates_sorted[-1],
                category_name=category_name,
            )
        )

    out.sort(key=lambda r: r.avg_amount, reverse=True)
    return out


__all__ = ["detect_recurring"]
