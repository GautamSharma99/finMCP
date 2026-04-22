"""Pure rule-matching engine.

Given a transaction's merchant key / narration and a list of rules,
returns the first matching rule (or None). No DB access, no I/O.
"""

from __future__ import annotations

import re
from collections.abc import Iterable

from finance_mcp.storage.models import Rule


def _rule_sort_key(rule: Rule) -> tuple[int, int, int]:
    # Lower priority number wins; within the same priority user-defined
    # rules beat defaults; within that, lower id (older) wins for stability.
    return (rule.priority, 0 if rule.is_user_defined else 1, rule.id or 0)


def _match(pattern: str, match_type: str, haystack: str) -> bool:
    if match_type == "contains":
        return pattern.upper() in haystack.upper()
    if match_type == "exact":
        return pattern.upper() == haystack.upper()
    if match_type == "regex":
        try:
            return re.search(pattern, haystack, re.IGNORECASE) is not None
        except re.error:
            return False
    return False


def categorize(
    clean_merchant: str | None,
    raw_description: str,
    rules: Iterable[Rule],
) -> Rule | None:
    """Return the first rule that matches, respecting priority.

    Tries `clean_merchant` first and falls back to `raw_description`.
    Manual overrides are handled by the caller, not here.
    """
    ordered = sorted(rules, key=_rule_sort_key)
    merchant = (clean_merchant or "").strip()
    desc = raw_description or ""

    for rule in ordered:
        if merchant and _match(rule.pattern, rule.match_type, merchant):
            return rule
        if _match(rule.pattern, rule.match_type, desc):
            return rule
    return None


__all__ = ["categorize"]
