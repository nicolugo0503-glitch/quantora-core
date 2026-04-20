import json
from datetime import datetime, timezone
from pathlib import Path

STATE_FILE_NAME = "smart_order_router.json"


def now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def default_state():
    return {
        "smart_order_router": {
            "enabled": True,
            "last_updated_at": None,
            "last_route_at": None,
            "last_split_at": None,
            "route_count": 0,
            "split_count": 0,
            "fallback_routes": 0,
            "telemetry": [],
        },
        "rules": {
            "max_child_orders": 3,
            "min_venue_score": 60.0,
            "prefer_lower_slippage": True,
            "prefer_lower_latency": True,
            "reserve_liquidity_buffer_pct": 0.1,
        },
        "venues": [],
        "routes": [],
        "history": [],
    }


def _ensure_state_file(artifacts_dir: Path):
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    path = artifacts_dir / STATE_FILE_NAME
    if not path.exists():
        path.write_text(json.dumps(default_state(), indent=2), encoding="utf-8")
    return path


def load_state(artifacts_dir: Path):
    path = _ensure_state_file(artifacts_dir)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        data = default_state()
    merged = default_state()
    merged.update({k: v for k, v in data.items() if k in merged})
    for k, v in default_state()["smart_order_router"].items():
        merged["smart_order_router"].setdefault(k, v)
    for k, v in default_state()["rules"].items():
        merged["rules"].setdefault(k, v)
    return merged


def save_state(artifacts_dir: Path, state):
    path = _ensure_state_file(artifacts_dir)
    path.write_text(json.dumps(state, indent=2), encoding="utf-8")


def _safe_float(value, default=0.0):
    try:
        if value in (None, ""):
            return default
        return float(value)
    except Exception:
        return default


def _safe_int(value, default=0):
    try:
        if value in (None, ""):
            return default
        return int(value)
    except Exception:
        return default


def build_status(artifacts_dir: Path):
    state = load_state(artifacts_dir)
    return {
        "smart_order_router": state["smart_order_router"],
        "rules": state["rules"],
        "venue_count": len(state.get("venues", [])),
        "route_count": len(state.get("routes", [])),
        "venues": state.get("venues", []),
        "recent_routes": state.get("routes", [])[-10:][::-1],
    }


def update_rules(artifacts_dir: Path, payload: dict):
    state = load_state(artifacts_dir)
    for key in state["rules"].keys():
        if key in payload and payload[key] is not None:
            state["rules"][key] = payload[key]
    state["smart_order_router"]["last_updated_at"] = now_iso()
    state["history"].append({"timestamp": now_iso(), "event": "sor_rules.updated"})
    state["history"] = state["history"][-100:]
    save_state(artifacts_dir, state)
    return {"status": "rules_updated", "rules": state["rules"]}


def ingest_venues(artifacts_dir: Path, payload: dict):
    state = load_state(artifacts_dir)
    venues = []
    for item in payload.get("venues", []):
        venue_id = item.get("venue_id") or f"venue_{len(venues)+1:03d}"
        venues.append({
            "venue_id": venue_id,
            "venue_name": item.get("venue_name") or venue_id,
            "quality_score": round(_safe_float(item.get("quality_score"), 0.0), 2),
            "avg_slippage_bps": round(_safe_float(item.get("avg_slippage_bps"), 0.0), 4),
            "avg_latency_ms": round(_safe_float(item.get("avg_latency_ms"), 0.0), 2),
            "available_liquidity": round(_safe_float(item.get("available_liquidity"), 0.0), 2),
            "flagged": bool(item.get("flagged", False)),
        })
    state["venues"] = venues
    sor = state["smart_order_router"]
    sor["last_updated_at"] = now_iso()
    sor["telemetry"].append({"timestamp": now_iso(), "event": "venues.ingested", "venue_count": len(venues)})
    sor["telemetry"] = sor["telemetry"][-50:]
    state["history"].append({"timestamp": now_iso(), "event": "venues.ingested", "venue_count": len(venues)})
    state["history"] = state["history"][-100:]
    save_state(artifacts_dir, state)
    return {"status": "venues_ingested", "venue_count": len(venues)}


