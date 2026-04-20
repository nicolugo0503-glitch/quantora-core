import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

STATE_FILE_NAME = "regime_aware_capital_allocation.json"
ADAPTIVE_POLICY_FILE = "adaptive_execution_policy_brain.json"
QUALITY_FILE = "execution_quality_scoreboard.json"
DRIFT_FILE = "execution_drift_monitor.json"


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
        "allocator": {
            "enabled": True,
            "last_updated_at": None,
            "last_context_at": None,
            "last_decision_at": None,
            "last_dispatch_at": None,
            "context_count": 0,
            "decision_count": 0,
            "dispatch_count": 0,
            "telemetry": [],
        },
        "policy": {
            "base_capital_usd": 1000000.0,
            "max_allocation_pct": 0.22,
            "min_allocation_pct": 0.02,
            "normal_risk_multiplier": 1.0,
            "stressed_risk_multiplier": 0.72,
            "crisis_risk_multiplier": 0.35,
            "execution_penalty_weight": 0.25,
            "strategy_weight": 0.45,
            "regime_weight": 0.30,
            "reserve_buffer_pct": 0.12,
            "halt_on_severe_drift": True,
        },
        "contexts": [],
        "decisions": [],
        "dispatches": [],
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
    for k, v in default_state()["allocator"].items():
        merged["allocator"].setdefault(k, v)
    for k, v in default_state()["policy"].items():
        merged["policy"].setdefault(k, v)
    return merged


def save_state(artifacts_dir: Path, state: Dict[str, Any]) -> None:
    path = _ensure_state_file(artifacts_dir)
    path.write_text(json.dumps(state, indent=2), encoding="utf-8")


def _latest(items):
    return items[-1] if items else None


def _policy_from_adaptive_mode(mode: str, policy: Dict[str, Any]) -> float:
    mapping = {
        "normal": _safe_float(policy.get("normal_risk_multiplier"), 1.0),
        "defensive": _safe_float(policy.get("stressed_risk_multiplier"), 0.72),
        "halt": 0.0,
        "stressed": _safe_float(policy.get("stressed_risk_multiplier"), 0.72),
        "crisis": _safe_float(policy.get("crisis_risk_multiplier"), 0.35),
    }
    return mapping.get((mode or "normal").lower(), _safe_float(policy.get("normal_risk_multiplier"), 1.0))


def build_context(artifacts_dir: Path, payload: Dict[str, Any]) -> Dict[str, Any]:
    adaptive = _load_json(artifacts_dir / ADAPTIVE_POLICY_FILE, {"decisions": []})
    quality = _load_json(artifacts_dir / QUALITY_FILE, {"scores": []})
    drift = _load_json(artifacts_dir / DRIFT_FILE, {"alerts": [], "snapshots": []})
    latest_policy = _latest(adaptive.get("decisions", [])) or {}
    latest_quality = quality.get("scores", [])
    latest_drift = _latest(drift.get("alerts", [])) or {}

    quality_score = _safe_float(payload.get("execution_quality_score"), _safe_float((latest_quality[0] if latest_quality else {}).get("quality_score"), 80.0))
    strategy_score = _safe_float(payload.get("strategy_score"), 0.65)
    regime_volatility = _safe_float(payload.get("market_volatility"), _safe_float(payload.get("regime_volatility"), 0.22))
    drift_severity = _safe_float(payload.get("drift_severity"), max(
        abs(_safe_float(latest_drift.get("slippage_drift_bps"), 0.0)) / 25.0,
        abs(_safe_float(latest_drift.get("latency_drift_ms"), 0.0)) / 600.0,
        abs(_safe_float(latest_drift.get("fill_rate_delta"), 0.0)) / 0.2,
    ))
    adaptive_mode = (payload.get("adaptive_mode") or (latest_policy.get("decision") or {}).get("mode") or "normal").lower()

    if regime_volatility >= 0.60:
        regime_label = "crisis"
    elif regime_volatility >= 0.35:
        regime_label = "stressed"
    elif regime_volatility >= 0.22:
        regime_label = "elevated"
    else:
        regime_label = "stable"

    return {
        "context_id": payload.get("context_id") or f"alloc_ctx_{int(datetime.now(timezone.utc).timestamp())}",
        "timestamp": now_iso(),
        "strategy_id": payload.get("strategy_id") or "strategy_primary",
        "symbol": (payload.get("symbol") or "AAPL").upper(),
        "market_volatility": round(regime_volatility, 4),
        "regime_label": regime_label,
        "execution_quality_score": round(quality_score, 2),
        "strategy_score": round(strategy_score, 4),
        "drift_severity": round(drift_severity, 4),
        "adaptive_mode": adaptive_mode,
        "requested_capital_usd": round(_safe_float(payload.get("requested_capital_usd"), 0.0), 2),
    }


