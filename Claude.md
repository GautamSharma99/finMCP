# CLAUDE.md

> Project-specific instructions for Claude Code working on the **Personal Finance Analyst MCP Server** (built with FastMCP 3.x).
> Read this file at the start of every session. The PRD (`PRD.md`) is the source of truth for *what* to build; this file governs *how* to work.

---

## 1. Project Snapshot

- **What:** A local MCP server that ingests dummy bank CSVs and exposes spending analytics via tools, resources, and prompts.
- **Why:** Learning/portfolio project — the goal is clean, impressive code, not a shipping product.
- **Stack:** Python 3.11+, **FastMCP 3.x** (`fastmcp` package from PrefectHQ), SQLite, pandas, pydantic v2, pytest + pytest-asyncio, ruff, mypy, uv.
- **Client:** Claude Desktop (primary), the `fastmcp dev` Inspector (development), any MCP-compatible client (secondary).
- **Data:** Dummy only. No real bank credentials, APIs, or PII ever touch this repo.

Full specification lives in `PRD.md`. When any doubt arises, the PRD wins.

---

## 2. Golden Rules (Non-Negotiable)

1. **Read `PRD.md` before starting any work session.** Re-read relevant sections before each phase.
2. **Work one phase at a time** (PRD §12). Finish → test → commit → ask before next phase.
3. **Ask before assuming.** If a spec detail is ambiguous, ask. Do not guess.
4. **Never implement non-goals** (PRD §1.3). No email parsing, no web UI, no real bank APIs, no investment tracking, no FastMCP Apps UI in v1.
5. **Never add dependencies** outside PRD §11.1 without explicit approval.
6. **Never reorganize project structure** (PRD §3.4) without asking.
7. **No real financial data anywhere.** Not in tests, not in fixtures, not in commits.
8. **Tests come with the code, not after.**
9. **Small, labeled commits** (`phase-2: add HDFC parser`).
10. **Use FastMCP 3.x correctly** (see §4 below). Getting this wrong is the single fastest way to waste a day.
11. **When in doubt, do the smallest thing that satisfies the PRD, then ask.**

---

## 3. Session Startup Checklist

Every new session:

1. `git status` and `git log --oneline -10` to orient.
2. Open `PRD.md` §12 and identify the current phase.
3. Run `make test` to confirm the baseline is green.
4. State to the user: "We're in Phase X. Last commit was Y. Ready to continue with Z — proceed?"
5. Wait for confirmation before writing code.

---

## 4. FastMCP-Specific Rules

These are the failure modes that will bite you. Memorize them.

### 4.1 Import Correctly

```python
# ✅ RIGHT — standalone FastMCP 3.x
from fastmcp import FastMCP, Client
from fastmcp.prompts import Message

# ❌ WRONG — this is FastMCP 1.x bundled in the official mcp SDK (deprecated for new projects)
from mcp.server.fastmcp import FastMCP
```

If you ever find yourself importing from `mcp.server.fastmcp`, stop. That's the old API. Our project uses the standalone `fastmcp` package (`pip install fastmcp`, version 3.2+).

### 4.2 Register With Decorators

```python
@mcp.tool
def my_tool(x: int, y: str = "default") -> MyModel:
    """Docstring becomes the tool description."""
    ...

@mcp.resource("finance://some/path/{arg}")
def my_resource(arg: str) -> str:
    ...

@mcp.prompt
def my_prompt(topic: str) -> list[Message]:
    ...
```

Rules:
- **Full type hints are mandatory.** FastMCP derives the JSON schema from them. Untyped args crash at registration time or produce `Any` in the schema.
- **Every tool/resource/prompt must have a docstring.** The client (and the user) sees it.
- **Return Pydantic models, not dicts.** All DTOs live in `storage/models.py`. If a tool needs a new return shape, add the model there first.
- **Parameter descriptions** that aren't obvious go in `pydantic.Field(description=...)`.
- **Resource URIs** use the `finance://` scheme consistently. Path params use `{name}` syntax.

