"""One-shot demo bootstrap.

Steps:

1. Generate 6 months of dummy CSVs into ``sample_data/``.
2. Initialise a fresh SQLite DB at ``FINANCE_MCP_DB_PATH``
   (defaults to ``~/.finance_mcp/finance.db``).
3. Create one HDFC Savings account and one ICICI Credit Card account.
4. Import every generated CSV.
5. Print a ready-to-paste Claude Desktop config snippet.

Re-runs are idempotent: duplicate transactions are skipped via dedup_hash.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

from finance_mcp.config import get_db_path
from finance_mcp.parsers.hdfc import HDFCParser
from finance_mcp.parsers.icici import ICICICreditCardParser
from finance_mcp.storage.db import init_db
from finance_mcp.storage.repository import Repository

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SAMPLE_DIR = PROJECT_ROOT / "sample_data"
HDFC_NAME = "HDFC Savings - Demo"
ICICI_NAME = "ICICI Credit Card - Demo"


def _regenerate_samples(months: int = 6, seed: int = 42) -> None:
    if SAMPLE_DIR.exists():
        shutil.rmtree(SAMPLE_DIR)
    subprocess.run(
        [
            sys.executable,
            str(PROJECT_ROOT / "scripts" / "generate_dummy_data.py"),
            "--output-dir",
            str(SAMPLE_DIR),
            "--months",
            str(months),
            "--seed",
            str(seed),
        ],
        check=True,
    )


def _import_all(repo: Repository) -> tuple[int, int]:
    hdfc = repo.get_account_by_name(HDFC_NAME) or repo.create_account(
        name=HDFC_NAME, type="savings", bank="HDFC"
    )
    icici = repo.get_account_by_name(ICICI_NAME) or repo.create_account(
        name=ICICI_NAME, type="credit_card", bank="ICICI"
    )
    assert hdfc.id is not None and icici.id is not None

    hdfc_parser = HDFCParser()
    icici_parser = ICICICreditCardParser()

    total_in = 0
    total_skip = 0
    for path in sorted(SAMPLE_DIR.glob("hdfc_savings_*.csv")):
        rows = hdfc_parser.parse(path)
        i, s = repo.bulk_insert_transactions(hdfc.id, rows)
        total_in += i
        total_skip += s
    for path in sorted(SAMPLE_DIR.glob("icici_creditcard_*.csv")):
        rows = icici_parser.parse(path)
        i, s = repo.bulk_insert_transactions(icici.id, rows)
        total_in += i
        total_skip += s
    return total_in, total_skip


def _claude_desktop_snippet() -> str:
    config = {
        "mcpServers": {
            "finance-analyst": {
                "command": "uv",
                "args": [
                    "--directory",
                    str(PROJECT_ROOT),
                    "run",
                    "finance-mcp",
                ],
            }
        }
    }
    return json.dumps(config, indent=2)


def main() -> None:
    print("1/4  Generating dummy CSVs...")
    _regenerate_samples()
    print(f"     wrote {sum(1 for _ in SAMPLE_DIR.iterdir())} files to {SAMPLE_DIR}")

    print("2/4  Initialising database...")
    db_path = get_db_path()
    init_db(db_path)
    print(f"     DB at {db_path}")

    print("3/4  Importing statements...")
    with Repository.open(db_path) as repo:
        inserted, skipped = _import_all(repo)
        print(f"     imported {inserted} transactions ({skipped} duplicates skipped)")

    print("4/4  Claude Desktop config:")
    print()
    print("Paste the block below into your Claude Desktop config file.")
    print("On macOS: ~/Library/Application Support/Claude/claude_desktop_config.json")
    print("On Windows: %AppData%\\Claude\\claude_desktop_config.json")
    print()
    print(_claude_desktop_snippet())
    print()
    print("Then restart Claude Desktop and ask: 'What are my top 5 merchants this year?'")


if __name__ == "__main__":
    main()
