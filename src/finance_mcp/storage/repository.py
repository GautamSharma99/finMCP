"""Data access layer.

All SQL in the project lives here. Callers work with Pydantic models
from `storage.models`; the repository handles row <-> model translation
and enforces invariants like dedup hashing.
"""

from __future__ import annotations

import hashlib
import re
import sqlite3
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import TYPE_CHECKING

from finance_mcp.errors import (
    AccountNotFoundError,
    CategoryNotFoundError,
    DuplicateTransactionError,
)
from finance_mcp.storage.db import connect, transaction
from finance_mcp.storage.models import (
    Account,
    Budget,
    Category,
    Goal,
    RawTransaction,
    Rule,
    Transaction,
)

if TYPE_CHECKING:
    from collections.abc import Iterable


_WHITESPACE_RE = re.compile(r"\s+")


def compute_dedup_hash(
    account_id: int,
    txn_date: date,
    amount: Decimal | float | int | str,
    raw_description: str,
) -> str:
    """Return the 16-hex-char dedup hash (PRD §4.2).

    Format: first 16 hex chars of
    sha256(account_id | txn_date_iso | amount_str | normalized_description).
    """
    normalized = _WHITESPACE_RE.sub(" ", raw_description).strip().upper()
    amount_str = f"{Decimal(str(amount)):.2f}"
    payload = f"{account_id}|{txn_date.isoformat()}|{amount_str}|{normalized}"
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return digest[:16]


