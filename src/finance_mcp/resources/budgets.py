"""`finance://budgets/current` resource."""

from __future__ import annotations

import json
from datetime import date

from finance_mcp.analytics.aggregations import budget_status_for_month
from finance_mcp.server import get_repo, mcp


@mcp.resource("finance://budgets/current")
def budgets_current() -> str:
    """Active monthly budgets with utilisation for the current month (JSON)."""
    today = date.today()
    with get_repo() as repo:
        statuses = budget_status_for_month(repo, today.year, today.month)
    return json.dumps(
        {
            "month": f"{today.year}-{today.month:02d}",
            "budgets": [s.model_dump() for s in statuses],
        },
        indent=2,
        default=str,
    )
