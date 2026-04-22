# Personal Finance Analyst MCP Server — Product Requirements Document

> **Document purpose:** This PRD is the single source of truth for building a Personal Finance Analyst MCP server as a learning/portfolio project. It is written to be fed directly to Claude Code as context. Every section is intentionally unambiguous; if something is ambiguous, Claude Code should ask before proceeding.

---

## 1. Project Overview

### 1.1 What We're Building

A locally-running **MCP server built with FastMCP** that turns a pile of bank/credit-card CSV statements into a searchable, analyzable personal finance knowledge base. Any MCP client (Claude Desktop, Cursor, etc.) can connect and have natural-language conversations about the user's money:

- "How much did I spend on food delivery last month vs the same month last year?"
- "What are my top 5 recurring subscriptions?"
- "Am I on track for my ₹10L emergency fund goal?"
- "Categorize all my Swiggy transactions as 'Food Delivery'."

### 1.2 Project Context

This is a **learning/portfolio project**, not a commercial product:

- Uses **dummy data only** — no real bank credentials, no OAuth, no API keys.
- A dummy-data generator script ships with the repo so anyone can clone and run.
- CSV formats mimic real Indian bank statements (HDFC, ICICI) for realism.
- Must be impressive on GitHub: clean code, tests, good README, demo-worthy.

### 1.3 Non-Goals (Explicitly Out of Scope)

To prevent scope creep, these are **NOT** part of v1:

- Connecting to any real bank, UPI, or payment API
- Email or SMS parsing
- Account Aggregator framework integration
- Multi-currency support (INR only)
- Web dashboard / UI (MCP + CLI only)
- Investment tracking (stocks, mutual funds)
- Tax calculation
- Multi-user support or authentication
- Cloud deployment / remote hosting
- FastMCP **Apps** (interactive UI components) — core MCP only in v1

---

## 2. Target Personas & User Stories

### 2.1 Primary Persona: The Learner-Developer

A developer learning MCP who wants to (a) build a useful project, (b) showcase MCP fluency on GitHub, and (c) maybe actually use the tool on their own (fake) data.

### 2.2 Core User Stories

| # | As a… | I want to… | So that… |
|---|-------|-----------|----------|
| U1 | user | import a bank CSV | my transactions are stored and queryable |
| U2 | user | ask "how much did I spend on X in month Y" | I get instant answers without spreadsheets |
| U3 | user | have transactions auto-categorized | I don't manually tag 500 rows |
| U4 | user | teach the system a new rule | future transactions categorize correctly |
| U5 | user | set a monthly budget per category | I can see if I'm over/under |
| U6 | user | set a savings goal | I can track progress |
| U7 | user | get a monthly review | I understand my financial month at a glance |
| U8 | user | detect recurring subscriptions | I can identify cuts |
| U9 | developer | clone the repo and run it in 2 minutes | I can evaluate/demo the project |
| U10 | developer | read clean code with tests | I trust the project quality |

---

## 3. Technical Architecture

### 3.1 Tech Stack (Locked In)

