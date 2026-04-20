from __future__ import annotations

from typing import Dict, Iterable, List


def _as_float(value, default: float = 0.0) -> float:
    try:
        if value in (None, ""):
            return default
        return float(value)
    except Exception:
        return default


def _round(value: float) -> float:
    return round(float(value), 2)


def _pool_kind_label(kind: str) -> str:
    kind = (kind or "operating").strip().lower()
    mapping = {
        "operating": "Operating",
        "investor": "Investor",
        "strategy": "Strategy",
        "reserve": "Reserve",
    }
    return mapping.get(kind, kind.title())


def build_real_fund_mode_package(
    pools: Iterable[Dict],
    investors: Iterable[Dict],
    flows: Iterable[Dict],
    allocations: Iterable[Dict],
    positions: Iterable[Dict],
) -> Dict:
    active_pools: List[Dict] = []
    total_pool_capital = 0.0
    total_pool_allocated = 0.0
    total_pool_reserve = 0.0
    for row in pools or []:
        status = (row.get("status") or "active").strip().lower()
        if status not in {"active", "approved", "open"}:
            continue
        capital = _as_float(row.get("capital_balance", row.get("balance")))
        allocated = _as_float(row.get("allocated_capital"))
        reserve = _as_float(row.get("reserve_capital"))
        available = capital - allocated - reserve
        total_pool_capital += capital
        total_pool_allocated += allocated
        total_pool_reserve += reserve
        active_pools.append(
            {
                "pool_id": row.get("id") or row.get("pool_id"),
                "name": row.get("name") or "Unnamed Pool",
                "pool_type": row.get("pool_type") or row.get("kind") or "operating",
                "pool_type_label": _pool_kind_label(row.get("pool_type") or row.get("kind")),
                "currency": row.get("currency") or "USD",
                "status": status,
                "capital_balance": _round(capital),
                "allocated_capital": _round(allocated),
                "reserve_capital": _round(reserve),
                "available_capital": _round(available),
                "strategy_scope": row.get("strategy_scope") or "multi-strategy",
                "created_at": row.get("created_at"),
            }
        )

    active_investors: List[Dict] = []
    investor_capital_total = 0.0
    for row in investors or []:
        status = (row.get("status") or "pending").strip().lower()
        commitment = _as_float(row.get("committed_capital"))
        distributed_pnl = _as_float(row.get("distributed_pnl"))
        current_equity = commitment + distributed_pnl
        if status in {"active", "funded"}:
            investor_capital_total += commitment
        active_investors.append(
            {
                "investor_id": row.get("id") or row.get("investor_id"),
                "investor_name": row.get("investor_name") or row.get("name") or "Unnamed Investor",
                "status": status,
                "currency": row.get("currency") or "USD",
                "committed_capital": _round(commitment),
                "distributed_pnl": _round(distributed_pnl),
                "current_equity": _round(current_equity),
                "ownership_percent": 0.0,
                "created_at": row.get("created_at"),
                "investor_type": row.get("investor_type") or "lp",
            }
        )

    nav_base = max(total_pool_capital, investor_capital_total, 0.0)
    if nav_base <= 0:
        nav_base = total_pool_capital or investor_capital_total or 1.0
    for row in active_investors:
        row["ownership_percent"] = round((_as_float(row.get("committed_capital")) / nav_base) * 100.0, 2) if nav_base > 0 else 0.0

    flow_rows: List[Dict] = []
    inflows = 0.0
    outflows = 0.0
    for row in flows or []:
        amount = abs(_as_float(row.get("amount")))
        flow_type = (row.get("flow_type") or row.get("type") or "deposit").strip().lower()
        signed_amount = amount if flow_type in {"deposit", "subscription", "capital_call", "inflow"} else -amount
        if signed_amount >= 0:
            inflows += signed_amount
        else:
            outflows += abs(signed_amount)
        flow_rows.append(
            {
                "flow_id": row.get("id") or row.get("flow_id"),
                "flow_type": flow_type,
                "investor_id": row.get("investor_id"),
                "pool_id": row.get("pool_id") or row.get("account_id"),
                "amount": _round(abs(signed_amount)),
                "direction": "in" if signed_amount >= 0 else "out",
                "note": row.get("note") or "",
                "created_at": row.get("created_at"),
            }
        )
    flow_rows.sort(key=lambda x: x.get("created_at") or "", reverse=True)

    strategy_allocations = {}
    for row in allocations or []:
        if (row.get("status") or "active") not in {"active", "approved"}:
            continue
        key = (row.get("strategy_key") or "unassigned").strip() or "unassigned"
        strategy_allocations.setdefault(key, 0.0)
        strategy_allocations[key] += _as_float(row.get("allocated_capital"))
    strategy_rows = [
        {"strategy_key": key, "allocated_capital": _round(value)}
        for key, value in sorted(strategy_allocations.items(), key=lambda kv: kv[1], reverse=True)
    ]

    unrealized_pnl = 0.0
    realized_pnl = 0.0
    for row in positions or []:
        realized_pnl += _as_float(row.get("realized_pnl"))
        unrealized_pnl += _as_float(row.get("unrealized_pnl"))
    fund_nav = total_pool_capital + realized_pnl + unrealized_pnl

    summary = {
        "module": "QNT30443",
        "fund_nav": _round(fund_nav),
        "pool_count": len(active_pools),
        "investor_count": len(active_investors),
        "active_investor_count": sum(1 for x in active_investors if x.get("status") in {"active", "funded"}),
        "capital_inflows": _round(inflows),
        "capital_outflows": _round(outflows),
        "net_flow": _round(inflows - outflows),
        "total_pool_capital": _round(total_pool_capital),
        "allocated_capital": _round(total_pool_allocated),
        "reserve_capital": _round(total_pool_reserve),
        "unallocated_capital": _round(total_pool_capital - total_pool_allocated - total_pool_reserve),
        "realized_pnl": _round(realized_pnl),
        "unrealized_pnl": _round(unrealized_pnl),
        "top_strategy": strategy_rows[0]["strategy_key"] if strategy_rows else None,
        "top_strategy_allocated_capital": strategy_rows[0]["allocated_capital"] if strategy_rows else 0.0,
    }
    return {
        "summary": summary,
        "pools": active_pools,
        "investors": active_investors,
        "capital_flows": flow_rows,
        "strategy_allocations": strategy_rows,
    }
