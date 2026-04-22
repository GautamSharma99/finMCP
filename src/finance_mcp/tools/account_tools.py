"""Account-related MCP tools."""

from __future__ import annotations

from finance_mcp.server import get_repo, mcp
from finance_mcp.storage.models import Account


@mcp.tool
def list_accounts() -> list[Account]:
    """List every account (savings, credit card, cash) in the database."""
    with get_repo() as repo:
        return repo.list_accounts()
