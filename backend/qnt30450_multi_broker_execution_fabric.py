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


def build_multi_broker_package(
    brokers: Iterable[Dict],
    routes: Iterable[Dict],
    executions: Iterable[Dict],
    failovers: Iterable[Dict],
) -> Dict:
    brokers = list(brokers or [])
    routes = list(routes or [])
    executions = list(executions or [])
    failovers = list(failovers or [])

    active_brokers = [b for b in brokers if (b.get("status") or "").lower() in {"active", "connected", "ready"}]
    active_routes = [r for r in routes if (r.get("status") or "").lower() in {"active", "live", "ready"}]
    successful_execs = [e for e in executions if (e.get("status") or "").lower() in {"filled", "completed", "applied", "sent"}]
    failed_execs = [e for e in executions if (e.get("status") or "").lower() in {"failed", "rejected", "error"}]
    triggered_failovers = [f for f in failovers if (f.get("status") or "").lower() in {"triggered", "applied", "completed"}]

    broker_rows: List[Dict] = []
    for row in brokers:
        broker_rows.append({
            "broker_id": row.get("id"),
            "broker_name": row.get("broker_name") or "broker",
            "broker_type": row.get("broker_type") or "execution",
            "status": row.get("status") or "draft",
            "latency_ms": int(_as_float(row.get("latency_ms"))),
            "created_at": row.get("created_at"),
        })

    route_rows: List[Dict] = []
    for row in routes:
        route_rows.append({
            "route_id": row.get("id"),
            "route_name": row.get("route_name") or "route",
            "symbol_scope": row.get("symbol_scope") or "global",
            "primary_broker": row.get("primary_broker") or "alpaca",
            "secondary_broker": row.get("secondary_broker") or "",
            "status": row.get("status") or "draft",
            "created_at": row.get("created_at"),
        })

    execution_rows: List[Dict] = []
    for row in executions:
        execution_rows.append({
            "execution_id": row.get("id"),
            "broker_name": row.get("broker_name") or "alpaca",
            "symbol": row.get("symbol") or "-",
            "side": row.get("side") or "buy",
            "notional_amount": _round(_as_float(row.get("notional_amount"))),
            "status": row.get("status") or "sent",
            "created_at": row.get("created_at"),
        })

    failover_rows: List[Dict] = []
    for row in failovers:
        failover_rows.append({
            "failover_id": row.get("id"),
            "route_name": row.get("route_name") or "route",
            "from_broker": row.get("from_broker") or "alpaca",
            "to_broker": row.get("to_broker") or "backup",
            "reason": row.get("reason") or "",
            "status": row.get("status") or "pending",
            "created_at": row.get("created_at"),
        })

    fabric_score = max(
        45,
        min(
            100,
            int(
                55
                + len(active_brokers) * 5
                + len(active_routes) * 4
                + len(successful_execs) * 2
                + len(triggered_failovers) * 2
                - len(failed_execs) * 3
            )
        ),
    )

    return {
        "summary": {
            "brokers_connected": len(active_brokers),
            "routes_active": len(active_routes),
            "executions_total": len(executions),
            "executions_successful": len(successful_execs),
            "executions_failed": len(failed_execs),
            "failovers_triggered": len(triggered_failovers),
            "fabric_score": fabric_score,
        },
        "brokers": broker_rows,
        "routes": route_rows,
        "executions": execution_rows,
        "failovers": failover_rows,
        "fabric_health": {
            "broker_registry_ready": bool(brokers),
            "routing_ready": bool(routes),
            "execution_ledger_ready": bool(executions),
            "failover_ready": bool(failovers),
            "fabric_score": fabric_score,
        },
    }
