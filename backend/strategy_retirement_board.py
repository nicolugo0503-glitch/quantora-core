import json
from datetime import datetime, timezone
from pathlib import Path

STATE_FILE_NAME = "strategy_retirement_board.json"


def now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def default_state():
    return {
        "retirement_board": {
            "enabled": True,
            "last_updated_at": None,
            "last_review_at": None,
            "last_reclamation_at": None,
            "total_reviews": 0,
            "retirements": 0,
            "watchlist_count": 0,
            "capital_reclaimed": 0.0,
            "telemetry": [],
        },
        "retirement_rules": {
            "retire_score_threshold": 42.0,
            "retire_drawdown_threshold": 20.0,
            "retire_loss_threshold": -10000.0,
            "watchlist_score_threshold": 55.0,
            "watchlist_drawdown_threshold": 14.0,
            "full_reclamation_on_retire": True,
            "watchlist_reclaim_pct": 0.4,
        },
        "reviews": [],
        "retired_strategies": [],
        "capital_events": [],
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
    for k, v in default_state()["retirement_board"].items():
        merged["retirement_board"].setdefault(k, v)
    for k, v in default_state()["retirement_rules"].items():
        merged["retirement_rules"].setdefault(k, v)
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
        "retirement_board": state["retirement_board"],
        "retirement_rules": state["retirement_rules"],
        "review_count": len(state.get("reviews", [])),
        "retired_count": len(state.get("retired_strategies", [])),
        "capital_event_count": len(state.get("capital_events", [])),
        "recent_reviews": state.get("reviews", [])[-10:][::-1],
        "recent_capital_events": state.get("capital_events", [])[-10:][::-1],
    }


def update_rules(artifacts_dir: Path, payload: dict):
    state = load_state(artifacts_dir)
    for key in state["retirement_rules"].keys():
        if key in payload and payload[key] is not None:
            state["retirement_rules"][key] = payload[key]
    state["retirement_board"]["last_updated_at"] = now_iso()
    state["history"].append({"timestamp": now_iso(), "event": "retirement_rules.updated"})
    state["history"] = state["history"][-100:]
    save_state(artifacts_dir, state)
    return {"status": "rules_updated", "retirement_rules": state["retirement_rules"]}


def review_strategy(artifacts_dir: Path, payload: dict):
    state = load_state(artifacts_dir)
    rules = state["retirement_rules"]

    strategy_id = payload.get("strategy_id") or "strategy_unknown"
    strategy_name = payload.get("strategy_name") or strategy_id
    performance_score = _safe_float(payload.get("performance_score"), 0.0)
    realized_pnl = _safe_float(payload.get("realized_pnl"), 0.0)
    drawdown_pct = _safe_float(payload.get("drawdown_pct"), 0.0)
    current_capital = _safe_float(payload.get("current_capital"), 0.0)
    current_lane = payload.get("current_lane") or "sandbox"

    decision = "hold"
    reclaim_capital = 0.0
    target_state = current_lane
    reason = "stable"

    if (
        performance_score <= _safe_float(rules["retire_score_threshold"])
        or drawdown_pct >= _safe_float(rules["retire_drawdown_threshold"])
        or realized_pnl <= _safe_float(rules["retire_loss_threshold"])
    ):
        decision = "retire"
        target_state = "retired"
        reclaim_capital = current_capital if bool(rules["full_reclamation_on_retire"]) else current_capital * 0.75
        reason = "retirement_threshold_breached"
    elif (
        performance_score <= _safe_float(rules["watchlist_score_threshold"])
        or drawdown_pct >= _safe_float(rules["watchlist_drawdown_threshold"])
    ):
        decision = "watchlist"
        target_state = "watchlist"
        reclaim_capital = round(current_capital * _safe_float(rules["watchlist_reclaim_pct"]), 2)
        reason = "watchlist_threshold_breached"

    review = {
        "review_id": f"ret_{len(state.get('reviews', []))+1:04d}",
        "timestamp": now_iso(),
        "strategy_id": strategy_id,
        "strategy_name": strategy_name,
        "performance_score": performance_score,
        "realized_pnl": realized_pnl,
        "drawdown_pct": drawdown_pct,
        "current_lane": current_lane,
        "current_capital": current_capital,
        "decision": decision,
        "target_state": target_state,
        "reclaim_capital": round(reclaim_capital, 2),
        "reason": reason,
    }

    state.setdefault("reviews", []).append(review)
    if decision == "retire":
        retired = {
            "strategy_id": strategy_id,
            "strategy_name": strategy_name,
            "retired_at": now_iso(),
            "last_lane": current_lane,
            "capital_reclaimed": round(reclaim_capital, 2),
            "reason": reason,
        }
        existing = next((r for r in state.setdefault("retired_strategies", []) if r.get("strategy_id") == strategy_id), None)
        if existing:
            existing.update(retired)
        else:
            state["retired_strategies"].append(retired)
    if decision in ("retire", "watchlist") and reclaim_capital > 0:
        capital_event = {
            "event_id": f"cap_{len(state.get('capital_events', []))+1:04d}",
            "timestamp": now_iso(),
            "strategy_id": strategy_id,
            "strategy_name": strategy_name,
            "decision": decision,
            "reclaimed_capital": round(reclaim_capital, 2),
        }
        state.setdefault("capital_events", []).append(capital_event)

    board = state["retirement_board"]
    board["last_review_at"] = now_iso()
    board["last_reclamation_at"] = now_iso() if reclaim_capital > 0 else board.get("last_reclamation_at")
    board["last_updated_at"] = now_iso()
    board["total_reviews"] = len(state["reviews"])
    board["retirements"] = len([r for r in state["reviews"] if r.get("decision") == "retire"])
    board["watchlist_count"] = len([r for r in state["reviews"] if r.get("decision") == "watchlist"])
    board["capital_reclaimed"] = round(sum(_safe_float(e.get("reclaimed_capital"), 0.0) for e in state.get("capital_events", [])), 2)
    board["telemetry"].append({
        "timestamp": now_iso(),
        "event": "strategy.reviewed",
        "strategy_id": strategy_id,
        "decision": decision,
        "reclaimed_capital": round(reclaim_capital, 2),
    })
    board["telemetry"] = board["telemetry"][-50:]
    state["history"].append({"timestamp": now_iso(), "event": "strategy.reviewed", "strategy_id": strategy_id, "decision": decision})
    state["history"] = state["history"][-100:]
    save_state(artifacts_dir, state)
    return {"status": "strategy_reviewed", "review": review}


def review_batch(artifacts_dir: Path, payload: dict):
    results = [review_strategy(artifacts_dir, item) for item in payload.get("strategies", [])]
    return {
        "status": "batch_reviewed",
        "review_count": len(results),
        "retirements": len([r for r in results if r["review"]["decision"] == "retire"]),
        "watchlist": len([r for r in results if r["review"]["decision"] == "watchlist"]),
        "holds": len([r for r in results if r["review"]["decision"] == "hold"]),
        "results": results,
    }
