"""Period comparisons and budget utilisation computations.

Pure functions that read through the repository; no direct SQL.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from finance_mcp.storage.models import (
    BudgetStatus,
    ComparisonRow,
    NetWorth,
)
from finance_mcp.storage.repository import Repository


def compare_periods(
    repo: Repository,
    period_a_start: date,
    period_a_end: date,
    period_b_start: date,
    period_b_end: date,
    group_by: str,
) -> list[ComparisonRow]:
    """Side-by-side totals for two windows.

    The union of group keys from both periods is emitted so missing
    groups show as zero on one side.
    """
    a = {k: total for k, total, _ in repo.spending_summary(period_a_start, period_a_end, group_by)}
    b = {k: total for k, total, _ in repo.spending_summary(period_b_start, period_b_end, group_by)}
    keys = sorted(set(a) | set(b))

    rows: list[ComparisonRow] = []
    for k in keys:
        a_val = a.get(k, Decimal("0"))
        b_val = b.get(k, Decimal("0"))
        delta = b_val - a_val
        pct = float(delta / a_val * 100) if a_val != 0 else None
        rows.append(
            ComparisonRow(
                group_key=k,
                period_a_total=float(a_val),
                period_b_total=float(b_val),
                delta=float(delta),
                delta_pct=pct,
            )
        )
    return rows


def budget_status_for_month(
    repo: Repository,
    year: int,
    month: int,
) -> list[BudgetStatus]:
    """Compute utilisation for every active monthly budget in the month."""
    first = date(year, month, 1)
    last = date(year + (1 if month == 12 else 0), (month % 12) + 1, 1)
    # last-day of month = day before `last`:
    from datetime import timedelta

    end_of_month = last - timedelta(days=1)

    out: list[BudgetStatus] = []
    for budget in repo.list_budgets():
        if budget.period != "monthly":
            continue
        # Include budgets whose start_date is on or before the target month.
        if budget.start_date > end_of_month:
            continue

        spend = repo.category_spend(budget.category_id, first, end_of_month)
        budgeted = Decimal(str(budget.amount))
        remaining = budgeted - spend
        util = float(spend / budgeted * 100) if budgeted != 0 else 0.0
        cat = repo.get_category(budget.category_id)
        out.append(
            BudgetStatus(
                category_name=cat.name,
                budgeted=float(budgeted),
                spent=float(spend),
                remaining=float(remaining),
                utilization_pct=util,
            )
        )
    return out


def net_worth(repo: Repository, as_of: date) -> NetWorth:
    """Return `NetWorth` as of the given date."""
    assets, liabilities = repo.net_worth_as_of(as_of)
    return NetWorth(
        as_of=as_of,
        total_assets=float(assets),
        total_liabilities=float(liabilities),
        net_worth=float(assets - liabilities),
    )


__all__ = ["budget_status_for_month", "compare_periods", "net_worth"]
