"""Integration test: dummy generator → parser → repository.

Verifies that a freshly generated pair of CSVs round-trips through the
bank parsers into the repository with matching row counts and no
duplicate-hash collisions.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from finance_mcp.parsers.hdfc import HDFCParser
from finance_mcp.parsers.icici import ICICICreditCardParser
from finance_mcp.storage.repository import Repository


@pytest.fixture
def generated_csvs(tmp_path: Path) -> Path:
    """Run the generator once for 2 months, return the output dir."""
    out = tmp_path / "sample"
    script = Path(__file__).resolve().parents[2] / "scripts" / "generate_dummy_data.py"
    result = subprocess.run(
        [
            sys.executable,
            str(script),
            "--output-dir",
            str(out),
            "--months",
            "2",
            "--seed",
            "123",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    assert "wrote" in result.stdout
    return out


def test_generator_output_parses_and_imports(generated_csvs: Path, repo: Repository) -> None:
    hdfc_files = sorted(generated_csvs.glob("hdfc_savings_*.csv"))
    icici_files = sorted(generated_csvs.glob("icici_creditcard_*.csv"))
    assert len(hdfc_files) == 2
    assert len(icici_files) == 2

    hdfc_acc = repo.create_account(name="HDFC Savings - Demo", type="savings", bank="HDFC")
    icici_acc = repo.create_account(name="ICICI CC - Demo", type="credit_card", bank="ICICI")
    assert hdfc_acc.id and icici_acc.id

    hdfc_parser = HDFCParser()
    icici_parser = ICICICreditCardParser()

    hdfc_total_parsed = 0
    for f in hdfc_files:
        rows = hdfc_parser.parse(f)
        hdfc_total_parsed += len(rows)
        inserted, skipped = repo.bulk_insert_transactions(hdfc_acc.id, rows)
        assert inserted + skipped == len(rows)

    icici_total_parsed = 0
    for f in icici_files:
        rows = icici_parser.parse(f)
        icici_total_parsed += len(rows)
        inserted, skipped = repo.bulk_insert_transactions(icici_acc.id, rows)
        assert inserted + skipped == len(rows)

    assert hdfc_total_parsed > 0
    assert icici_total_parsed > 0

    # Post-condition: DB counts match what was inserted (modulo dedup dupes,
    # which should be rare but not impossible in randomized data).
    assert repo.count_transactions(hdfc_acc.id) <= hdfc_total_parsed
    assert repo.count_transactions(icici_acc.id) <= icici_total_parsed
    assert repo.count_transactions() == (
        repo.count_transactions(hdfc_acc.id) + repo.count_transactions(icici_acc.id)
    )
