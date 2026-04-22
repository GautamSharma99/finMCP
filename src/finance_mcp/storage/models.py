"""Pydantic DTOs shared across the finance_mcp package.

Every module boundary exchanges these models, not raw dicts. FastMCP
derives tool schemas from these types.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

AccountType = Literal["savings", "credit_card", "cash"]
Period = Literal["monthly", "quarterly", "yearly"]
MatchType = Literal["contains", "regex", "exact"]
CategorySource = Literal["rule", "manual", "uncategorized"]
GroupBy = Literal["category", "merchant", "month"]


class _Base(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# --- Core entities ----------------------------------------------------------


class Account(_Base):
    """A bank account or credit card."""

    id: int | None = None
    name: str
    type: AccountType
    bank: str | None = None
    currency: str = "INR"
    created_at: datetime | None = None


class Category(_Base):
    """A category in the hierarchical tree."""

    id: int | None = None
    name: str
    parent_id: int | None = None
    icon: str | None = None
    is_income: bool = False


class Rule(_Base):
    """A pattern-to-category matching rule."""

    id: int | None = None
    pattern: str
    match_type: MatchType = "contains"
    category_id: int
    priority: int = 100
    is_user_defined: bool = False
    created_at: datetime | None = None


class RawTransaction(_Base):
    """A transaction straight out of a parser, before DB persistence."""

    txn_date: date
    value_date: date | None = None
    amount: Decimal
    currency: str = "INR"
    raw_description: str
    clean_merchant: str | None = None
    reference_no: str | None = None
    running_balance: Decimal | None = None


class Transaction(_Base):
    """A persisted transaction."""

    id: int | None = None
    account_id: int
    txn_date: date
    value_date: date | None = None
    amount: Decimal
    currency: str = "INR"
    raw_description: str
    clean_merchant: str | None = None
    category_id: int | None = None
    category_source: CategorySource | None = None
    reference_no: str | None = None
    running_balance: Decimal | None = None
    is_transfer: bool = False
    transfer_pair_id: int | None = None
    notes: str | None = None
    created_at: datetime | None = None
    dedup_hash: str


class Budget(_Base):
    """A spend budget for a category over a period."""

    id: int | None = None
    category_id: int
    amount: Decimal
    period: Period
    start_date: date
    end_date: date | None = None
    created_at: datetime | None = None


class Goal(_Base):
    """A savings goal."""

    id: int | None = None
    name: str
    target_amount: Decimal
    current_amount: Decimal = Decimal("0")
    deadline: date | None = None
    linked_account_id: int | None = None
    created_at: datetime | None = None


# --- Tool result / view types ----------------------------------------------


class OperationResult(_Base):
    """Generic success/failure envelope used by mutation tools."""

    success: bool
    message: str = ""
    affected: int = 0


class ImportResult(_Base):
    """Outcome of an `import_statement` call."""

    success: bool
    account_id: int | None = None
    rows_imported: int = 0
    rows_skipped: int = 0
    message: str = ""


class SummaryRow(_Base):
    """One row of a spending summary."""

    group_key: str = Field(description="Category name, merchant, or YYYY-MM month")
    total_amount: Decimal
    txn_count: int


class ComparisonRow(_Base):
    """One row of a period-vs-period comparison."""

    group_key: str
    period_a_total: Decimal
    period_b_total: Decimal
    delta: Decimal
    delta_pct: float | None = None


class BudgetStatus(_Base):
    """A budget + its utilization for a given period."""

    category_name: str
    budgeted: Decimal
    spent: Decimal
    remaining: Decimal
    utilization_pct: float


class GoalProgress(_Base):
    """Progress toward a goal."""

    name: str
    target_amount: Decimal
    current_amount: Decimal
    progress_pct: float
    deadline: date | None = None
    on_track: bool | None = None


class RecurringTxn(_Base):
    """A detected recurring/subscription charge."""

    merchant: str
    avg_amount: Decimal
    cadence_days: int
    occurrences: int
    last_seen: date
    category_name: str | None = None


class NetWorth(_Base):
    """Net worth snapshot."""

    as_of: date
    total_assets: Decimal
    total_liabilities: Decimal
    net_worth: Decimal


__all__ = [
    "Account",
    "AccountType",
    "Budget",
    "BudgetStatus",
    "Category",
    "CategorySource",
    "ComparisonRow",
    "Goal",
    "GoalProgress",
    "GroupBy",
    "ImportResult",
    "MatchType",
    "NetWorth",
    "OperationResult",
    "Period",
    "RawTransaction",
    "RecurringTxn",
    "Rule",
    "SummaryRow",
    "Transaction",
]
