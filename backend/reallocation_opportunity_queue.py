import json
from datetime import datetime, timezone
from pathlib import Path

STATE_FILE_NAME = "reallocation_opportunity_queue.json"


def now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def default_state():
    return {
        "reallocation_board": {
            "enabled": True,
            "last_updated_at": None,
            "last_queue_refresh_at": None,
            "last_reallocation_at": None,
            "total_candidates_ranked": 0,
            "queued_opportunities": 0,
            "approved_reallocations": 0,
            "reallocated_capital": 0.0,
            "telemetry": [],
        },
        "queue_rules": {
            "min_opportunity_score": 65.0,
            "max_queue_size": 20,
            "max_reallocation_per_candidate": 50000.0,
            "watchlist_haircut_pct": 0.5,
            "priority_bonus": 10.0,
            "validation_required": True,
        },
        "opportunities": [],
        "reallocation_events": [],
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
    for k, v in default_state()["reallocation_board"].items():
        merged["reallocation_board"].setdefault(k, v)
    for k, v in default_state()["queue_rules"].items():
        merged["queue_rules"].setdefault(k, v)
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
        "reallocation_board": state["reallocation_board"],
        "queue_rules": state["queue_rules"],
        "opportunity_count": len(state.get("opportunities", [])),
        "reallocation_event_count": len(state.get("reallocation_events", [])),
        "top_opportunities": state.get("opportunities", [])[:10],
        "recent_reallocation_events": state.get("reallocation_events", [])[-10:][::-1],
    }


def update_rules(artifacts_dir: Path, payload: dict):
    state = load_state(artifacts_dir)
    for key in state["queue_rules"].keys():
        if key in payload and payload[key] is not None:
            state["queue_rules"][key] = payload[key]
    state["reallocation_board"]["last_updated_at"] = now_iso()
    state["history"].append({"timestamp": now_iso(), "event": "queue_rules.updated"})
    state["history"] = state["history"][-100:]
    save_state(artifacts_dir, state)
    return {"status": "rules_updated", "queue_rules": state["queue_rules"]}


def refresh_queue(artifacts_dir: Path, payload: dict):
    state = load_state(artifacts_dir)
    rules = state["queue_rules"]
    candidates = payload.get("candidates", [])
    ranked = []

    for item in candidates:
        candidate_id = item.get("candidate_id") or f"cand_{len(ranked)+1:04d}"
        strategy_name = item.get("strategy_name") or candidate_id
        verdict = (item.get("verdict") or "WATCHLIST").upper()
        opportunity_score = _safe_float(item.get("opportunity_score"), 0.0)
        edge_score = _safe_float(item.get("edge_score"), 0.0)
        confidence = _safe_float(item.get("confidence"), 0.0)
        reclaimed_capital_pool = _safe_float(item.get("reclaimed_capital_pool"), 0.0)
        priority = bool(item.get("priority", False))

        adjusted_score = opportunity_score + (rules["priority_bonus"] if priority else 0.0)
        if verdict == "WATCHLIST":
            adjusted_score *= (1.0 - _safe_float(rules["watchlist_haircut_pct"], 0.5))

        if rules.get("validation_required", True) and verdict == "REJECTED":
            continue
        if adjusted_score < _safe_float(rules["min_opportunity_score"], 65.0):
            continue

        ranked.append({
            "candidate_id": candidate_id,
            "strategy_name": strategy_name,
            "verdict": verdict,
            "opportunity_score": round(opportunity_score, 2),
            "adjusted_score": round(adjusted_score, 2),
            "edge_score": round(edge_score, 2),
            "confidence": round(confidence, 4),
            "priority": priority,
            "reclaimed_capital_pool": round(reclaimed_capital_pool, 2),
        })

    ranked.sort(key=lambda x: x["adjusted_score"], reverse=True)
    ranked = ranked[: max(_safe_int(rules["max_queue_size"], 20), 1)]

    state["opportunities"] = ranked
    board = state["reallocation_board"]
    board["last_queue_refresh_at"] = now_iso()
    board["last_updated_at"] = now_iso()
    board["total_candidates_ranked"] = len(candidates)
    board["queued_opportunities"] = len(ranked)
    board["telemetry"].append({
        "timestamp": now_iso(),
        "event": "queue.refreshed",
        "queued_opportunities": len(ranked),
    })
    board["telemetry"] = board["telemetry"][-50:]
    state["history"].append({"timestamp": now_iso(), "event": "queue.refreshed", "queued_opportunities": len(ranked)})
    state["history"] = state["history"][-100:]
    save_state(artifacts_dir, state)
    return {"status": "queue_refreshed", "opportunities": ranked}


def reallocate_capital(artifacts_dir: Path, payload: dict):
    state = load_state(artifacts_dir)
    rules = state["queue_rules"]
    candidate_id = payload.get("candidate_id")
    available_capital = _safe_float(payload.get("available_capital"), 0.0)
    opp = next((o for o in state.get("opportunities", []) if o.get("candidate_id") == candidate_id), None)
    if not opp:
        return {"status": "error", "message": "candidate_not_in_queue"}

    recommended = min(
        available_capital,
        _safe_float(opp.get("reclaimed_capital_pool"), 0.0),
        _safe_float(rules.get("max_reallocation_per_candidate"), 50000.0),
    )
    event = {
        "event_id": f"realloc_{len(state.get('reallocation_events', []))+1:04d}",
        "timestamp": now_iso(),
        "candidate_id": opp["candidate_id"],
        "strategy_name": opp["strategy_name"],
        "allocated_capital": round(recommended, 2),
        "available_capital": round(available_capital, 2),
        "adjusted_score": opp["adjusted_score"],
        "verdict": opp["verdict"],
    }
    state.setdefault("reallocation_events", []).append(event)

    board = state["reallocation_board"]
    board["last_reallocation_at"] = now_iso()
    board["last_updated_at"] = now_iso()
    board["approved_reallocations"] = len(state["reallocation_events"])
    board["reallocated_capital"] = round(sum(_safe_float(e.get("allocated_capital"), 0.0) for e in state["reallocation_events"]), 2)
    board["telemetry"].append({
        "timestamp": now_iso(),
        "event": "capital.reallocated",
        "candidate_id": opp["candidate_id"],
        "allocated_capital": round(recommended, 2),
    })
    board["telemetry"] = board["telemetry"][-50:]
    state["history"].append({"timestamp": now_iso(), "event": "capital.reallocated", "candidate_id": opp["candidate_id"], "allocated_capital": round(recommended, 2)})
    state["history"] = state["history"][-100:]
    save_state(artifacts_dir, state)
    return {"status": "capital_reallocated", "reallocation_event": event}
