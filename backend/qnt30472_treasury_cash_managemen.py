
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


def build_treasury_package(
    treasury_accounts: Iterable[Dict],
    cash_movements: Iterable[Dict],
    yield_strategies: Iterable[Dict],
    liquidity_snapshots: Iterable[Dict],
) -> Dict:
    treasury_accounts = list(treasury_accounts or [])
    cash_movements = list(cash_movements or [])
    yield_strategies = list(yield_strategies or [])
    liquidity_snapshots = list(liquidity_snapshots or [])

    active_accounts = [x for x in treasury_accounts if (x.get("status") or "").lower() in {"active", "live", "funded"}]
    completed_movements = [x for x in cash_movements if (x.get("status") or "").lower() in {"completed", "settled", "posted"}]
    live_yield = [x for x in yield_strategies if (x.get("status") or "").lower() in {"active", "live", "deployed"}]
    healthy_liquidity = [x for x in liquidity_snapshots if (x.get("status") or "").lower() in {"healthy", "ok", "green"}]

    total_cash = sum(_as_float(x.get("balance")) for x in treasury_accounts)
    total_movement = sum(_as_float(x.get("amount")) for x in cash_movements)
    avg_yield = round(
        sum(_as_float(x.get("apy_percent")) for x in yield_strategies) / len(yield_strategies),
        2
    ) if yield_strategies else 0.0

    account_rows: List[Dict] = []
    for row in treasury_accounts:
        account_rows.append({
            "account_id": row.get("id"),
            "account_name": row.get("account_name") or "Treasury Account",
            "account_type": row.get("account_type") or "operating",
            "balance": _round(_as_float(row.get("balance"))),
            "status": row.get("status") or "draft",
            "created_at": row.get("created_at"),
        })

    movement_rows: List[Dict] = []
    for row in cash_movements:
        movement_rows.append({
            "movement_id": row.get("id"),
            "movement_name": row.get("movement_name") or "Cash Movement",
            "direction": row.get("direction") or "inflow",
            "amount": _round(_as_float(row.get("amount"))),
            "status": row.get("status") or "pending",
            "created_at": row.get("created_at"),
        })

    strategy_rows: List[Dict] = []
    for row in yield_strategies:
        strategy_rows.append({
            "strategy_id": row.get("id"),
            "strategy_name": row.get("strategy_name") or "Yield Strategy",
            "vehicle_type": row.get("vehicle_type") or "t_bill",
            "apy_percent": _round(_as_float(row.get("apy_percent"))),
            "status": row.get("status") or "draft",
            "created_at": row.get("created_at"),
        })

    snapshot_rows: List[Dict] = []
    for row in liquidity_snapshots:
        snapshot_rows.append({
            "snapshot_id": row.get("id"),
            "snapshot_name": row.get("snapshot_name") or "Liquidity Snapshot",
            "available_cash": _round(_as_float(row.get("available_cash"))),
            "reserved_cash": _round(_as_float(row.get("reserved_cash"))),
            "status": row.get("status") or "unknown",
            "created_at": row.get("created_at"),
        })

    treasury_score = max(
        45,
        min(
            100,
            int(
                60
                + len(active_accounts) * 3
                + len(completed_movements) * 2
                + len(live_yield) * 3
                + len(healthy_liquidity) * 2
                + (5 if avg_yield >= 4 else 0)
            )
        ),
    )

    return {
        "summary": {
            "accounts_total": len(treasury_accounts),
            "accounts_active": len(active_accounts),
            "cash_total": _round(total_cash),
            "movements_total": len(cash_movements),
            "movement_volume_total": _round(total_movement),
            "yield_strategies_total": len(yield_strategies),
            "average_apy_percent": avg_yield,
            "liquidity_snapshots_total": len(liquidity_snapshots),
            "treasury_score": treasury_score,
        },
        "treasury_accounts": account_rows,
        "cash_movements": movement_rows,
        "yield_strategies": strategy_rows,
        "liquidity_snapshots": snapshot_rows,
        "treasury_health": {
            "account_registry_ready": bool(treasury_accounts),
            "movement_registry_ready": bool(cash_movements),
            "yield_registry_ready": bool(yield_strategies),
            "liquidity_registry_ready": bool(liquidity_snapshots),
            "treasury_score": treasury_score,
        },
    }
