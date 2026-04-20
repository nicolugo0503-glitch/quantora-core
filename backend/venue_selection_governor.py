import json
from datetime import datetime, timezone
from pathlib import Path

STATE_FILE_NAME = "venue_selection_governor.json"


def now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def default_state():
    return {
        "venue_governor": {
            "enabled": True,
            "last_updated_at": None,
            "last_policy_update_at": None,
            "last_selection_at": None,
            "selection_count": 0,
            "blocked_venues": 0,
            "fallback_count": 0,
            "telemetry": [],
        },
        "policy": {
            "mode": "adaptive",
            "max_venues": 1,
            "min_score": 65.0,
            "avoid_flagged": True,
            "fallback_enabled": True,
            "fallback_venue_id": "",
        },
        "venues": [],
        "decisions": [],
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
    for k, v in default_state()["venue_governor"].items():
        merged["venue_governor"].setdefault(k, v)
    for k, v in default_state()["policy"].items():
        merged["policy"].setdefault(k, v)
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
        "venue_governor": state["venue_governor"],
        "policy": state["policy"],
        "venue_count": len(state.get("venues", [])),
        "decision_count": len(state.get("decisions", [])),
        "venues": state.get("venues", []),
        "recent_decisions": state.get("decisions", [])[-10:][::-1],
    }


def update_policy(artifacts_dir: Path, payload: dict):
    state = load_state(artifacts_dir)
    for key in state["policy"].keys():
        if key in payload and payload[key] is not None:
            state["policy"][key] = payload[key]
    state["venue_governor"]["last_updated_at"] = now_iso()
    state["venue_governor"]["last_policy_update_at"] = now_iso()
    state["history"].append({"timestamp": now_iso(), "event": "policy.updated"})
    state["history"] = state["history"][-100:]
    save_state(artifacts_dir, state)
    return {"status": "policy_updated", "policy": state["policy"]}


def ingest_venues(artifacts_dir: Path, payload: dict):
    state = load_state(artifacts_dir)
    venues = []
    for item in payload.get("venues", []):
        venue_id = item.get("venue_id") or f"venue_{len(venues)+1:03d}"
        venues.append({
            "venue_id": venue_id,
            "venue_name": item.get("venue_name") or venue_id,
            "quality_score": round(_safe_float(item.get("quality_score"), 0.0), 2),
            "flagged": bool(item.get("flagged", False)),
            "avg_slippage_bps": round(_safe_float(item.get("avg_slippage_bps"), 0.0), 4),
            "fill_rate": round(_safe_float(item.get("fill_rate"), 0.0), 4),
            "reject_rate": round(_safe_float(item.get("reject_rate"), 0.0), 4),
            "avg_latency_ms": round(_safe_float(item.get("avg_latency_ms"), 0.0), 2),
        })
    venues.sort(key=lambda x: x["quality_score"], reverse=True)
    state["venues"] = venues
    vg = state["venue_governor"]
    vg["last_updated_at"] = now_iso()
    vg["blocked_venues"] = len([v for v in venues if v["flagged"]])
    vg["telemetry"].append({"timestamp": now_iso(), "event": "venues.ingested", "venue_count": len(venues)})
    vg["telemetry"] = vg["telemetry"][-50:]
    state["history"].append({"timestamp": now_iso(), "event": "venues.ingested", "venue_count": len(venues)})
    state["history"] = state["history"][-100:]
    save_state(artifacts_dir, state)
    return {"status": "venues_ingested", "venue_count": len(venues)}


def select_venue(artifacts_dir: Path, payload: dict):
    state = load_state(artifacts_dir)
    policy = state["policy"]
    venues = state.get("venues", [])
    filtered = []
    for v in venues:
        if policy.get("avoid_flagged", True) and v.get("flagged"):
            continue
        if _safe_float(v.get("quality_score"), 0.0) < _safe_float(policy.get("min_score"), 65.0):
            continue
        filtered.append(v)

    fallback_used = False
    reason = "highest_quality_score"
    selected = None
    if filtered:
        selected = filtered[0]
    elif policy.get("fallback_enabled", True):
        fb = policy.get("fallback_venue_id", "")
        if fb:
            selected = next((v for v in venues if v.get("venue_id") == fb), None)
        if selected is None and venues:
            selected = sorted(venues, key=lambda x: x["quality_score"], reverse=True)[0]
        fallback_used = selected is not None
        reason = "fallback_used" if selected is not None else "no_venue_available"

    decision = {
        "decision_id": f"venue_{len(state.get('decisions', []))+1:04d}",
        "timestamp": now_iso(),
        "order_id": payload.get("order_id") or f"order_{len(state.get('decisions', []))+1:04d}",
        "symbol": (payload.get("symbol") or "AAPL").upper(),
        "side": (payload.get("side") or "buy").lower(),
        "selected_venue": selected.get("venue_id") if selected else None,
        "selected_venue_name": selected.get("venue_name") if selected else None,
        "score": selected.get("quality_score") if selected else None,
        "fallback_used": fallback_used,
        "reason": reason,
        "blocked": selected is None,
    }
    state.setdefault("decisions", []).append(decision)
    vg = state["venue_governor"]
    vg["last_selection_at"] = now_iso()
    vg["last_updated_at"] = now_iso()
    vg["selection_count"] = len(state["decisions"])
    vg["fallback_count"] = len([d for d in state["decisions"] if d.get("fallback_used")])
    vg["telemetry"].append({
        "timestamp": now_iso(),
        "event": "venue.selected",
        "selected_venue": decision["selected_venue"],
        "fallback_used": fallback_used,
    })
    vg["telemetry"] = vg["telemetry"][-50:]
    state["history"].append({"timestamp": now_iso(), "event": "venue.selected", "selected_venue": decision["selected_venue"]})
    state["history"] = state["history"][-100:]
    save_state(artifacts_dir, state)
    return {"status": "venue_selected", "decision": decision}


def batch_select(artifacts_dir: Path, payload: dict):
    results = []
    for item in payload.get("orders", []):
        results.append(select_venue(artifacts_dir, item)["decision"])
    return {"status": "batch_selected", "decision_count": len(results), "decisions": results}
