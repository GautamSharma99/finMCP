"""Goal MCP tools."""

from __future__ import annotations

from datetime import date

from finance_mcp.server import get_repo, mcp
from finance_mcp.storage.models import Goal, GoalProgress


@mcp.tool
def set_goal(
    name: str,
    target_amount: float,
    deadline: date | None = None,
    linked_account: str | None = None,
) -> Goal:
    """Create or update a savings goal.

    If ``linked_account`` is provided, its current positive balance is
    used to track progress toward the target.
    """
    with get_repo() as repo:
        linked_id: int | None = None
        if linked_account:
            acct = repo.get_account_by_name(linked_account)
            if acct is None:
                raise ValueError(f"unknown account: {linked_account!r}")
            linked_id = acct.id
        return repo.upsert_goal(
            name=name,
            target_amount=target_amount,
            deadline=deadline,
            linked_account_id=linked_id,
        )


@mcp.tool
def get_goal_progress(goal_name: str | None = None) -> list[GoalProgress]:
    """Return progress rows for one or all goals."""
    with get_repo() as repo:
        goals = [repo.get_goal_by_name(goal_name)] if goal_name else repo.list_goals()
        out: list[GoalProgress] = []
        for g in goals:
            current = g.current_amount
            # If linked to an account, use that account's running net
            # as the current amount.
            if g.linked_account_id is not None:
                assets, _ = repo.net_worth_as_of(date.today())
                current = max(float(assets), 0.0)
            target = g.target_amount
            pct = (current / target * 100) if target > 0 else 0.0
            on_track = pct >= 50 if g.deadline is None else None
            out.append(
                GoalProgress(
                    name=g.name,
                    target_amount=target,
                    current_amount=current,
                    progress_pct=pct,
                    deadline=g.deadline,
                    on_track=on_track,
                )
            )
        return out
