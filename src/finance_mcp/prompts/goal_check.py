"""`goal_check` prompt."""

from __future__ import annotations

from fastmcp.prompts import Message

from finance_mcp.server import mcp


@mcp.prompt
def goal_check(goal_name: str | None = None) -> list[Message]:
    """Progress against a named goal (or all goals) with projected hit date."""
    target = f"the '{goal_name}' goal" if goal_name else "all my savings goals"
    return [
        Message(
            role="user",
            content=(
                f"Report my progress toward {target}. Use `get_goal_progress` to "
                "see current vs target. Compute: on-track/off-track, the average "
                "monthly contribution based on the last 3 months, and a projected "
                "hit date at that rate. Recommend a monthly contribution needed to "
                "hit the deadline if one is set."
            ),
        )
    ]
