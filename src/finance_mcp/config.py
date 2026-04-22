"""Runtime configuration and paths."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _default_db_path() -> Path:
    env = os.environ.get("FINANCE_MCP_DB_PATH")
    if env:
        return Path(env)
    return Path.home() / ".finance_mcp" / "finance.db"


@dataclass(frozen=True)
class Settings:
    """Immutable runtime settings resolved at import time."""

    db_path: Path
    default_currency: str = "INR"


settings = Settings(db_path=_default_db_path())
