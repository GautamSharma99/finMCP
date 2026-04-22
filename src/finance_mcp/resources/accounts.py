"""`finance://accounts` resource."""

from __future__ import annotations

import json

from finance_mcp.server import get_repo, mcp


@mcp.resource("finance://accounts")
def accounts_resource() -> str:
    """JSON list of every account with running transaction count and net balance."""
    with get_repo() as repo:
        accounts = repo.list_accounts()
        payload = []
        for a in accounts:
            assert a.id is not None
            txns = repo.list_transactions(account_id=a.id, limit=100000)
            total = sum(float(t.amount) for t in txns)
            payload.append(
                {
                    "id": a.id,
                    "name": a.name,
                    "type": a.type,
                    "bank": a.bank,
                    "currency": a.currency,
                    "txn_count": len(txns),
                    "net_balance": round(total, 2),
                }
            )
    return json.dumps({"accounts": payload}, indent=2, default=str)
