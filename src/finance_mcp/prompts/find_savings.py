"""`find_savings` prompt."""

from __future__ import annotations

from fastmcp.prompts import Message

from finance_mcp.server import mcp


@mcp.prompt
def find_savings(target_amount: float | None = None) -> list[Message]:
    """Surface cuts the user could make to hit an optional monthly savings target."""
    goal_line = f" My monthly savings target is ₹{target_amount:,.0f}." if target_amount else ""
    return [
        Message(
            role="user",
            content=(
                "Analyse my spending over the last 90 days and identify "
                "3-5 concrete categories or merchants where I'm likely overspending."
                f"{goal_line} Use `get_spending_summary`, `detect_recurring`, and "
                "`compare_periods` tools as needed. For each suggestion give the "
                "expected monthly saving in ₹ and a one-line rationale."
            ),
        )
    ]