### 4.3 Decorated Functions Stay Callable

FastMCP 3.x preserves the underlying function. Use this for unit tests:

```python
# Direct call — no MCP transport involved
from finance_mcp.tools.query_tools import query_transactions
result = query_transactions(start_date=date(2025, 1, 1))
```

**Prefer direct calls for logic tests.** Use the in-memory `Client` only for tests that exercise the MCP layer itself (schema, URIs, prompt rendering).

### 4.4 In-Memory Client for MCP-Layer Tests

```python
import pytest
from fastmcp import Client
from finance_mcp.server import mcp

@pytest.mark.asyncio
async def test_tool_via_mcp():
    async with Client(mcp) as client:
        result = await client.call_tool("list_accounts", {})
        assert result.data == []
```

- Don't spawn subprocesses or sockets in tests.
- Use the `mcp_client` fixture from `conftest.py` (PRD §10.2).
- `pytest-asyncio` is configured with `asyncio_mode = "auto"` — don't add `@pytest.mark.asyncio` to every test unless needed.

### 4.5 Register Modules Via Import in server.py

Decorators only fire when their module is imported. The canonical pattern (PRD §5.1) imports all tool/resource/prompt submodules in `server.py`. When you add a new tool module, add its import there.

### 4.6 Use `fastmcp dev` for Iteration

Don't edit → restart Claude Desktop over and over. Run `make dev` — it hot-reloads on save and opens the Inspector UI where you can invoke tools and inspect schemas directly.

### 4.7 Don't Use FastMCP Features That Aren't in the PRD

Tempting but out of scope for v1: Apps (interactive UI), CodeMode, MultiAuth, OpenTelemetry, Prefab, proxying, server composition. Don't bolt these on. They're great — for v2.

### 4.8 Context Object

If you ever need request-scoped info (logging, progress, cancellation), inject a `fastmcp.Context` parameter:

```python
from fastmcp import Context

@mcp.tool
def slow_task(items: list[str], ctx: Context) -> None:
    """Progress reporting example."""
    for i, item in enumerate(items):
        ctx.info(f"Processing {item}")
        ctx.report_progress(i, len(items))
```

You probably won't need this in v1 — mention it here so you know it exists when it'd actually help.

---

## 5. Coding Standards

### 5.1 Python Style

- **Formatter:** `ruff format` — single source of truth.
- **Linter:** `ruff check` — must be clean before commit.
- **Type checker:** `mypy --strict` on `src/`. Tests typed but looser.
- **Line length:** 100 chars.
- **Imports:** stdlib / third-party / first-party, alphabetized. Ruff handles it.
- **Docstrings:** Google style. Public functions + classes require them; private helpers only if non-obvious.
- **f-strings** over `.format()` or `%`.
- **Pathlib** over `os.path`.
- **Datetimes:** tz-aware or explicitly naive with a comment. `date` for `txn_date`.

### 5.2 Typing

- Every function signature fully typed. No `Any` unless commented.
- Pydantic models cross every module boundary. No raw dicts.
- `from __future__ import annotations` at the top of every module.

### 5.3 Errors

- Never bare `except:` or `except Exception:` without re-raising or logging with context.
- Custom exceptions in `finance_mcp/errors.py` (e.g. `ParseError`, `DuplicateTransactionError`, `RuleConflictError`).
- Tool handlers return structured error objects (`OperationResult(success=False, ...)`) instead of raising up to the MCP layer when the error is user-facing.

### 5.4 Logging

- `logging.getLogger(__name__)` — no `print()` in library code.
- `INFO` for lifecycle events (import started/finished), `DEBUG` for per-row, `WARNING` for recoverable oddities, `ERROR` for failures.
- Scripts under `scripts/` may use `print` or `rich`.

---

## 6. Architecture Rules

### 6.1 Layering (Strictly Enforced)

```
server.py → tools/ → repository + engine + analytics → storage/db.py
                ↑
           pydantic models (shared)
```

