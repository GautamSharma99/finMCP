"""Insight resources: monthly review and rolling 30-day summary."""

from __future__ import annotations

from finance_mcp.analytics.insights import render_last_30_days, render_monthly_report
from finance_mcp.server import get_repo, mcp


@mcp.resource("finance://insights/monthly/{month}")
def monthly_insight(month: str) -> str:
    """Markdown monthly report for a ``YYYY-MM`` month."""
    with get_repo() as repo:
        return render_monthly_report(repo, month)


@mcp.resource("finance://insights/summary/last-30-days")
def last_30_days_summary() -> str:
    """Markdown rolling-30-day summary of spending and net worth."""
    with get_repo() as repo:
        return render_last_30_days(repo)
