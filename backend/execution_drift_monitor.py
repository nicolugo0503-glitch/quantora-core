import json
from datetime import datetime, timezone
from pathlib import Path

STATE_FILE_NAME = "execution_drift_monitor.json"


def now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def default_state():
    return {
        "drift_monitor": {
            "enabled": True,
            "last_updated_at": None,
            "last_snapshot_at": None,
            "last_alert_at": None,
            "snapshot_count": 0,
            "alert_count": 0,
            "regime_deviation_count": 0,
            "telemetry": [],
        },
        "rules": {
            "max_slippage_drift_bps": 8.0,
            "max_latency_drift_ms": 180.0,
            "min_fill_rate_delta": -0.06,
            "max_volatility_regime_shift": 0.18,
            "alert_on_regime_mismatch": True,
        },
        "snapshots": [],
        "alerts": [],
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
    for k, v in default_state()["drift_monitor"].items():
        merged["drift_monitor"].setdefault(k, v)
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


def build_status(artifacts_dir: Path):
    state = load_state(artifacts_dir)
    return {
        "drift_monitor": state["drift_monitor"],
        "rules": state["rules"],
        "snapshot_count": len(state.get("snapshots", [])),
        "alert_count": len(state.get("alerts", [])),
        "recent_snapshots": state.get("snapshots", [])[-10:][::-1],
        "recent_alerts": state.get("alerts", [])[-10:][::-1],
    }


def update_rules(artifacts_dir: Path, payload: dict):
    state = load_state(artifacts_dir)
    for key in state["rules"].keys():
        if key in payload and payload[key] is not None:
            state["rules"][key] = payload[key]
    state["drift_monitor"]["last_updated_at"] = now_iso()
    state["history"].append({"timestamp": now_iso(), "event": "drift_rules.updated"})
    state["history"] = state["history"][-100:]
    save_state(artifacts_dir, state)
    return {"status": "rules_updated", "rules": state["rules"]}


def capture_snapshot(artifacts_dir: Path, payload: dict):
    state = load_state(artifacts_dir)

    snapshot = {
        "snapshot_id": f"snap_{len(state.get('snapshots', []))+1:04d}",
        "timestamp": now_iso(),
        "symbol": (payload.get("symbol") or "AAPL").upper(),
        "baseline_slippage_bps": round(_safe_float(payload.get("baseline_slippage_bps"), 0.0), 4),
        "current_slippage_bps": round(_safe_float(payload.get("current_slippage_bps"), 0.0), 4),
        "baseline_latency_ms": round(_safe_float(payload.get("baseline_latency_ms"), 0.0), 2),
        "current_latency_ms": round(_safe_float(payload.get("current_latency_ms"), 0.0), 2),
        "baseline_fill_rate": round(_safe_float(payload.get("baseline_fill_rate"), 0.0), 4),
        "current_fill_rate": round(_safe_float(payload.get("current_fill_rate"), 0.0), 4),
        "baseline_regime_vol": round(_safe_float(payload.get("baseline_regime_vol"), 0.0), 4),
        "current_regime_vol": round(_safe_float(payload.get("current_regime_vol"), 0.0), 4),
    }
    state.setdefault("snapshots", []).append(snapshot)

    dm = state["drift_monitor"]
    dm["last_snapshot_at"] = now_iso()
    dm["last_updated_at"] = now_iso()
    dm["snapshot_count"] = len(state["snapshots"])
    dm["telemetry"].append({"timestamp": now_iso(), "event": "snapshot.captured", "symbol": snapshot["symbol"]})
    dm["telemetry"] = dm["telemetry"][-50:]
    state["history"].append({"timestamp": now_iso(), "event": "snapshot.captured", "symbol": snapshot["symbol"]})
    state["history"] = state["history"][-100:]
    save_state(artifacts_dir, state)
    return {"status": "snapshot_captured", "snapshot": snapshot}


def evaluate_drift(artifacts_dir: Path, payload: dict):
    state = load_state(artifacts_dir)
    rules = state["rules"]
    snapshot = payload.get("snapshot")
    if not snapshot:
        if not state.get("snapshots"):
            return {"status": "error", "message": "no_snapshot_available"}
        snapshot = state["snapshots"][-1]

    slip_drift = _safe_float(snapshot.get("current_slippage_bps")) - _safe_float(snapshot.get("baseline_slippage_bps"))
    latency_drift = _safe_float(snapshot.get("current_latency_ms")) - _safe_float(snapshot.get("baseline_latency_ms"))
    fill_delta = _safe_float(snapshot.get("current_fill_rate")) - _safe_float(snapshot.get("baseline_fill_rate"))
    regime_shift = _safe_float(snapshot.get("current_regime_vol")) - _safe_float(snapshot.get("baseline_regime_vol"))

    reasons = []
    if abs(slip_drift) > _safe_float(rules["max_slippage_drift_bps"]):
        reasons.append("slippage_drift")
    if abs(latency_drift) > _safe_float(rules["max_latency_drift_ms"]):
        reasons.append("latency_drift")
    if fill_delta < _safe_float(rules["min_fill_rate_delta"]):
        reasons.append("fill_rate_degradation")
    if abs(regime_shift) > _safe_float(rules["max_volatility_regime_shift"]) and bool(rules.get("alert_on_regime_mismatch", True)):
        reasons.append("regime_shift")

    alert = {
        "alert_id": f"alert_{len(state.get('alerts', []))+1:04d}",
        "timestamp": now_iso(),
        "symbol": snapshot.get("symbol", "AAPL"),
        "slippage_drift_bps": round(slip_drift, 4),
        "latency_drift_ms": round(latency_drift, 2),
        "fill_rate_delta": round(fill_delta, 4),
        "regime_vol_shift": round(regime_shift, 4),
        "triggered": len(reasons) > 0,
        "reasons": reasons,
    }
    state.setdefault("alerts", []).append(alert)

    dm = state["drift_monitor"]
    dm["last_alert_at"] = now_iso()
    dm["last_updated_at"] = now_iso()
    dm["alert_count"] = len([a for a in state["alerts"] if a.get("triggered")])
    dm["regime_deviation_count"] = len([a for a in state["alerts"] if "regime_shift" in a.get("reasons", [])])
    dm["telemetry"].append({"timestamp": now_iso(), "event": "drift.evaluated", "triggered": alert["triggered"]})
    dm["telemetry"] = dm["telemetry"][-50:]
    state["history"].append({"timestamp": now_iso(), "event": "drift.evaluated", "triggered": alert["triggered"]})
    state["history"] = state["history"][-100:]
    save_state(artifacts_dir, state)
    return {"status": "drift_evaluated", "alert": alert}
