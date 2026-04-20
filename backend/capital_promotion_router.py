import json
from datetime import datetime, timezone
from pathlib import Path

STATE_FILE_NAME = "capital_promotion_router.json"


def now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def default_state():
    return {
        "promotion_router": {
            "enabled": True,
            "last_updated_at": None,
            "last_routing_at": None,
            "last_execution_gate_at": None,
            "approved_routes": 0,
            "sandbox_routes": 0,
            "blocked_routes": 0,
            "gated_orders": 0,
            "released_orders": 0,
            "telemetry": [],
        },
        "routing_rules": {
            "approved_target": "funded_live",
            "watchlist_target": "sandbox",
            "rejected_target": "blocked",
            "max_watchlist_capital_pct": 0.5,
            "require_approval_for_execution": True,
            "block_rejected_execution": True,
        },
        "routes": [],
        "execution_decisions": [],
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
    for k, v in default_state()["promotion_router"].items():
        merged["promotion_router"].setdefault(k, v)
    for k, v in default_state()["routing_rules"].items():
        merged["routing_rules"].setdefault(k, v)
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


def build_status(artifacts_dir: Path):
    state = load_state(artifacts_dir)
    return {
        "promotion_router": state["promotion_router"],
        "routing_rules": state["routing_rules"],
        "route_count": len(state.get("routes", [])),
        "execution_decision_count": len(state.get("execution_decisions", [])),
        "recent_routes": state.get("routes", [])[-10:][::-1],
        "recent_execution_decisions": state.get("execution_decisions", [])[-10:][::-1],
    }


def update_rules(artifacts_dir: Path, payload: dict):
    state = load_state(artifacts_dir)
    for key in state["routing_rules"].keys():
        if key in payload and payload[key] is not None:
            state["routing_rules"][key] = payload[key]
    state["promotion_router"]["last_updated_at"] = now_iso()
    state["history"].append({"timestamp": now_iso(), "event": "routing_rules.updated"})
    state["history"] = state["history"][-100:]
    save_state(artifacts_dir, state)
    return {"status": "rules_updated", "routing_rules": state["routing_rules"]}


def route_candidate(artifacts_dir: Path, payload: dict):
    state = load_state(artifacts_dir)
    rules = state["routing_rules"]

    verdict = (payload.get("verdict") or "REJECTED").upper()
    candidate_id = payload.get("candidate_id") or "candidate_unknown"
    strategy_name = payload.get("strategy_name") or candidate_id
    requested_capital = _safe_float(payload.get("requested_capital"), 0.0)

    target = rules["rejected_target"]
    allocated_capital = 0.0
    execution_mode = "blocked"

    if verdict == "APPROVED":
        target = rules["approved_target"]
        allocated_capital = requested_capital
        execution_mode = "live"
    elif verdict == "WATCHLIST":
        target = rules["watchlist_target"]
        allocated_capital = round(requested_capital * (_safe_float(rules["max_watchlist_capital_pct"], 0.5)), 2)
        execution_mode = "sandbox"

    route = {
        "route_id": f"route_{len(state.get('routes', []))+1:04d}",
        "timestamp": now_iso(),
        "candidate_id": candidate_id,
        "strategy_name": strategy_name,
        "verdict": verdict,
        "target": target,
        "requested_capital": requested_capital,
        "allocated_capital": allocated_capital,
        "execution_mode": execution_mode,
    }

    state.setdefault("routes", []).append(route)
    router = state["promotion_router"]
    router["last_routing_at"] = now_iso()
    router["last_updated_at"] = now_iso()
    router["approved_routes"] = len([r for r in state["routes"] if r.get("verdict") == "APPROVED"])
    router["sandbox_routes"] = len([r for r in state["routes"] if r.get("verdict") == "WATCHLIST"])
    router["blocked_routes"] = len([r for r in state["routes"] if r.get("verdict") == "REJECTED"])
    router["telemetry"].append({
        "timestamp": now_iso(),
        "event": "candidate.routed",
        "candidate_id": candidate_id,
        "verdict": verdict,
        "target": target,
    })
    router["telemetry"] = router["telemetry"][-50:]
    state["history"].append({"timestamp": now_iso(), "event": "candidate.routed", "candidate_id": candidate_id, "verdict": verdict})
    state["history"] = state["history"][-100:]
    save_state(artifacts_dir, state)
    return {"status": "candidate_routed", "route": route}


def execution_gate_decision(artifacts_dir: Path, payload: dict):
    state = load_state(artifacts_dir)
    rules = state["routing_rules"]

    candidate_id = payload.get("candidate_id") or "candidate_unknown"
    strategy_name = payload.get("strategy_name") or candidate_id
    verdict = (payload.get("verdict") or "REJECTED").upper()
    requested_order_notional = _safe_float(payload.get("requested_order_notional"), 0.0)

    allow_execution = False
    execution_lane = "blocked"
    reason = "rejected_by_default"

    if verdict == "APPROVED":
        allow_execution = True
        execution_lane = "live"
        reason = "approved_for_live_execution"
    elif verdict == "WATCHLIST":
        allow_execution = not bool(rules.get("require_approval_for_execution"))
        execution_lane = "sandbox"
        reason = "watchlist_sandbox_only"

    if verdict == "REJECTED" and bool(rules.get("block_rejected_execution")):
        allow_execution = False
        execution_lane = "blocked"
        reason = "rejected_execution_blocked"

    decision = {
        "decision_id": f"gate_{len(state.get('execution_decisions', []))+1:04d}",
        "timestamp": now_iso(),
        "candidate_id": candidate_id,
        "strategy_name": strategy_name,
        "verdict": verdict,
        "requested_order_notional": requested_order_notional,
        "allow_execution": allow_execution,
        "execution_lane": execution_lane,
        "reason": reason,
    }

    state.setdefault("execution_decisions", []).append(decision)
    router = state["promotion_router"]
    router["last_execution_gate_at"] = now_iso()
    router["last_updated_at"] = now_iso()
    router["gated_orders"] = len(state["execution_decisions"])
    router["released_orders"] = len([d for d in state["execution_decisions"] if d.get("allow_execution")])
    router["telemetry"].append({
        "timestamp": now_iso(),
        "event": "execution.gated",
        "candidate_id": candidate_id,
        "allow_execution": allow_execution,
        "lane": execution_lane,
    })
    router["telemetry"] = router["telemetry"][-50:]
    state["history"].append({"timestamp": now_iso(), "event": "execution.gated", "candidate_id": candidate_id, "allow_execution": allow_execution})
    state["history"] = state["history"][-100:]
    save_state(artifacts_dir, state)
    return {"status": "execution_decided", "decision": decision}