class Repository:
    """Thin CRUD facade over a SQLite connection.

    Construct with `Repository(connection)` or `Repository.open(path)`.
    Close via the context-manager protocol or `close()`.
    """

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    @classmethod
    def open(cls, db_path: str | Path) -> Repository:
        """Open a new repository backed by the SQLite file at `db_path`."""
        return cls(connect(db_path))

    def __enter__(self) -> Repository:
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        self.close()

    def close(self) -> None:
        """Close the underlying connection."""
        self._conn.close()

    @property
    def connection(self) -> sqlite3.Connection:
        """Access the raw connection (for tests and migrations)."""
        return self._conn

    # --- Accounts ----------------------------------------------------------

    def create_account(
        self,
        name: str,
        type: str,
        bank: str | None = None,
        currency: str = "INR",
    ) -> Account:
        """Insert a new account and return the persisted model."""
        with transaction(self._conn):
            cur = self._conn.execute(
                "INSERT INTO accounts(name, type, bank, currency) VALUES (?, ?, ?, ?)",
                (name, type, bank, currency),
            )
            account_id = cur.lastrowid
        return self.get_account(account_id)  # type: ignore[arg-type]

    def get_account(self, account_id: int) -> Account:
        """Return the account with `account_id` or raise."""
        row = self._conn.execute("SELECT * FROM accounts WHERE id = ?", (account_id,)).fetchone()
        if row is None:
            raise AccountNotFoundError(f"account id={account_id}")
        return _account_from_row(row)

    def get_account_by_name(self, name: str) -> Account | None:
        """Return the account matching `name` exactly, or None."""
        row = self._conn.execute("SELECT * FROM accounts WHERE name = ?", (name,)).fetchone()
        return _account_from_row(row) if row else None

    def list_accounts(self) -> list[Account]:
        """Return every account ordered by id."""
        rows = self._conn.execute("SELECT * FROM accounts ORDER BY id").fetchall()
        return [_account_from_row(r) for r in rows]

    # --- Categories --------------------------------------------------------

    def list_categories(self) -> list[Category]:
        """Return every category ordered by parent then name."""
        rows = self._conn.execute(
            "SELECT * FROM categories ORDER BY COALESCE(parent_id, id), name"
        ).fetchall()
        return [_category_from_row(r) for r in rows]

    def get_category(self, category_id: int) -> Category:
        """Return the category with `category_id` or raise."""
        row = self._conn.execute("SELECT * FROM categories WHERE id = ?", (category_id,)).fetchone()
        if row is None:
            raise CategoryNotFoundError(f"category id={category_id}")
        return _category_from_row(row)

    def find_category_by_name(self, name: str) -> Category | None:
        """Case-insensitive lookup. Prefers leaf categories over parents.

        If multiple leaves match, returns the lowest id for determinism.
        """
        rows = self._conn.execute(
            """
            SELECT * FROM categories
            WHERE LOWER(name) = LOWER(?)
            ORDER BY CASE WHEN parent_id IS NULL THEN 1 ELSE 0 END, id
            """,
            (name,),
        ).fetchall()
        return _category_from_row(rows[0]) if rows else None

    def create_category(
        self,
        name: str,
        parent_id: int | None = None,
        icon: str | None = None,
        is_income: bool = False,
    ) -> Category:
        """Insert a new category and return it."""
        with transaction(self._conn):
            cur = self._conn.execute(
                "INSERT INTO categories(name, parent_id, icon, is_income) VALUES (?, ?, ?, ?)",
                (name, parent_id, icon, int(is_income)),
            )
            return self.get_category(cur.lastrowid)  # type: ignore[arg-type]

    # --- Rules -------------------------------------------------------------

    def create_rule(
        self,
        pattern: str,
        category_id: int,
        match_type: str = "contains",
        priority: int = 50,
        is_user_defined: bool = False,
    ) -> Rule:
        """Insert a categorization rule and return it."""
        with transaction(self._conn):
            cur = self._conn.execute(
                """
                INSERT INTO rules(pattern, match_type, category_id, priority, is_user_defined)
                VALUES (?, ?, ?, ?, ?)
                """,
                (pattern, match_type, category_id, priority, int(is_user_defined)),
            )
            rule_id = cur.lastrowid
        return self.get_rule(rule_id)  # type: ignore[arg-type]

    def get_rule(self, rule_id: int) -> Rule:
        """Return a rule by id."""
        row = self._conn.execute("SELECT * FROM rules WHERE id = ?", (rule_id,)).fetchone()
        if row is None:
            raise KeyError(f"rule id={rule_id}")
        return _rule_from_row(row)

    def list_rules(self, user_only: bool = False) -> list[Rule]:
        """Return rules ordered by priority then user-defined-first."""
        sql = "SELECT * FROM rules"
        params: tuple[object, ...] = ()
        if user_only:
            sql += " WHERE is_user_defined = 1"
        sql += " ORDER BY priority ASC, is_user_defined DESC, id ASC"
        rows = self._conn.execute(sql, params).fetchall()
        return [_rule_from_row(r) for r in rows]

    def delete_rule(self, rule_id: int) -> int:
        """Delete a rule by id. Returns affected row count."""
        with transaction(self._conn):
            cur = self._conn.execute("DELETE FROM rules WHERE id = ?", (rule_id,))
            return cur.rowcount

    def count_rules(self) -> int:
        """Return the total rule count."""
        return int(self._conn.execute("SELECT COUNT(*) AS n FROM rules").fetchone()["n"])

    # --- Budgets -----------------------------------------------------------

    def upsert_budget(
        self,
        category_id: int,
        amount: Decimal | float,
        period: str,
        start_date: date,
        end_date: date | None = None,
    ) -> Budget:
        """Insert or update a budget (UNIQUE on category/period/start_date)."""
        amount_str = str(Decimal(str(amount)))
        with transaction(self._conn):
            self._conn.execute(
                """
                INSERT INTO budgets(category_id, amount, period, start_date, end_date)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(category_id, period, start_date)
                DO UPDATE SET amount = excluded.amount, end_date = excluded.end_date
                """,
                (
                    category_id,
                    amount_str,
                    period,
                    start_date.isoformat(),
                    end_date.isoformat() if end_date else None,
                ),
            )
        row = self._conn.execute(
            """
            SELECT * FROM budgets
            WHERE category_id = ? AND period = ? AND start_date = ?
            """,
            (category_id, period, start_date.isoformat()),
        ).fetchone()
        return _budget_from_row(row)

    def list_budgets(self) -> list[Budget]:
        """All budgets ordered by start_date desc."""
        rows = self._conn.execute(
            "SELECT * FROM budgets ORDER BY start_date DESC, id DESC"
        ).fetchall()
        return [_budget_from_row(r) for r in rows]

    def category_spend(self, category_id: int, start_date: date, end_date: date) -> Decimal:
        """Return the absolute spend (positive) on a category over a window.

        Only debits (negative amounts) are summed; credits (refunds) net
        off to reduce the reported spend.
        """
        row = self._conn.execute(
            """
            SELECT COALESCE(SUM(CAST(amount AS REAL)), 0) AS s
            FROM transactions t
            WHERE t.txn_date >= ? AND t.txn_date <= ?
              AND t.category_id IN (
                SELECT id FROM categories WHERE id = ?
                UNION SELECT id FROM categories WHERE parent_id = ?
              )
            """,
            (start_date.isoformat(), end_date.isoformat(), category_id, category_id),
        ).fetchone()
        # Stored debits are negative; a spend of 1000 appears as -1000 in SUM.
        return Decimal(str(-float(row["s"])))

    # --- Goals -------------------------------------------------------------

    def upsert_goal(
        self,
        name: str,
        target_amount: Decimal | float,
        deadline: date | None = None,
        linked_account_id: int | None = None,
    ) -> Goal:
        """Insert or update a goal keyed by name."""
        amount_str = str(Decimal(str(target_amount)))
        with transaction(self._conn):
            self._conn.execute(
                """
                INSERT INTO goals(name, target_amount, deadline, linked_account_id)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(name) DO UPDATE SET
                    target_amount = excluded.target_amount,
                    deadline = excluded.deadline,
                    linked_account_id = excluded.linked_account_id
                """,
                (
                    name,
                    amount_str,
                    deadline.isoformat() if deadline else None,
                    linked_account_id,
                ),
            )
        return self.get_goal_by_name(name)

    def get_goal_by_name(self, name: str) -> Goal:
        row = self._conn.execute("SELECT * FROM goals WHERE name = ?", (name,)).fetchone()
        if row is None:
            raise KeyError(f"goal name={name!r}")
        return _goal_from_row(row)

    def list_goals(self) -> list[Goal]:
        rows = self._conn.execute("SELECT * FROM goals ORDER BY id").fetchall()
        return [_goal_from_row(r) for r in rows]

    def set_goal_current_amount(self, name: str, amount: Decimal | float) -> Goal:
        with transaction(self._conn):
            self._conn.execute(
                "UPDATE goals SET current_amount = ? WHERE name = ?",
                (str(Decimal(str(amount))), name),
            )
        return self.get_goal_by_name(name)

    # --- Aggregates --------------------------------------------------------

    def net_worth_as_of(self, as_of: date) -> tuple[Decimal, Decimal]:
        """Return ``(assets, liabilities)`` as positive numbers.

        Assets: sum of positive net balances on savings/cash accounts.
        Liabilities: absolute value of negative net balances on credit
        card accounts (i.e. outstanding card debt).
        """
        row = self._conn.execute(
            """
            SELECT
              COALESCE(SUM(CASE WHEN a.type IN ('savings','cash')
                  AND CAST(t.amount AS REAL) > 0 THEN CAST(t.amount AS REAL) END), 0)
                -
              COALESCE(SUM(CASE WHEN a.type IN ('savings','cash')
                  AND CAST(t.amount AS REAL) < 0 THEN ABS(CAST(t.amount AS REAL)) END), 0)
              AS assets,
              COALESCE(SUM(CASE WHEN a.type = 'credit_card'
                  THEN CAST(t.amount AS REAL) END), 0) AS cc_net
            FROM transactions t JOIN accounts a ON a.id = t.account_id
            WHERE t.txn_date <= ?
            """,
            (as_of.isoformat(),),
        ).fetchone()
        assets = Decimal(str(row["assets"]))
        cc_net = Decimal(str(row["cc_net"]))
        # On credit cards, debit = -amount spent, payments = +amount. A
        # net-negative cc means outstanding debt; net-positive means
        # prepayment (treated as zero liability).
        liabilities = -cc_net if cc_net < 0 else Decimal("0")
        return assets, liabilities

    def merchant_history(
        self,
        min_occurrences: int,
        lookback_start: date,
    ) -> list[tuple[str, list[date], list[Decimal], int | None]]:
        """Return per-merchant history for recurring detection.

        Emits ``(merchant, [dates], [amounts], category_id)`` for every
        merchant with at least ``min_occurrences`` debits since
        ``lookback_start``.
        """
        rows = self._conn.execute(
            """
            SELECT clean_merchant, txn_date, amount, category_id
            FROM transactions
            WHERE clean_merchant IS NOT NULL
              AND clean_merchant != ''
              AND txn_date >= ?
              AND CAST(amount AS REAL) < 0
            ORDER BY clean_merchant, txn_date
            """,
            (lookback_start.isoformat(),),
        ).fetchall()

        dates_by: dict[str, list[date]] = {}
        amounts_by: dict[str, list[Decimal]] = {}
        category_by: dict[str, int | None] = {}

        for r in rows:
            m = str(r["clean_merchant"])
            dates_by.setdefault(m, []).append(_parse_date(r["txn_date"]))
            amounts_by.setdefault(m, []).append(Decimal(str(r["amount"])))
            if category_by.get(m) is None and r["category_id"] is not None:
                category_by[m] = int(r["category_id"])

        out: list[tuple[str, list[date], list[Decimal], int | None]] = []
        for m, ds in dates_by.items():
            if len(ds) < min_occurrences:
                continue
            out.append((m, ds, amounts_by[m], category_by.get(m)))
        return out

    # --- Transactions ------------------------------------------------------

    def insert_transaction(
        self,
        account_id: int,
        raw: RawTransaction,
        category_id: int | None = None,
        category_source: str | None = None,
    ) -> Transaction:
        """Insert a transaction derived from a parser row.

        Raises `DuplicateTransactionError` if a transaction with the same
        dedup hash already exists.
        """
        dedup = compute_dedup_hash(account_id, raw.txn_date, raw.amount, raw.raw_description)
        try:
            with transaction(self._conn):
                cur = self._conn.execute(
                    """
                    INSERT INTO transactions(
                        account_id, txn_date, value_date, amount, currency,
                        raw_description, clean_merchant, category_id,
                        category_source, reference_no, running_balance,
                        dedup_hash
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        account_id,
                        raw.txn_date.isoformat(),
                        raw.value_date.isoformat() if raw.value_date else None,
                        str(raw.amount),
                        raw.currency,
                        raw.raw_description,
                        raw.clean_merchant,
                        category_id,
                        category_source,
                        raw.reference_no,
                        str(raw.running_balance) if raw.running_balance is not None else None,
                        dedup,
                    ),
                )
                txn_id = cur.lastrowid
        except sqlite3.IntegrityError as exc:
            if "dedup_hash" in str(exc):
                raise DuplicateTransactionError(dedup) from exc
            raise
        return self.get_transaction(txn_id)  # type: ignore[arg-type]

    def get_transaction(self, txn_id: int) -> Transaction:
        """Return a transaction by id, or raise via KeyError."""
        row = self._conn.execute("SELECT * FROM transactions WHERE id = ?", (txn_id,)).fetchone()
        if row is None:
            raise KeyError(f"transaction id={txn_id}")
        return _transaction_from_row(row)

    def list_transactions(
        self, account_id: int | None = None, limit: int = 1000
    ) -> list[Transaction]:
        """List transactions, optionally filtered to an account."""
        if account_id is None:
            rows = self._conn.execute(
                "SELECT * FROM transactions ORDER BY txn_date DESC, id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        else:
            rows = self._conn.execute(
                """
                SELECT * FROM transactions
                WHERE account_id = ?
                ORDER BY txn_date DESC, id DESC LIMIT ?
                """,
                (account_id, limit),
            ).fetchall()
        return [_transaction_from_row(r) for r in rows]

    def query_transactions(
        self,
        start_date: date | None = None,
        end_date: date | None = None,
        category: str | None = None,
        account: str | None = None,
        merchant: str | None = None,
        min_amount: Decimal | float | None = None,
        max_amount: Decimal | float | None = None,
        uncategorized_only: bool = False,
        limit: int = 100,
    ) -> list[Transaction]:
        """Filter transactions across accounts with AND semantics.

        Category matches either leaf or parent name. Account matches the
        stored account name exactly. Merchant is a case-insensitive
        substring of ``clean_merchant`` or ``raw_description``.
        """
        clauses: list[str] = []
        params: list[object] = []

        if start_date is not None:
            clauses.append("t.txn_date >= ?")
            params.append(start_date.isoformat())
        if end_date is not None:
            clauses.append("t.txn_date <= ?")
            params.append(end_date.isoformat())
        if min_amount is not None:
            clauses.append("CAST(t.amount AS REAL) >= ?")
            params.append(float(min_amount))
        if max_amount is not None:
            clauses.append("CAST(t.amount AS REAL) <= ?")
            params.append(float(max_amount))
        if merchant:
            clauses.append(
                "(UPPER(COALESCE(t.clean_merchant, '')) LIKE ? OR UPPER(t.raw_description) LIKE ?)"
            )
            needle = f"%{merchant.upper()}%"
            params.extend([needle, needle])
        if account:
            clauses.append("t.account_id = (SELECT id FROM accounts WHERE name = ?)")
            params.append(account)
        if category:
            # Match transactions whose category is the named leaf or any
            # child of a parent with that name.
            clauses.append(
                "t.category_id IN ("
                " SELECT id FROM categories WHERE LOWER(name) = LOWER(?)"
                " UNION"
                " SELECT id FROM categories"
                "  WHERE parent_id = (SELECT id FROM categories"
                "   WHERE LOWER(name) = LOWER(?) AND parent_id IS NULL)"
                ")"
            )
            params.extend([category, category])
        if uncategorized_only:
            clauses.append("(t.category_id IS NULL OR t.category_source = 'uncategorized')")

        where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
        sql = f"SELECT t.* FROM transactions t{where} ORDER BY t.txn_date DESC, t.id DESC LIMIT ?"
        params.append(int(limit))
        rows = self._conn.execute(sql, params).fetchall()
        return [_transaction_from_row(r) for r in rows]

    def spending_summary(
        self,
        start_date: date,
        end_date: date,
        group_by: str,
    ) -> list[tuple[str, Decimal, int]]:
        """Return ``(group_key, total_amount, txn_count)`` tuples.

        ``group_by`` must be one of 'category', 'merchant', or 'month'.
        Amounts are summed as stored (debits negative, credits positive).
        Results are ordered by total descending (most negative first).
        """
        if group_by == "category":
            sql = (
                "SELECT COALESCE(c.name, 'Uncategorized') AS k,"
                " CAST(SUM(t.amount) AS TEXT) AS total,"
                " COUNT(*) AS n "
                "FROM transactions t LEFT JOIN categories c ON c.id = t.category_id "
                "WHERE t.txn_date >= ? AND t.txn_date <= ? "
                "GROUP BY k ORDER BY SUM(t.amount) ASC"
            )
        elif group_by == "merchant":
            sql = (
                "SELECT COALESCE(t.clean_merchant, 'Unknown') AS k,"
                " CAST(SUM(t.amount) AS TEXT) AS total,"
                " COUNT(*) AS n "
                "FROM transactions t "
                "WHERE t.txn_date >= ? AND t.txn_date <= ? "
                "GROUP BY k ORDER BY SUM(t.amount) ASC"
            )
        elif group_by == "month":
            sql = (
                "SELECT strftime('%Y-%m', t.txn_date) AS k,"
                " CAST(SUM(t.amount) AS TEXT) AS total,"
                " COUNT(*) AS n "
                "FROM transactions t "
                "WHERE t.txn_date >= ? AND t.txn_date <= ? "
                "GROUP BY k ORDER BY k ASC"
            )
        else:
            raise ValueError(f"invalid group_by: {group_by!r}")

        rows = self._conn.execute(sql, (start_date.isoformat(), end_date.isoformat())).fetchall()
        return [(r["k"], Decimal(str(r["total"])), int(r["n"])) for r in rows]

    def count_transactions(self, account_id: int | None = None) -> int:
        """Return the number of transactions (optionally per account)."""
        if account_id is None:
            row = self._conn.execute("SELECT COUNT(*) AS n FROM transactions").fetchone()
        else:
            row = self._conn.execute(
                "SELECT COUNT(*) AS n FROM transactions WHERE account_id = ?",
                (account_id,),
            ).fetchone()
        return int(row["n"])

    def set_transaction_category(
        self,
        txn_id: int,
        category_id: int,
        source: str = "manual",
    ) -> Transaction:
        """Assign a category to a transaction and return the updated row.

        Manual labels (``category_source='manual'``) are never silently
        overwritten by rule-based reassignment; callers pass
        ``source='manual'`` to explicitly override.
        """
        current = self.get_transaction(txn_id)
        if current.category_source == "manual" and source == "rule":
            return current
        with transaction(self._conn):
            self._conn.execute(
                "UPDATE transactions SET category_id = ?, category_source = ? WHERE id = ?",
                (category_id, source, txn_id),
            )
        return self.get_transaction(txn_id)

    def bulk_update_category(
        self,
        category_id: int,
        merchant: str | None = None,
        uncategorized_only: bool = True,
        source: str = "manual",
    ) -> int:
        """Reassign matching transactions to a category. Returns row count.

        Manual labels are never overwritten, regardless of ``source``.
        """
        clauses: list[str] = ["category_source IS NOT 'manual'"]
        params: list[object] = [category_id, source]

        if uncategorized_only:
            clauses.append("(category_id IS NULL OR category_source = 'uncategorized')")
        if merchant:
            clauses.append(
                "(UPPER(COALESCE(clean_merchant, '')) LIKE ? OR UPPER(raw_description) LIKE ?)"
            )
            needle = f"%{merchant.upper()}%"
            params.extend([needle, needle])

        sql = "UPDATE transactions SET category_id = ?, category_source = ? WHERE " + " AND ".join(
            clauses
        )
        with transaction(self._conn):
            cur = self._conn.execute(sql, params)
            return cur.rowcount

    def bulk_insert_transactions(
        self,
        account_id: int,
        rows: Iterable[RawTransaction],
        auto_categorize: bool = True,
    ) -> tuple[int, int]:
        """Insert many raw transactions, optionally applying rules.

        Returns ``(inserted, skipped_duplicates)``. When ``auto_categorize`` is
        True, the engine classifies each row against the current rule set
        and stores the winning rule's category with ``category_source='rule'``.
        """
        # Local import — avoids a top-level circular dependency with the
        # categorization package, which imports from storage.
        from finance_mcp.categorization.engine import categorize

        rule_list = self.list_rules() if auto_categorize else []

        inserted = 0
        skipped = 0
        for raw in rows:
            category_id: int | None = None
            source: str | None = None
            if auto_categorize:
                match = categorize(raw.clean_merchant, raw.raw_description, rule_list)
                if match is not None:
                    category_id = match.category_id
                    source = "rule"
            try:
                self.insert_transaction(
                    account_id,
                    raw,
                    category_id=category_id,
                    category_source=source,
                )
                inserted += 1
            except DuplicateTransactionError:
                skipped += 1
        return inserted, skipped


# --- Row -> model adapters -------------------------------------------------


def _account_from_row(row: sqlite3.Row) -> Account:
    return Account(
        id=row["id"],
        name=row["name"],
        type=row["type"],
        bank=row["bank"],
        currency=row["currency"],
        created_at=_parse_timestamp(row["created_at"]),
    )


def _budget_from_row(row: sqlite3.Row) -> Budget:
    return Budget(
        id=row["id"],
        category_id=row["category_id"],
        amount=float(Decimal(str(row["amount"]))),
        period=row["period"],
        start_date=_parse_date(row["start_date"]),
        end_date=_parse_date(row["end_date"]) if row["end_date"] else None,
        created_at=_parse_timestamp(row["created_at"]),
    )


def _goal_from_row(row: sqlite3.Row) -> Goal:
    return Goal(
        id=row["id"],
        name=row["name"],
        target_amount=float(Decimal(str(row["target_amount"]))),
        current_amount=float(Decimal(str(row["current_amount"]))),
        deadline=_parse_date(row["deadline"]) if row["deadline"] else None,
        linked_account_id=row["linked_account_id"],
        created_at=_parse_timestamp(row["created_at"]),
    )


def _rule_from_row(row: sqlite3.Row) -> Rule:
    return Rule(
        id=row["id"],
        pattern=row["pattern"],
        match_type=row["match_type"],
        category_id=row["category_id"],
        priority=row["priority"],
        is_user_defined=bool(row["is_user_defined"]),
        created_at=_parse_timestamp(row["created_at"]),
    )


def _category_from_row(row: sqlite3.Row) -> Category:
    return Category(
        id=row["id"],
        name=row["name"],
        parent_id=row["parent_id"],
        icon=row["icon"],
        is_income=bool(row["is_income"]),
    )


def _transaction_from_row(row: sqlite3.Row) -> Transaction:
    return Transaction(
        id=row["id"],
        account_id=row["account_id"],
        txn_date=_parse_date(row["txn_date"]),
        value_date=_parse_date(row["value_date"]) if row["value_date"] else None,
        amount=float(Decimal(str(row["amount"]))),
        currency=row["currency"],
        raw_description=row["raw_description"],
        clean_merchant=row["clean_merchant"],
        category_id=row["category_id"],
        category_source=row["category_source"],
        reference_no=row["reference_no"],
        running_balance=(
            float(Decimal(str(row["running_balance"])))
            if row["running_balance"] is not None
            else None
        ),
        is_transfer=bool(row["is_transfer"]),
        transfer_pair_id=row["transfer_pair_id"],
        notes=row["notes"],
        created_at=_parse_timestamp(row["created_at"]),
        dedup_hash=row["dedup_hash"],
    )


def _parse_date(value: object) -> date:
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value))


def _parse_timestamp(value: object) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    # SQLite CURRENT_TIMESTAMP uses 'YYYY-MM-DD HH:MM:SS'
    return datetime.fromisoformat(str(value).replace(" ", "T"))
