# finance-analyst-mcp

A local-first **MCP server** that turns your bank statements into a conversation. Ask Claude where your money goes, spot subscriptions, and track goals — all from your machine, with no bank API keys involved.

Built with [FastMCP 3.x](https://github.com/jlowin/fastmcp) + SQLite + pandas + pydantic v2.

> ⚠️ **Dummy data only.** This repo ships with a synthetic data generator that produces realistic Indian-bank CSVs (HDFC Savings, ICICI Credit Card). No real credentials, APIs, or PII are involved.

---

## Why

Plain data questions about your own spending — *"How much did I spend on food delivery last month?"*, *"Which subscriptions renew on the 5th?"*, *"Am I on track for my emergency fund?"* — are awkward in a spreadsheet and borderline impossible without one. This project plugs into any MCP-compatible client (Claude Desktop, Cursor, the `fastmcp dev` Inspector) and answers them in natural language.

---

## Quickstart

```bash
git clone https://github.com/your/finance-analyst-mcp.git
cd finance-analyst-mcp
uv sync --extra dev
uv run python scripts/setup_demo.py      # generates + imports 6 months of data
```

That prints a Claude Desktop config block. Paste it into:

- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%AppData%\Claude\claude_desktop_config.json`

Restart Claude Desktop and ask something like *"what are my top 5 merchants this year?"*.

For iteration without Claude Desktop, run the Inspector:

```bash
make dev    # fastmcp dev src/finance_mcp/server.py
```

---

## Example conversations

> **You:** What did I spend on food delivery in January 2025?
>
> *Claude uses `get_spending_summary` → returns ₹6,230 across 14 transactions.*

> **You:** Which subscriptions do I have?
>
> *Claude uses `detect_recurring` → Netflix ₹649/mo, Spotify ₹119/mo, ACT Fibernet ₹1,049/mo.*

> **You:** Categorize all my Swiggy charges as Groceries.
>
> *Claude uses `create_rule(pattern="SWIGGY", category="Groceries", priority=40)` then `bulk_categorize`.*

> **You:** Set a ₹10L emergency fund goal.
>
> *Claude uses `set_goal(name="Emergency Fund", target_amount=1000000)`.*

---

## Architecture

```
┌─────────────────────┐
│   MCP Client        │   Claude Desktop, Cursor, Inspector
└──────────┬──────────┘
           │  stdio / JSON-RPC
┌──────────▼──────────┐
│  FastMCP Server     │   src/finance_mcp/server.py
│  @mcp.tool          │   - 16 tools
│  @mcp.resource      │   - 5 resources
│  @mcp.prompt        │   - 3 prompts
└──────────┬──────────┘
           │
    ┌──────┴──────┬─────────────┬──────────────┐
    ▼             ▼             ▼              ▼
┌────────┐  ┌──────────┐  ┌──────────┐  ┌───────────┐
│Parsers │  │Repository│  │Categoriz.│  │Analytics  │
│ hdfc   │  │(SQLite)  │  │  engine  │  │  engine   │
│ icici  │  └──────────┘  └──────────┘  └───────────┘
└────────┘
```

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for details.

---

## Tools, resources, prompts

| Kind | Name | Purpose |
| --- | --- | --- |
| tool | `import_statement` | Parse a bank CSV into the DB |
| tool | `list_accounts` | Enumerate accounts |
| tool | `query_transactions` | Filter by date / category / merchant / amount |
| tool | `get_spending_summary` | Aggregate by category / merchant / month |
| tool | `compare_periods` | Side-by-side totals for two windows |
| tool | `categorize_transaction` | Manually relabel one transaction |
| tool | `bulk_categorize` | Reassign many transactions at once |
| tool | `create_rule` | User-defined categorization rule |
| tool | `list_rules` | Enumerate rules |
| tool | `delete_rule` | Remove a rule |
| tool | `set_budget` | Monthly / quarterly / yearly spend cap |
| tool | `get_budget_status` | Utilisation for a YYYY-MM |
| tool | `set_goal` | Savings goal |
| tool | `get_goal_progress` | Progress + projections |
| tool | `detect_recurring` | Subscription detector |
| tool | `get_net_worth` | Assets - liabilities snapshot |
| resource | `finance://accounts` | JSON accounts + balances |
| resource | `finance://categories/tree` | Hierarchical category tree |
| resource | `finance://budgets/current` | Current-month budgets + utilisation |
| resource | `finance://insights/monthly/{month}` | Markdown monthly review |
| resource | `finance://insights/summary/last-30-days` | Markdown rolling-30-day summary |
| prompt | `monthly_review` | Structured review walkthrough |
| prompt | `find_savings` | Where to cut to hit a target |
| prompt | `goal_check` | Progress + projected hit date |

Full signatures: [`docs/MCP_INTERFACE.md`](docs/MCP_INTERFACE.md).

---

## Project structure

```
finance-analyst-mcp/
├── src/finance_mcp/
│   ├── server.py            # FastMCP app + entry point
│   ├── parsers/             # bank CSV parsers + normalize_merchant
│   ├── storage/             # SQLite, schema, migrations, repository
│   ├── categorization/      # rule engine + default rules
│   ├── analytics/           # aggregations, recurring, insights
│   ├── tools/               # @mcp.tool modules
│   ├── resources/           # @mcp.resource modules
│   └── prompts/             # @mcp.prompt modules
├── scripts/
│   ├── generate_dummy_data.py
│   └── setup_demo.py
├── sample_data/             # generated CSVs
└── tests/
```

---

## Testing

```bash
make test                        # full suite with coverage
uv run pytest tests/test_parsers -v
uv run pytest -k "recurring"
```

CI: [`.github/workflows/ci.yml`](.github/workflows/ci.yml) runs ruff, mypy, and pytest on every push.

---

## Roadmap (v2 teasers)

- Plaid / Account Aggregator integration (real bank connections)
- Apps-style interactive UI via FastMCP Apps
- Forecasting (next-month spend by category)
- Multi-currency support
- Mobile PWA client

---

## License

MIT.
