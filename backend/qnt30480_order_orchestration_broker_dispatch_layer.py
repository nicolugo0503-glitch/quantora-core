
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


def build_order_dispatch_package(
    order_rows: Iterable[Dict],
    dispatch_rows: Iterable[Dict],
    broker_ack_rows: Iterable[Dict],
    orchestration_rows: Iterable[Dict],
) -> Dict:
    order_rows = list(order_rows or [])
    dispatch_rows = list(dispatch_rows or [])
    broker_ack_rows = list(broker_ack_rows or [])
    orchestration_rows = list(orchestration_rows or [])

    open_orders = [x for x in order_rows if (x.get("status") or "").lower() in {"created", "open", "pending"}]
    dispatched_orders = [x for x in dispatch_rows if (x.get("status") or "").lower() in {"sent", "dispatched", "routed"}]
    acked_orders = [x for x in broker_ack_rows if (x.get("status") or "").lower() in {"acked", "accepted", "received"}]
    stable_flows = [x for x in orchestration_rows if (x.get("status") or "").lower() in {"stable", "healthy", "completed"}]

    total_order_notional = sum(_as_float(x.get("order_notional")) for x in order_rows)
    total_dispatched_notional = sum(_as_float(x.get("dispatch_notional")) for x in dispatch_rows)

    order_view: List[Dict] = []
    for row in order_rows:
        order_view.append({
            "order_id": row.get("id"),
            "strategy_name": row.get("strategy_name") or "Strategy",
            "symbol": row.get("symbol") or "SPY",
            "order_notional": _round(_as_float(row.get("order_notional"))),
            "side": row.get("side") or "buy",
            "status": row.get("status") or "draft",
            "created_at": row.get("created_at"),
        })

    dispatch_view: List[Dict] = []
    for row in dispatch_rows:
        dispatch_view.append({
            "dispatch_id": row.get("id"),
            "broker_name": row.get("broker_name") or "Broker",
            "symbol": row.get("symbol") or "SPY",
            "dispatch_notional": _round(_as_float(row.get("dispatch_notional"))),
            "status": row.get("status") or "draft",
            "created_at": row.get("created_at"),
        })

    ack_view: List[Dict] = []
    for row in broker_ack_rows:
        ack_view.append({
            "ack_id": row.get("id"),
            "broker_name": row.get("broker_name") or "Broker",
            "broker_order_id": row.get("broker_order_id") or "broker_order",
            "latency_ms": int(_as_float(row.get("latency_ms"))),
            "status": row.get("status") or "pending",
            "created_at": row.get("created_at"),
        })

    orchestration_view: List[Dict] = []
    for row in orchestration_rows:
        orchestration_view.append({
            "flow_id": row.get("id"),
            "flow_name": row.get("flow_name") or "Dispatch Flow",
            "processed_orders": int(_as_float(row.get("processed_orders"))),
            "status": row.get("status") or "draft",
            "created_at": row.get("created_at"),
        })

    dispatch_score = max(
        45,
        min(
            100,
            int(
                64
                + len(open_orders) * 2
                + len(dispatched_orders) * 3
                + len(acked_orders) * 4
                + len(stable_flows) * 2
            )
        ),
    )

    dispatch_state = "IDLE"
    if open_orders or dispatched_orders:
        dispatch_state = "ROUTING"
    if acked_orders and stable_flows:
        dispatch_state = "LIVE"

    return {
        "summary": {
            "orders_total": len(order_rows),
            "orders_open": len(open_orders),
            "dispatches_total": len(dispatch_rows),
            "dispatches_live": len(dispatched_orders),
            "broker_acks_total": len(broker_ack_rows),
            "broker_acks_live": len(acked_orders),
            "flows_total": len(orchestration_rows),
            "order_notional_total": _round(total_order_notional),
            "dispatch_notional_total": _round(total_dispatched_notional),
            "dispatch_score": dispatch_score,
            "dispatch_state": dispatch_state,
        },
        "orders": order_view,
        "dispatches": dispatch_view,
        "broker_acks": ack_view,
        "flows": orchestration_view,
        "dispatch_health": {
            "order_registry_ready": bool(order_rows),
            "dispatch_registry_ready": bool(dispatch_rows),
            "ack_registry_ready": bool(broker_ack_rows),
            "flow_registry_ready": bool(orchestration_rows),
            "dispatch_score": dispatch_score,
            "dispatch_state": dispatch_state,
        },
    }
