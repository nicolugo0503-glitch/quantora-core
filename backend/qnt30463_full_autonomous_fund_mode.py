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
    return round(float(value), 4)


def build_full_autonomous_fund_package(
    capital_pools: Iterable[Dict],
    strategy_allocations: Iterable[Dict],
    execution_decisions: Iterable[Dict],
    autonomous_runs: Iterable[Dict],
) -> Dict:
    capital_pools = list(capital_pools or [])
    strategy_allocations = list(strategy_allocations or [])
    execution_decisions = list(execution_decisions or [])
    autonomous_runs = list(autonomous_runs or [])

    total_capital = sum(_as_float(x.get("capital_amount")) for x in capital_pools)
    active_allocations = [x for x in strategy_allocations if (x.get("status") or "").lower() in {"active", "deployed", "live"}]
    executed_decisions = [x for x in execution_decisions if (x.get("status") or "").lower() in {"executed", "completed", "applied"}]
    completed_runs = [x for x in autonomous_runs if (x.get("status") or "").lower() in {"completed", "closed", "executed"}]

    allocation_rows: List[Dict] = []
    total_score = sum(_as_float(x.get("score")) for x in strategy_allocations)
    for row in strategy_allocations:
        score = _as_float(row.get("score"))
        allocation = (score / total_score) if total_score else 0.0
        allocation_rows.append({
            "allocation_id": row.get("id"),
            "strategy_name": row.get("strategy_name") or "Strategy",
            "score": _round(score),
            "allocation_weight": _round(allocation),
            "status": row.get("status") or "draft",
            "created_at": row.get("created_at"),
        })

    pool_rows: List[Dict] = []
    for row in capital_pools:
        pool_rows.append({
            "pool_id": row.get("id"),
            "pool_name": row.get("pool_name") or "Capital Pool",
            "capital_amount": _round(_as_float(row.get("capital_amount"))),
            "status": row.get("status") or "active",
            "created_at": row.get("created_at"),
        })

    decision_rows: List[Dict] = []
    for row in execution_decisions:
        signal = _as_float(row.get("signal"))
        if signal > 0.7:
            action = "BUY"
        elif signal < -0.7:
            action = "SELL"
        else:
            action = "HOLD"
        decision_rows.append({
            "decision_id": row.get("id"),
            "strategy_name": row.get("strategy_name") or "Strategy",
            "signal": _round(signal),
            "action": action,
            "status": row.get("status") or "queued",
            "created_at": row.get("created_at"),
        })

    run_rows: List[Dict] = []
    for row in autonomous_runs:
        run_rows.append({
            "run_id": row.get("id"),
            "run_name": row.get("run_name") or "Autonomous Run",
            "status": row.get("status") or "draft",
            "decisions_count": int(_as_float(row.get("decisions_count"))),
            "created_at": row.get("created_at"),
        })

    fund_score = max(
        45,
        min(
            100,
            int(
                60
                + len(capital_pools) * 3
                + len(active_allocations) * 4
                + len(executed_decisions) * 2
                + len(completed_runs) * 4
            )
        ),
    )

    return {
        "summary": {
            "capital_pools": len(capital_pools),
            "total_capital": _round(total_capital),
            "strategy_allocations": len(strategy_allocations),
            "active_allocations": len(active_allocations),
            "executed_decisions": len(executed_decisions),
            "completed_runs": len(completed_runs),
            "fund_score": fund_score,
        },
        "capital_pools": pool_rows,
        "strategy_allocations": allocation_rows,
        "execution_decisions": decision_rows,
        "autonomous_runs": run_rows,
        "fund_health": {
            "capital_registry_ready": bool(capital_pools),
            "allocation_engine_ready": bool(strategy_allocations),
            "decision_engine_ready": bool(execution_decisions),
            "run_engine_ready": bool(autonomous_runs),
            "fund_score": fund_score,
        },
    }