- **`server.py`** wires FastMCP and imports modules. No business logic.
- **`tools/`** validate input, call service functions, shape output. Thin.
- **`repository.py`** is the only module allowed to run SQL.
- **`parsers/`** are pure: CSV in → `RawTransaction` list out. No DB.
- **`categorization/engine.py`** is pure: transaction + rules in → category_id out. No DB.
- **`analytics/`** reads via repository, returns Pydantic models. No direct SQL.

If SQL escapes `repository.py`, stop and refactor.

### 6.2 Database

- Schema changes: edit `schema.sql` + add a numbered migration under `storage/migrations/` (`001_init.sql`, `002_add_notes.sql`).
- Never hand-edit an existing migration — always add a new one.
- All queries parameterized. **No string interpolation into SQL, ever.**
- Transactions around every multi-statement write.
- `PRAGMA foreign_keys = ON` in connection setup.

### 6.3 MCP Contract Stability

- Tool/resource/prompt names and shapes in PRD §6 are **the contract**. Don't rename or re-shape without updating the PRD first and flagging to the user.
- Breaking contract changes require an explicit "I'm about to break the contract — confirm?" from you.

---

## 7. Testing Standards

### 7.1 Structure

- Mirror `src/` layout under `tests/`.
- Shared fixtures in `conftest.py`: temp DB, sample CSVs, `mcp_client`, seeded rules.

### 7.2 What to Test

- **Parsers:** ≥3 fixture CSVs each, including edge cases (empty row, refund, multi-line description, malformed date).
- **`normalize_merchant`:** ≥20 cases covering every prefix/VPA/refno pattern.
- **Categorization:** priority ordering, user-rule precedence, manual-override protection.
- **Repository:** round-trip every entity; unique-constraint violations raise cleanly.
- **Analytics:** small hand-built datasets with known outputs.
- **MCP tools:** invoke via `mcp_client.call_tool`. Also call the underlying function directly for logic assertions.
- **MCP resources:** invoke via `mcp_client.read_resource`.
- **MCP prompts:** invoke via `mcp_client.get_prompt`.
- **Integration:** generator → import → query via Client → assert counts.

### 7.3 Coverage Gates

Overall ≥80%, parsers ≥95%, categorization ≥90%, analytics ≥85%. A coverage drop blocks a phase.

### 7.4 Running Tests

```bash
make test                              # full suite with coverage
uv run pytest tests/test_parsers/ -v   # one directory
uv run pytest -k "hdfc"                # by keyword
uv run pytest --lf                     # last failed
uv run pytest tests/test_server/ -v    # MCP-layer tests only
```

---

## 8. Git & Commits

### 8.1 Branching

- `main` is the integration branch. Keep it green.
- Feature work: `phase-N/short-slug` (e.g. `phase-3/categorization-engine`).

### 8.2 Commit Messages

Format: `<phase>: <imperative summary>` (≤72 chars).

Examples:
- `phase-1: scaffold project structure and tooling`
- `phase-2: add HDFC parser with fixture tests`
- `phase-3: implement rule priority and user overrides`
- `phase-4: wire query_transactions tool via @mcp.tool`

Body (optional) explains *why*, not *what*.

### 8.3 When to Commit

- After each green test run on a logical unit of work.
- Never commit failing tests or commented-out code.
- Never commit generated DBs (`*.db`, `*.sqlite`) — add to `.gitignore`.
- `sample_data/` CSVs **are** committed.

---

## 9. Working With the User

### 9.1 Default Behavior

- Before each phase: summarize the plan in 3–6 bullets, ask for go-ahead.
- After each phase: show what works, run tests, show coverage, ask to proceed.
- Every session: run §3 checklist.

### 9.2 When to Ask

- Spec is ambiguous or missing a detail.
- You'd need a dependency not in PRD §11.1.
- You think a PRD requirement is wrong or should change.
- A phase reveals a design flaw from an earlier phase.
- A test fails for a reason that suggests a spec gap.
- You're tempted to use a FastMCP feature that isn't covered in §4 of this file.

### 9.3 When Not to Ask

