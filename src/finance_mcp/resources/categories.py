"""`finance://categories/tree` resource."""

from __future__ import annotations

import json

from finance_mcp.server import get_repo, mcp


@mcp.resource("finance://categories/tree")
def categories_tree() -> str:
    """Hierarchical category tree as JSON."""
    with get_repo() as repo:
        cats = repo.list_categories()

    by_id = {c.id: c for c in cats if c.id is not None}
    children: dict[int | None, list[int]] = {}
    for c in cats:
        if c.id is None:
            continue
        children.setdefault(c.parent_id, []).append(c.id)

    def build(parent_id: int | None) -> list[dict[str, object]]:
        nodes: list[dict[str, object]] = []
        for cid in children.get(parent_id, []):
            c = by_id[cid]
            nodes.append(
                {
                    "id": c.id,
                    "name": c.name,
                    "is_income": c.is_income,
                    "children": build(cid),
                }
            )
        return nodes

    return json.dumps({"tree": build(None)}, indent=2)
