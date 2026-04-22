"""Tests for MCP resources via the in-memory Client."""

from __future__ import annotations

import json
from datetime import date
from decimal import Decimal

from fastmcp import Client

from finance_mcp.storage.models import RawTransaction
from finance_mcp.storage.repository import Repository


async def _read_text(client: Client, uri: str) -> str:
    result = await client.read_resource(uri)
    assert result, f"no content for {uri}"
    # FastMCP returns a list of ResourceContents; use the first.
    item = result[0]
    assert hasattr(item, "text")
    return str(item.text)


async def test_accounts_resource(mcp_client: Client, repo: Repository) -> None:
    acct = repo.create_account(name="HDFC Demo", type="savings", bank="HDFC")
    assert acct.id is not None
    repo.bulk_insert_transactions(
        acct.id,
        [
            RawTransaction(
                txn_date=date(2025, 1, 1),
                amount=Decimal("50000"),
                raw_description="NEFT CR-SALARY",
                clean_merchant="SALARY",
            ),
        ],
    )
    body = await _read_text(mcp_client, "finance://accounts")
    data = json.loads(body)
    names = [a["name"] for a in data["accounts"]]
    assert "HDFC Demo" in names


async def test_categories_tree_resource(mcp_client: Client) -> None:
    body = await _read_text(mcp_client, "finance://categories/tree")
    data = json.loads(body)
    names = [n["name"] for n in data["tree"]]
    assert "Food & Dining" in names
    # Food & Dining must have children.
    food = next(n for n in data["tree"] if n["name"] == "Food & Dining")
    child_names = {c["name"] for c in food["children"]}
    assert "Food Delivery" in child_names


async def test_budgets_current_resource(mcp_client: Client, repo: Repository) -> None:
    # No budgets → empty list but valid JSON.
    body = await _read_text(mcp_client, "finance://budgets/current")
    data = json.loads(body)
    assert "budgets" in data


async def test_monthly_insight_resource(mcp_client: Client, repo: Repository) -> None:
    acct = repo.create_account(name="HDFC", type="savings", bank="HDFC")
    assert acct.id is not None
    repo.bulk_insert_transactions(
        acct.id,
        [
            RawTransaction(
                txn_date=date(2025, 1, 10),
                amount=Decimal("-500"),
                raw_description="UPI-SWIGGY",
                clean_merchant="SWIGGY",
            ),
        ],
    )
    body = await _read_text(mcp_client, "finance://insights/monthly/2025-01")
    assert "Monthly Review — 2025-01" in body
    assert "Food Delivery" in body


async def test_last_30_days_resource(mcp_client: Client) -> None:
    body = await _read_text(mcp_client, "finance://insights/summary/last-30-days")
    assert "Rolling 30-Day Summary" in body
