"""Budget MCP tools."""

from __future__ import annotations

from datetime import date
from typing import Literal

from finance_mcp.analytics.aggregations import budget_status_for_month
from finance_mcp.server import get_repo, mcp
from finance_mcp.storage.models import Budget, BudgetStatus


@mcp.tool
def set_budget(
    category_name: str,
    amount: float,
    period: Literal["monthly", "quarterly", "yearly"] = "monthly",
    start_date: date | None = None,
) -> Budget:
    """Create or update a budget for a category.

    Upserts by (category, period, start_date). If ``start_date`` is
    omitted, uses the first of the current month.
    """
    if start_date is None:
        today = date.today()
        start_date = date(today.year, today.month, 1)

    with get_repo() as repo:
        cat = repo.find_category_by_name(category_name)
        if cat is None or cat.id is None:
            raise ValueError(f"unknown category: {category_name!r}")
        return repo.upsert_budget(
            category_id=cat.id, amount=amount, period=period, start_date=start_date
        )


@mcp.tool
def get_budget_status(month: str) -> list[BudgetStatus]:
    """Return budget utilisation for a ``YYYY-MM`` month."""
    try:
        year_s, month_s = month.split("-")
        year, m = int(year_s), int(month_s)
    except ValueError as exc:
        raise ValueError(f"expected month as YYYY-MM, got {month!r}") from exc
    with get_repo() as repo:
        return budget_status_for_month(repo, year, m)