def build_status(artifacts_dir: Path) -> Dict[str, Any]:
    state = load_state(artifacts_dir)
    return {
        "allocator": state["allocator"],
        "policy": state["policy"],
        "context_count": len(state.get("contexts", [])),
        "decision_count": len(state.get("decisions", [])),
        "dispatch_count": len(state.get("dispatches", [])),
        "latest_context": _latest(state.get("contexts", [])),
        "latest_decision": _latest(state.get("decisions", [])),
        "latest_dispatch": _latest(state.get("dispatches", [])),
        "recent_decisions": state.get("decisions", [])[-10:][::-1],
    }


def update_policy(artifacts_dir: Path, payload: Dict[str, Any]) -> Dict[str, Any]:
    state = load_state(artifacts_dir)
    for key in state["policy"].keys():
        if key in payload and payload[key] is not None:
            state["policy"][key] = payload[key]
    state["allocator"]["last_updated_at"] = now_iso()
    state["history"].append({"timestamp": now_iso(), "event": "allocator.policy_updated"})
    state["history"] = state["history"][-200:]
    save_state(artifacts_dir, state)
    return {"status": "policy_updated", "policy": state["policy"]}


def ingest_context(artifacts_dir: Path, payload: Dict[str, Any]) -> Dict[str, Any]:
    state = load_state(artifacts_dir)
    context = build_context(artifacts_dir, payload)
    state.setdefault("contexts", []).append(context)
    state["allocator"]["last_context_at"] = now_iso()
    state["allocator"]["last_updated_at"] = now_iso()
    state["allocator"]["context_count"] = len(state["contexts"])
    state["allocator"].setdefault("telemetry", []).append({
        "timestamp": now_iso(),
        "event": "allocator.context_ingested",
        "strategy_id": context["strategy_id"],
        "regime": context["regime_label"],
    })
    state["allocator"]["telemetry"] = state["allocator"]["telemetry"][-100:]
    save_state(artifacts_dir, state)
    return {"status": "context_ingested", "context": context}