- **Language:** Python 3.11+ (3.12 preferred)
- **MCP framework:** **FastMCP 3.x** — install with `uv add fastmcp`. Use the standalone PrefectHQ/fastmcp package (`from fastmcp import FastMCP`). **Do NOT** use `mcp.server.fastmcp` (that is the deprecated FastMCP 1.x bundled in the official SDK).
- **Storage:** SQLite (stdlib `sqlite3` + thin wrapper)
- **Data parsing:** `pandas` for CSV ingestion
- **Validation:** `pydantic` v2 (FastMCP derives JSON schemas from type hints automatically)
- **CLI:** `typer` for the dummy-data generator
- **Testing:** `pytest` + `pytest-asyncio` + `pytest-cov` (use FastMCP's in-memory `Client` for tool/resource/prompt tests)
- **Linting/Formatting:** `ruff` (single tool for both)
- **Type checking:** `mypy` (strict mode on `src/`)
- **Dummy data:** `faker` with `en_IN` locale
- **Package manager:** `uv`

### 3.2 Why FastMCP

FastMCP gives us decorator-based tool/resource/prompt registration (`@mcp.tool`, `@mcp.resource`, `@mcp.prompt`), automatic Pydantic schema generation from type hints, `fastmcp dev` with hot reload and the Inspector UI, and first-class in-memory testing via `Client(server)`. Registered functions **stay callable as regular Python**, so unit tests can call them directly without going through the MCP transport. It's the most widely-used Python MCP framework (~70% of Python MCP servers) and the code is markedly shorter and clearer than the raw SDK.

### 3.3 High-Level Architecture

```
┌─────────────────────┐
│   MCP Client        │   (Claude Desktop, Cursor, `fastmcp dev` Inspector)
│  (not our code)     │
└──────────┬──────────┘
           │  stdio / JSON-RPC
┌──────────▼──────────┐
│  FastMCP Server     │   src/finance_mcp/server.py
│  @mcp.tool          │   - Tool registrations
│  @mcp.resource      │   - Resource URIs
│  @mcp.prompt        │   - Prompt templates
└──────────┬──────────┘
           │
    ┌──────┴──────┬─────────────┬──────────────┐
    ▼             ▼             ▼              ▼
┌────────┐  ┌──────────┐  ┌──────────┐  ┌───────────┐
│Parsers │  │Repository│  │Categoriz.│  │Analytics  │
│ hdfc   │  │(SQLite)  │  │  engine  │  │  engine   │
│ icici  │  │          │  │          │  │           │
│generic │  │          │  │          │  │           │
└────────┘  └──────────┘  └──────────┘  └───────────┘
```

### 3.4 Project Structure

```
finance-analyst-mcp/
├── README.md
├── LICENSE                       # MIT
├── pyproject.toml
├── uv.lock
├── .gitignore
├── .python-version
├── Makefile                      # common tasks: test, lint, dev, demo
├── docs/
│   ├── ARCHITECTURE.md
│   ├── MCP_INTERFACE.md          # list of all tools/resources/prompts
│   └── DEMO.md                   # demo transcript with Claude Desktop
├── src/
│   └── finance_mcp/
│       ├── __init__.py
│       ├── server.py             # FastMCP app + entry point
│       ├── config.py             # settings, paths, defaults
│       ├── errors.py             # custom exceptions
│       ├── tools/
│       │   ├── __init__.py
│       │   ├── import_tools.py
│       │   ├── query_tools.py
│       │   ├── category_tools.py
│       │   ├── budget_tools.py
│       │   ├── goal_tools.py
│       │   └── insight_tools.py
│       ├── resources/
│       │   ├── __init__.py
│       │   ├── accounts.py
│       │   ├── categories.py
│       │   ├── budgets.py
│       │   └── insights.py
│       ├── prompts/
│       │   ├── __init__.py
│       │   ├── monthly_review.py
│       │   ├── find_savings.py
│       │   └── goal_check.py
│       ├── parsers/
│       │   ├── __init__.py
│       │   ├── base.py           # BankParser ABC
│       │   ├── hdfc.py
│       │   ├── icici.py
│       │   ├── generic.py
│       │   └── normalize.py      # normalize_merchant()
│       ├── storage/
│       │   ├── __init__.py
│       │   ├── db.py             # connection, migrations
│       │   ├── schema.sql        # full DDL
│       │   ├── models.py         # Pydantic models (shared DTOs)
│       │   └── repository.py     # CRUD operations
│       ├── categorization/
│       │   ├── __init__.py
│       │   ├── engine.py         # rule matcher (pure)
│       │   ├── rules.py          # CRUD for rules
│       │   └── default_rules.py  # 30+ shipped rules
│       └── analytics/
│           ├── __init__.py
│           ├── aggregations.py
│           ├── recurring.py
│           └── insights.py
├── scripts/
│   ├── generate_dummy_data.py
│   └── setup_demo.py
├── sample_data/                  # checked into git
│   ├── hdfc_savings_jan_2025.csv
│   ├── hdfc_savings_feb_2025.csv
│   ├── hdfc_savings_mar_2025.csv
│   ├── icici_creditcard_jan_2025.csv
│   ├── icici_creditcard_feb_2025.csv
│   └── icici_creditcard_mar_2025.csv
└── tests/
    ├── __init__.py
    ├── conftest.py               # fixtures: temp DB, sample CSVs, in-memory Client
    ├── test_parsers/
    │   ├── test_normalize.py
    │   ├── test_hdfc.py
    │   ├── test_icici.py
    │   └── fixtures/
    ├── test_storage/
    │   └── test_repository.py
    ├── test_categorization/
    │   ├── test_engine.py
    │   └── test_rules.py
    ├── test_analytics/
    │   ├── test_aggregations.py
    │   └── test_recurring.py
    └── test_server/
        ├── test_tools.py         # uses FastMCP in-memory Client
        ├── test_resources.py
        └── test_prompts.py
```

---

## 4. Database Schema

### 4.1 Full DDL (Save as `src/finance_mcp/storage/schema.sql`)

```sql
-- Accounts: bank accounts, credit cards
CREATE TABLE IF NOT EXISTS accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,           -- e.g. "HDFC Savings - 1234"
    type TEXT NOT NULL,                   -- 'savings' | 'credit_card' | 'cash'
    bank TEXT,                            -- 'HDFC', 'ICICI', etc.
    currency TEXT NOT NULL DEFAULT 'INR',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    parent_id INTEGER REFERENCES categories(id) ON DELETE SET NULL,
    icon TEXT,
    is_income BOOLEAN NOT NULL DEFAULT 0,
    UNIQUE(name, parent_id)
);

CREATE TABLE IF NOT EXISTS rules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pattern TEXT NOT NULL,
    match_type TEXT NOT NULL DEFAULT 'contains', -- 'contains' | 'regex' | 'exact'
    category_id INTEGER NOT NULL REFERENCES categories(id),
    priority INTEGER NOT NULL DEFAULT 100,       -- lower = higher priority
    is_user_defined BOOLEAN NOT NULL DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id INTEGER NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    txn_date DATE NOT NULL,
    value_date DATE,
    amount DECIMAL(12, 2) NOT NULL,       -- positive = credit, negative = debit
    currency TEXT NOT NULL DEFAULT 'INR',
    raw_description TEXT NOT NULL,
    clean_merchant TEXT,
    category_id INTEGER REFERENCES categories(id),
    category_source TEXT,                 -- 'rule' | 'manual' | 'uncategorized'
    reference_no TEXT,
    running_balance DECIMAL(12, 2),
    is_transfer BOOLEAN NOT NULL DEFAULT 0,
    transfer_pair_id INTEGER REFERENCES transactions(id),
    notes TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    dedup_hash TEXT NOT NULL UNIQUE
);
CREATE INDEX IF NOT EXISTS idx_txn_date ON transactions(txn_date);
CREATE INDEX IF NOT EXISTS idx_txn_account ON transactions(account_id);
CREATE INDEX IF NOT EXISTS idx_txn_category ON transactions(category_id);
CREATE INDEX IF NOT EXISTS idx_txn_merchant ON transactions(clean_merchant);

CREATE TABLE IF NOT EXISTS budgets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category_id INTEGER NOT NULL REFERENCES categories(id) ON DELETE CASCADE,
    amount DECIMAL(12, 2) NOT NULL,
    period TEXT NOT NULL,                 -- 'monthly' | 'quarterly' | 'yearly'
    start_date DATE NOT NULL,
    end_date DATE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(category_id, period, start_date)
);

CREATE TABLE IF NOT EXISTS goals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    target_amount DECIMAL(12, 2) NOT NULL,
    current_amount DECIMAL(12, 2) NOT NULL DEFAULT 0,
    deadline DATE,
    linked_account_id INTEGER REFERENCES accounts(id),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS imports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id INTEGER NOT NULL REFERENCES accounts(id),
    file_path TEXT NOT NULL,
    file_hash TEXT NOT NULL,
    rows_imported INTEGER NOT NULL,
    rows_skipped INTEGER NOT NULL,
    imported_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

### 4.2 Dedup Hash

```
sha256(account_id | txn_date_iso | amount_str | raw_description_normalized)[:16]
```

### 4.3 Default Category Seeds

- **Income**: Salary, Interest, Refunds, Other Income
- **Food & Dining**: Groceries, Restaurants, Food Delivery, Cafes
- **Transport**: Fuel, Ride-hailing, Public Transit, Parking
- **Utilities**: Electricity, Internet, Mobile, Water, Gas
- **Housing**: Rent, Maintenance, Home Supplies
- **Entertainment**: Streaming, Movies, Events, Gaming
- **Shopping**: Clothing, Electronics, General
- **Health**: Pharmacy, Doctor, Gym, Insurance
- **Financial**: Credit Card Payment, Loan EMI, Investments, Bank Fees
- **Travel**: Flights, Hotels, Trains
- **Transfers**: Self-Transfer, P2P
- **Uncategorized**

---

## 5. FastMCP Server Pattern (Reference Implementation)

The server file must follow this shape. Tools register with `@mcp.tool`, resources with `@mcp.resource`, prompts with `@mcp.prompt`. FastMCP derives the JSON schema from the function signature.

### 5.1 Entry Point (`src/finance_mcp/server.py`)

```python
from __future__ import annotations

from fastmcp import FastMCP

from finance_mcp.config import settings
from finance_mcp.storage.db import init_db

mcp = FastMCP(
    name="finance-analyst",
    instructions=(
        "Personal Finance Analyst. Use tools to import bank CSVs, query "
        "transactions, manage budgets and goals, and detect recurring charges. "
        "Read resources for at-a-glance context. Use prompts for structured reviews."
    ),
)

# Importing these modules triggers the @mcp.tool/@mcp.resource/@mcp.prompt
# decorators to register handlers on the `mcp` instance above.
from finance_mcp.tools import (  # noqa: E402, F401
    import_tools, query_tools, category_tools,
    budget_tools, goal_tools, insight_tools,
)
from finance_mcp.resources import (  # noqa: E402, F401
    accounts, categories, budgets, insights,
)
from finance_mcp.prompts import (  # noqa: E402, F401
    monthly_review, find_savings, goal_check,
)


def main() -> None:
    """Entry point for `finance-mcp` console script and `python -m finance_mcp.server`."""
    init_db(settings.db_path)
    mcp.run()  # defaults to stdio transport


if __name__ == "__main__":
    main()
```

### 5.2 Example Tool Module

```python
# src/finance_mcp/tools/query_tools.py
from __future__ import annotations

from datetime import date

from pydantic import Field

from finance_mcp.server import mcp
from finance_mcp.storage.models import Transaction
from finance_mcp.storage.repository import Repository


@mcp.tool
def query_transactions(
    start_date: date | None = None,
    end_date: date | None = None,
    category: str | None = Field(default=None, description="Category name (leaf or parent)"),
    account: str | None = None,
    merchant: str | None = None,
    min_amount: float | None = None,
    max_amount: float | None = None,
    limit: int = 100,
) -> list[Transaction]:
    """Filter transactions across all accounts. All filters are AND-ed."""
    return Repository.get().query_transactions(
        start_date=start_date, end_date=end_date,
        category=category, account=account, merchant=merchant,
        min_amount=min_amount, max_amount=max_amount, limit=limit,
    )
```

### 5.3 Example Resource Module

```python
# src/finance_mcp/resources/insights.py
from __future__ import annotations

from finance_mcp.server import mcp
from finance_mcp.analytics.insights import render_monthly_report


@mcp.resource("finance://insights/monthly/{month}")
def monthly_insight(month: str) -> str:
    """Markdown monthly report for a YYYY-MM month."""
    return render_monthly_report(month)
```

### 5.4 Example Prompt Module

```python
# src/finance_mcp/prompts/monthly_review.py
from __future__ import annotations

from fastmcp.prompts import Message

from finance_mcp.server import mcp


@mcp.prompt
def monthly_review(month: str) -> list[Message]:
    """Structured monthly financial review for YYYY-MM."""
    return [
        Message(
            role="user",
            content=(
                f"Please review my finances for {month}. "
                f"Use the finance://insights/monthly/{month} resource for data. "
                "Cover: total income vs expense, top 5 categories, notable transactions, "
                "budget status, comparison to previous month, and 2–3 concrete suggestions."
            ),
        )
    ]
```

---

## 6. MCP Interface Specification

Exact contract. FastMCP generates schemas from type hints — these are the Python signatures.

### 6.1 Tools

| Tool name | Signature |
|-----------|-----------|
| `import_statement` | `(file_path: str, account_name: str, bank: str \| None = None) -> ImportResult` |
| `list_accounts` | `() -> list[Account]` |
| `query_transactions` | `(start_date=None, end_date=None, category=None, account=None, merchant=None, min_amount=None, max_amount=None, limit=100) -> list[Transaction]` |
| `get_spending_summary` | `(start_date: date, end_date: date, group_by: Literal['category','merchant','month']) -> list[SummaryRow]` |
| `compare_periods` | `(period_a_start, period_a_end, period_b_start, period_b_end, group_by) -> list[ComparisonRow]` |
| `categorize_transaction` | `(transaction_id: int, category_name: str) -> OperationResult` |
| `bulk_categorize` | `(category_name: str, merchant: str \| None = None, uncategorized_only: bool = True) -> OperationResult` |
| `create_rule` | `(pattern, category_name, match_type='contains', priority=50) -> Rule` |
| `list_rules` | `(user_only: bool = False) -> list[Rule]` |
| `delete_rule` | `(rule_id: int) -> OperationResult` |
| `set_budget` | `(category_name, amount, period, start_date) -> Budget` |
| `get_budget_status` | `(month: str) -> list[BudgetStatus]` |
| `set_goal` | `(name, target_amount, deadline=None, linked_account=None) -> Goal` |
| `get_goal_progress` | `(goal_name: str \| None = None) -> list[GoalProgress]` |
| `detect_recurring` | `(min_occurrences: int = 3, lookback_months: int = 6) -> list[RecurringTxn]` |
| `get_net_worth` | `(as_of: date \| None = None) -> NetWorth` |

All tool functions must:
- Have full type hints on every parameter and the return type.
- Return a Pydantic model (or list of them) defined in `storage/models.py`.
- Include a docstring — FastMCP uses it as the tool description.
- Use `pydantic.Field(description=...)` for any parameter whose meaning isn't obvious from the name.

### 6.2 Resources

| URI pattern | Returns |
|-------------|---------|
| `finance://accounts` | JSON list of all accounts with balances |
| `finance://categories/tree` | Hierarchical category tree (JSON) |
| `finance://budgets/current` | Active budgets with utilization (JSON) |
| `finance://insights/monthly/{month}` | Markdown monthly report |
| `finance://insights/summary/last-30-days` | Markdown rolling 30-day summary |

### 6.3 Prompts

| Prompt name | Arguments | Purpose |
|-------------|-----------|---------|
| `monthly_review` | `month: str` | Structured walkthrough of a given month |
| `find_savings` | `target_amount: float \| None = None` | Surface cuts to hit a target |
| `goal_check` | `goal_name: str \| None = None` | Progress + projected hit date |

---

## 7. Parser Specifications

### 7.1 HDFC Savings CSV

Columns: `Date, Narration, Chq./Ref.No., Value Dt, Withdrawal Amt., Deposit Amt., Closing Balance`

- Date: `DD/MM/YY`
- `Withdrawal Amt.` → negative amount; `Deposit Amt.` → positive
- Narration examples:
  - `UPI-SWIGGY-swiggy@axl-...-PAYMENT FROM PHONE` → merchant `SWIGGY`
  - `POS 4567XXXX UBER INDIA SYSTEMS` → `UBER INDIA`
  - `NEFT DR-AXISCN0123-ACME CORP SALARY` → `ACME CORP SALARY`
- Skip rows with no amounts (summary/header rows)

### 7.2 ICICI Credit Card CSV

Columns: `Transaction Date, Transaction Details, Ref No, Amount (INR), Debit/Credit`

- Date: `DD-MM-YYYY`
- `DR` → negative, `CR` → positive

### 7.3 Generic Parser

Stub for v1. Accepts a user-supplied column mapping later.

### 7.4 Merchant Normalization (`parsers/normalize.py`)

`normalize_merchant(raw: str) -> str`:

1. Uppercase
2. Strip prefixes: `UPI-`, `POS`, `NEFT DR-`, `IMPS-`, `ACH D-`
3. Strip trailing ref numbers: `-?\d{6,}$`, `-XXXXXX.*`
4. Strip VPAs: `@ybl`, `@axl`, `@paytm`, etc.
5. Collapse whitespace
6. Truncate to 80 chars

Unit-test with ≥20 examples.

---

## 8. Categorization Engine

### 8.1 Algorithm

On insert (or re-categorize):

1. Fetch rules ordered by `priority ASC, is_user_defined DESC`.
2. For each rule, match against `clean_merchant`, fall back to `raw_description`.
3. First match wins → `category_id`, `category_source='rule'`.
4. No match → `Uncategorized`, `category_source='uncategorized'`.

**Manual overrides (`category_source='manual'`) are never overwritten by rules.**

### 8.2 Default Rules (≥30)

Must span all top-level categories. Examples:

| Pattern | Match | Category |
|---------|-------|----------|
| `SWIGGY` | contains | Food & Dining > Food Delivery |
| `ZOMATO` | contains | Food & Dining > Food Delivery |
| `BLINKIT` | contains | Food & Dining > Groceries |
| `UBER` | contains | Transport > Ride-hailing |
| `OLA` | contains | Transport > Ride-hailing |
| `BESCOM` | contains | Utilities > Electricity |
| `ACT FIBERNET` | contains | Utilities > Internet |
| `NETFLIX` | contains | Entertainment > Streaming |
| `SPOTIFY` | contains | Entertainment > Streaming |
| `AMAZON` | contains | Shopping > General |
| `FLIPKART` | contains | Shopping > General |
| `SALARY` | contains | Income > Salary |
| …≥18 more… | | |

Full list in `default_rules.py`.

---

## 9. Dummy Data Generator

### 9.1 CLI

```
python scripts/generate_dummy_data.py \
    --output-dir sample_data/ \
    --months 6 \
    --monthly-income 120000 \
    --seed 42
```

Must generate:

- 1 HDFC Savings CSV per month (realistic narrations, correct format)
- 1 ICICI Credit Card CSV per month
- Baked-in patterns:
  - Salary credit on the 1st (HDFC)
  - Rent debit ~5th (HDFC)
  - Monthly subscriptions: Netflix, Spotify, ACT Fibernet
  - 2–5 Swiggy/Zomato per week (weekend-weighted)
  - 1–3 Uber/Ola per week
  - Big purchases every 2–4 weeks
  - 1 credit card bill payment per month (HDFC → ICICI, detected as transfer)
  - 1–2 refunds randomly
  - Closing balances that correctly sum
- Reproducible: same `--seed` → identical output
- Must parse cleanly through the respective parser (integration test)

---

## 10. Testing Requirements

### 10.1 Coverage Targets

- Overall ≥80%
- `parsers/` ≥95%
- `categorization/` ≥90%
- `analytics/` ≥85%

### 10.2 FastMCP In-Memory Client (Required for Server Tests)

FastMCP ships an in-memory `Client` that talks to the server without subprocess or network. Use this for all tool/resource/prompt tests:

```python
# tests/conftest.py
import pytest
import pytest_asyncio
from fastmcp import Client

from finance_mcp.server import mcp
from finance_mcp.storage.db import init_db


@pytest_asyncio.fixture
async def mcp_client(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("FINANCE_MCP_DB_PATH", str(db_path))
    init_db(db_path)
    async with Client(mcp) as client:
        yield client
```

```python
# tests/test_server/test_tools.py
import pytest


@pytest.mark.asyncio
async def test_list_accounts_empty(mcp_client):
    result = await mcp_client.call_tool("list_accounts", {})
    assert result.data == []
```

Because FastMCP keeps decorated functions callable, pure logic can **also** be tested by calling the function directly — prefer that for non-MCP-concerned assertions.

### 10.3 Required Test Categories

- Unit tests for every parser (≥3 fixtures each, including refunds, multi-line descriptions, malformed dates)
- Unit tests for `normalize_merchant` (≥20 cases)
- Rule-matching tests (priority, user-override protection)
- Repository CRUD round-trip
- Analytics tests with known-input / known-output datasets
- Integration test: generator → parser → DB → Client query → assert counts
- Every tool invoked via `mcp_client.call_tool`; every resource via `mcp_client.read_resource`; every prompt via `mcp_client.get_prompt`

### 10.4 CI (GitHub Actions)

`.github/workflows/ci.yml` runs on push/PR:
- `ruff check`
- `ruff format --check`
- `mypy src/`
- `pytest --cov`

---

## 11. Developer Experience

### 11.1 `pyproject.toml` (Reference)

```toml
[project]
name = "finance-analyst-mcp"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "fastmcp>=3.2.0",
    "pydantic>=2.6",
    "pandas>=2.2",
    "typer>=0.12",
    "faker>=25",
]

[project.optional-dependencies]
dev = [
    "pytest>=8",
    "pytest-asyncio>=0.23",
    "pytest-cov>=5",
    "ruff>=0.5",
    "mypy>=1.10",
]

[project.scripts]
finance-mcp = "finance_mcp.server:main"

[tool.pytest.ini_options]
asyncio_mode = "auto"
```

### 11.2 README Must Contain

1. One-paragraph pitch with demo GIF/screenshot placeholder
2. Quickstart (≤5 commands):
   ```
   git clone ...
   cd finance-analyst-mcp
   uv sync
   uv run python scripts/setup_demo.py
   # then paste the claude_desktop_config.json snippet
   ```
3. 3–4 example conversations
4. Architecture diagram
5. Table of tools/resources/prompts
6. Tech stack and project structure
7. Testing section
8. Roadmap (v2 teasers)
9. License (MIT)

### 11.3 Makefile

```makefile
.PHONY: install test lint format dev inspect generate demo clean

install:
	uv sync

test:
	uv run pytest --cov=src/finance_mcp

lint:
	uv run ruff check src/ tests/
	uv run mypy src/

format:
	uv run ruff format src/ tests/

dev:
	uv run fastmcp dev src/finance_mcp/server.py   # hot-reload + Inspector UI

inspect:
	uv run fastmcp inspect src/finance_mcp/server.py

generate:
	uv run python scripts/generate_dummy_data.py --output-dir sample_data/ --months 6 --seed 42

demo:
	uv run python scripts/setup_demo.py

clean:
	rm -rf .pytest_cache .mypy_cache .ruff_cache dist build *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} +
```

### 11.4 Claude Desktop Config (in README)

```json
{
  "mcpServers": {
    "finance-analyst": {
      "command": "uv",
      "args": [
        "--directory", "/absolute/path/to/finance-analyst-mcp",
        "run", "finance-mcp"
      ]
    }
  }
}
```

The `finance-mcp` entry point is defined in `[project.scripts]` and calls `main()` in `server.py`.

### 11.5 Local Development Flow

- **Iterate on tools:** `make dev` starts `fastmcp dev` with hot reload and opens the Inspector. This replaces the painful edit → restart Claude Desktop loop.
- **Integration-test a tool:** write a pytest using the `mcp_client` fixture.
- **Check schema/tool list:** `make inspect`.

---

## 12. Implementation Phases (For Claude Code)

Build in this exact order. At the end of each phase the project must be runnable and tested.

### Phase 1 — Foundation (Day 1)
1. Scaffold project structure, `pyproject.toml` with FastMCP, `.gitignore`, `Makefile`, ruff/mypy config
2. `schema.sql` and `storage/db.py` (connection + migrations)
3. `storage/models.py` (Pydantic models for all DTOs: Account, Transaction, Category, Rule, Budget, Goal, plus tool result types like `ImportResult`, `OperationResult`, `SummaryRow`, `BudgetStatus`, `GoalProgress`, `RecurringTxn`, `NetWorth`)
4. `storage/repository.py` with CRUD for accounts, categories, transactions
5. Seed default categories on DB init
6. Tests for repository layer
**Acceptance:** `pytest` green; can init DB and insert entities from a script.

### Phase 2 — Parsers + Dummy Data (Day 2)
1. `parsers/normalize.py` + unit tests (≥20 cases)
2. `parsers/base.py` ABC
3. `parsers/hdfc.py` + fixture tests
4. `parsers/icici.py` + fixture tests
5. `scripts/generate_dummy_data.py` producing 6 months of both formats
6. Integration test: generator output → parser → DB counts match
**Acceptance:** `make generate` creates valid CSVs that round-trip through parsers.

### Phase 3 — Categorization (Day 3)
1. `categorization/default_rules.py` with ≥30 rules
2. `categorization/engine.py` (matching algorithm, pure)
3. `categorization/rules.py` (CRUD + priority)
4. Auto-categorize on import
5. Tests for priority ordering and user-override protection
**Acceptance:** After importing dummy data, ≥70% of transactions auto-categorized.

### Phase 4 — FastMCP Server: Core Tools (Day 4)
1. `server.py` with `FastMCP` instance + `main()` entry point
2. Tool modules with `@mcp.tool`: `import_statement`, `list_accounts`, `query_transactions`, `get_spending_summary`, `categorize_transaction`, `bulk_categorize`, `create_rule`, `list_rules`, `delete_rule`
3. Every tool: full type hints + docstring + Pydantic return model
4. In-memory `Client` fixture in `conftest.py`
5. `test_server/test_tools.py` covers every tool (happy + error paths)
**Acceptance:** `make dev` opens Inspector, every tool callable; Claude Desktop can connect and list tools.

### Phase 5 — Analytics + Advanced Tools (Day 5)
1. `analytics/aggregations.py`
2. `analytics/recurring.py` (subscription detection)
3. Tools: `compare_periods`, `set_budget`, `get_budget_status`, `set_goal`, `get_goal_progress`, `detect_recurring`, `get_net_worth`
**Acceptance:** All v1 tools implemented, tested via in-memory Client.

### Phase 6 — Resources + Prompts (Day 6)
1. Resources with `@mcp.resource(...)`: accounts, categories tree, current budgets, monthly insight (`finance://insights/monthly/{month}`), 30-day summary
2. Prompts with `@mcp.prompt`: `monthly_review`, `find_savings`, `goal_check`
3. Markdown insight renderer in `analytics/insights.py`
**Acceptance:** Resources appear in Inspector; prompts render structured Message lists.

### Phase 7 — Polish (Day 7)
1. `scripts/setup_demo.py` — one-command demo bootstrap (generate → init → import → print Claude Desktop config snippet)
2. README with demo conversations, architecture diagram, badges
3. `docs/` files
4. GitHub Actions CI
5. Demo GIF / asciinema cast
6. Final coverage pass
**Acceptance:** A stranger can clone → `make demo` → connect Claude Desktop → useful conversation in <5 min.

---

## 13. Acceptance Criteria (Definition of Done)

- [ ] Clean clone → `make demo` → Claude Desktop connection in <5 min
- [ ] All 16 tools, 5 resources, 3 prompts from §6 implemented via FastMCP decorators
- [ ] Dummy data generator produces 6 months of plausible data from a seed
- [ ] Parsers handle both HDFC and ICICI fixture CSVs
- [ ] ≥80% overall test coverage; parser coverage ≥95%
- [ ] Server tests use FastMCP's in-memory `Client`
- [ ] `ruff check`, `ruff format --check`, `mypy src/` all clean
- [ ] GitHub Actions CI green
- [ ] README: quickstart, 3+ conversations, tool table, architecture
- [ ] ≥30 default categorization rules shipped
- [ ] Recurring detector identifies the seeded subscriptions
- [ ] No real financial data anywhere in the repo

---

## 14. Instructions for Claude Code

1. **Read this entire PRD before writing any code.**
2. **Confirm the plan** with the user before starting Phase 1 — list the phases and ask which to start.
3. **Work phase by phase.** Do not jump ahead. End each phase with green tests and a brief demo to the user.
4. **Ask, don't assume.** If anything is ambiguous, ask.
5. **Commits small, labeled by phase** (`phase-2: add HDFC parser`).
6. **Use project structure in §3.4 verbatim.** Don't reorganize without approval.
7. **FastMCP 3.x only.** `from fastmcp import FastMCP`. **Never** `from mcp.server.fastmcp import FastMCP` (that's the deprecated v1).
8. **No dependencies** outside §11.1 without approval.
9. **No non-goals from §1.3**, no matter how small.
10. **Clarity over cleverness.**
11. **Tests come with the code, not after.**

When uncertain about scope: **"do the smallest thing that satisfies the PRD, then ask."**

---

*End of PRD.*