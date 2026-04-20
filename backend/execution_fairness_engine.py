import json
from datetime import datetime, timezone
from pathlib import Path

STATE_FILE_NAME = "execution_fairness_settlement.json"


def now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def default_state():
    return {
        "fairness_engine": {
            "enabled": True,
            "last_updated_at": None,
            "last_review_at": None,
            "last_settlement_at": None,
            "review_count": 0,
            "settlement_count": 0,
            "fairness_breaches": 0,
            "total_slippage_cost": 0.0,
            "telemetry": [],
        },
        "rules": {
            "max_slippage_bps": 25.0,
            "fair_fill_deviation_bps": 15.0,
            "capital_penalty_multiplier": 1.0,
            "block_on_fairness_breach": False,
            "min_settlement_notional": 100.0,
        },
        "reviews": [],
        "settlements": [],
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
    for k, v in default_state()["fairness_engine"].items():
        merged["fairness_engine"].setdefault(k, v)
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
        "fairness_engine": state["fairness_engine"],
        "rules": state["rules"],
        "review_count": len(state.get("reviews", [])),
        "settlement_count": len(state.get("settlements", [])),
        "recent_reviews": state.get("reviews", [])[-10:][::-1],
        "recent_settlements": state.get("settlements", [])[-10:][::-1],
    }


def update_rules(artifacts_dir: Path, payload: dict):
    state = load_state(artifacts_dir)
    for key in state["rules"].keys():
        if key in payload and payload[key] is not None:
            state["rules"][key] = payload[key]
    state["fairness_engine"]["last_updated_at"] = now_iso()
    state["history"].append({"timestamp": now_iso(), "event": "fairness_rules.updated"})
    state["history"] = state["history"][-100:]
    save_state(artifacts_dir, state)
    return {"status": "rules_updated", "rules": state["rules"]}


def review_execution(artifacts_dir: Path, payload: dict):
    state = load_state(artifacts_dir)
    rules = state["rules"]

    strategy_id = payload.get("strategy_id") or "strategy_unknown"
    strategy_name = payload.get("strategy_name") or strategy_id
    expected_price = _safe_float(payload.get("expected_price"), 0.0)
    fill_price = _safe_float(payload.get("fill_price"), 0.0)
    quantity = max(_safe_float(payload.get("quantity"), 0.0), 0.0)
    side = (payload.get("side") or "buy").lower()

    if expected_price <= 0 or fill_price <= 0 or quantity <= 0:
        return {"status": "error", "message": "invalid_execution_payload"}

    slippage_bps = ((fill_price - expected_price) / expected_price) * 10000.0
    if side == "sell":
        slippage_bps = ((expected_price - fill_price) / expected_price) * 10000.0

    slippage_cost = abs(fill_price - expected_price) * quantity
    fairness_breach = abs(slippage_bps) > _safe_float(rules["fair_fill_deviation_bps"], 15.0)
    blocked = bool(rules["block_on_fairness_breach"]) and fairness_breach

    review = {
        "review_id": f"fair_{len(state.get('reviews', []))+1:04d}",
        "timestamp": now_iso(),
        "strategy_id": strategy_id,
        "strategy_name": strategy_name,
        "side": side,
        "expected_price": round(expected_price, 6),
        "fill_price": round(fill_price, 6),
        "quantity": round(quantity, 6),
        "slippage_bps": round(slippage_bps, 4),
        "slippage_cost": round(slippage_cost, 4),
        "fairness_breach": fairness_breach,
        "blocked": blocked,
    }
    state.setdefault("reviews", []).append(review)

    engine = state["fairness_engine"]
    engine["last_review_at"] = now_iso()
    engine["last_updated_at"] = now_iso()
    engine["review_count"] = len(state["reviews"])
    engine["fairness_breaches"] = len([r for r in state["reviews"] if r.get("fairness_breach")])
    engine["total_slippage_cost"] = round(sum(_safe_float(r.get("slippage_cost"), 0.0) for r in state["reviews"]), 4)
    engine["telemetry"].append({
        "timestamp": now_iso(),
        "event": "execution.reviewed",
        "strategy_id": strategy_id,
        "slippage_bps": round(slippage_bps, 4),
        "fairness_breach": fairness_breach,
    })
    engine["telemetry"] = engine["telemetry"][-50:]
    state["history"].append({"timestamp": now_iso(), "event": "execution.reviewed", "strategy_id": strategy_id})
    state["history"] = state["history"][-100:]
    save_state(artifacts_dir, state)
    return {"status": "execution_reviewed", "review": review}


def settle_capital(artifacts_dir: Path, payload: dict):
    state = load_state(artifacts_dir)
    rules = state["rules"]

    strategy_id = payload.get("strategy_id") or "strategy_unknown"
    strategy_name = payload.get("strategy_name") or strategy_id
    gross_notional = _safe_float(payload.get("gross_notional"), 0.0)
    realized_pnl = _safe_float(payload.get("realized_pnl"), 0.0)
    slippage_cost = _safe_float(payload.get("slippage_cost"), 0.0)
    fees = _safe_float(payload.get("fees"), 0.0)

    if gross_notional < _safe_float(rules["min_settlement_notional"], 100.0):
        return {"status": "error", "message": "notional_below_settlement_threshold"}

    penalty = max(slippage_cost, 0.0) * _safe_float(rules["capital_penalty_multiplier"], 1.0)
    net_settlement = realized_pnl - slippage_cost - fees - penalty

    settlement = {
        "settlement_id": f"settle_{len(state.get('settlements', []))+1:04d}",
        "timestamp": now_iso(),
        "strategy_id": strategy_id,
        "strategy_name": strategy_name,
        "gross_notional": round(gross_notional, 4),
        "realized_pnl": round(realized_pnl, 4),
        "slippage_cost": round(slippage_cost, 4),
        "fees": round(fees, 4),
        "capital_penalty": round(penalty, 4),
        "net_settlement": round(net_settlement, 4),
    }
    state.setdefault("settlements", []).append(settlement)

    engine = state["fairness_engine"]
    engine["last_settlement_at"] = now_iso()
    engine["last_updated_at"] = now_iso()
    engine["settlement_count"] = len(state["settlements"])
    engine["telemetry"].append({
        "timestamp": now_iso(),
        "event": "capital.settled",
        "strategy_id": strategy_id,
        "net_settlement": round(net_settlement, 4),
    })
    engine["telemetry"] = engine["telemetry"][-50:]
    state["history"].append({"timestamp": now_iso(), "event": "capital.settled", "strategy_id": strategy_id})
    state["history"] = state["history"][-100:]
    save_state(artifacts_dir, state)
    return {"status": "capital_settled", "settlement": settlement}
