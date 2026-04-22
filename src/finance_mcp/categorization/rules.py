"""Rules service layer.

High-level helpers that sit atop the repository and turn category
*names* into category *ids* for user-facing tools. This module does not
run SQL directly — all persistence goes through `Repository`.
"""

from __future__ import annotations

import logging

from finance_mcp.categorization.default_rules import DEFAULT_RULES
from finance_mcp.errors import CategoryNotFoundError
from finance_mcp.storage.models import Rule
from finance_mcp.storage.repository import Repository

logger = logging.getLogger(__name__)


def seed_default_rules(repo: Repository) -> int:
    """Idempotently seed the built-in rules. Returns count newly inserted.

    Safe to call on every startup: if any rules already exist it no-ops.
    """
    if repo.count_rules() > 0:
        return 0

    inserted = 0
    for pattern, match_type, category_name, priority in DEFAULT_RULES:
        cat = repo.find_category_by_name(category_name)
        if cat is None or cat.id is None:
            logger.warning("default rule skipped: no category %r", category_name)
            continue
        repo.create_rule(
            pattern=pattern,
            category_id=cat.id,
            match_type=match_type,
            priority=priority,
            is_user_defined=False,
        )
        inserted += 1
    logger.info("seeded %d default categorization rules", inserted)
    return inserted


def create_user_rule(
    repo: Repository,
    pattern: str,
    category_name: str,
    match_type: str = "contains",
    priority: int = 50,
) -> Rule:
    """Create a user-defined rule; resolves category by name."""
    cat = repo.find_category_by_name(category_name)
    if cat is None or cat.id is None:
        raise CategoryNotFoundError(category_name)
    return repo.create_rule(
        pattern=pattern,
        category_id=cat.id,
        match_type=match_type,
        priority=priority,
        is_user_defined=True,
    )


__all__ = ["create_user_rule", "seed_default_rules"]
