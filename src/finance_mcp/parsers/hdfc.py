"""HDFC Savings account CSV parser (PRD §7.1).

Expected columns (exact casing tolerated):

    Date, Narration, Chq./Ref.No., Value Dt,
    Withdrawal Amt., Deposit Amt., Closing Balance

- Date format: ``DD/MM/YY``.
- ``Withdrawal Amt.`` entries produce negative transactions;
  ``Deposit Amt.`` entries produce positive transactions.
- Summary / header rows with no amounts are skipped.
"""

from __future__ import annotations

import logging
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

import pandas as pd

from finance_mcp.errors import ParseError
from finance_mcp.parsers.base import BankParser
from finance_mcp.parsers.normalize import normalize_merchant
from finance_mcp.storage.models import RawTransaction

logger = logging.getLogger(__name__)

_DATE_FMTS = ("%d/%m/%y", "%d/%m/%Y")

_REQUIRED = {
    "date": ("date",),
    "narration": ("narration",),
    "ref_no": ("chq./ref.no.", "chq/ref no", "chq/ref.no", "ref no", "ref.no"),
    "value_dt": ("value dt", "value date", "value dt."),
    "withdrawal": ("withdrawal amt.", "withdrawal amt", "withdrawal"),
    "deposit": ("deposit amt.", "deposit amt", "deposit"),
    "balance": ("closing balance", "balance"),
}


def _normalize_header(name: str) -> str:
    return name.strip().lower()


def _resolve_columns(df: pd.DataFrame) -> dict[str, str]:
    """Map our canonical column keys to the actual CSV headers."""
    headers = {_normalize_header(c): c for c in df.columns}
    resolved: dict[str, str] = {}
    for key, aliases in _REQUIRED.items():
        for alias in aliases:
            if alias in headers:
                resolved[key] = headers[alias]
                break
    missing = [k for k in _REQUIRED if k not in resolved]
    if missing:
        raise ParseError(f"HDFC CSV missing columns: {missing} (got {list(df.columns)})")
    return resolved


def _parse_date(raw: str) -> datetime:
    for fmt in _DATE_FMTS:
        try:
            return datetime.strptime(raw.strip(), fmt)
        except ValueError:
            continue
    raise ValueError(f"unrecognised HDFC date {raw!r}")


def _parse_decimal(raw: object) -> Decimal | None:
    if raw is None or (isinstance(raw, float) and pd.isna(raw)):
        return None
    s = str(raw).strip().replace(",", "")
    if not s:
        return None
    try:
        return Decimal(s)
    except InvalidOperation:
        return None


class HDFCParser(BankParser):
    """Parse an HDFC Savings statement CSV into `RawTransaction` rows."""

    bank = "HDFC"

    def parse(self, path: str | Path) -> list[RawTransaction]:
        path = Path(path)
        try:
            df = pd.read_csv(path, dtype=str, keep_default_na=False, skipinitialspace=True)
        except (FileNotFoundError, pd.errors.EmptyDataError, pd.errors.ParserError) as exc:
            raise ParseError(f"could not read HDFC CSV {path}: {exc}") from exc

        cols = _resolve_columns(df)
        rows: list[RawTransaction] = []

        for idx, row in df.iterrows():
            raw_date = str(row[cols["date"]]).strip()
            narration = str(row[cols["narration"]]).strip()
            if not raw_date or not narration:
                continue

            withdrawal = _parse_decimal(row[cols["withdrawal"]])
            deposit = _parse_decimal(row[cols["deposit"]])
            if withdrawal is None and deposit is None:
                # Summary / closing-balance / header rows.
                logger.debug("skipping HDFC row %s with no amount", idx)
                continue
            if withdrawal and withdrawal != 0 and deposit and deposit != 0:
                raise ParseError(f"HDFC row {idx} has both withdrawal and deposit amounts")

            amount = -withdrawal if withdrawal else deposit
            assert amount is not None

            try:
                txn_date = _parse_date(raw_date).date()
            except ValueError as exc:
                raise ParseError(f"HDFC row {idx}: {exc}") from exc

            value_raw = str(row[cols["value_dt"]]).strip()
            value_dt = _parse_date(value_raw).date() if value_raw else None

            balance = _parse_decimal(row[cols["balance"]])
            ref = str(row[cols["ref_no"]]).strip() or None

            rows.append(
                RawTransaction(
                    txn_date=txn_date,
                    value_date=value_dt,
                    amount=amount,
                    raw_description=narration,
                    clean_merchant=normalize_merchant(narration),
                    reference_no=ref,
                    running_balance=balance,
                )
            )

        return rows


__all__ = ["HDFCParser"]
