# Demo Transcript

A walkthrough of a real Claude Desktop session after `make demo`.

---

### Getting started

> **You:** What accounts do I have?
>
> **Claude:** I see two: HDFC Savings - Demo (a savings account) and ICICI Credit Card - Demo. They together hold 205 transactions across Jan-Jun 2025. Want a summary by category?

### Spending questions

> **You:** How much did I spend on food delivery in February?
>
> **Claude:** *(calls `get_spending_summary(start_date="2025-02-01", end_date="2025-02-28", group_by="category")`)*
>
> ₹6,482 on food delivery in February across 13 transactions. Swiggy was 58% of it.

> **You:** Compare January to February spending.
>
> **Claude:** *(calls `compare_periods`)* Your biggest shifts:
> - Food Delivery: up ₹1,800
> - Shopping > General: down ₹4,200 (no Amazon splurge)
> - Transport: flat

### Subscription detection

> **You:** What subscriptions do I have?
>
> **Claude:** *(calls `detect_recurring(min_occurrences=3, lookback_months=6)`)*
> - NETFLIX: ₹649 every ~30d (6x)
> - SPOTIFY: ₹119 every ~30d (6x)
> - ACT FIBERNET: ₹1,049 every ~30d (6x)

### Rules + bulk categorization

> **You:** Categorize all Blinkit charges as Groceries.
>
> **Claude:** *(calls `create_rule(pattern="BLINKIT", category_name="Groceries", priority=40)` then `bulk_categorize(category_name="Groceries", merchant="BLINKIT", uncategorized_only=False)`)*
> Rule created. 14 transactions updated to Groceries.

### Goals

> **You:** Set a ₹10 lakh emergency fund goal.
>
> **Claude:** *(calls `set_goal(name="Emergency Fund", target_amount=1000000)`)* Done. Want me to track against your HDFC Savings balance?

### The `monthly_review` prompt

Invoking the `monthly_review` prompt for `2025-03` produces a full markdown report (top categories, budget status, notable transactions, suggestions) by reading `finance://insights/monthly/2025-03` under the hood.
