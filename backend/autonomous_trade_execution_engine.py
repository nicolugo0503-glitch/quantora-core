import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

try:
    from backend.regime_aware_capital_allocation import decide_allocation, dispatch_allocation, ingest_context as ingest_allocation_context
    from backend.adaptive_execution_policy_brain import decide_policy as decide_adaptive_policy, ingest_context as ingest_adaptive_context
    from backend.smart_order_router import route_order, ingest_venues as sor_ingest_venues
    from backend.venue_selection_governor import select_venue, ingest_venues as governor_ingest_venues
except Exception:
    from regime_aware_capital_allocation import decide_allocation, dispatch_allocation, ingest_context as ingest_allocation_context
    from adaptive_execution_policy_brain import decide_policy as decide_adaptive_policy, ingest_context as ingest_adaptive_context
    from smart_order_router import route_order, ingest_venues as sor_ingest_venues
    from venue_selection_governor import select_venue, ingest_venues as governor_ingest_venues

STATE_FILE_NAME = "autonomous_trade_execution_engine.json"
QUALITY_FILE = "execution_quality_scoreboard.json"


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value in (None, ""):
            return default
        return float(value)
    except Exception:
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        if value in (None, ""):
            return default
        return int(value)
    except Exception:
        return default


def default_state() -> Dict[str, Any]:
    return {
        "engine": {
            "enabled": True,
            "paper_mode": True,
            "auto_dispatch_enabled": True,
            "last_updated_at": None,
            "last_signal_at": None,
            "last_cycle_at": None,
            "last_dispatch_at": None,
            "signal_count": 0,
            "cycle_count": 0,
            "execution_count": 0,
            "blocked_count": 0,
            "telemetry": [],
        },
        "controls": {
            "min_signal_confidence": 0.55,
            "max_notional_per_trade_usd": 125000.0,
            "default_price_buffer_bps": 10.0,
            "default_order_type": "limit",
            "close_loop_reconcile_enabled": True,
            "max_routes_per_cycle": 3,
        },
        "signals": [],
        "cycles": [],
        "orders": [],
        "dispatches": [],
        "lifecycle": [],
        "history": [],
    }


def _ensure_state_file(artifacts_dir: Path) -> Path:
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    path = artifacts_dir / STATE_FILE_NAME
    if not path.exists():
        path.write_text(json.dumps(default_state(), indent=2), encoding="utf-8")
    return path


def _load_json(path: Path, fallback: dict) -> dict:
    if not path.exists():
        return fallback
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return fallback


def load_state(artifacts_dir: Path) -> Dict[str, Any]:
    path = _ensure_state_file(artifacts_dir)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        data = default_state()
    merged = default_state()
    merged.update({k: v for k, v in data.items() if k in merged})
    for k, v in default_state()["engine"].items():
        merged["engine"].setdefault(k, v)
    for k, v in default_state()["controls"].items():
        merged["controls"].setdefault(k, v)
    return merged


def save_state(artifacts_dir: Path, state: Dict[str, Any]) -> None:
    path = _ensure_state_file(artifacts_dir)
    path.write_text(json.dumps(state, indent=2), encoding="utf-8")


def _latest(items: List[Dict[str, Any]]):
    return items[-1] if items else None


def _quality_scores(artifacts_dir: Path) -> List[Dict[str, Any]]:
    quality = _load_json(artifacts_dir / QUALITY_FILE, {"scores": []})
    scores = list(quality.get("scores", []))
    scores.sort(key=lambda x: (_safe_float(x.get("quality_score"), 0.0), -_safe_float(x.get("avg_slippage_bps"), 0.0)), reverse=True)
    return scores