def decide_allocation(artifacts_dir: Path, payload: Dict[str, Any]) -> Dict[str, Any]:
    state = load_state(artifacts_dir)
    policy = state["policy"]
    context = payload.get("context") or build_context(artifacts_dir, payload)

    base_capital = max(_safe_float(policy.get("base_capital_usd"), 1000000.0), 1.0)
    min_pct = max(_safe_float(policy.get("min_allocation_pct"), 0.02), 0.0)
    max_pct = max(_safe_float(policy.get("max_allocation_pct"), 0.22), min_pct)

    regime_factor = {
        "stable": 1.0,
        "elevated": 0.88,
        "stressed": _safe_float(policy.get("stressed_risk_multiplier"), 0.72),
        "crisis": _safe_float(policy.get("crisis_risk_multiplier"), 0.35),
    }.get(context.get("regime_label"), 0.9)
    policy_mode_factor = _policy_from_adaptive_mode(context.get("adaptive_mode"), policy)
    execution_factor = max(0.15, min(1.1, _safe_float(context.get("execution_quality_score"), 80.0) / 100.0))
    strategy_factor = max(0.10, min(1.2, _safe_float(context.get("strategy_score"), 0.65)))
    drift_factor = max(0.0, 1.0 - min(1.0, _safe_float(context.get("drift_severity"), 0.0)))

    blended_score = (
        regime_factor * _safe_float(policy.get("regime_weight"), 0.30)
        + strategy_factor * _safe_float(policy.get("strategy_weight"), 0.45)
        + execution_factor * (1.0 - _safe_float(policy.get("regime_weight"), 0.30) - _safe_float(policy.get("strategy_weight"), 0.45))
    )
    target_pct = max(min_pct, min(max_pct, blended_score * policy_mode_factor * max(0.25, drift_factor)))
    reserve_buffer_pct = max(0.0, min(0.5, _safe_float(policy.get("reserve_buffer_pct"), 0.12)))
    gross_capital = round(base_capital * target_pct, 2)
    reserve_buffer_usd = round(gross_capital * reserve_buffer_pct, 2)
    deployable_capital_usd = round(max(0.0, gross_capital - reserve_buffer_usd), 2)

    halted = bool(policy.get("halt_on_severe_drift", True) and (context.get("adaptive_mode") == "halt" or _safe_float(context.get("drift_severity"), 0.0) >= 1.0))
    if halted:
        gross_capital = 0.0
        reserve_buffer_usd = 0.0
        deployable_capital_usd = 0.0
        target_pct = 0.0

    decision = {
        "allocation_id": payload.get("allocation_id") or f"alloc_{len(state.get('decisions', []))+1:04d}",
        "timestamp": now_iso(),
        "strategy_id": context["strategy_id"],
        "symbol": context["symbol"],
        "regime_label": context["regime_label"],
        "adaptive_mode": context["adaptive_mode"],
        "target_allocation_pct": round(target_pct, 4),
        "capital_base_usd": round(base_capital, 2),
        "gross_capital_usd": gross_capital,
        "reserve_buffer_usd": reserve_buffer_usd,
        "deployable_capital_usd": deployable_capital_usd,
        "execution_quality_score": context["execution_quality_score"],
        "strategy_score": context["strategy_score"],
        "drift_severity": context["drift_severity"],
        "halted": halted,
    }
    state.setdefault("decisions", []).append(decision)
    state["allocator"]["last_decision_at"] = now_iso()
    state["allocator"]["last_updated_at"] = now_iso()
    state["allocator"]["decision_count"] = len(state["decisions"])
    save_state(artifacts_dir, state)
    return {"status": "allocation_decided", "decision": decision, "context": context}


def dispatch_allocation(artifacts_dir: Path, payload: Dict[str, Any]) -> Dict[str, Any]:
    state = load_state(artifacts_dir)
    decision = payload.get("decision") or _latest(state.get("decisions", [])) or decide_allocation(artifacts_dir, payload)["decision"]
    dispatch = {
        "dispatch_id": payload.get("dispatch_id") or f"alloc_dispatch_{len(state.get('dispatches', []))+1:04d}",
        "timestamp": now_iso(),
        "allocation_id": decision.get("allocation_id"),
        "strategy_id": decision.get("strategy_id"),
        "symbol": decision.get("symbol"),
        "deployable_capital_usd": decision.get("deployable_capital_usd", 0.0),
        "halted": decision.get("halted", False),
        "status": "blocked" if decision.get("halted") else "capital_released",
    }
    state.setdefault("dispatches", []).append(dispatch)
    state["allocator"]["last_dispatch_at"] = now_iso()
    state["allocator"]["last_updated_at"] = now_iso()
    state["allocator"]["dispatch_count"] = len(state["dispatches"])
    save_state(artifacts_dir, state)
    return {"status": "allocation_dispatched", "dispatch": dispatch, "decision": decision}
