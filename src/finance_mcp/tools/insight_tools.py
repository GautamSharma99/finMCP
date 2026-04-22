"""Insight MCP tools: period comparisons, recurring detection, net worth."""

from __future__ import annotations

from datetime import date
from typing import Literal

from finance_mcp.analytics.aggregations import compare_periods as _compare_periods
from finance_mcp.analytics.aggregations import net_worth as _net_worth
from finance_mcp.analytics.recurring import detect_recurring as _detect_recurring
from finance_mcp.server import get_repo, mcp
from finance_mcp.storage.models import ComparisonRow, NetWorth, RecurringTxn


@mcp.tool
def compare_periods(
    period_a_start: date,
    period_a_end: date,
    period_b_start: date,
    period_b_end: date,
    group_by: Literal["category", "merchant", "month"] = "category",
) -> list[ComparisonRow]:
    """Compare totals between two windows, grouped by category/merchant/month."""
    with get_repo() as repo:
        return _compare_periods(
            repo, period_a_start, period_a_end, period_b_start, period_b_end, group_by
        )


@mcp.tool
def detect_recurring(
    min_occurrences: int = 3,
    lookback_months: int = 6,
) -> list[RecurringTxn]:
    """Detect likely recurring subscriptions across all accounts."""
    with get_repo() as repo:
        return _detect_recurring(
            repo, min_occurrences=min_occurrences, lookback_months=lookback_months
        )


@mcp.tool
def get_net_worth(as_of: date | None = None) -> NetWorth:
    """Return the net worth snapshot on or before a given date (today by default)."""
    with get_repo() as repo:
        return _net_worth(repo, as_of or date.today())
