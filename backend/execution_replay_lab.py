import json
from datetime import datetime, timezone
from pathlib import Path

STATE_FILE_NAME = "execution_replay_lab.json"


def now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def default_state():
    return {
        "replay_lab": {
            "enabled": True,
            "last_updated_at": None,
            "last_replay_at": None,
            "last_attribution_at": None,
            "replay_count": 0,
            "attribution_count": 0,
            "fill_count": 0,
            "telemetry": [],
        },
        "rules": {
            "max_replay_events": 500,
            "slippage_alert_bps": 20.0,
            "latency_alert_ms": 750.0,
            "venue_weight_enabled": True,
            "pnl_weight_enabled": True,
        },
        "replays": [],
        "attributions": [],
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
    for k, v in default_state()["replay_lab"].items():
        merged["replay_lab"].setdefault(k, v)
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
        "replay_lab": state["replay_lab"],
        "rules": state["rules"],
        "replay_count": len(state.get("replays", [])),
        "attribution_count": len(state.get("attributions", [])),
        "recent_replays": state.get("replays", [])[-10:][::-1],
        "recent_attributions": state.get("attributions", [])[-10:][::-1],
    }


def update_rules(artifacts_dir: Path, payload: dict):
    state = load_state(artifacts_dir)
    for key in state["rules"].keys():
        if key in payload and payload[key] is not None:
            state["rules"][key] = payload[key]
    state["replay_lab"]["last_updated_at"] = now_iso()
    state["history"].append({"timestamp": now_iso(), "event": "replay_rules.updated"})
    state["history"] = state["history"][-100:]
    save_state(artifacts_dir, state)
    return {"status": "rules_updated", "rules": state["rules"]}


def replay_execution(artifacts_dir: Path, payload: dict):
    state = load_state(artifacts_dir)
    events = payload.get("events", [])[: int(state["rules"]["max_replay_events"])]
    replay_id = f"replay_{len(state.get('replays', []))+1:04d}"
    total_qty = sum(_safe_float(e.get("quantity"), 0.0) for e in events)
    avg_latency = round(sum(_safe_float(e.get("latency_ms"), 0.0) for e in events) / max(len(events), 1), 2)
    avg_slippage = round(sum(_safe_float(e.get("slippage_bps"), 0.0) for e in events) / max(len(events), 1), 4)
    replay = {
        "replay_id": replay_id,
        "timestamp": now_iso(),
        "order_id": payload.get("order_id") or replay_id,
        "symbol": (payload.get("symbol") or "AAPL").upper(),
        "event_count": len(events),
        "total_quantity": round(total_qty, 4),
        "avg_latency_ms": avg_latency,
        "avg_slippage_bps": avg_slippage,
        "alerts": {
            "latency": avg_latency > _safe_float(state["rules"]["latency_alert_ms"]),
            "slippage": abs(avg_slippage) > _safe_float(state["rules"]["slippage_alert_bps"]),
        }
    }
    state.setdefault("replays", []).append(replay)
    lab = state["replay_lab"]
    lab["last_replay_at"] = now_iso()
    lab["last_updated_at"] = now_iso()
    lab["replay_count"] = len(state["replays"])
    lab["fill_count"] += len(events)
    lab["telemetry"].append({"timestamp": now_iso(), "event": "execution.replayed", "event_count": len(events)})
    lab["telemetry"] = lab["telemetry"][-50:]
    state["history"].append({"timestamp": now_iso(), "event": "execution.replayed", "event_count": len(events)})
    state["history"] = state["history"][-100:]
    save_state(artifacts_dir, state)
    return {"status": "execution_replayed", "replay": replay}


def attribute_fills(artifacts_dir: Path, payload: dict):
    state = load_state(artifacts_dir)
    fills = payload.get("fills", [])
    total_qty = sum(_safe_float(f.get("quantity"), 0.0) for f in fills)
    total_pnl = sum(_safe_float(f.get("realized_pnl"), 0.0) for f in fills)

    venue_map = {}
    for f in fills:
        venue = f.get("venue_id") or "unknown"
        venue_map.setdefault(venue, {"venue_id": venue, "quantity": 0.0, "realized_pnl": 0.0, "slippage_bps": 0.0, "count": 0})
        venue_map[venue]["quantity"] += _safe_float(f.get("quantity"), 0.0)
        venue_map[venue]["realized_pnl"] += _safe_float(f.get("realized_pnl"), 0.0)
        venue_map[venue]["slippage_bps"] += _safe_float(f.get("slippage_bps"), 0.0)
        venue_map[venue]["count"] += 1

    breakdown = []
    for venue, data in venue_map.items():
        breakdown.append({
            "venue_id": venue,
            "quantity": round(data["quantity"], 4),
            "realized_pnl": round(data["realized_pnl"], 4),
            "avg_slippage_bps": round(data["slippage_bps"] / max(data["count"], 1), 4),
            "fill_share_pct": round((data["quantity"] / max(total_qty, 0.0001)) * 100.0, 2),
        })
    breakdown.sort(key=lambda x: x["realized_pnl"], reverse=True)

    attribution = {
        "attribution_id": f"attr_{len(state.get('attributions', []))+1:04d}",
        "timestamp": now_iso(),
        "strategy_id": payload.get("strategy_id") or "strategy_unknown",
        "symbol": (payload.get("symbol") or "AAPL").upper(),
        "fill_count": len(fills),
        "total_quantity": round(total_qty, 4),
        "total_realized_pnl": round(total_pnl, 4),
        "venue_breakdown": breakdown,
    }
    state.setdefault("attributions", []).append(attribution)
    lab = state["replay_lab"]
    lab["last_attribution_at"] = now_iso()
    lab["last_updated_at"] = now_iso()
    lab["attribution_count"] = len(state["attributions"])
    lab["telemetry"].append({"timestamp": now_iso(), "event": "fills.attributed", "fill_count": len(fills)})
    lab["telemetry"] = lab["telemetry"][-50:]
    state["history"].append({"timestamp": now_iso(), "event": "fills.attributed", "fill_count": len(fills)})
    state["history"] = state["history"][-100:]
    save_state(artifacts_dir, state)
    return {"status": "fills_attributed", "attribution": attribution}
