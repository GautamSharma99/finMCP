"""Markdown renderers for insight resources."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from finance_mcp.analytics.aggregations import budget_status_for_month, net_worth
from finance_mcp.analytics.recurring import detect_recurring
from finance_mcp.storage.repository import Repository


def _fmt_money(value: float | Decimal) -> str:
    v = float(value)
    return f"₹{v:,.0f}" if abs(v) >= 100 else f"₹{v:,.2f}"


def _month_bounds(month: str) -> tuple[date, date]:
    try:
        y, m = (int(x) for x in month.split("-"))
    except ValueError as exc:
        raise ValueError(f"expected YYYY-MM, got {month!r}") from exc
    first = date(y, m, 1)
    next_first = date(y + (1 if m == 12 else 0), (m % 12) + 1, 1)
    last = next_first - timedelta(days=1)
    return first, last


def render_monthly_report(repo: Repository, month: str) -> str:
    """Return a Markdown monthly financial report for ``YYYY-MM``."""
    first, last = _month_bounds(month)
    summary = repo.spending_summary(first, last, "category")

    income = sum((total for _, total, _ in summary if total > 0), Decimal("0"))
    expense = sum((-total for _, total, _ in summary if total < 0), Decimal("0"))
    net = income - expense

    lines: list[str] = [
        f"# Monthly Review — {month}",
        "",
        "## Totals",
        f"- Income: {_fmt_money(income)}",
        f"- Expense: {_fmt_money(expense)}",
        f"- Net: {_fmt_money(net)}",
        "",
        "## Top Spending Categories",
    ]
    top_expenses = sorted(
        [(k, total, n) for k, total, n in summary if total < 0],
        key=lambda t: t[1],
    )[:5]
    if top_expenses:
        for key, total, n in top_expenses:
            lines.append(f"- **{key}** — {_fmt_money(-total)} across {n} txns")
    else:
        lines.append("_No expenses recorded._")

    lines.extend(["", "## Budgets"])
    try:
        y, m = (int(x) for x in month.split("-"))
        statuses = budget_status_for_month(repo, y, m)
    except ValueError:
        statuses = []
    if statuses:
        for s in statuses:
            lines.append(
                f"- {s.category_name}: {_fmt_money(s.spent)} / {_fmt_money(s.budgeted)}"
                f" ({s.utilization_pct:.0f}% used)"
            )
    else:
        lines.append("_No budgets configured._")

    # Recurring
    recurring = detect_recurring(repo, min_occurrences=3, lookback_months=6, today=last)
    if recurring:
        lines.extend(["", "## Recurring Charges (last 6 months)"])
        for r in recurring[:10]:
            lines.append(
                f"- {r.merchant}: {_fmt_money(r.avg_amount)} every ~{r.cadence_days}d"
                f" ({r.occurrences}x)"
            )

    return "\n".join(lines) + "\n"


def render_last_30_days(repo: Repository, today: date | None = None) -> str:
    """Return a Markdown rolling 30-day summary."""
    today = today or date.today()
    start = today - timedelta(days=30)
    summary = repo.spending_summary(start, today, "category")
    nw = net_worth(repo, today)

    lines: list[str] = [
        f"# Rolling 30-Day Summary — {start.isoformat()} to {today.isoformat()}",
        "",
        f"- Net worth: {_fmt_money(nw.net_worth)}"
        f" (assets {_fmt_money(nw.total_assets)}, "
        f"liabilities {_fmt_money(nw.total_liabilities)})",
        "",
        "## Spending by Category",
    ]
    rows = sorted(
        [(k, total, n) for k, total, n in summary if total < 0],
        key=lambda t: t[1],
    )
    if rows:
        for key, total, n in rows[:10]:
            lines.append(f"- {key}: {_fmt_money(-total)} ({n} txns)")
    else:
        lines.append("_No spending recorded._")

    return "\n".join(lines) + "\n"


__all__ = ["render_last_30_days", "render_monthly_report"]
