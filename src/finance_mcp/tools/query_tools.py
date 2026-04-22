"""Transaction query + summary MCP tools."""

from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import Field

from finance_mcp.server import get_repo, mcp
from finance_mcp.storage.models import GroupBy, SummaryRow, Transaction


@mcp.tool
def query_transactions(
    start_date: date | None = None,
    end_date: date | None = None,
    category: str | None = Field(default=None, description="Category name (leaf or parent)"),
    account: str | None = None,
    merchant: str | None = Field(
        default=None, description="Case-insensitive substring of merchant or description"
    ),
    min_amount: float | None = None,
    max_amount: float | None = None,
    limit: int = 100,
) -> list[Transaction]:
    """Filter transactions across accounts. All filters are AND-ed.

    Amounts use the stored sign (debit = negative, credit = positive).
    """
    with get_repo() as repo:
        return repo.query_transactions(
            start_date=start_date,
            end_date=end_date,
            category=category,
            account=account,
            merchant=merchant,
            min_amount=min_amount,
            max_amount=max_amount,
            limit=limit,
        )


@mcp.tool
def get_spending_summary(
    start_date: date,
    end_date: date,
    group_by: Literal["category", "merchant", "month"] = "category",
) -> list[SummaryRow]:
    """Aggregate transactions within a date range.

    Group by top-level bucket: ``category``, ``merchant``, or ``month``
    (YYYY-MM). Totals preserve sign, so the ordering surfaces the
    largest spending groups first.
    """
    with get_repo() as repo:
        rows = repo.spending_summary(start_date, end_date, group_by)
    return [SummaryRow(group_key=k, total_amount=float(total), txn_count=n) for k, total, n in rows]


# Re-export for static analysis (FastMCP itself doesn't need this).
__all__ = ["GroupBy", "get_spending_summary", "query_transactions"]
