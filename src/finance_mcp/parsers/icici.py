"""ICICI Credit Card CSV parser (PRD §7.2).

Expected columns:

    Transaction Date, Transaction Details, Ref No, Amount (INR), Debit/Credit

- Date format: ``DD-MM-YYYY``.
- ``DR`` in the Debit/Credit column produces a negative amount;
  ``CR`` produces a positive (refund, reward, or payment) amount.
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

_DATE_FMTS = ("%d-%m-%Y", "%d/%m/%Y", "%Y-%m-%d")

_REQUIRED = {
    "date": ("transaction date", "date"),
    "details": ("transaction details", "details", "description"),
    "ref_no": ("ref no", "ref no.", "reference no"),
    "amount": ("amount (inr)", "amount", "amount inr"),
    "type": ("debit/credit", "type", "dr/cr"),
}


def _resolve_columns(df: pd.DataFrame) -> dict[str, str]:
    headers = {c.strip().lower(): c for c in df.columns}
    resolved: dict[str, str] = {}
    for key, aliases in _REQUIRED.items():
        for alias in aliases:
            if alias in headers:
                resolved[key] = headers[alias]
                break
    missing = [k for k in _REQUIRED if k not in resolved]
    if missing:
        raise ParseError(f"ICICI CSV missing columns: {missing} (got {list(df.columns)})")
    return resolved


def _parse_date(raw: str) -> datetime:
    for fmt in _DATE_FMTS:
        try:
            return datetime.strptime(raw.strip(), fmt)
        except ValueError:
            continue
    raise ValueError(f"unrecognised ICICI date {raw!r}")


def _parse_amount(raw: object) -> Decimal | None:
    if raw is None or (isinstance(raw, float) and pd.isna(raw)):
        return None
    s = str(raw).strip().replace(",", "").replace("₹", "")
    if not s:
        return None
    try:
        return Decimal(s)
    except InvalidOperation:
        return None


class ICICICreditCardParser(BankParser):
    """Parse an ICICI Credit Card statement CSV."""

    bank = "ICICI"

    def parse(self, path: str | Path) -> list[RawTransaction]:
        path = Path(path)
        try:
            df = pd.read_csv(path, dtype=str, keep_default_na=False, skipinitialspace=True)
        except (FileNotFoundError, pd.errors.EmptyDataError, pd.errors.ParserError) as exc:
            raise ParseError(f"could not read ICICI CSV {path}: {exc}") from exc

        cols = _resolve_columns(df)
        rows: list[RawTransaction] = []

        for idx, row in df.iterrows():
            raw_date = str(row[cols["date"]]).strip()
            details = str(row[cols["details"]]).strip()
            amount_raw = _parse_amount(row[cols["amount"]])
            drcr = str(row[cols["type"]]).strip().upper()

            if not raw_date or not details or amount_raw is None:
                logger.debug("skipping ICICI row %s (empty/invalid)", idx)
                continue
            if drcr not in {"DR", "CR"}:
                raise ParseError(f"ICICI row {idx}: expected DR/CR, got {drcr!r}")

            try:
                txn_date = _parse_date(raw_date).date()
            except ValueError as exc:
                raise ParseError(f"ICICI row {idx}: {exc}") from exc

            amount = -amount_raw if drcr == "DR" else amount_raw
            ref = str(row[cols["ref_no"]]).strip() or None

            rows.append(
                RawTransaction(
                    txn_date=txn_date,
                    amount=amount,
                    raw_description=details,
                    clean_merchant=normalize_merchant(details),
                    reference_no=ref,
                )
            )

        return rows


__all__ = ["ICICICreditCardParser"]
