
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


def build_rebalancing_package(
    rebalance_rows: Iterable[Dict],
    allocation_rows: Iterable[Dict],
    trigger_rows: Iterable[Dict],
    adjustment_rows: Iterable[Dict],
) -> Dict:
    rebalance_rows = list(rebalance_rows or [])
    allocation_rows = list(allocation_rows or [])
    trigger_rows = list(trigger_rows or [])
    adjustment_rows = list(adjustment_rows or [])

    active_rebalances = [x for x in rebalance_rows if (x.get("status") or "").lower() in {"active", "running", "approved"}]
    active_allocations = [x for x in allocation_rows if (x.get("status") or "").lower() in {"active", "target", "live"}]
    fired_triggers = [x for x in trigger_rows if (x.get("status") or "").lower() in {"fired", "triggered", "breach"}]
    applied_adjustments = [x for x in adjustment_rows if (x.get("status") or "").lower() in {"applied", "executed", "completed"}]

    target_capital_total = sum(_as_float(x.get("target_capital")) for x in allocation_rows)
    adjusted_capital_total = sum(_as_float(x.get("adjusted_capital")) for x in adjustment_rows)

    rebalance_view: List[Dict] = []
    for row in rebalance_rows:
        rebalance_view.append({
            "rebalance_id": row.get("id"),
            "rebalance_name": row.get("rebalance_name") or "Rebalance Cycle",
            "rebalance_mode": row.get("rebalance_mode") or "risk_budget",
            "status": row.get("status") or "draft",
            "created_at": row.get("created_at"),
        })

    allocation_view: List[Dict] = []
    for row in allocation_rows:
        allocation_view.append({
            "allocation_id": row.get("id"),
            "strategy_name": row.get("strategy_name") or "Strategy",
            "target_capital": _round(_as_float(row.get("target_capital"))),
            "weight_percent": _round(_as_float(row.get("weight_percent"))),
            "status": row.get("status") or "draft",
            "created_at": row.get("created_at"),
        })

    trigger_view: List[Dict] = []
    for row in trigger_rows:
        trigger_view.append({
            "trigger_id": row.get("id"),
            "trigger_name": row.get("trigger_name") or "Drift Trigger",
            "trigger_value": _round(_as_float(row.get("trigger_value"))),
            "threshold_value": _round(_as_float(row.get("threshold_value"))),
            "status": row.get("status") or "draft",
            "created_at": row.get("created_at"),
        })

    adjustment_view: List[Dict] = []
    for row in adjustment_rows:
        adjustment_view.append({
            "adjustment_id": row.get("id"),
            "strategy_name": row.get("strategy_name") or "Strategy",
            "adjusted_capital": _round(_as_float(row.get("adjusted_capital"))),
            "adjustment_reason": row.get("adjustment_reason") or "rebalance",
            "status": row.get("status") or "draft",
            "created_at": row.get("created_at"),
        })

    rebalance_score = max(
        45,
        min(
            100,
            int(
                66
                + len(active_rebalances) * 3
                + len(active_allocations) * 2
                + len(fired_triggers) * 2
                + len(applied_adjustments) * 3
            )
        ),
    )

    rebalance_state = "IDLE"
    if active_allocations or fired_triggers:
        rebalance_state = "MONITORING"
    if active_rebalances and applied_adjustments:
        rebalance_state = "REBALANCING"

    return {
        "summary": {
            "rebalances_total": len(rebalance_rows),
            "rebalances_active": len(active_rebalances),
            "allocations_total": len(allocation_rows),
            "allocations_active": len(active_allocations),
            "triggers_total": len(trigger_rows),
            "triggers_fired": len(fired_triggers),
            "adjustments_total": len(adjustment_rows),
            "adjustments_applied": len(applied_adjustments),
            "target_capital_total": _round(target_capital_total),
            "adjusted_capital_total": _round(adjusted_capital_total),
            "rebalance_score": rebalance_score,
            "rebalance_state": rebalance_state,
        },
        "rebalances": rebalance_view,
        "allocations": allocation_view,
        "triggers": trigger_view,
        "adjustments": adjustment_view,
        "rebalance_health": {
            "rebalance_registry_ready": bool(rebalance_rows),
            "allocation_registry_ready": bool(allocation_rows),
            "trigger_registry_ready": bool(trigger_rows),
            "adjustment_registry_ready": bool(adjustment_rows),
            "rebalance_score": rebalance_score,
            "rebalance_state": rebalance_state,
        },
    }
