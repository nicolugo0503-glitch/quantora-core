
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


def build_signal_execution_bridge_package(
    signal_rows: Iterable[Dict],
    routing_rows: Iterable[Dict],
    execution_intent_rows: Iterable[Dict],
    automation_cycle_rows: Iterable[Dict],
) -> Dict:
    signal_rows = list(signal_rows or [])
    routing_rows = list(routing_rows or [])
    execution_intent_rows = list(execution_intent_rows or [])
    automation_cycle_rows = list(automation_cycle_rows or [])

    live_signals = [x for x in signal_rows if (x.get("status") or "").lower() in {"live", "active", "validated"}]
    routed_signals = [x for x in routing_rows if (x.get("status") or "").lower() in {"routed", "approved", "forwarded"}]
    executable_intents = [x for x in execution_intent_rows if (x.get("status") or "").lower() in {"ready", "queued", "approved"}]
    stable_cycles = [x for x in automation_cycle_rows if (x.get("status") or "").lower() in {"stable", "healthy", "completed"}]

    total_signal_strength = sum(abs(_as_float(x.get("signal_strength"))) for x in signal_rows)
    total_notional = sum(_as_float(x.get("target_notional")) for x in execution_intent_rows)

    signal_view: List[Dict] = []
    for row in signal_rows:
        signal_view.append({
            "signal_id": row.get("id"),
            "signal_name": row.get("signal_name") or "Signal",
            "signal_strength": _round(_as_float(row.get("signal_strength"))),
            "signal_type": row.get("signal_type") or "momentum",
            "status": row.get("status") or "draft",
            "created_at": row.get("created_at"),
        })

    routing_view: List[Dict] = []
    for row in routing_rows:
        routing_view.append({
            "routing_id": row.get("id"),
            "signal_name": row.get("signal_name") or "Signal",
            "target_strategy": row.get("target_strategy") or "Strategy",
            "routing_mode": row.get("routing_mode") or "policy",
            "status": row.get("status") or "draft",
            "created_at": row.get("created_at"),
        })

    intent_view: List[Dict] = []
    for row in execution_intent_rows:
        intent_view.append({
            "intent_id": row.get("id"),
            "strategy_name": row.get("strategy_name") or "Strategy",
            "target_notional": _round(_as_float(row.get("target_notional"))),
            "order_side": row.get("order_side") or "buy",
            "status": row.get("status") or "draft",
            "created_at": row.get("created_at"),
        })

    cycle_view: List[Dict] = []
    for row in automation_cycle_rows:
        cycle_view.append({
            "cycle_id": row.get("id"),
            "cycle_name": row.get("cycle_name") or "Automation Cycle",
            "processed_signals": int(_as_float(row.get("processed_signals"))),
            "status": row.get("status") or "draft",
            "created_at": row.get("created_at"),
        })

    bridge_score = max(
        45,
        min(
            100,
            int(
                63
                + len(live_signals) * 3
                + len(routed_signals) * 3
                + len(executable_intents) * 4
                + len(stable_cycles) * 2
            )
        ),
    )

    bridge_state = "IDLE"
    if live_signals or routed_signals:
        bridge_state = "ARMED"
    if executable_intents and stable_cycles:
        bridge_state = "FLOWING"

    return {
        "summary": {
            "signals_total": len(signal_rows),
            "signals_live": len(live_signals),
            "routes_total": len(routing_rows),
            "routes_active": len(routed_signals),
            "intents_total": len(execution_intent_rows),
            "intents_ready": len(executable_intents),
            "cycles_total": len(automation_cycle_rows),
            "signal_strength_total": _round(total_signal_strength),
            "target_notional_total": _round(total_notional),
            "bridge_score": bridge_score,
            "bridge_state": bridge_state,
        },
        "signals": signal_view,
        "routes": routing_view,
        "execution_intents": intent_view,
        "automation_cycles": cycle_view,
        "bridge_health": {
            "signal_registry_ready": bool(signal_rows),
            "routing_registry_ready": bool(routing_rows),
            "intent_registry_ready": bool(execution_intent_rows),
            "cycle_registry_ready": bool(automation_cycle_rows),
            "bridge_score": bridge_score,
            "bridge_state": bridge_state,
        },
    }
