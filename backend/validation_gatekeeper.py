import json
from datetime import datetime, timezone
from pathlib import Path

STATE_FILE_NAME = "validation_gatekeeper.json"


def now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def default_state():
    return {
        "validation_grid": {
            "enabled": True,
            "last_updated_at": None,
            "last_validation_at": None,
            "last_promotion_review_at": None,
            "total_candidates_reviewed": 0,
            "approved_candidates": 0,
            "rejected_candidates": 0,
            "watchlist_candidates": 0,
            "telemetry": [],
        },
        "rules": {
            "min_promotion_score": 70.0,
            "min_backtest_win_rate": 0.56,
            "max_drawdown_pct": 12.0,
            "min_edge_score": 60.0,
            "min_stability_score": 62.0,
            "require_risk_budget_cap": 2.0,
            "watchlist_band": 5.0,
        },
        "reviews": [],
        "watchlist": [],
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
    for k, v in default_state()["validation_grid"].items():
        merged["validation_grid"].setdefault(k, v)
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
        "validation_grid": state["validation_grid"],
        "rules": state["rules"],
        "review_count": len(state.get("reviews", [])),
        "watchlist_count": len(state.get("watchlist", [])),
        "recent_reviews": state.get("reviews", [])[-10:][::-1],
    }


def update_rules(artifacts_dir: Path, payload: dict):
    state = load_state(artifacts_dir)
    for key in state["rules"].keys():
        if key in payload and payload[key] is not None:
            state["rules"][key] = payload[key]
    state["validation_grid"]["last_updated_at"] = now_iso()
    state["history"].append({"timestamp": now_iso(), "event": "rules.updated"})
    state["history"] = state["history"][-100:]
    save_state(artifacts_dir, state)
    return {"status": "rules_updated", "rules": state["rules"]}


def evaluate_candidate(artifacts_dir: Path, payload: dict):
    state = load_state(artifacts_dir)
    rules = state["rules"]

    candidate_id = payload.get("candidate_id") or "candidate_unknown"
    strategy_name = payload.get("strategy_name") or candidate_id
    promotion_score = _safe_float(payload.get("promotion_score"), 0.0)
    backtest_win_rate = _safe_float(payload.get("backtest_win_rate"), 0.0)
    max_drawdown = _safe_float(payload.get("max_drawdown"), 999.0)
    edge_score = _safe_float(payload.get("edge_score"), 0.0)
    stability_score = _safe_float(payload.get("stability_score"), 0.0)
    risk_budget_pct = _safe_float(payload.get("risk_budget_pct"), 99.0)

    blockers = []
    if promotion_score < _safe_float(rules["min_promotion_score"]):
        blockers.append("promotion_score_below_threshold")
    if backtest_win_rate < _safe_float(rules["min_backtest_win_rate"]):
        blockers.append("backtest_win_rate_below_threshold")
    if max_drawdown > _safe_float(rules["max_drawdown_pct"]):
        blockers.append("max_drawdown_above_limit")
    if edge_score < _safe_float(rules["min_edge_score"]):
        blockers.append("edge_score_below_threshold")
    if stability_score < _safe_float(rules["min_stability_score"]):
        blockers.append("stability_score_below_threshold")
    if risk_budget_pct > _safe_float(rules["require_risk_budget_cap"]):
        blockers.append("risk_budget_above_cap")

    verdict = "APPROVED"
    watchlist = False
    if blockers:
        # watchlist if within band and only soft blockers
        soft = {"promotion_score_below_threshold", "backtest_win_rate_below_threshold", "edge_score_below_threshold", "stability_score_below_threshold"}
        within_band = (
            promotion_score >= (_safe_float(rules["min_promotion_score"]) - _safe_float(rules["watchlist_band"])) and
            backtest_win_rate >= (_safe_float(rules["min_backtest_win_rate"]) - 0.02) and
            edge_score >= (_safe_float(rules["min_edge_score"]) - _safe_float(rules["watchlist_band"])) and
            stability_score >= (_safe_float(rules["min_stability_score"]) - _safe_float(rules["watchlist_band"]))
        )
        if within_band and all(b in soft for b in blockers):
            verdict = "WATCHLIST"
            watchlist = True
        else:
            verdict = "REJECTED"

    review = {
        "review_id": f"review_{len(state.get('reviews', []))+1:04d}",
        "timestamp": now_iso(),
        "candidate_id": candidate_id,
        "strategy_name": strategy_name,
        "promotion_score": promotion_score,
        "backtest_win_rate": backtest_win_rate,
        "max_drawdown": max_drawdown,
        "edge_score": edge_score,
        "stability_score": stability_score,
        "risk_budget_pct": risk_budget_pct,
        "verdict": verdict,
        "blockers": blockers,
    }

    state.setdefault("reviews", []).append(review)
    if watchlist:
        state.setdefault("watchlist", []).append(review)

    grid = state["validation_grid"]
    grid["last_validation_at"] = now_iso()
    grid["last_updated_at"] = now_iso()
    grid["total_candidates_reviewed"] = len(state["reviews"])
    grid["approved_candidates"] = len([r for r in state["reviews"] if r.get("verdict") == "APPROVED"])
    grid["rejected_candidates"] = len([r for r in state["reviews"] if r.get("verdict") == "REJECTED"])
    grid["watchlist_candidates"] = len([r for r in state["reviews"] if r.get("verdict") == "WATCHLIST"])
    grid["telemetry"].append({
        "timestamp": now_iso(),
        "event": "candidate.validated",
        "candidate_id": candidate_id,
        "verdict": verdict,
    })
    grid["telemetry"] = grid["telemetry"][-50:]
    state["history"].append({"timestamp": now_iso(), "event": "candidate.validated", "candidate_id": candidate_id, "verdict": verdict})
    state["history"] = state["history"][-100:]
    save_state(artifacts_dir, state)
    return {"status": "validated", "review": review}


def review_promotion_batch(artifacts_dir: Path, payload: dict):
    state = load_state(artifacts_dir)
    results = []
    for candidate in payload.get("candidates", []):
        results.append(evaluate_candidate(artifacts_dir, candidate)["review"])
    state = load_state(artifacts_dir)
    state["validation_grid"]["last_promotion_review_at"] = now_iso()
    save_state(artifacts_dir, state)
    approved = [r for r in results if r["verdict"] == "APPROVED"]
    watchlist = [r for r in results if r["verdict"] == "WATCHLIST"]
    rejected = [r for r in results if r["verdict"] == "REJECTED"]
    return {
        "status": "promotion_batch_reviewed",
        "approved_count": len(approved),
        "watchlist_count": len(watchlist),
        "rejected_count": len(rejected),
        "approved": approved,
        "watchlist": watchlist,
        "rejected": rejected,
    }
