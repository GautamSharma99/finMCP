# Architecture

## Layering

```
server.py → tools / resources / prompts
                    ↓
          repository + engine + analytics
                    ↓
                storage/db.py (SQLite)
```

- **`server.py`** creates the `FastMCP` instance and imports submodules so their decorators fire.
- **`tools/`** modules are thin: validate, call service functions, shape output. Never import SQLite.
- **`storage/repository.py`** is the only module allowed to execute SQL. Everything above it exchanges Pydantic models (`storage/models.py`).
- **`parsers/`** are pure: CSV path in, `RawTransaction` list out. They don't read or write the DB.
- **`categorization/engine.py`** is pure: `(clean_merchant, raw_description, rules) → Rule | None`.
- **`analytics/`** reads through `Repository`, produces Pydantic DTOs.

## Data flow on import

1. `import_statement` tool opens a repository.
2. Picks a parser from the bank hint / filename.
3. Parser returns a list of `RawTransaction`s.
4. `Repository.bulk_insert_transactions` fires the categorization engine on each row and inserts with `category_source='rule'` when a rule matches.
5. Duplicates (by 16-hex dedup_hash) are silently skipped.

## Money representation

- On **wire** (tool return schemas): `float`. Pydantic's `Decimal` JSON schema uses a negative lookahead that the jsonschema-rs validator in the FastMCP client path can't parse.
- In **storage**: SQLite TEXT columns that round-trip through `Decimal`.
- In **analytics**: computations use `Decimal` to avoid accumulated float error; outputs are converted to `float` at the boundary.

## DB conventions

- `PRAGMA foreign_keys = ON` for every connection.
- WAL journal mode.
- Schema changes: numbered SQL files under `storage/migrations/` — never edited, only appended.
- `schema_migrations` table records applied versions.
- Default categories + rules seeded idempotently on first `init_db`.

## Testing

- Repository / analytics: direct pytest with an ephemeral temp DB fixture.
- MCP-layer tests: in-memory `fastmcp.Client` fixture (no sockets, no subprocesses).
- Parsers: CSV fixture files under `tests/test_parsers/fixtures/`.
- Integration: runs the dummy-data generator, then parses + imports it.