def seed_execution_stack(artifacts_dir: Path) -> Dict[str, Any]:
    quality_scores = _quality_scores(artifacts_dir)
    if not quality_scores:
        quality_scores = [
            {"venue_id": "lit_nyse", "venue_name": "Lit NYSE", "quality_score": 92.0, "flagged": False, "avg_slippage_bps": 3.2, "fill_rate": 0.98, "reject_rate": 0.01, "avg_latency_ms": 31.0, "available_liquidity": 1800.0},
            {"venue_id": "lit_nasdaq", "venue_name": "Lit NASDAQ", "quality_score": 89.0, "flagged": False, "avg_slippage_bps": 4.1, "fill_rate": 0.97, "reject_rate": 0.015, "avg_latency_ms": 28.0, "available_liquidity": 1500.0},
            {"venue_id": "dark_pool_x", "venue_name": "Dark Pool X", "quality_score": 58.0, "flagged": True, "avg_slippage_bps": 9.8, "fill_rate": 0.82, "reject_rate": 0.07, "avg_latency_ms": 74.0, "available_liquidity": 2200.0},
        ]
    venues = []
    for row in quality_scores:
        venues.append({
            "venue_id": row.get("venue_id"),
            "venue_name": row.get("venue_name") or row.get("venue_id"),
            "quality_score": round(_safe_float(row.get("quality_score"), 0.0), 2),
            "flagged": bool(row.get("flagged", False)),
            "avg_slippage_bps": round(_safe_float(row.get("avg_slippage_bps"), 0.0), 4),
            "fill_rate": round(_safe_float(row.get("fill_rate"), 0.95), 4),
            "reject_rate": round(_safe_float(row.get("reject_rate"), 0.02), 4),
            "avg_latency_ms": round(_safe_float(row.get("avg_latency_ms"), 35.0), 2),
            "available_liquidity": round(_safe_float(row.get("available_liquidity"), 1000.0), 2),
            "orders": _safe_int(row.get("orders"), 0),
        })
    governor_ingest_venues(artifacts_dir, {"venues": venues})
    sor_ingest_venues(artifacts_dir, {"venues": venues})
    return {"status": "execution_stack_seeded", "venues": len(venues)}


def build_status(artifacts_dir: Path) -> Dict[str, Any]:
    state = load_state(artifacts_dir)
    return {
        "engine": state["engine"],
        "controls": state["controls"],
        "signal_count": len(state.get("signals", [])),
        "cycle_count": len(state.get("cycles", [])),
        "order_count": len(state.get("orders", [])),
        "dispatch_count": len(state.get("dispatches", [])),
        "lifecycle_count": len(state.get("lifecycle", [])),
        "latest_signal": _latest(state.get("signals", [])),
        "latest_cycle": _latest(state.get("cycles", [])),
        "latest_dispatch": _latest(state.get("dispatches", [])),
        "recent_orders": state.get("orders", [])[-10:][::-1],
    }


def update_controls(artifacts_dir: Path, payload: Dict[str, Any]) -> Dict[str, Any]:
    state = load_state(artifacts_dir)
    for key in state["controls"].keys():
        if key in payload and payload[key] is not None:
            state["controls"][key] = payload[key]
    if "paper_mode" in payload and payload.get("paper_mode") is not None:
        state["engine"]["paper_mode"] = bool(payload.get("paper_mode"))
    if "auto_dispatch_enabled" in payload and payload.get("auto_dispatch_enabled") is not None:
        state["engine"]["auto_dispatch_enabled"] = bool(payload.get("auto_dispatch_enabled"))
    state["engine"]["last_updated_at"] = now_iso()
    save_state(artifacts_dir, state)
    return {"status": "controls_updated", "controls": state["controls"], "engine": state["engine"]}


def ingest_signal(artifacts_dir: Path, payload: Dict[str, Any]) -> Dict[str, Any]:
    state = load_state(artifacts_dir)
    signal = {
        "signal_id": payload.get("signal_id") or f"sig_{len(state.get('signals', []))+1:04d}",
        "timestamp": now_iso(),
        "strategy_id": payload.get("strategy_id") or "strategy_primary",
        "symbol": (payload.get("symbol") or "AAPL").upper(),
        "side": (payload.get("side") or "buy").lower(),
        "confidence": round(_safe_float(payload.get("confidence"), 0.6), 4),
        "target_price": round(_safe_float(payload.get("target_price"), 195.0), 4),
        "market_price": round(_safe_float(payload.get("market_price"), _safe_float(payload.get("target_price"), 195.0)), 4),
        "requested_qty": round(_safe_float(payload.get("requested_qty"), 100.0), 4),
        "urgency": (payload.get("urgency") or "normal").lower(),
        "strategy_score": round(_safe_float(payload.get("strategy_score"), 0.7), 4),
        "market_volatility": round(_safe_float(payload.get("market_volatility"), 0.22), 4),
        "execution_quality_score": round(_safe_float(payload.get("execution_quality_score"), 85.0), 2),
    }
    state.setdefault("signals", []).append(signal)
    state["engine"]["last_signal_at"] = now_iso()
    state["engine"]["last_updated_at"] = now_iso()
    state["engine"]["signal_count"] = len(state["signals"])
    state["engine"].setdefault("telemetry", []).append({
        "timestamp": now_iso(),
        "event": "signal.ingested",
        "signal_id": signal["signal_id"],
        "symbol": signal["symbol"],
    })
    state["engine"]["telemetry"] = state["engine"]["telemetry"][-100:]
    save_state(artifacts_dir, state)
    return {"status": "signal_ingested", "signal": signal}


