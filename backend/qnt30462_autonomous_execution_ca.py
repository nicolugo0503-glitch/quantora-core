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


def build_autonomous_v2_package(
    allocation_models: Iterable[Dict],
    execution_plans: Iterable[Dict],
    signals: Iterable[Dict],
    autonomy_cycles: Iterable[Dict],
) -> Dict:
    allocation_models = list(allocation_models or [])
    execution_plans = list(execution_plans or [])
    signals = list(signals or [])
    autonomy_cycles = list(autonomy_cycles or [])

    active_models = [x for x in allocation_models if (x.get("status") or "").lower() in {"active", "ready", "live"}]
    approved_plans = [x for x in execution_plans if (x.get("status") or "").lower() in {"approved", "ready", "executing"}]
    buy_signals = [x for x in signals if _as_float(x.get("signal_strength")) > 0.7]
    sell_signals = [x for x in signals if _as_float(x.get("signal_strength")) < -0.7]
    completed_cycles = [x for x in autonomy_cycles if (x.get("status") or "").lower() in {"completed", "closed", "executed"}]

    model_rows: List[Dict] = []
    for row in allocation_models:
        model_rows.append({
            "model_id": row.get("id"),
            "model_name": row.get("model_name") or "Allocation Model",
            "status": row.get("status") or "draft",
            "expected_turnover": _round(_as_float(row.get("expected_turnover"))),
            "risk_budget": _round(_as_float(row.get("risk_budget"))),
            "created_at": row.get("created_at"),
        })

    plan_rows: List[Dict] = []
    for row in execution_plans:
        plan_rows.append({
            "plan_id": row.get("id"),
            "plan_name": row.get("plan_name") or "Execution Plan",
            "strategy_name": row.get("strategy_name") or "Strategy",
            "status": row.get("status") or "draft",
            "allocation_weight": _round(_as_float(row.get("allocation_weight"))),
            "created_at": row.get("created_at"),
        })

    signal_rows: List[Dict] = []
    for row in signals:
        signal_strength = _as_float(row.get("signal_strength"))
        if signal_strength > 0.7:
            action = "BUY"
        elif signal_strength < -0.7:
            action = "SELL"
        else:
            action = "HOLD"
        signal_rows.append({
            "signal_id": row.get("id"),
            "signal_name": row.get("signal_name") or "Signal",
            "signal_strength": _round(signal_strength),
            "action": action,
            "status": row.get("status") or "live",
            "created_at": row.get("created_at"),
        })

    cycle_rows: List[Dict] = []
    for row in autonomy_cycles:
        cycle_rows.append({
            "cycle_id": row.get("id"),
            "cycle_name": row.get("cycle_name") or "Autonomy Cycle",
            "status": row.get("status") or "draft",
            "actions_executed": int(_as_float(row.get("actions_executed"))),
            "created_at": row.get("created_at"),
        })

    engine_score = max(
        45,
        min(
            100,
            int(
                58
                + len(active_models) * 4
                + len(approved_plans) * 3
                + len(completed_cycles) * 3
                + len(buy_signals)
                + len(sell_signals)
            )
        ),
    )

    return {
        "summary": {
            "models_total": len(allocation_models),
            "models_active": len(active_models),
            "plans_total": len(execution_plans),
            "plans_approved": len(approved_plans),
            "buy_signals": len(buy_signals),
            "sell_signals": len(sell_signals),
            "cycles_completed": len(completed_cycles),
            "engine_score": engine_score,
        },
        "allocation_models": model_rows,
        "execution_plans": plan_rows,
        "signals": signal_rows,
        "autonomy_cycles": cycle_rows,
        "engine_health": {
            "model_registry_ready": bool(allocation_models),
            "plan_registry_ready": bool(execution_plans),
            "signal_engine_ready": bool(signals),
            "cycle_engine_ready": bool(autonomy_cycles),
            "engine_score": engine_score,
        },
    }
