"""MCP Client tests for Phase-5 tools."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from fastmcp import Client

from finance_mcp.storage.models import RawTransaction
from finance_mcp.storage.repository import Repository


def _seed(repo: Repository, account_id: int, data: list[tuple[date, str, str, str]]) -> None:
    repo.bulk_insert_transactions(
        account_id,
        [
            RawTransaction(
                txn_date=d,
                amount=Decimal(amt),
                raw_description=desc,
                clean_merchant=merch,
            )
            for d, amt, desc, merch in data
        ],
    )


async def test_compare_periods_tool(mcp_client: Client, repo: Repository) -> None:
    acct = repo.create_account(name="HDFC", type="savings", bank="HDFC")
    assert acct.id is not None
    _seed(
        repo,
        acct.id,
        [
            (date(2025, 1, 5), "-500", "UPI-SWIGGY", "SWIGGY"),
            (date(2025, 2, 5), "-200", "UPI-SWIGGY", "SWIGGY"),
        ],
    )
    res = await mcp_client.call_tool(
        "compare_periods",
        {
            "period_a_start": "2025-01-01",
            "period_a_end": "2025-01-31",
            "period_b_start": "2025-02-01",
            "period_b_end": "2025-02-28",
            "group_by": "category",
        },
    )
    food = next(r for r in res.data if r.group_key == "Food Delivery")
    assert food.period_a_total == -500
    assert food.period_b_total == -200


async def test_budget_roundtrip(mcp_client: Client, repo: Repository) -> None:
    created = await mcp_client.call_tool(
        "set_budget",
        {
            "category_name": "Food Delivery",
            "amount": 1500.0,
            "period": "monthly",
            "start_date": "2025-01-01",
        },
    )
    assert created.data.amount == 1500

    # Seed a couple of debits.
    acct = repo.create_account(name="HDFC", type="savings", bank="HDFC")
    assert acct.id is not None
    _seed(
        repo,
        acct.id,
        [(date(2025, 1, 5), "-500", "UPI-SWIGGY", "SWIGGY")],
    )

    status = await mcp_client.call_tool("get_budget_status", {"month": "2025-01"})
    assert len(status.data) == 1
    b = status.data[0]
    assert b.category_name == "Food Delivery"
    assert b.spent == 500
    assert b.remaining == 1000


async def test_budget_invalid_month(mcp_client: Client) -> None:
    from fastmcp.exceptions import ToolError

    with pytest.raises(ToolError):
        await mcp_client.call_tool("get_budget_status", {"month": "garbage"})


async def test_goal_and_progress(mcp_client: Client) -> None:
    g = await mcp_client.call_tool(
        "set_goal",
        {"name": "Emergency Fund", "target_amount": 100000.0},
    )
    assert g.data.target_amount == 100000

    prog = await mcp_client.call_tool("get_goal_progress", {})
    names = [p.name for p in prog.data]
    assert "Emergency Fund" in names


async def test_get_net_worth(mcp_client: Client, repo: Repository) -> None:
    acct = repo.create_account(name="HDFC", type="savings", bank="HDFC")
    assert acct.id is not None
    _seed(
        repo,
        acct.id,
        [
            (date(2025, 1, 1), "100000", "NEFT CR-SALARY", "SALARY"),
            (date(2025, 1, 5), "-15000", "NEFT-RENT", "RENT"),
        ],
    )
    res = await mcp_client.call_tool("get_net_worth", {"as_of": "2025-01-31"})
    assert res.data.total_assets == 85000
    assert res.data.net_worth == 85000


async def test_detect_recurring_tool(mcp_client: Client, repo: Repository) -> None:
    acct = repo.create_account(name="HDFC", type="savings", bank="HDFC")
    assert acct.id is not None
    # 6 monthly Spotify charges within the last 6 months relative to today.
    today = date.today()
    for i in range(6):
        # Walk back from today one month at a time.
        year = today.year
        month = today.month - i
        while month <= 0:
            month += 12
            year -= 1
        day = min(10, 28)
        repo.bulk_insert_transactions(
            acct.id,
            [
                RawTransaction(
                    txn_date=date(year, month, day),
                    amount=Decimal("-119.00"),
                    raw_description="ACH D-SPOTIFY",
                    clean_merchant="SPOTIFY",
                ),
            ],
        )
    res = await mcp_client.call_tool(
        "detect_recurring",
        {"min_occurrences": 3, "lookback_months": 7},
    )
    merchants = {r.merchant for r in res.data}
    assert "SPOTIFY" in merchants
