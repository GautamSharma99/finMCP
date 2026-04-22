"""Statement-import MCP tool."""

from __future__ import annotations

import logging
from pathlib import Path

from finance_mcp.errors import ParseError
from finance_mcp.parsers.base import BankParser
from finance_mcp.parsers.hdfc import HDFCParser
from finance_mcp.parsers.icici import ICICICreditCardParser
from finance_mcp.server import get_repo, mcp
from finance_mcp.storage.models import ImportResult

logger = logging.getLogger(__name__)


def _parser_for(bank: str | None, file_path: str) -> BankParser:
    """Pick a parser from the bank hint or filename."""
    key = (bank or "").lower()
    name = Path(file_path).name.lower()
    if "hdfc" in key or "hdfc" in name:
        return HDFCParser()
    if "icici" in key or "icici" in name:
        return ICICICreditCardParser()
    raise ValueError(f"no parser available for bank={bank!r} file={file_path!r}")


@mcp.tool
def import_statement(
    file_path: str,
    account_name: str,
    bank: str | None = None,
) -> ImportResult:
    """Import a bank statement CSV into the given account.

    Args:
        file_path: Absolute path to the CSV file.
        account_name: Name of an existing account (created if missing).
        bank: Optional bank hint (``"HDFC"`` or ``"ICICI"``). If omitted,
            inferred from the filename.
    """
    path = Path(file_path)
    if not path.exists():
        return ImportResult(success=False, message=f"file not found: {path}")

    try:
        parser = _parser_for(bank, file_path)
    except ValueError as exc:
        return ImportResult(success=False, message=str(exc))

    try:
        rows = parser.parse(path)
    except ParseError as exc:
        return ImportResult(success=False, message=f"parse error: {exc}")

    with get_repo() as repo:
        acct = repo.get_account_by_name(account_name)
        if acct is None:
            acct_type = "credit_card" if parser.bank == "ICICI" else "savings"
            acct = repo.create_account(name=account_name, type=acct_type, bank=parser.bank)
        assert acct.id is not None

        inserted, skipped = repo.bulk_insert_transactions(acct.id, rows)

    return ImportResult(
        success=True,
        account_id=acct.id,
        rows_imported=inserted,
        rows_skipped=skipped,
        message=f"{inserted} imported, {skipped} duplicates skipped",
    )