- Standard Python idioms and internal refactors.
- Adding docstrings, type hints, or tests.
- Fixing your own lint/type errors.
- Naming internal helpers and variables.

### 9.4 Proposing Changes

If you want to deviate from the PRD:

1. State the current requirement.
2. State your proposed change.
3. Give 1–3 reasons.
4. State the tradeoff.
5. Wait for approval.

---

## 10. File & Directory Conventions

- **Never create files outside PRD §3.4** without asking.
- **Scratch work** goes in `/tmp` or a gitignored `scratch/` dir.
- **Generated artifacts** (DB, logs, coverage) in gitignored `.local/` or `build/`.
- **Secrets:** none should exist. If you think you need one, stop.

---

## 11. Running the Project Locally

```bash
# One-time setup
uv sync
uv run python scripts/generate_dummy_data.py --output-dir sample_data/ --months 6 --seed 42

# Development with hot reload + Inspector UI
make dev

# Run server over stdio (the mode Claude Desktop uses)
uv run finance-mcp

# One-shot demo bootstrap (Phase 7+)
make demo
```

Claude Desktop config goes in the README. The path is absolute — remind users to update it.

---

## 12. Anti-Patterns to Avoid

Things that have sunk similar projects:

1. **Importing from `mcp.server.fastmcp`.** That's v1. Use `from fastmcp import FastMCP`.
2. **Using `fastmcp.Server` or ad-hoc JSON-RPC.** Use the decorators.
3. **Skipping type hints on tool params.** FastMCP needs them for schema generation.
4. **Returning raw dicts from tools.** Return Pydantic models from `storage/models.py`.
5. **Bloating the schema upfront.** Start with tables in PRD §4.1. Add columns only when a concrete tool needs them.
6. **Building a "smart" categorizer first.** Ship the rule engine. ML/embeddings are out of scope.
7. **Parsing "all bank formats" upfront.** HDFC + ICICI is the v1 bar.
8. **Spreading SQL across modules.** Keep it in `repository.py`.
9. **Skipping the dummy data generator.** It's a first-class artifact.
10. **Over-abstracting.** Concrete first. Abstract when a second or third use case demands it.
11. **Silent exception swallowing.** Every `except` must log or re-raise with context.
12. **Tests that test the mock.** If the test passes when the code is deleted, it's a bad test.
13. **README written last.** Update it at the end of each phase.
14. **Wall-clock time in tests.** Use fixed dates in fixtures.
15. **Running the server via subprocess in tests.** Use the in-memory `Client`.

---

## 13. Common Commands Cheat Sheet

```bash
# Dev loop
make install             # uv sync
make format              # ruff format
make lint                # ruff check + mypy
make test                # pytest with coverage
make dev                 # fastmcp dev (hot reload + Inspector)
make inspect             # fastmcp inspect (dump schema/tool list)
make generate            # regenerate dummy CSVs
make demo                # one-shot bootstrap
make clean

# Ad-hoc
uv run python -c "from finance_mcp.storage.db import init_db; init_db()"
uv run finance-mcp                                        # run server over stdio
uv run pytest tests/test_parsers/test_hdfc.py -v
uv run pytest --cov=src/finance_mcp --cov-report=term-missing
```

---

## 14. Definition of "Done" for Any Unit of Work

- [ ] Code typed and docstring'd per standards.
- [ ] Tests exist and pass; module coverage target met.
- [ ] `ruff check`, `ruff format --check`, `mypy src/` clean.
- [ ] README / docs updated if user-visible.
- [ ] Commit message follows §8.2.
- [ ] User has seen the result and confirmed before moving on.

---

## 15. Escalation

If you're genuinely stuck (not just "this is hard"):

1. State the problem in one sentence.
2. List what you've tried.
3. List 2–3 possible paths with tradeoffs.
4. Ask the user to pick.

Do not thrash. Do not silently abandon a test. Do not rewrite working code to avoid a hard bug.

---

*End of CLAUDE.md. PRD.md is the spec; this file is the contract for how we work.*