import json
from datetime import datetime, timezone
from pathlib import Path

STATE_FILE_NAME = "opportunity_auction_engine.json"


def now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def default_state():
    return {
        "auction_engine": {
            "enabled": True,
            "last_updated_at": None,
            "last_auction_at": None,
            "last_award_at": None,
            "auction_count": 0,
            "awarded_candidates": 0,
            "rejected_candidates": 0,
            "total_awarded_capital": 0.0,
            "telemetry": [],
        },
        "auction_rules": {
            "min_bid_score": 70.0,
            "max_winners": 3,
            "max_capital_per_winner": 60000.0,
            "priority_multiplier": 1.15,
            "confidence_multiplier_weight": 0.35,
            "edge_multiplier_weight": 0.30,
            "validation_required": True,
        },
        "bids": [],
        "awards": [],
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
    for k, v in default_state()["auction_engine"].items():
        merged["auction_engine"].setdefault(k, v)
    for k, v in default_state()["auction_rules"].items():
        merged["auction_rules"].setdefault(k, v)
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
        "auction_engine": state["auction_engine"],
        "auction_rules": state["auction_rules"],
        "bid_count": len(state.get("bids", [])),
        "award_count": len(state.get("awards", [])),
        "top_bids": state.get("bids", [])[:10],
        "recent_awards": state.get("awards", [])[-10:][::-1],
    }


def update_rules(artifacts_dir: Path, payload: dict):
    state = load_state(artifacts_dir)
    for key in state["auction_rules"].keys():
        if key in payload and payload[key] is not None:
            state["auction_rules"][key] = payload[key]
    state["auction_engine"]["last_updated_at"] = now_iso()
    state["history"].append({"timestamp": now_iso(), "event": "auction_rules.updated"})
    state["history"] = state["history"][-100:]
    save_state(artifacts_dir, state)
    return {"status": "rules_updated", "auction_rules": state["auction_rules"]}


def run_auction(artifacts_dir: Path, payload: dict):
    state = load_state(artifacts_dir)
    rules = state["auction_rules"]
    bids = []

    for item in payload.get("candidates", []):
        candidate_id = item.get("candidate_id") or f"cand_{len(bids)+1:04d}"
        strategy_name = item.get("strategy_name") or candidate_id
        verdict = (item.get("verdict") or "WATCHLIST").upper()
        base_score = _safe_float(item.get("opportunity_score"), 0.0)
        confidence = _safe_float(item.get("confidence"), 0.0)
        edge_score = _safe_float(item.get("edge_score"), 0.0)
        requested_capital = _safe_float(item.get("requested_capital"), 0.0)
        priority = bool(item.get("priority", False))

        if rules.get("validation_required", True) and verdict == "REJECTED":
            continue

        weighted = base_score
        weighted += confidence * 100.0 * _safe_float(rules["confidence_multiplier_weight"], 0.35)
        weighted += edge_score * _safe_float(rules["edge_multiplier_weight"], 0.30)
        if priority:
            weighted *= _safe_float(rules["priority_multiplier"], 1.15)

        if weighted < _safe_float(rules["min_bid_score"], 70.0):
            continue

        bids.append({
            "candidate_id": candidate_id,
            "strategy_name": strategy_name,
            "verdict": verdict,
            "priority": priority,
            "base_score": round(base_score, 2),
            "confidence": round(confidence, 4),
            "edge_score": round(edge_score, 2),
            "requested_capital": round(requested_capital, 2),
            "bid_score": round(weighted, 2),
        })

    bids.sort(key=lambda x: x["bid_score"], reverse=True)
    state["bids"] = bids

    engine = state["auction_engine"]
    engine["last_auction_at"] = now_iso()
    engine["last_updated_at"] = now_iso()
    engine["auction_count"] += 1
    engine["telemetry"].append({
        "timestamp": now_iso(),
        "event": "auction.ran",
        "bid_count": len(bids),
    })
    engine["telemetry"] = engine["telemetry"][-50:]
    state["history"].append({"timestamp": now_iso(), "event": "auction.ran", "bid_count": len(bids)})
    state["history"] = state["history"][-100:]
    save_state(artifacts_dir, state)
    return {"status": "auction_ran", "bids": bids}


def award_capital(artifacts_dir: Path, payload: dict):
    state = load_state(artifacts_dir)
    rules = state["auction_rules"]
    available_capital = _safe_float(payload.get("available_capital"), 0.0)
    winners = []
    remaining = available_capital
    max_winners = max(_safe_int(rules["max_winners"], 3), 1)

    for bid in state.get("bids", [])[:max_winners]:
        award_capital = min(
            remaining,
            _safe_float(bid.get("requested_capital"), 0.0),
            _safe_float(rules["max_capital_per_winner"], 60000.0),
        )
        if award_capital <= 0:
            continue
        winners.append({
            "award_id": f"award_{len(state.get('awards', [])) + len(winners) + 1:04d}",
            "timestamp": now_iso(),
            "candidate_id": bid["candidate_id"],
            "strategy_name": bid["strategy_name"],
            "bid_score": bid["bid_score"],
            "awarded_capital": round(award_capital, 2),
            "verdict": bid["verdict"],
        })
        remaining -= award_capital

    state.setdefault("awards", []).extend(winners)

    engine = state["auction_engine"]
    engine["last_award_at"] = now_iso()
    engine["last_updated_at"] = now_iso()
    engine["awarded_candidates"] = len(state["awards"])
    engine["rejected_candidates"] = max(0, len(state.get("bids", [])) - len(winners))
    engine["total_awarded_capital"] = round(sum(_safe_float(a.get("awarded_capital"), 0.0) for a in state["awards"]), 2)
    engine["telemetry"].append({
        "timestamp": now_iso(),
        "event": "capital.awarded",
        "winner_count": len(winners),
        "awarded_capital": round(sum(w["awarded_capital"] for w in winners), 2),
    })
    engine["telemetry"] = engine["telemetry"][-50:]
    state["history"].append({"timestamp": now_iso(), "event": "capital.awarded", "winner_count": len(winners)})
    state["history"] = state["history"][-100:]
    save_state(artifacts_dir, state)
    return {"status": "capital_awarded", "winners": winners, "remaining_capital": round(remaining, 2)}
