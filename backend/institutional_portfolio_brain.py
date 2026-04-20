import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

STATE_FILE_NAME = "institutional_portfolio_brain.json"


def now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def default_state():
    return {
        "portfolio_brain": {
            "enabled": True,
            "last_updated_at": None,
            "last_coordination_at": None,
            "last_allocator_sync_at": None,
            "last_regime_tag": "neutral",
            "coordination_cycles": 0,
            "active_overlays": 0,
            "cross_strategy_conflicts": 0,
            "capital_rotation_score": 0.0,
            "diversification_score": 50.0,
            "telemetry": [],
        },
        "strategies": [],
        "coordination": {
            "max_active_strategies": 6,
            "max_symbol_overlap": 2,
            "conflict_penalty": 12.5,
            "rotation_threshold": 65.0,
            "min_diversification_score": 45.0,
            "auto_pause_on_conflict": True,
        },
        "allocations": [],
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
        state = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        state = default_state()
    merged = default_state()
    merged.update({k: v for k, v in state.items() if k in merged})
    for key, value in default_state()["portfolio_brain"].items():
        merged["portfolio_brain"].setdefault(key, value)
    for key, value in default_state()["coordination"].items():
        merged["coordination"].setdefault(key, value)
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


def strategy_score(item):
    realized = _safe_float(item.get("realized_pnl"))
    unrealized = _safe_float(item.get("unrealized_pnl"))
    win_rate = _safe_float(item.get("win_rate"), 0.5)
    confidence = _safe_float(item.get("confidence"), 0.5)
    volatility = max(_safe_float(item.get("volatility"), 0.2), 0.01)
    activity = max(_safe_int(item.get("activity"), 1), 1)
    regime_fit = _safe_float(item.get("regime_fit"), 0.5)
    base = (realized * 0.28) + (unrealized * 0.12) + (win_rate * 100 * 0.26) + (confidence * 100 * 0.18) + (regime_fit * 100 * 0.16)
    penalty = volatility * 14 + max(0, activity - 25) * 0.1
    return round(base - penalty, 2)


def build_status(artifacts_dir: Path):
    state = load_state(artifacts_dir)
    pb = state["portfolio_brain"]
    strategies = state.get("strategies", [])
    allocations = state.get("allocations", [])
    active = [s for s in strategies if s.get("status", "active").lower() == "active"]
    conflicts = [s for s in strategies if s.get("coordination_flag") not in (None, "", "clear")]
    return {
        "portfolio_brain": pb,
        "coordination": state.get("coordination", {}),
        "strategy_count": len(strategies),
        "active_strategy_count": len(active),
        "allocation_count": len(allocations),
        "cross_strategy_conflicts": len(conflicts),
        "top_strategies": sorted(
            [
                {
                    "strategy_id": s.get("strategy_id"),
                    "strategy_name": s.get("strategy_name"),
                    "score": s.get("score", strategy_score(s)),
                    "allocation_pct": s.get("allocation_pct", 0.0),
                    "market": s.get("market", "equities"),
                }
                for s in strategies
            ],
            key=lambda x: x["score"],
            reverse=True,
        )[:5],
    }


def ingest_snapshot(artifacts_dir: Path, payload):
    state = load_state(artifacts_dir)
    strategies = []
    for idx, item in enumerate(payload.get("strategies", []), start=1):
        s = deepcopy(item)
        s["strategy_id"] = s.get("strategy_id") or f"strat_{idx:03d}"
        s["strategy_name"] = s.get("strategy_name") or s["strategy_id"]
        s["market"] = (s.get("market") or "equities").lower()
        s["symbols"] = s.get("symbols") or []
        s["score"] = strategy_score(s)
        s["status"] = (s.get("status") or "active").lower()
        s["coordination_flag"] = "clear"
        strategies.append(s)
    state["strategies"] = strategies
    state["portfolio_brain"]["last_updated_at"] = now_iso()
    state["portfolio_brain"]["last_regime_tag"] = payload.get("regime_tag") or state["portfolio_brain"]["last_regime_tag"]
    state["history"].append({"timestamp": now_iso(), "event": "snapshot.ingested", "strategy_count": len(strategies)})
    state["history"] = state["history"][-100:]
    save_state(artifacts_dir, state)
    return {"status": "ingested", "strategy_count": len(strategies), "regime_tag": state["portfolio_brain"]["last_regime_tag"]}


def evaluate_coordination(artifacts_dir: Path, payload):
    state = load_state(artifacts_dir)
    coord = state["coordination"]
    for key in ["max_active_strategies", "max_symbol_overlap", "conflict_penalty", "rotation_threshold", "min_diversification_score", "auto_pause_on_conflict"]:
        if key in payload and payload[key] is not None:
            coord[key] = payload[key]
    strategies = state.get("strategies", [])
    symbol_map = {}
    market_counts = {}
    for s in strategies:
        for sym in s.get("symbols", []):
            symbol_map.setdefault(sym.upper(), []).append(s["strategy_id"])
        market_counts[s.get("market", "equities")] = market_counts.get(s.get("market", "equities"), 0) + 1

    conflicts = []
    for s in strategies:
        overlap_count = 0
        overlap_symbols = []
        for sym in s.get("symbols", []):
            ids = symbol_map.get(sym.upper(), [])
            if len(ids) > coord["max_symbol_overlap"]:
                overlap_count += len(ids) - 1
                overlap_symbols.append(sym.upper())
        flag = "clear"
        adjusted_score = s.get("score", strategy_score(s))
        if overlap_count > 0:
            adjusted_score -= overlap_count * float(coord["conflict_penalty"])
            flag = "overlap_conflict"
        s["coordination_flag"] = flag
        s["adjusted_score"] = round(adjusted_score, 2)
        if overlap_symbols:
            conflicts.append({
                "strategy_id": s["strategy_id"],
                "strategy_name": s["strategy_name"],
                "symbols": sorted(set(overlap_symbols)),
                "adjusted_score": s["adjusted_score"],
            })

    ranked = sorted(strategies, key=lambda x: x.get("adjusted_score", x.get("score", 0.0)), reverse=True)
    winners = ranked[: max(int(coord["max_active_strategies"]), 1)]
    winner_ids = {w["strategy_id"] for w in winners}
    total_positive = sum(max(w.get("adjusted_score", 0.0), 1.0) for w in winners) or 1.0
    allocations = []
    for s in ranked:
        recommended = "active" if s["strategy_id"] in winner_ids else "bench"
        if s.get("coordination_flag") == "overlap_conflict" and coord.get("auto_pause_on_conflict") and s["strategy_id"] not in winner_ids:
            recommended = "paused"
        alloc_pct = round((max(s.get("adjusted_score", 0.0), 0.0) / total_positive) * 100.0, 2) if s["strategy_id"] in winner_ids else 0.0
        s["recommended_state"] = recommended
        s["allocation_pct"] = alloc_pct
        allocations.append({
            "strategy_id": s["strategy_id"],
            "strategy_name": s["strategy_name"],
            "recommended_state": recommended,
            "allocation_pct": alloc_pct,
            "adjusted_score": s.get("adjusted_score", s.get("score", 0.0)),
            "market": s.get("market", "equities"),
        })

    used_markets = {a["market"] for a in allocations if a["allocation_pct"] > 0}
    diversification_score = round(min(100.0, 30.0 + len(used_markets) * 18.0 + max(0, len(winner_ids) - len(conflicts)) * 4.0), 2)
    capital_rotation_score = round(sum(a["allocation_pct"] for a in allocations if a["recommended_state"] == "active"), 2)

    pb = state["portfolio_brain"]
    pb["last_coordination_at"] = now_iso()
    pb["coordination_cycles"] += 1
    pb["cross_strategy_conflicts"] = len(conflicts)
    pb["active_overlays"] = len(winner_ids)
    pb["capital_rotation_score"] = capital_rotation_score
    pb["diversification_score"] = diversification_score
    pb["telemetry"].append({
        "timestamp": now_iso(),
        "event": "coordination.evaluated",
        "active_overlays": len(winner_ids),
        "conflict_count": len(conflicts),
        "diversification_score": diversification_score,
    })
    pb["telemetry"] = pb["telemetry"][-50:]
    state["allocations"] = allocations
    state["history"].append({"timestamp": now_iso(), "event": "coordination.completed", "active_count": len(winner_ids), "conflicts": len(conflicts)})
    state["history"] = state["history"][-100:]
    save_state(artifacts_dir, state)
    return {
        "status": "coordinated",
        "coordination": coord,
        "portfolio_brain": pb,
        "conflicts": conflicts,
        "allocations": allocations,
        "top_active": [a for a in allocations if a["recommended_state"] == "active"][:5],
    }


def sync_allocator(artifacts_dir: Path, payload):
    state = load_state(artifacts_dir)
    total_capital = _safe_float(payload.get("total_capital"), 100000.0)
    reserve_pct = max(0.0, min(0.9, _safe_float(payload.get("reserve_pct"), 0.1)))
    deployable = round(total_capital * (1.0 - reserve_pct), 2)
    applied = []
    for a in state.get("allocations", []):
        notional = round(deployable * (a.get("allocation_pct", 0.0) / 100.0), 2)
        applied.append({
            **a,
            "recommended_notional": notional,
            "reserve_pct": round(reserve_pct * 100.0, 2),
        })
    state["allocations"] = applied
    state["portfolio_brain"]["last_allocator_sync_at"] = now_iso()
    state["history"].append({
        "timestamp": now_iso(),
        "event": "allocator.synced",
        "total_capital": total_capital,
        "deployable_capital": deployable,
    })
    state["history"] = state["history"][-100:]
    save_state(artifacts_dir, state)
    return {
        "status": "allocator_synced",
        "total_capital": total_capital,
        "deployable_capital": deployable,
        "reserve_pct": round(reserve_pct * 100.0, 2),
        "allocations": applied,
    }
