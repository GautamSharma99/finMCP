# MCP Interface

All signatures are the Python functions — FastMCP derives JSON schemas from them.

## Tools

### Import & browse

```python
import_statement(file_path: str, account_name: str, bank: str | None = None) -> ImportResult
list_accounts() -> list[Account]
query_transactions(
    start_date: date | None = None,
    end_date: date | None = None,
    category: str | None = None,
    account: str | None = None,
    merchant: str | None = None,
    min_amount: float | None = None,
    max_amount: float | None = None,
    limit: int = 100,
) -> list[Transaction]
```

### Aggregates

```python
get_spending_summary(
    start_date: date, end_date: date,
    group_by: Literal["category","merchant","month"] = "category",
) -> list[SummaryRow]

compare_periods(
    period_a_start: date, period_a_end: date,
    period_b_start: date, period_b_end: date,
    group_by: Literal["category","merchant","month"] = "category",
) -> list[ComparisonRow]

get_net_worth(as_of: date | None = None) -> NetWorth
detect_recurring(min_occurrences: int = 3, lookback_months: int = 6) -> list[RecurringTxn]
```

### Categorization

```python
categorize_transaction(transaction_id: int, category_name: str) -> OperationResult
bulk_categorize(
    category_name: str,
    merchant: str | None = None,
    uncategorized_only: bool = True,
) -> OperationResult

create_rule(
    pattern: str,
    category_name: str,
    match_type: Literal["contains","regex","exact"] = "contains",
    priority: int = 50,
) -> Rule
list_rules(user_only: bool = False) -> list[Rule]
delete_rule(rule_id: int) -> OperationResult
```

### Budgets & goals

```python
set_budget(
    category_name: str, amount: float,
    period: Literal["monthly","quarterly","yearly"] = "monthly",
    start_date: date | None = None,
) -> Budget
get_budget_status(month: str) -> list[BudgetStatus]    # month = "YYYY-MM"

set_goal(
    name: str, target_amount: float,
    deadline: date | None = None,
    linked_account: str | None = None,
) -> Goal
get_goal_progress(goal_name: str | None = None) -> list[GoalProgress]
```

## Resources

| URI | Returns |
| --- | --- |
| `finance://accounts` | JSON list of accounts + running balance |
| `finance://categories/tree` | JSON hierarchical category tree |
| `finance://budgets/current` | JSON budgets for the current month with utilisation |
| `finance://insights/monthly/{month}` | Markdown report for `YYYY-MM` |
| `finance://insights/summary/last-30-days` | Markdown rolling 30-day summary |

## Prompts

| Name | Args | Purpose |
| --- | --- | --- |
| `monthly_review` | `month: str` | Structured review of a month |
| `find_savings` | `target_amount: float \| None = None` | Where to cut to hit a target |
| `goal_check` | `goal_name: str \| None = None` | Progress + projected hit date |
