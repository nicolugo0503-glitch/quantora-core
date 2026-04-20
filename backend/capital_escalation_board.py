import json
from datetime import datetime, timezone
from pathlib import Path

STATE_FILE_NAME = "capital_escalation_board.json"


def now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def default_state():
    return {
        "capital_escalation_board": {
            "enabled": True,
            "last_updated_at": None,
            "last_review_at": None,
            "last_ladder_run_at": None,
            "total_reviews": 0,
            "promotions": 0,
            "reductions": 0,
            "kills": 0,
            "telemetry": [],
        },
        "ladder_rules": {
            "sandbox_max_capital": 5000.0,
            "limited_live_max_capital": 15000.0,
            "scaled_live_max_capital": 50000.0,
            "priority_capital_max_capital": 150000.0,
            "min_promote_score": 72.0,
            "min_scaled_score": 80.0,
            "min_priority_score": 88.0,
            "degrade_score_threshold": 60.0,
            "kill_score_threshold": 45.0,
            "max_drawdown_kill_pct": 18.0,
        },
        "allocations": [],
        "reviews": [],
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
    for k, v in default_state()["capital_escalation_board"].items():
        merged["capital_escalation_board"].setdefault(k, v)
    for k, v in default_state()["ladder_rules"].items():
        merged["ladder_rules"].setdefault(k, v)
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
        "capital_escalation_board": state["capital_escalation_board"],
        "ladder_rules": state["ladder_rules"],
        "allocation_count": len(state.get("allocations", [])),
        "review_count": len(state.get("reviews", [])),
        "recent_reviews": state.get("reviews", [])[-10:][::-1],
        "recent_allocations": state.get("allocations", [])[-10:][::-1],
    }


def update_rules(artifacts_dir: Path, payload: dict):
    state = load_state(artifacts_dir)
    for key in state["ladder_rules"].keys():
        if key in payload and payload[key] is not None:
            state["ladder_rules"][key] = payload[key]
    state["capital_escalation_board"]["last_updated_at"] = now_iso()
    state["history"].append({"timestamp": now_iso(), "event": "ladder_rules.updated"})
    state["history"] = state["history"][-100:]
    save_state(artifacts_dir, state)
    return {"status": "rules_updated", "ladder_rules": state["ladder_rules"]}


def review_strategy(artifacts_dir: Path, payload: dict):
    state = load_state(artifacts_dir)
    rules = state["ladder_rules"]

    strategy_id = payload.get("strategy_id") or "strategy_unknown"
    strategy_name = payload.get("strategy_name") or strategy_id
    performance_score = _safe_float(payload.get("performance_score"), 0.0)
    win_rate = _safe_float(payload.get("win_rate"), 0.0)
    realized_pnl = _safe_float(payload.get("realized_pnl"), 0.0)
    drawdown_pct = _safe_float(payload.get("drawdown_pct"), 0.0)
    current_lane = payload.get("current_lane") or "sandbox"
    current_capital = _safe_float(payload.get("current_capital"), 0.0)

    decision = "hold"
    target_lane = current_lane
    target_capital = current_capital
    reason = "stable"

    if drawdown_pct >= _safe_float(rules["max_drawdown_kill_pct"]) or performance_score <= _safe_float(rules["kill_score_threshold"]):
        decision = "kill"
        target_lane = "blocked"
        target_capital = 0.0
        reason = "kill_threshold_breached"
    elif performance_score < _safe_float(rules["degrade_score_threshold"]):
        decision = "reduce"
        if current_lane == "priority_capital":
            target_lane = "scaled_live"
            target_capital = min(current_capital * 0.6, _safe_float(rules["scaled_live_max_capital"]))
        elif current_lane == "scaled_live":
            target_lane = "limited_live"
            target_capital = min(current_capital * 0.5, _safe_float(rules["limited_live_max_capital"]))
        elif current_lane == "limited_live":
            target_lane = "sandbox"
            target_capital = min(current_capital * 0.4, _safe_float(rules["sandbox_max_capital"]))
        else:
            target_lane = "sandbox"
            target_capital = min(current_capital * 0.5, _safe_float(rules["sandbox_max_capital"]))
        reason = "performance_decay"
    elif performance_score >= _safe_float(rules["min_priority_score"]) and win_rate >= 0.62:
        decision = "promote"
        target_lane = "priority_capital"
        target_capital = _safe_float(rules["priority_capital_max_capital"])
        reason = "priority_capital_earned"
    elif performance_score >= _safe_float(rules["min_scaled_score"]) and win_rate >= 0.58:
        decision = "promote"
        target_lane = "scaled_live"
        target_capital = _safe_float(rules["scaled_live_max_capital"])
        reason = "scaled_live_earned"
    elif performance_score >= _safe_float(rules["min_promote_score"]) and win_rate >= 0.54:
        decision = "promote"
        target_lane = "limited_live"
        target_capital = _safe_float(rules["limited_live_max_capital"])
        reason = "limited_live_earned"

    review = {
        "review_id": f"escalation_{len(state.get('reviews', []))+1:04d}",
        "timestamp": now_iso(),
        "strategy_id": strategy_id,
        "strategy_name": strategy_name,
        "performance_score": performance_score,
        "win_rate": win_rate,
        "realized_pnl": realized_pnl,
        "drawdown_pct": drawdown_pct,
        "current_lane": current_lane,
        "current_capital": current_capital,
        "decision": decision,
        "target_lane": target_lane,
        "target_capital": round(target_capital, 2),
        "reason": reason,
    }

    allocation = {
        "strategy_id": strategy_id,
        "strategy_name": strategy_name,
        "lane": target_lane,
        "allocated_capital": round(target_capital, 2),
        "updated_at": now_iso(),
        "decision": decision,
    }

    state.setdefault("reviews", []).append(review)
    existing = next((a for a in state.setdefault("allocations", []) if a.get("strategy_id") == strategy_id), None)
    if existing:
        existing.update(allocation)
    else:
        state["allocations"].append(allocation)

    board = state["capital_escalation_board"]
    board["last_review_at"] = now_iso()
    board["last_ladder_run_at"] = now_iso()
    board["last_updated_at"] = now_iso()
    board["total_reviews"] = len(state["reviews"])
    board["promotions"] = len([r for r in state["reviews"] if r.get("decision") == "promote"])
    board["reductions"] = len([r for r in state["reviews"] if r.get("decision") == "reduce"])
    board["kills"] = len([r for r in state["reviews"] if r.get("decision") == "kill"])
    board["telemetry"].append({
        "timestamp": now_iso(),
        "event": "strategy.reviewed",
        "strategy_id": strategy_id,
        "decision": decision,
        "target_lane": target_lane,
    })
    board["telemetry"] = board["telemetry"][-50:]
    state["history"].append({"timestamp": now_iso(), "event": "strategy.reviewed", "strategy_id": strategy_id, "decision": decision})
    state["history"] = state["history"][-100:]
    save_state(artifacts_dir, state)
    return {"status": "strategy_reviewed", "review": review, "allocation": allocation}


def review_batch(artifacts_dir: Path, payload: dict):
    results = [review_strategy(artifacts_dir, item) for item in payload.get("strategies", [])]
    return {
        "status": "batch_reviewed",
        "review_count": len(results),
        "promotions": len([r for r in results if r["review"]["decision"] == "promote"]),
        "reductions": len([r for r in results if r["review"]["decision"] == "reduce"]),
        "kills": len([r for r in results if r["review"]["decision"] == "kill"]),
        "results": results,
    }
