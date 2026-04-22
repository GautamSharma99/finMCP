"""Abstract base class for bank-statement parsers.

Concrete parsers consume a CSV path and yield `RawTransaction` rows.
Parsers are pure: they must not touch the DB, write files, or mutate
global state.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from finance_mcp.storage.models import RawTransaction


class BankParser(ABC):
    """Convert a bank-statement CSV into a list of `RawTransaction`."""

    #: Short bank identifier used for logs and `Account.bank`.
    bank: str = ""

    @abstractmethod
    def parse(self, path: str | Path) -> list[RawTransaction]:
        """Parse the CSV at `path` and return the transactions it contains.

        Raises:
            ParseError: if the file cannot be parsed.
        """
