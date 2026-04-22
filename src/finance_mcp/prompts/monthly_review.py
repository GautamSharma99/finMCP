"""`monthly_review` prompt."""

from __future__ import annotations

from fastmcp.prompts import Message

from finance_mcp.server import mcp


@mcp.prompt
def monthly_review(month: str) -> list[Message]:
    """Structured monthly financial review for ``YYYY-MM``."""
    return [
        Message(
            role="user",
            content=(
                f"Please review my finances for {month}. "
                f"Use the `finance://insights/monthly/{month}` resource for the "
                "full data dump, then summarise: total income vs expense, top 5 "
                "categories, notable one-off transactions, budget status, a "
                "comparison to the previous month, and 2-3 concrete suggestions "
                "for reducing spend."
            ),
        )
    ]
