import json
from datetime import datetime, timezone
from pathlib import Path

STATE_FILE_NAME = "execution_quality_scoreboard.json"


def now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def default_state():
    return {
        "quality_scoreboard": {
            "enabled": True,
            "last_updated_at": None,
            "last_ingest_at": None,
            "last_score_refresh_at": None,
            "venue_count": 0,
            "score_count": 0,
            "accountability_flags": 0,
            "telemetry": [],
        },
        "rules": {
            "max_avg_slippage_bps": 20.0,
            "min_fill_rate": 0.9,
            "max_reject_rate": 0.08,
            "max_latency_ms": 800.0,
            "flag_score_threshold": 60.0,
        },
        "venues": [],
        "scores": [],
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
    for k, v in default_state()["quality_scoreboard"].items():
        merged["quality_scoreboard"].setdefault(k, v)
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
        "quality_scoreboard": state["quality_scoreboard"],
        "rules": state["rules"],
        "venue_count": len(state.get("venues", [])),
        "score_count": len(state.get("scores", [])),
        "top_scores": state.get("scores", [])[:10],
    }


def update_rules(artifacts_dir: Path, payload: dict):
    state = load_state(artifacts_dir)
    for key in state["rules"].keys():
        if key in payload and payload[key] is not None:
            state["rules"][key] = payload[key]
    state["quality_scoreboard"]["last_updated_at"] = now_iso()
    state["history"].append({"timestamp": now_iso(), "event": "quality_rules.updated"})
    state["history"] = state["history"][-100:]
    save_state(artifacts_dir, state)
    return {"status": "rules_updated", "rules": state["rules"]}


def ingest_venue_metrics(artifacts_dir: Path, payload: dict):
    state = load_state(artifacts_dir)
    venues = []
    for item in payload.get("venues", []):
        venue_id = item.get("venue_id") or f"venue_{len(venues)+1:03d}"
        venues.append({
            "venue_id": venue_id,
            "venue_name": item.get("venue_name") or venue_id,
            "avg_slippage_bps": round(_safe_float(item.get("avg_slippage_bps"), 0.0), 4),
            "fill_rate": round(_safe_float(item.get("fill_rate"), 0.0), 4),
            "reject_rate": round(_safe_float(item.get("reject_rate"), 0.0), 4),
            "avg_latency_ms": round(_safe_float(item.get("avg_latency_ms"), 0.0), 2),
            "orders": int(_safe_float(item.get("orders"), 0)),
        })
    state["venues"] = venues
    board = state["quality_scoreboard"]
    board["last_ingest_at"] = now_iso()
    board["last_updated_at"] = now_iso()
    board["venue_count"] = len(venues)
    board["telemetry"].append({"timestamp": now_iso(), "event": "venues.ingested", "venue_count": len(venues)})
    board["telemetry"] = board["telemetry"][-50:]
    state["history"].append({"timestamp": now_iso(), "event": "venues.ingested", "venue_count": len(venues)})
    state["history"] = state["history"][-100:]
    save_state(artifacts_dir, state)
    return {"status": "venues_ingested", "venue_count": len(venues)}


def refresh_scores(artifacts_dir: Path):
    state = load_state(artifacts_dir)
    rules = state["rules"]
    scores = []

    for v in state.get("venues", []):
        slip_penalty = max(0.0, v["avg_slippage_bps"] - _safe_float(rules["max_avg_slippage_bps"])) * 1.5
        fill_bonus = min(v["fill_rate"] / max(_safe_float(rules["min_fill_rate"]), 0.0001), 1.25) * 25.0
        reject_penalty = max(0.0, v["reject_rate"] - _safe_float(rules["max_reject_rate"])) * 250.0
        latency_penalty = max(0.0, v["avg_latency_ms"] - _safe_float(rules["max_latency_ms"])) / 20.0
        base = 75.0 + fill_bonus - slip_penalty - reject_penalty - latency_penalty
        score = round(max(0.0, min(100.0, base)), 2)
        flagged = score < _safe_float(rules["flag_score_threshold"])
        scores.append({
            "venue_id": v["venue_id"],
            "venue_name": v["venue_name"],
            "quality_score": score,
            "flagged": flagged,
            "avg_slippage_bps": v["avg_slippage_bps"],
            "fill_rate": v["fill_rate"],
            "reject_rate": v["reject_rate"],
            "avg_latency_ms": v["avg_latency_ms"],
            "orders": v["orders"],
        })

    scores.sort(key=lambda x: x["quality_score"], reverse=True)
    state["scores"] = scores
    board = state["quality_scoreboard"]
    board["last_score_refresh_at"] = now_iso()
    board["last_updated_at"] = now_iso()
    board["score_count"] = len(scores)
    board["accountability_flags"] = len([s for s in scores if s["flagged"]])
    board["telemetry"].append({"timestamp": now_iso(), "event": "scores.refreshed", "score_count": len(scores)})
    board["telemetry"] = board["telemetry"][-50:]
    state["history"].append({"timestamp": now_iso(), "event": "scores.refreshed", "score_count": len(scores)})
    state["history"] = state["history"][-100:]
    save_state(artifacts_dir, state)
    return {"status": "scores_refreshed", "scores": scores}
