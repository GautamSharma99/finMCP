"""Tests for the HDFC Savings parser."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from finance_mcp.errors import ParseError
from finance_mcp.parsers.hdfc import HDFCParser

FIXTURES = Path(__file__).parent / "fixtures"


def test_parses_basic_hdfc_csv() -> None:
    rows = HDFCParser().parse(FIXTURES / "hdfc_basic.csv")
    assert len(rows) == 4

    salary = rows[0]
    assert salary.txn_date == date(2025, 1, 1)
    assert salary.amount == Decimal("120000.00")
    assert salary.clean_merchant and "ACME" in salary.clean_merchant
    assert salary.running_balance == Decimal("125000.00")

    swiggy = rows[1]
    assert swiggy.amount == Decimal("-450.00")
    assert swiggy.clean_merchant == "SWIGGY"

    uber = rows[2]
    assert uber.amount == Decimal("-320.50")
    assert "UBER" in (uber.clean_merchant or "")

    netflix = rows[3]
    assert netflix.amount == Decimal("-649.00")


def test_edge_cases_skip_summary_and_include_refund() -> None:
    rows = HDFCParser().parse(FIXTURES / "hdfc_edge.csv")
    # 3 real rows: zomato, refund, big bazaar. OPENING BALANCE + TOTAL skipped.
    assert len(rows) == 3
    amounts = [r.amount for r in rows]
    assert amounts == [Decimal("-560.00"), Decimal("999.00"), Decimal("-1450.00")]

    # Multi-line narration should still be captured (newline preserved, merchant cleaned).
    multi = rows[2]
    assert "BIG BAZAAR" in multi.raw_description.upper()


def test_bad_date_raises_parse_error() -> None:
    with pytest.raises(ParseError):
        HDFCParser().parse(FIXTURES / "hdfc_bad_date.csv")


def test_missing_columns_raises() -> None:
    bad = FIXTURES / "hdfc_missing.csv"
    bad.write_text("Foo,Bar\n1,2\n", encoding="utf-8")
    try:
        with pytest.raises(ParseError):
            HDFCParser().parse(bad)
    finally:
        bad.unlink()


def test_bank_identifier() -> None:
    assert HDFCParser().bank == "HDFC"


def test_both_amounts_raises() -> None:
    with pytest.raises(ParseError):
        HDFCParser().parse(FIXTURES / "hdfc_both_amounts.csv")


def test_file_not_found_raises() -> None:
    with pytest.raises(ParseError):
        HDFCParser().parse(FIXTURES / "does_not_exist.csv")


def test_invalid_amount_token_is_skipped(tmp_path: Path) -> None:
    csv = tmp_path / "bad_amount.csv"
    csv.write_text(
        "Date,Narration,Chq./Ref.No.,Value Dt,Withdrawal Amt.,Deposit Amt.,Closing Balance\n"
        "01/01/25,JUNK ROW,R1,01/01/25,not-a-number,,100.00\n",
        encoding="utf-8",
    )
    # Both amounts unparseable -> row is skipped, so 0 rows returned.
    rows = HDFCParser().parse(csv)
    assert rows == []
