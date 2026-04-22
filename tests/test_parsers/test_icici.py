"""Tests for the ICICI Credit Card parser."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from finance_mcp.errors import ParseError
from finance_mcp.parsers.icici import ICICICreditCardParser

FIXTURES = Path(__file__).parent / "fixtures"


def test_parses_basic_icici_csv() -> None:
    rows = ICICICreditCardParser().parse(FIXTURES / "icici_basic.csv")
    assert len(rows) == 5

    swiggy = rows[0]
    assert swiggy.txn_date == date(2025, 1, 2)
    assert swiggy.amount == Decimal("-650.00")
    assert swiggy.clean_merchant and "SWIGGY" in swiggy.clean_merchant

    refund = rows[3]
    assert refund.amount == Decimal("1200.00")  # CR -> positive

    payment = rows[4]
    assert payment.amount == Decimal("15000.00")


def test_edge_cases_handle_quotes_currency_symbol_and_empty_details() -> None:
    rows = ICICICreditCardParser().parse(FIXTURES / "icici_edge.csv")
    # Opening-balance row + empty-details row are skipped → 3 rows remain.
    assert len(rows) == 3
    bb, uber, prime = rows
    assert bb.amount == Decimal("-1250.50")
    assert uber.amount == Decimal("-320.00")
    assert "UBER" in (uber.clean_merchant or "")
    assert prime.amount == Decimal("-179.00")


def test_bad_drcr_raises() -> None:
    with pytest.raises(ParseError):
        ICICICreditCardParser().parse(FIXTURES / "icici_bad_type.csv")


def test_bank_identifier() -> None:
    assert ICICICreditCardParser().bank == "ICICI"


def test_missing_columns_raises(tmp_path: Path) -> None:
    bad = tmp_path / "icici_missing.csv"
    bad.write_text("A,B\n1,2\n", encoding="utf-8")
    with pytest.raises(ParseError):
        ICICICreditCardParser().parse(bad)


def test_bad_date_raises(tmp_path: Path) -> None:
    bad = tmp_path / "icici_bad_date.csv"
    bad.write_text(
        "Transaction Date,Transaction Details,Ref No,Amount (INR),Debit/Credit\n"
        "99-99-9999,NOPE,R1,100.00,DR\n",
        encoding="utf-8",
    )
    with pytest.raises(ParseError):
        ICICICreditCardParser().parse(bad)


def test_file_not_found_raises() -> None:
    with pytest.raises(ParseError):
        ICICICreditCardParser().parse(FIXTURES / "does_not_exist.csv")


def test_invalid_amount_is_skipped(tmp_path: Path) -> None:
    csv = tmp_path / "icici_bad_amt.csv"
    csv.write_text(
        "Transaction Date,Transaction Details,Ref No,Amount (INR),Debit/Credit\n"
        "02-01-2025,SKIPPED,R1,not-money,DR\n",
        encoding="utf-8",
    )
    assert ICICICreditCardParser().parse(csv) == []
