"""Shared test fixtures."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest

from finance_mcp.storage.db import init_db
from finance_mcp.storage.repository import Repository


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    """A freshly-initialized SQLite DB in a temp dir, seeded with defaults."""
    path = tmp_path / "finance.db"
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
