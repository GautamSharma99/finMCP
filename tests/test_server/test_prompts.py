"""Tests for MCP prompts via the in-memory Client."""

from __future__ import annotations

from fastmcp import Client


async def test_monthly_review_prompt(mcp_client: Client) -> None:
    result = await mcp_client.get_prompt("monthly_review", {"month": "2025-01"})
    assert result.messages
    content = str(result.messages[0].content)
    assert "2025-01" in content


async def test_find_savings_prompt(mcp_client: Client) -> None:
    result = await mcp_client.get_prompt("find_savings", {"target_amount": 10000})
    content = str(result.messages[0].content)
    assert "10,000" in content


async def test_find_savings_prompt_no_target(mcp_client: Client) -> None:
    result = await mcp_client.get_prompt("find_savings", {})
    content = str(result.messages[0].content)
    # No target → no goal line but still mentions spending analysis.
    assert "spending" in content.lower()


async def test_goal_check_prompt(mcp_client: Client) -> None:
    result = await mcp_client.get_prompt("goal_check", {"goal_name": "Emergency Fund"})
    content = str(result.messages[0].content)
    assert "Emergency Fund" in content
