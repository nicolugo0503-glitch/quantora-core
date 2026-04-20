import json
from datetime import datetime, timezone
from pathlib import Path

STATE_FILE_NAME = "adaptive_execution_policy_brain.json"
DRIFT_STATE_FILE = "execution_drift_monitor.json"
QUALITY_STATE_FILE = "execution_quality_scoreboard.json"
VENUE_GOVERNOR_FILE = "venue_selection_governor.json"
SOR_FILE = "smart_order_router.json"


def now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def default_state():
    return {
        "policy_brain": {
            "enabled": True,
            "last_updated_at": None,
            "last_context_at": None,
            "last_decision_at": None,
            "last_dispatch_at": None,
            "context_count": 0,
            "decision_count": 0,
            "dispatch_count": 0,
            "halt_count": 0,
            "telemetry": [],
        },
        "rules": {
            "max_slippage_drift_bps": 8.0,
            "max_latency_drift_ms": 180.0,
            "min_fill_rate_delta": -0.06,
            "high_volatility_threshold": 0.35,
            "crisis_volatility_threshold": 0.60,
            "min_liquidity_score": 0.40,
            "min_venue_quality_score": 70.0,
            "default_order_size_multiplier": 1.00,
            "defensive_order_size_multiplier": 0.60,
            "halt_order_size_multiplier": 0.00,
            "default_participation_rate": 0.12,
            "defensive_participation_rate": 0.05,
            "max_child_orders_normal": 3,
            "max_child_orders_defensive": 2,
            "default_execution_tolerance_bps": 16.0,
            "stressed_execution_tolerance_bps": 30.0,
            "enable_auto_halt": True,
        },
        "contexts": [],
        "decisions": [],
        "dispatches": [],
        "history": [],
    }


DEFAULT_DRIFT_STATE = {
    "alerts": [],
    "snapshots": [],
}

DEFAULT_QUALITY_STATE = {
    "scores": [],
}

DEFAULT_GOVERNOR_STATE = {
    "policy": {
        "mode": "adaptive",
        "max_venues": 1,
        "min_score": 65.0,
        "avoid_flagged": True,
        "fallback_enabled": True,
        "fallback_venue_id": "",
    }
}

DEFAULT_SOR_STATE = {
    "rules": {
        "max_child_orders": 3,
        "min_venue_score": 60.0,
        "prefer_lower_slippage": True,
        "prefer_lower_latency": True,
        "reserve_liquidity_buffer_pct": 0.1,
    }
}


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


def _ensure_state_file(artifacts_dir: Path):
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    path = artifacts_dir / STATE_FILE_NAME
    if not path.exists():
        path.write_text(json.dumps(default_state(), indent=2), encoding="utf-8")
    return path


def _load_json(path: Path, fallback: dict):
    if not path.exists():
        return fallback
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return fallback


