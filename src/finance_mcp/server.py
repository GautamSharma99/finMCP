"""FastMCP server wiring for the Personal Finance Analyst.

This file creates the `mcp` instance and, by importing the tool / resource
/ prompt submodules, triggers their decorators to register handlers.

Run with::

    uv run finance-mcp
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import TYPE_CHECKING

from fastmcp import FastMCP

from finance_mcp.config import get_db_path
from finance_mcp.storage.db import init_db
from finance_mcp.storage.repository import Repository

if TYPE_CHECKING:
    from collections.abc import Iterator

mcp: FastMCP = FastMCP(
    name="finance-analyst",
    instructions=(
        "Personal Finance Analyst. Use tools to import bank CSVs, query "
        "transactions, manage budgets and goals, and detect recurring "
        "charges. Read resources for at-a-glance context. Use prompts for "
        "structured reviews."
    ),
)


@contextmanager
def get_repo() -> Iterator[Repository]:
    """Open a repository bound to the currently configured DB path.

    Used by tool implementations. Each invocation opens a fresh
    connection and closes it on exit — cheap enough for SQLite and keeps
    tests simple.
    """
    path = get_db_path()
    init_db(path)  # idempotent; cheap after first run
    repo = Repository.open(path)
    try:
        yield repo
    finally:
        repo.close()


# Importing these modules fires the decorators that register handlers on `mcp`.
from finance_mcp.prompts import (  # noqa: E402, F401
    find_savings,
    goal_check,
    monthly_review,
)
from finance_mcp.resources import (  # noqa: E402, F401
    accounts,
    budgets,
    categories,
    insights,
)
from finance_mcp.tools import (  # noqa: E402, F401
    account_tools,
    budget_tools,
    category_tools,
    goal_tools,
    import_tools,
    insight_tools,
    query_tools,
    rule_tools,
)


def main() -> None:
    """Entry point for the `finance-mcp` console script."""
    init_db(get_db_path())
    mcp.run()


if __name__ == "__main__":
    main()
