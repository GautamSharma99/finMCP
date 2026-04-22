"""Category-assignment MCP tools."""

from __future__ import annotations

from finance_mcp.server import get_repo, mcp
from finance_mcp.storage.models import OperationResult


@mcp.tool
def categorize_transaction(
    transaction_id: int,
    category_name: str,
) -> OperationResult:
    """Assign a transaction to a category, marking the label as manual.

    Once marked manual, subsequent rule-based runs will not overwrite it.
    """
    with get_repo() as repo:
        category = repo.find_category_by_name(category_name)
        if category is None or category.id is None:
            return OperationResult(success=False, message=f"unknown category: {category_name!r}")
        try:
            repo.get_transaction(transaction_id)
        except KeyError:
            return OperationResult(success=False, message=f"no such transaction: {transaction_id}")
        updated = repo.set_transaction_category(transaction_id, category.id, source="manual")
    return OperationResult(
        success=True,
        affected=1,
        message=f"categorized txn {updated.id} as {category_name}",
    )


@mcp.tool
def bulk_categorize(
    category_name: str,
    merchant: str | None = None,
    uncategorized_only: bool = True,
) -> OperationResult:
    """Assign many transactions to a category at once.

    When ``uncategorized_only=True`` (default) only uncategorized
    transactions are updated. Manual overrides are always preserved.
    """
    with get_repo() as repo:
        category = repo.find_category_by_name(category_name)
        if category is None or category.id is None:
            return OperationResult(success=False, message=f"unknown category: {category_name!r}")
        n = repo.bulk_update_category(
            category_id=category.id,
            merchant=merchant,
            uncategorized_only=uncategorized_only,
        )
    return OperationResult(success=True, affected=n, message=f"updated {n} transactions")