def _save_json(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def load_state(artifacts_dir: Path):
    path = _ensure_state_file(artifacts_dir)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        data = default_state()
    merged = default_state()
    merged.update({k: v for k, v in data.items() if k in merged})
    for k, v in default_state()["policy_brain"].items():
        merged["policy_brain"].setdefault(k, v)
    for k, v in default_state()["rules"].items():
        merged["rules"].setdefault(k, v)
    return merged


def save_state(artifacts_dir: Path, state):
    path = _ensure_state_file(artifacts_dir)
    path.write_text(json.dumps(state, indent=2), encoding="utf-8")


def _latest(items):
    return items[-1] if items else None


def _regime_label(volatility: float, crisis_threshold: float, stressed_threshold: float):
    if volatility >= crisis_threshold:
        return "crisis"
    if volatility >= stressed_threshold:
        return "stressed"
    if volatility >= stressed_threshold * 0.7:
        return "elevated"
    return "stable"


def _infer_context(artifacts_dir: Path, payload: dict):
    drift_state = _load_json(artifacts_dir / DRIFT_STATE_FILE, DEFAULT_DRIFT_STATE)
    quality_state = _load_json(artifacts_dir / QUALITY_STATE_FILE, DEFAULT_QUALITY_STATE)

    latest_snapshot = _latest(drift_state.get("snapshots", [])) or {}
    latest_alert = _latest(drift_state.get("alerts", [])) or {}
    venue_scores = payload.get("venue_scores") or quality_state.get("scores", [])

    market_volatility = _safe_float(
        payload.get("market_volatility"),
        _safe_float(latest_snapshot.get("current_regime_vol"), _safe_float(payload.get("regime_vol"), 0.22)),
    )
    regime_shift = _safe_float(
        payload.get("regime_shift"),
        abs(_safe_float(latest_alert.get("regime_vol_shift"), market_volatility - _safe_float(latest_snapshot.get("baseline_regime_vol"), 0.0))),
    )
    context = {
        "context_id": payload.get("context_id") or f"ctx_{int(datetime.now(timezone.utc).timestamp())}",
        "timestamp": now_iso(),
        "symbol": (payload.get("symbol") or latest_snapshot.get("symbol") or "AAPL").upper(),
        "side": (payload.get("side") or "buy").lower(),
        "order_quantity": round(_safe_float(payload.get("order_quantity"), 100.0), 4),
        "urgency": (payload.get("urgency") or "normal").lower(),
        "market_volatility": round(market_volatility, 4),
        "regime_shift": round(regime_shift, 4),
        "liquidity_score": round(_safe_float(payload.get("liquidity_score"), 0.55), 4),
        "slippage_drift_bps": round(_safe_float(payload.get("slippage_drift_bps"), _safe_float(latest_alert.get("slippage_drift_bps"), 0.0)), 4),
        "latency_drift_ms": round(_safe_float(payload.get("latency_drift_ms"), _safe_float(latest_alert.get("latency_drift_ms"), 0.0)), 2),
        "fill_rate_delta": round(_safe_float(payload.get("fill_rate_delta"), _safe_float(latest_alert.get("fill_rate_delta"), 0.0)), 4),
        "drift_triggered": bool(payload.get("drift_triggered", latest_alert.get("triggered", False))),
        "drift_reasons": payload.get("drift_reasons") or latest_alert.get("reasons", []),
        "venue_scores": venue_scores,
    }
    return context


def build_status(artifacts_dir: Path):
    state = load_state(artifacts_dir)
    latest_context = _latest(state.get("contexts", []))
    latest_decision = _latest(state.get("decisions", []))
    latest_dispatch = _latest(state.get("dispatches", []))
    return {
        "policy_brain": state["policy_brain"],
        "rules": state["rules"],
        "context_count": len(state.get("contexts", [])),
        "decision_count": len(state.get("decisions", [])),
        "dispatch_count": len(state.get("dispatches", [])),
        "latest_context": latest_context,
        "latest_decision": latest_decision,
        "latest_dispatch": latest_dispatch,
        "recent_decisions": state.get("decisions", [])[-10:][::-1],
    }


def update_rules(artifacts_dir: Path, payload: dict):
    state = load_state(artifacts_dir)
    for key in state["rules"].keys():
        if key in payload and payload[key] is not None:
            state["rules"][key] = payload[key]
    state["policy_brain"]["last_updated_at"] = now_iso()
    state["history"].append({"timestamp": now_iso(), "event": "rules.updated"})
    state["history"] = state["history"][-200:]
    save_state(artifacts_dir, state)
    return {"status": "rules_updated", "rules": state["rules"]}


def ingest_context(artifacts_dir: Path, payload: dict):
    state = load_state(artifacts_dir)
    context = _infer_context(artifacts_dir, payload)
    context["regime_label"] = _regime_label(
        context["market_volatility"],
        _safe_float(state["rules"]["crisis_volatility_threshold"], 0.60),
        _safe_float(state["rules"]["high_volatility_threshold"], 0.35),
    )
    state.setdefault("contexts", []).append(context)
    brain = state["policy_brain"]
    brain["last_context_at"] = now_iso()
    brain["last_updated_at"] = now_iso()
    brain["context_count"] = len(state["contexts"])
    brain["telemetry"].append({"timestamp": now_iso(), "event": "context.ingested", "symbol": context["symbol"], "regime": context["regime_label"]})
    brain["telemetry"] = brain["telemetry"][-100:]
    state["history"].append({"timestamp": now_iso(), "event": "context.ingested", "symbol": context["symbol"]})
    state["history"] = state["history"][-200:]
    save_state(artifacts_dir, state)
    return {"status": "context_ingested", "context": context}


def decide_policy(artifacts_dir: Path, payload: dict):
    state = load_state(artifacts_dir)
    rules = state["rules"]
    context = payload.get("context") or _infer_context(artifacts_dir, payload)
    if not context.get("regime_label"):
        context["regime_label"] = _regime_label(
            _safe_float(context.get("market_volatility"), 0.0),
            _safe_float(rules["crisis_volatility_threshold"], 0.60),
            _safe_float(rules["high_volatility_threshold"], 0.35),
        )

    venue_scores = list(context.get("venue_scores") or [])
    min_venue_quality = _safe_float(rules["min_venue_quality_score"], 70.0)
    eligible_venues = [v for v in venue_scores if (not v.get("flagged")) and _safe_float(v.get("quality_score"), 0.0) >= min_venue_quality]
    blocked_venues = [v.get("venue_id") for v in venue_scores if v.get("flagged") or _safe_float(v.get("quality_score"), 0.0) < min_venue_quality]
    preferred_venues = [v.get("venue_id") for v in sorted(eligible_venues, key=lambda x: _safe_float(x.get("quality_score"), 0.0), reverse=True)[:3]]

    slip_drift = abs(_safe_float(context.get("slippage_drift_bps"), 0.0))
    latency_drift = abs(_safe_float(context.get("latency_drift_ms"), 0.0))
    fill_rate_delta = _safe_float(context.get("fill_rate_delta"), 0.0)
    regime_shift = abs(_safe_float(context.get("regime_shift"), 0.0))
    volatility = _safe_float(context.get("market_volatility"), 0.0)
    liquidity = _safe_float(context.get("liquidity_score"), 0.0)
    urgency = (context.get("urgency") or "normal").lower()

    extreme_drift = (
        slip_drift >= (_safe_float(rules["max_slippage_drift_bps"], 8.0) * 2.0)
        or latency_drift >= (_safe_float(rules["max_latency_drift_ms"], 180.0) * 2.0)
        or fill_rate_delta <= (_safe_float(rules["min_fill_rate_delta"], -0.06) * 2.0)
    )
    stressed = (
        bool(context.get("drift_triggered"))
        or volatility >= _safe_float(rules["high_volatility_threshold"], 0.35)
        or liquidity < _safe_float(rules["min_liquidity_score"], 0.40)
        or len(blocked_venues) >= max(1, len(venue_scores) // 2)
        or regime_shift >= (_safe_float(rules["high_volatility_threshold"], 0.35) * 0.5)
    )
    crisis = (
        volatility >= _safe_float(rules["crisis_volatility_threshold"], 0.60)
        or extreme_drift
        or (len(eligible_venues) == 0 and len(venue_scores) > 0)
    )

    mode = "normal"
    if crisis and bool(rules.get("enable_auto_halt", True)):
        mode = "halt"
    elif stressed:
        mode = "defensive"

    order_size_multiplier = _safe_float(rules["default_order_size_multiplier"], 1.0)
    participation_rate = _safe_float(rules["default_participation_rate"], 0.12)
    max_child_orders = _safe_int(rules["max_child_orders_normal"], 3)
    execution_tolerance_bps = _safe_float(rules["default_execution_tolerance_bps"], 16.0)
    venue_mode = "performance_weighted"
    reasons = []

    if context.get("drift_triggered"):
        reasons.append("execution_drift_detected")
    if volatility >= _safe_float(rules["high_volatility_threshold"], 0.35):
        reasons.append("volatility_spike")
    if liquidity < _safe_float(rules["min_liquidity_score"], 0.40):
        reasons.append("thin_liquidity")
    if len(blocked_venues) > 0:
        reasons.append("venue_quality_degradation")
    if urgency == "high":
        reasons.append("urgent_parent_order")

    if mode == "defensive":
        order_size_multiplier = _safe_float(rules["defensive_order_size_multiplier"], 0.60)
        participation_rate = _safe_float(rules["defensive_participation_rate"], 0.05)
        max_child_orders = _safe_int(rules["max_child_orders_defensive"], 2)
        execution_tolerance_bps = _safe_float(rules["stressed_execution_tolerance_bps"], 30.0)
        venue_mode = "quality_escape"
    elif mode == "halt":
        order_size_multiplier = _safe_float(rules["halt_order_size_multiplier"], 0.0)
        participation_rate = 0.0
        max_child_orders = 0
        execution_tolerance_bps = _safe_float(rules["stressed_execution_tolerance_bps"], 30.0)
        venue_mode = "kill_switch"
        reasons.append("auto_halt_condition")

    if urgency == "high" and mode != "halt":
        execution_tolerance_bps += 5.0
        max_child_orders = max(max_child_orders, 2)
        venue_mode = "urgent_quality_bias"

    adjusted_quantity = round(max(_safe_float(context.get("order_quantity"), 0.0) * order_size_multiplier, 0.0), 4)
    reserve_liquidity_buffer_pct = round(max(0.05, min(0.55, 1.0 - participation_rate + (0.10 if mode != "normal" else 0.0))), 4)

    decision = {
        "decision_id": payload.get("decision_id") or f"policy_{len(state.get('decisions', [])) + 1:04d}",
        "timestamp": now_iso(),
        "symbol": context.get("symbol", "AAPL"),
        "side": context.get("side", "buy"),
        "regime_label": context.get("regime_label", "stable"),
        "mode": mode,
        "reasons": list(dict.fromkeys(reasons)),
        "order_quantity": round(_safe_float(context.get("order_quantity"), 0.0), 4),
        "adjusted_order_quantity": adjusted_quantity,
        "order_size_multiplier": round(order_size_multiplier, 4),
        "participation_rate": round(participation_rate, 4),
        "execution_tolerance_bps": round(execution_tolerance_bps, 4),
        "max_child_orders": max_child_orders,
        "venue_mode": venue_mode,
        "preferred_venues": preferred_venues,
        "blocked_venues": blocked_venues,
        "drift_summary": {
            "slippage_drift_bps": round(slip_drift, 4),
            "latency_drift_ms": round(latency_drift, 2),
            "fill_rate_delta": round(fill_rate_delta, 4),
            "regime_shift": round(regime_shift, 4),
            "drift_triggered": bool(context.get("drift_triggered")),
        },
        "routing_override": {
            "venue_governor_policy": {
                "mode": "adaptive_guarded" if mode != "normal" else "adaptive",
                "max_venues": 1 if mode != "normal" else min(2, max(1, len(preferred_venues) or 1)),
                "min_score": round(min_venue_quality + (5.0 if mode != "normal" else 0.0), 2),
                "avoid_flagged": True,
                "fallback_enabled": mode != "halt",
                "fallback_venue_id": preferred_venues[0] if preferred_venues else "",
            },
            "smart_order_router_rules": {
                "max_child_orders": max_child_orders,
                "min_venue_score": round(min_venue_quality + (5.0 if mode != "normal" else 0.0), 2),
                "prefer_lower_slippage": True,
                "prefer_lower_latency": mode != "normal" or urgency == "high",
                "reserve_liquidity_buffer_pct": reserve_liquidity_buffer_pct,
            },
        },
    }

    state.setdefault("decisions", []).append(decision)
    brain = state["policy_brain"]
    brain["last_decision_at"] = now_iso()
    brain["last_updated_at"] = now_iso()
    brain["decision_count"] = len(state["decisions"])
    brain["halt_count"] = len([d for d in state["decisions"] if d.get("mode") == "halt"])
    brain["telemetry"].append({"timestamp": now_iso(), "event": "policy.decided", "mode": mode, "symbol": decision["symbol"]})
    brain["telemetry"] = brain["telemetry"][-100:]
    state["history"].append({"timestamp": now_iso(), "event": "policy.decided", "mode": mode, "symbol": decision["symbol"]})
    state["history"] = state["history"][-200:]
    save_state(artifacts_dir, state)
    return {"status": "policy_decided", "decision": decision}


def dispatch_override(artifacts_dir: Path, payload: dict):
    state = load_state(artifacts_dir)
    decision = payload.get("decision")
    if not decision:
        if not state.get("decisions"):
            return {"status": "error", "message": "no_policy_decision_available"}
        decision = state["decisions"][-1]

    governor_path = artifacts_dir / VENUE_GOVERNOR_FILE
    sor_path = artifacts_dir / SOR_FILE
    governor_state = _load_json(governor_path, DEFAULT_GOVERNOR_STATE)
    sor_state = _load_json(sor_path, DEFAULT_SOR_STATE)

    governor_override = decision.get("routing_override", {}).get("venue_governor_policy", {})
    sor_override = decision.get("routing_override", {}).get("smart_order_router_rules", {})

    governor_state.setdefault("policy", {}).update(governor_override)
    governor_state.setdefault("venue_governor", {})["last_updated_at"] = now_iso()
    governor_state.setdefault("history", []).append({
        "timestamp": now_iso(),
        "event": "adaptive_execution.override_dispatched",
        "decision_id": decision.get("decision_id"),
        "mode": decision.get("mode"),
    })
    governor_state["history"] = governor_state["history"][-200:]

    sor_state.setdefault("rules", {}).update(sor_override)
    sor_state.setdefault("smart_order_router", {})["last_updated_at"] = now_iso()
    sor_state.setdefault("history", []).append({
        "timestamp": now_iso(),
        "event": "adaptive_execution.override_dispatched",
        "decision_id": decision.get("decision_id"),
        "mode": decision.get("mode"),
    })
    sor_state["history"] = sor_state["history"][-200:]

    _save_json(governor_path, governor_state)
    _save_json(sor_path, sor_state)

    dispatch = {
        "dispatch_id": payload.get("dispatch_id") or f"dispatch_{len(state.get('dispatches', [])) + 1:04d}",
        "timestamp": now_iso(),
        "decision_id": decision.get("decision_id"),
        "mode": decision.get("mode"),
        "symbol": decision.get("symbol"),
        "governor_policy": governor_override,
        "sor_rules": sor_override,
        "status": "override_dispatched",
    }
    state.setdefault("dispatches", []).append(dispatch)
    brain = state["policy_brain"]
    brain["last_dispatch_at"] = now_iso()
    brain["last_updated_at"] = now_iso()
    brain["dispatch_count"] = len(state["dispatches"])
    brain["telemetry"].append({"timestamp": now_iso(), "event": "override.dispatched", "decision_id": decision.get("decision_id"), "mode": decision.get("mode")})
    brain["telemetry"] = brain["telemetry"][-100:]
    state["history"].append({"timestamp": now_iso(), "event": "override.dispatched", "decision_id": decision.get("decision_id")})
    state["history"] = state["history"][-200:]
    save_state(artifacts_dir, state)
    return {"status": "override_dispatched", "dispatch": dispatch, "decision": decision}
