"""Rule-management MCP tools."""

from __future__ import annotations

from typing import Literal

from finance_mcp.categorization.rules import create_user_rule
from finance_mcp.errors import CategoryNotFoundError
from finance_mcp.server import get_repo, mcp
from finance_mcp.storage.models import OperationResult, Rule


@mcp.tool
def create_rule(
    pattern: str,
    category_name: str,
    match_type: Literal["contains", "regex", "exact"] = "contains",
    priority: int = 50,
) -> Rule:
    """Create a user-defined categorization rule.

    Lower ``priority`` wins on ties. User-defined rules beat built-ins
    when priorities are equal.
    """
    with get_repo() as repo:
        try:
            return create_user_rule(
                repo,
                pattern=pattern,
                category_name=category_name,
                match_type=match_type,
                priority=priority,
            )
        except CategoryNotFoundError as exc:
            # Surface as a real exception so the client sees a tool error.
            raise ValueError(f"unknown category: {exc}") from exc


@mcp.tool
def list_rules(user_only: bool = False) -> list[Rule]:
    """Return categorization rules sorted by priority then user-first."""
    with get_repo() as repo:
        return repo.list_rules(user_only=user_only)


@mcp.tool
def delete_rule(rule_id: int) -> OperationResult:
    """Delete a categorization rule by id."""
    with get_repo() as repo:
        affected = repo.delete_rule(rule_id)
    if affected == 0:
        return OperationResult(success=False, message=f"no such rule: {rule_id}")
    return OperationResult(success=True, affected=affected, message=f"deleted rule {rule_id}")
