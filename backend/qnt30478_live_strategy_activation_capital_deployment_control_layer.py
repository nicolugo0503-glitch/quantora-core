
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


def build_strategy_activation_package(
    activation_rows: Iterable[Dict],
    deployment_rows: Iterable[Dict],
    capital_gate_rows: Iterable[Dict],
    runtime_rows: Iterable[Dict],
) -> Dict:
    activation_rows = list(activation_rows or [])
    deployment_rows = list(deployment_rows or [])
    capital_gate_rows = list(capital_gate_rows or [])
    runtime_rows = list(runtime_rows or [])

    active_strategies = [x for x in activation_rows if (x.get("status") or "").lower() in {"active", "live", "enabled"}]
    deployed_strategies = [x for x in deployment_rows if (x.get("status") or "").lower() in {"deployed", "running", "live"}]
    open_gates = [x for x in capital_gate_rows if (x.get("status") or "").lower() in {"open", "approved", "released"}]
    healthy_runtime = [x for x in runtime_rows if (x.get("status") or "").lower() in {"healthy", "green", "stable"}]

    allocated_capital = sum(_as_float(x.get("allocated_capital")) for x in deployment_rows)
    released_capital = sum(_as_float(x.get("released_capital")) for x in capital_gate_rows)

    activation_view: List[Dict] = []
    for row in activation_rows:
        activation_view.append({
            "activation_id": row.get("id"),
            "strategy_name": row.get("strategy_name") or "Strategy",
            "activation_mode": row.get("activation_mode") or "manual",
            "status": row.get("status") or "draft",
            "created_at": row.get("created_at"),
        })

    deployment_view: List[Dict] = []
    for row in deployment_rows:
        deployment_view.append({
            "deployment_id": row.get("id"),
            "strategy_name": row.get("strategy_name") or "Strategy",
            "allocated_capital": _round(_as_float(row.get("allocated_capital"))),
            "deployment_state": row.get("deployment_state") or "warming",
            "status": row.get("status") or "draft",
            "created_at": row.get("created_at"),
        })

    gate_view: List[Dict] = []
    for row in capital_gate_rows:
        gate_view.append({
            "gate_id": row.get("id"),
            "gate_name": row.get("gate_name") or "Capital Gate",
            "released_capital": _round(_as_float(row.get("released_capital"))),
            "approval_source": row.get("approval_source") or "risk_engine",
            "status": row.get("status") or "closed",
            "created_at": row.get("created_at"),
        })

    runtime_view: List[Dict] = []
    for row in runtime_rows:
        runtime_view.append({
            "runtime_id": row.get("id"),
            "strategy_name": row.get("strategy_name") or "Strategy",
            "heartbeat_seconds": int(_as_float(row.get("heartbeat_seconds"))),
            "runtime_note": row.get("runtime_note") or "stable",
            "status": row.get("status") or "unknown",
            "created_at": row.get("created_at"),
        })

    control_score = max(
        45,
        min(
            100,
            int(
                62
                + len(active_strategies) * 3
                + len(deployed_strategies) * 4
                + len(open_gates) * 2
                + len(healthy_runtime) * 2
            )
        ),
    )

    control_state = "IDLE"
    if active_strategies or deployed_strategies:
        control_state = "ARMED"
    if deployed_strategies and healthy_runtime:
        control_state = "LIVE"

    return {
        "summary": {
            "activations_total": len(activation_rows),
            "activations_live": len(active_strategies),
            "deployments_total": len(deployment_rows),
            "deployments_live": len(deployed_strategies),
            "capital_gates_total": len(capital_gate_rows),
            "capital_gates_open": len(open_gates),
            "runtime_monitors_total": len(runtime_rows),
            "allocated_capital_total": _round(allocated_capital),
            "released_capital_total": _round(released_capital),
            "control_score": control_score,
            "control_state": control_state,
        },
        "activations": activation_view,
        "deployments": deployment_view,
        "capital_gates": gate_view,
        "runtime_monitors": runtime_view,
        "control_health": {
            "activation_registry_ready": bool(activation_rows),
            "deployment_registry_ready": bool(deployment_rows),
            "gate_registry_ready": bool(capital_gate_rows),
            "runtime_registry_ready": bool(runtime_rows),
            "control_score": control_score,
            "control_state": control_state,
        },
    }
