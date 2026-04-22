"""SQLite connection and migration machinery.

`init_db` creates the schema from the cumulative migrations in `migrations/`
and seeds the default category tree on first run. `connect` returns a
configured `sqlite3.Connection` with foreign keys enabled and Row factory set.
"""

from __future__ import annotations

import logging
import sqlite3
from collections.abc import Iterable
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterator

logger = logging.getLogger(__name__)

_MIGRATIONS_DIR = Path(__file__).parent / "migrations"


def connect(db_path: str | Path) -> sqlite3.Connection:
    """Open a SQLite connection with FK enforcement and Row rows.

    Args:
        db_path: Filesystem path to the SQLite database file.

    Returns:
        A configured `sqlite3.Connection`.
    """
    conn = sqlite3.connect(
        str(db_path),
        detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES,
        isolation_level=None,  # autocommit; we manage transactions explicitly
    )
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


@contextmanager
def transaction(conn: sqlite3.Connection) -> Iterator[sqlite3.Connection]:
    """Context manager wrapping a statement group in BEGIN/COMMIT."""
    conn.execute("BEGIN")
    try:
        yield conn
    except BaseException:
        conn.execute("ROLLBACK")
        raise
    else:
        conn.execute("COMMIT")


def _iter_migrations() -> Iterable[tuple[str, Path]]:
    if not _MIGRATIONS_DIR.exists():
        return []
    return sorted((p.stem, p) for p in _MIGRATIONS_DIR.glob("*.sql") if p.is_file())


def _applied_versions(conn: sqlite3.Connection) -> set[str]:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version TEXT PRIMARY KEY,
            applied_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    cur = conn.execute("SELECT version FROM schema_migrations")
    return {row["version"] for row in cur.fetchall()}


def _apply_migrations(conn: sqlite3.Connection) -> None:
    applied = _applied_versions(conn)
    for version, path in _iter_migrations():
        if version in applied:
            continue
        sql = path.read_text(encoding="utf-8")
        logger.info("Applying migration %s", version)
        # NOTE: executescript commits any active transaction, so we don't
        # wrap in our own BEGIN/COMMIT. Record the version in a follow-up
        # statement; the script itself is expected to be idempotent.
        conn.executescript(sql)
        conn.execute("INSERT INTO schema_migrations(version) VALUES (?)", (version,))


# Default category seeds — PRD §4.3.
_DEFAULT_CATEGORIES: tuple[tuple[str, tuple[str, ...], bool], ...] = (
    ("Income", ("Salary", "Interest", "Refunds", "Other Income"), True),
    ("Food & Dining", ("Groceries", "Restaurants", "Food Delivery", "Cafes"), False),
    ("Transport", ("Fuel", "Ride-hailing", "Public Transit", "Parking"), False),
    ("Utilities", ("Electricity", "Internet", "Mobile", "Water", "Gas"), False),
    ("Housing", ("Rent", "Maintenance", "Home Supplies"), False),
    ("Entertainment", ("Streaming", "Movies", "Events", "Gaming"), False),
    ("Shopping", ("Clothing", "Electronics", "General"), False),
    ("Health", ("Pharmacy", "Doctor", "Gym", "Insurance"), False),
    (
        "Financial",
        ("Credit Card Payment", "Loan EMI", "Investments", "Bank Fees"),
        False,
    ),
    ("Travel", ("Flights", "Hotels", "Trains"), False),
    ("Transfers", ("Self-Transfer", "P2P"), False),
    ("Uncategorized", (), False),
)


def _seed_default_categories(conn: sqlite3.Connection) -> None:
    """Idempotently seed the default category tree (PRD §4.3)."""
    existing = conn.execute("SELECT 1 FROM categories LIMIT 1").fetchone()
    if existing is not None:
        return

    with transaction(conn):
        for parent_name, children, is_income in _DEFAULT_CATEGORIES:
            cur = conn.execute(
                "INSERT INTO categories(name, parent_id, is_income) VALUES (?, NULL, ?)",
                (parent_name, int(is_income)),
            )
            parent_id = cur.lastrowid
            for child_name in children:
                conn.execute(
                    "INSERT INTO categories(name, parent_id, is_income) VALUES (?, ?, ?)",
                    (child_name, parent_id, int(is_income)),
                )


def init_db(db_path: str | Path) -> None:
    """Create the database, apply migrations, seed categories.

    Safe to call repeatedly: migrations and seeds are idempotent.
    """
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = connect(path)
    try:
        _apply_migrations(conn)
        _seed_default_categories(conn)
    finally:
        conn.close()