def execute_cycle(artifacts_dir: Path, payload: Dict[str, Any]) -> Dict[str, Any]:
    state = load_state(artifacts_dir)
    controls = state["controls"]
    seed_execution_stack(artifacts_dir)
    signal = payload.get("signal") or _latest(state.get("signals", []))
    if not signal:
        return {"status": "blocked", "reason": "no_signal_available"}
    if _safe_float(signal.get("confidence"), 0.0) < _safe_float(controls.get("min_signal_confidence"), 0.55):
        state["engine"]["blocked_count"] = _safe_int(state["engine"].get("blocked_count"), 0) + 1
        save_state(artifacts_dir, state)
        return {"status": "blocked", "reason": "signal_below_confidence_threshold", "signal": signal}

    adaptive_context = {
        "symbol": signal["symbol"],
        "side": signal["side"],
        "order_quantity": signal["requested_qty"],
        "urgency": signal.get("urgency"),
        "market_volatility": signal.get("market_volatility"),
        "liquidity_score": payload.get("liquidity_score", 0.55),
        "venue_scores": _quality_scores(artifacts_dir),
        "slippage_drift_bps": payload.get("slippage_drift_bps", 0.0),
        "latency_drift_ms": payload.get("latency_drift_ms", 0.0),
        "fill_rate_delta": payload.get("fill_rate_delta", 0.0),
        "drift_triggered": bool(payload.get("drift_triggered", False)),
    }
    ingest_adaptive_context(artifacts_dir, adaptive_context)
    adaptive = decide_adaptive_policy(artifacts_dir, {})
    adaptive_decision = adaptive.get("decision") or {}

    allocation_context = {
        "strategy_id": signal["strategy_id"],
        "symbol": signal["symbol"],
        "market_volatility": signal.get("market_volatility"),
        "execution_quality_score": signal.get("execution_quality_score"),
        "strategy_score": signal.get("strategy_score"),
        "adaptive_mode": adaptive_decision.get("mode", "normal"),
        "drift_severity": adaptive_decision.get("drift_severity", 0.0),
    }
    ingest_allocation_context(artifacts_dir, allocation_context)
    allocation = decide_allocation(artifacts_dir, allocation_context)
    allocation_decision = allocation.get("decision") or {}
    allocation_dispatch = dispatch_allocation(artifacts_dir, {"decision": allocation_decision})

    market_price = max(_safe_float(signal.get("market_price"), 0.0), 0.0001)
    deployable_capital = min(
        _safe_float(allocation_decision.get("deployable_capital_usd"), 0.0),
        _safe_float(controls.get("max_notional_per_trade_usd"), 125000.0),
    )
    if adaptive_decision.get("mode") == "halt" or allocation_decision.get("halted") or deployable_capital <= 0:
        cycle = {
            "cycle_id": payload.get("cycle_id") or f"cycle_{len(state.get('cycles', []))+1:04d}",
            "timestamp": now_iso(),
            "signal_id": signal.get("signal_id"),
            "status": "blocked",
            "block_reason": "adaptive_halt" if adaptive_decision.get("mode") == "halt" else "capital_unavailable",
            "adaptive_decision": adaptive_decision,
            "allocation_decision": allocation_decision,
            "allocation_dispatch": allocation_dispatch.get("dispatch"),
        }
        state.setdefault("cycles", []).append(cycle)
        state["engine"]["last_cycle_at"] = now_iso()
        state["engine"]["last_updated_at"] = now_iso()
        state["engine"]["cycle_count"] = len(state["cycles"])
        state["engine"]["blocked_count"] = _safe_int(state["engine"].get("blocked_count"), 0) + 1
        save_state(artifacts_dir, state)
        return {"status": "blocked", "cycle": cycle}

    target_qty = round(min(_safe_float(signal.get("requested_qty"), 0.0), deployable_capital / market_price), 6)
    order_notional = round(target_qty * market_price, 2)
    venue = select_venue(artifacts_dir, {"symbol": signal["symbol"], "side": signal["side"], "order_id": signal["signal_id"]})
    venue_decision = venue.get("decision") or {}
    routed = route_order(artifacts_dir, {
        "order_id": signal.get("signal_id"),
        "symbol": signal["symbol"],
        "side": signal["side"],
        "quantity": target_qty,
    })
    route = routed.get("route") or {}
    order = {
        "order_id": payload.get("order_id") or f"autox_{len(state.get('orders', []))+1:04d}",
        "timestamp": now_iso(),
        "signal_id": signal.get("signal_id"),
        "strategy_id": signal.get("strategy_id"),
        "symbol": signal.get("symbol"),
        "side": signal.get("side"),
        "quantity": target_qty,
        "market_price": market_price,
        "limit_price": round(market_price * (1 + (_safe_float(controls.get("default_price_buffer_bps"), 10.0) / 10000.0 if signal.get("side") == "buy" else -_safe_float(controls.get("default_price_buffer_bps"), 10.0) / 10000.0)), 4),
        "notional_usd": order_notional,
        "order_type": controls.get("default_order_type", "limit"),
        "selected_venue": venue_decision.get("selected_venue"),
        "selected_venue_name": venue_decision.get("selected_venue_name"),
        "route_id": route.get("route_id"),
        "child_orders": route.get("child_orders", []),
        "mode": "paper" if state["engine"].get("paper_mode", True) else "live",
        "execution_status": "routed",
    }
    lifecycle = {
        "lifecycle_id": payload.get("lifecycle_id") or f"life_{len(state.get('lifecycle', []))+1:04d}",
        "timestamp": now_iso(),
        "order_id": order["order_id"],
        "signal_id": signal.get("signal_id"),
        "stages": [
            {"stage": "signal_received", "timestamp": signal.get("timestamp")},
            {"stage": "adaptive_policy_decided", "timestamp": now_iso(), "mode": adaptive_decision.get("mode")},
            {"stage": "capital_allocated", "timestamp": now_iso(), "deployable_capital_usd": allocation_decision.get("deployable_capital_usd")},
            {"stage": "venue_selected", "timestamp": now_iso(), "venue_id": venue_decision.get("selected_venue")},
            {"stage": "order_routed", "timestamp": now_iso(), "route_id": route.get("route_id")},
        ],
        "status": "active",
    }
    cycle = {
        "cycle_id": payload.get("cycle_id") or f"cycle_{len(state.get('cycles', []))+1:04d}",
        "timestamp": now_iso(),
        "signal_id": signal.get("signal_id"),
        "status": "executed",
        "adaptive_decision": adaptive_decision,
        "allocation_decision": allocation_decision,
        "allocation_dispatch": allocation_dispatch.get("dispatch"),
        "venue_decision": venue_decision,
        "route": route,
        "order": order,
    }
    state.setdefault("orders", []).append(order)
    state.setdefault("cycles", []).append(cycle)
    state.setdefault("lifecycle", []).append(lifecycle)
    state["engine"]["last_cycle_at"] = now_iso()
    state["engine"]["last_updated_at"] = now_iso()
    state["engine"]["cycle_count"] = len(state["cycles"])
    state["engine"]["execution_count"] = len(state["orders"])
    save_state(artifacts_dir, state)
    return {"status": "cycle_executed", "cycle": cycle, "order": order, "lifecycle": lifecycle}


def dispatch_cycle(artifacts_dir: Path, payload: Dict[str, Any]) -> Dict[str, Any]:
    state = load_state(artifacts_dir)
    cycle = payload.get("cycle") or _latest(state.get("cycles", []))
    if not cycle:
        return {"status": "blocked", "reason": "no_cycle_available"}
    dispatch = {
        "dispatch_id": payload.get("dispatch_id") or f"dispatch_{len(state.get('dispatches', []))+1:04d}",
        "timestamp": now_iso(),
        "cycle_id": cycle.get("cycle_id"),
        "order_id": ((cycle.get("order") or {}).get("order_id")),
        "mode": "paper" if state["engine"].get("paper_mode", True) else "live",
        "status": "dispatched" if cycle.get("status") == "executed" else "blocked",
        "auto_dispatch": bool(state["engine"].get("auto_dispatch_enabled", True)),
    }
    state.setdefault("dispatches", []).append(dispatch)
    state["engine"]["last_dispatch_at"] = now_iso()
    state["engine"]["last_updated_at"] = now_iso()
    save_state(artifacts_dir, state)
    return {"status": "cycle_dispatched", "dispatch": dispatch, "cycle": cycle}
