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


def build_autonomous_capital_package(
    strategies: Iterable[Dict],
    pools: Iterable[Dict],
    plans: Iterable[Dict],
    executions: Iterable[Dict],
) -> Dict:
    strategies = list(strategies or [])
    pools = list(pools or [])
    plans = list(plans or [])
    executions = list(executions or [])

    total_capital = sum(_as_float(p.get("capital_balance")) for p in pools)
    approved_plans = [p for p in plans if (p.get("status") or "").lower() in {"approved", "ready", "executing"}]
    draft_plans = [p for p in plans if (p.get("status") or "").lower() in {"draft", "proposed", "pending"}]
    executed = [e for e in executions if (e.get("status") or "").lower() in {"sent", "filled", "completed", "applied"}]

    ranked: List[Dict] = []
    for row in strategies:
        score = _as_float(row.get("score") or row.get("strategy_score") or row.get("rank_score"))
        current_alloc = _as_float(row.get("allocated_capital") or row.get("current_allocation"))
        target_weight = max(0.0, min(1.0, score / 100.0))
        target_capital = total_capital * target_weight if total_capital > 0 else current_alloc
        delta = target_capital - current_alloc
        ranked.append({
            "strategy_id": row.get("strategy_id") or row.get("id"),
            "strategy_name": row.get("strategy_name") or row.get("name") or "strategy",
            "score": _round(score),
            "current_allocation": _round(current_alloc),
            "target_capital": _round(target_capital),
            "delta_capital": _round(delta),
            "direction": "increase" if delta > 0 else "decrease" if delta < 0 else "hold",
        })

    ranked.sort(key=lambda x: x["score"], reverse=True)

    execution_health = {
        "total_capital_base": _round(total_capital),
        "strategy_inputs_ready": bool(strategies),
        "plan_queue_ready": True,
        "approved_plan_count": len(approved_plans),
        "executed_actions": len(executed),
        "autonomy_score": max(45, min(100, int(50 + len(plans) * 4 + len(executed) * 5 + len(strategies) * 2))),
    }

    return {
        "summary": {
            "tracked_strategies": len(strategies),
            "capital_base": _round(total_capital),
            "draft_plans": len(draft_plans),
            "approved_plans": len(approved_plans),
            "executed_actions": len(executed),
            "autonomy_score": execution_health["autonomy_score"],
        },
        "recommended_allocations": ranked,
        "plans": list(plans),
        "executions": list(executions),
        "execution_health": execution_health,
    }
