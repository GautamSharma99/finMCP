"""Integration tests for MCP tools via the in-memory FastMCP Client."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from fastmcp import Client

from finance_mcp.storage.models import RawTransaction
from finance_mcp.storage.repository import Repository

FIXTURES = Path(__file__).resolve().parents[1] / "test_parsers" / "fixtures"


async def test_list_accounts_empty(mcp_client: Client) -> None:
    result = await mcp_client.call_tool("list_accounts", {})
    assert result.data == []


async def test_import_hdfc_then_list(mcp_client: Client) -> None:
    res = await mcp_client.call_tool(
        "import_statement",
        {
            "file_path": str(FIXTURES / "hdfc_basic.csv"),
            "account_name": "HDFC Demo",
            "bank": "HDFC",
        },
    )
    data = res.data
    assert data.success is True
    assert data.rows_imported == 4
    assert data.rows_skipped == 0

    accounts = await mcp_client.call_tool("list_accounts", {})
    assert len(accounts.data) == 1
    assert accounts.data[0].name == "HDFC Demo"


async def test_import_missing_file_returns_error(mcp_client: Client) -> None:
    res = await mcp_client.call_tool(
        "import_statement",
        {"file_path": "/nope/does-not-exist.csv", "account_name": "X"},
    )
    assert res.data.success is False


async def test_query_with_filters(mcp_client: Client, repo: Repository) -> None:
    acct = repo.create_account(name="HDFC", type="savings", bank="HDFC")
    assert acct.id is not None
    rows = [
        RawTransaction(
            txn_date=date(2025, 1, 5),
            amount=Decimal("-400"),
            raw_description="UPI-SWIGGY-swiggy@axl-112233",
            clean_merchant="SWIGGY",
        ),
        RawTransaction(
            txn_date=date(2025, 2, 10),
            amount=Decimal("-250"),
            raw_description="UPI-ZOMATO-zomato@ybl-445566",
            clean_merchant="ZOMATO",
        ),
        RawTransaction(
            txn_date=date(2025, 2, 15),
            amount=Decimal("50000"),
            raw_description="NEFT CR-ACME SALARY",
            clean_merchant="ACME SALARY",
        ),
    ]
    repo.bulk_insert_transactions(acct.id, rows)

    # Filter: Food Delivery in Feb only.
    res = await mcp_client.call_tool(
        "query_transactions",
        {
            "start_date": "2025-02-01",
            "end_date": "2025-02-28",
            "category": "Food Delivery",
        },
    )
    assert len(res.data) == 1
    assert "ZOMATO" in (res.data[0].clean_merchant or "")

    # Filter: merchant substring.
    res = await mcp_client.call_tool("query_transactions", {"merchant": "swiggy"})
    assert len(res.data) == 1
    assert "SWIGGY" in (res.data[0].clean_merchant or "")


async def test_spending_summary_by_category(mcp_client: Client, repo: Repository) -> None:
    acct = repo.create_account(name="HDFC", type="savings", bank="HDFC")
    assert acct.id is not None
    repo.bulk_insert_transactions(
        acct.id,
        [
            RawTransaction(
                txn_date=date(2025, 1, 5),
                amount=Decimal("-400"),
                raw_description="UPI-SWIGGY",
                clean_merchant="SWIGGY",
            ),
            RawTransaction(
                txn_date=date(2025, 1, 6),
                amount=Decimal("-250"),
                raw_description="UPI-ZOMATO",
                clean_merchant="ZOMATO",
            ),
        ],
    )
    res = await mcp_client.call_tool(
        "get_spending_summary",
        {"start_date": "2025-01-01", "end_date": "2025-01-31", "group_by": "category"},
    )
    keys = {r.group_key for r in res.data}
    assert "Food Delivery" in keys


async def test_categorize_transaction_marks_manual(mcp_client: Client, repo: Repository) -> None:
    acct = repo.create_account(name="HDFC", type="savings", bank="HDFC")
    assert acct.id is not None
    repo.bulk_insert_transactions(
        acct.id,
        [
            RawTransaction(
                txn_date=date(2025, 1, 5),
                amount=Decimal("-400"),
                raw_description="UPI-SWIGGY",
                clean_merchant="SWIGGY",
            ),
        ],
    )
    txn = repo.list_transactions(account_id=acct.id)[0]
    assert txn.id is not None
    res = await mcp_client.call_tool(
        "categorize_transaction",
        {"transaction_id": txn.id, "category_name": "Restaurants"},
    )
    assert res.data.success is True

    # Verify it was stored as manual.
    updated = repo.get_transaction(txn.id)
    assert updated.category_source == "manual"


async def test_categorize_unknown_category_returns_error(mcp_client: Client) -> None:
    res = await mcp_client.call_tool(
        "categorize_transaction",
        {"transaction_id": 1, "category_name": "Nope"},
    )
    assert res.data.success is False


async def test_bulk_categorize(mcp_client: Client, repo: Repository) -> None:
    acct = repo.create_account(name="HDFC", type="savings", bank="HDFC")
    assert acct.id is not None
    repo.bulk_insert_transactions(
        acct.id,
        [
            RawTransaction(
                txn_date=date(2025, 1, 5),
                amount=Decimal("-400"),
                raw_description="POS SOME RANDOM SHOP",
                clean_merchant="SOME RANDOM SHOP",
            ),
        ],
        auto_categorize=False,
    )
    res = await mcp_client.call_tool(
        "bulk_categorize",
        {"category_name": "General", "merchant": "SOME RANDOM SHOP"},
    )
    assert res.data.success is True
    assert res.data.affected == 1


async def test_rule_crud_cycle(mcp_client: Client) -> None:
    created = await mcp_client.call_tool(
        "create_rule",
        {"pattern": "TESTMERCH", "category_name": "General", "priority": 45},
    )
    rule = created.data
    assert rule.id is not None
    assert rule.is_user_defined is True

    listed = await mcp_client.call_tool("list_rules", {"user_only": True})
    assert any(r.pattern == "TESTMERCH" for r in listed.data)

    deleted = await mcp_client.call_tool("delete_rule", {"rule_id": rule.id})
    assert deleted.data.success is True


async def test_delete_missing_rule(mcp_client: Client) -> None:
    res = await mcp_client.call_tool("delete_rule", {"rule_id": 99999})
    assert res.data.success is False


async def test_create_rule_unknown_category_raises(mcp_client: Client) -> None:
    from fastmcp.exceptions import ToolError

    with pytest.raises(ToolError):
        await mcp_client.call_tool("create_rule", {"pattern": "X", "category_name": "Nope"})