def route_order(artifacts_dir: Path, payload: dict):
    state = load_state(artifacts_dir)
    rules = state["rules"]
    order_qty = max(_safe_float(payload.get("quantity"), 0.0), 0.0)

    eligible = []
    for v in state.get("venues", []):
        if v.get("flagged"):
            continue
        if _safe_float(v.get("quality_score"), 0.0) < _safe_float(rules.get("min_venue_score"), 60.0):
            continue
        eligible.append(v)

    if rules.get("prefer_lower_slippage", True):
        eligible.sort(key=lambda x: (_safe_float(x.get("avg_slippage_bps"), 0.0), -_safe_float(x.get("quality_score"), 0.0), _safe_float(x.get("avg_latency_ms"), 0.0)))
    else:
        eligible.sort(key=lambda x: (-_safe_float(x.get("quality_score"), 0.0), _safe_float(x.get("avg_latency_ms"), 0.0)))

    max_children = max(_safe_int(rules.get("max_child_orders"), 3), 1)
    selected = eligible[:max_children]

    remaining = order_qty
    child_orders = []
    for v in selected:
        liquidity = max(_safe_float(v.get("available_liquidity"), 0.0) * (1.0 - _safe_float(rules.get("reserve_liquidity_buffer_pct"), 0.1)), 0.0)
        alloc = min(remaining, liquidity)
        if alloc <= 0:
            continue
        child_orders.append({
            "venue_id": v["venue_id"],
            "venue_name": v["venue_name"],
            "quantity": round(alloc, 4),
            "quality_score": v["quality_score"],
            "avg_slippage_bps": v["avg_slippage_bps"],
            "avg_latency_ms": v["avg_latency_ms"],
        })
        remaining -= alloc
        if remaining <= 0:
            break

    fallback_used = remaining > 0 and len(selected) > 0
    if fallback_used:
        child_orders.append({
            "venue_id": selected[0]["venue_id"],
            "venue_name": selected[0]["venue_name"],
            "quantity": round(remaining, 4),
            "quality_score": selected[0]["quality_score"],
            "avg_slippage_bps": selected[0]["avg_slippage_bps"],
            "avg_latency_ms": selected[0]["avg_latency_ms"],
            "fallback_fill": True,
        })
        remaining = 0.0

    route = {
        "route_id": f"sor_{len(state.get('routes', []))+1:04d}",
        "timestamp": now_iso(),
        "order_id": payload.get("order_id") or f"ord_{len(state.get('routes', []))+1:04d}",
        "symbol": (payload.get("symbol") or "AAPL").upper(),
        "side": (payload.get("side") or "buy").lower(),
        "requested_quantity": round(order_qty, 4),
        "child_orders": child_orders,
        "unfilled_quantity": round(remaining, 4),
        "fallback_used": fallback_used,
    }
    state.setdefault("routes", []).append(route)

    sor = state["smart_order_router"]
    sor["last_route_at"] = now_iso()
    sor["last_split_at"] = now_iso()
    sor["last_updated_at"] = now_iso()
    sor["route_count"] = len(state["routes"])
    sor["split_count"] = sum(len(r.get("child_orders", [])) for r in state["routes"])
    sor["fallback_routes"] = len([r for r in state["routes"] if r.get("fallback_used")])
    sor["telemetry"].append({"timestamp": now_iso(), "event": "order.routed", "order_id": route["order_id"], "child_orders": len(child_orders)})
    sor["telemetry"] = sor["telemetry"][-50:]
    state["history"].append({"timestamp": now_iso(), "event": "order.routed", "order_id": route["order_id"]})
    state["history"] = state["history"][-100:]
    save_state(artifacts_dir, state)
    return {"status": "order_routed", "route": route}
