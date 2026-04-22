"""Shared test fixtures."""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator
from pathlib import Path

import pytest
import pytest_asyncio
from fastmcp import Client

from finance_mcp.server import mcp
from finance_mcp.storage.db import init_db
from finance_mcp.storage.repository import Repository


@pytest.fixture
def db_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A freshly-initialized SQLite DB in a temp dir, seeded with defaults.

    Also binds ``FINANCE_MCP_DB_PATH`` so tools opening a repository via
    ``get_repo()`` land on the same file.
    """
    path = tmp_path / "finance.db"
    monkeypatch.setenv("FINANCE_MCP_DB_PATH", str(path))
    init_db(path)
    return path


@pytest.fixture
def repo(db_path: Path) -> Iterator[Repository]:
    """An open `Repository` bound to the temp DB; closed on teardown."""
    r = Repository.open(db_path)
    try:
        yield r
    finally:
        r.close()


@pytest_asyncio.fixture
async def mcp_client(db_path: Path) -> AsyncIterator[Client]:
    """A FastMCP in-memory client bound to the temp DB (via env)."""
    async with Client(mcp) as client:
        yield client
