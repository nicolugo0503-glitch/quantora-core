import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

STATE_FILE_NAME = "strategy_factory.json"


def now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def default_state():
    return {
        "strategy_factory": {
            "enabled": True,
            "last_updated_at": None,
            "last_generation_at": None,
            "last_backtest_at": None,
            "last_promotion_at": None,
            "factory_cycles": 0,
            "templates_count": 0,
            "candidates_count": 0,
            "promoted_count": 0,
            "rejected_count": 0,
            "telemetry": [],
        },
        "templates": [],
        "candidates": [],
        "promoted_strategies": [],
        "routing": {
            "default_market": "equities",
            "promotion_score_threshold": 67.5,
            "min_backtest_win_rate": 0.54,
            "min_edge_score": 58.0,
            "max_live_risk_budget_pct": 2.0,
            "auto_promote": False,
        },
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
    for k, v in default_state()["strategy_factory"].items():
        merged["strategy_factory"].setdefault(k, v)
    for k, v in default_state()["routing"].items():
        merged["routing"].setdefault(k, v)
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


def _score_candidate(candidate):
    sharpe = _safe_float(candidate.get("backtest_sharpe"), 0.0)
    win_rate = _safe_float(candidate.get("backtest_win_rate"), 0.5)
    pnl = _safe_float(candidate.get("backtest_pnl"), 0.0)
    drawdown = max(_safe_float(candidate.get("max_drawdown"), 0.0), 0.0)
    edge = _safe_float(candidate.get("edge_score"), 50.0)
    regime_fit = _safe_float(candidate.get("regime_fit"), 0.5)
    stability = _safe_float(candidate.get("stability_score"), 50.0)
    novelty = _safe_float(candidate.get("novelty_score"), 50.0)
    base = sharpe * 16.0 + win_rate * 100 * 0.24 + edge * 0.26 + regime_fit * 100 * 0.12 + stability * 0.12 + novelty * 0.10 + pnl * 0.002
    penalty = drawdown * 0.65
    return round(base - penalty, 2)


def build_status(artifacts_dir: Path):
    state = load_state(artifacts_dir)
    return {
        "strategy_factory": state["strategy_factory"],
        "routing": state["routing"],
        "template_count": len(state.get("templates", [])),
        "candidate_count": len(state.get("candidates", [])),
        "promoted_count": len(state.get("promoted_strategies", [])),
        "top_candidates": sorted(
            [
                {
                    "candidate_id": c.get("candidate_id"),
                    "strategy_name": c.get("strategy_name"),
                    "promotion_score": c.get("promotion_score", _score_candidate(c)),
                    "status": c.get("status", "generated"),
                    "market": c.get("market", "equities"),
                }
                for c in state.get("candidates", [])
            ],
            key=lambda x: x["promotion_score"],
            reverse=True,
        )[:8],
    }


def upsert_templates(artifacts_dir: Path, payload: dict):
    state = load_state(artifacts_dir)
    templates = state.get("templates", [])
    for item in payload.get("templates", []):
        template_id = item.get("template_id") or f"template_{len(templates)+1:03d}"
        item["template_id"] = template_id
        item["name"] = item.get("name") or template_id
        item["market"] = (item.get("market") or state["routing"]["default_market"]).lower()
        item["signal_family"] = item.get("signal_family") or "momentum"
        item["timeframe"] = item.get("timeframe") or "1h"
        item["mutation_bias"] = item.get("mutation_bias") or "balanced"
        existing = next((x for x in templates if x.get("template_id") == template_id), None)
        if existing:
            existing.update(item)
        else:
            templates.append(item)
    state["templates"] = templates
    state["strategy_factory"]["templates_count"] = len(templates)
    state["strategy_factory"]["last_updated_at"] = now_iso()
    state["history"].append({"timestamp": now_iso(), "event": "templates.upserted", "count": len(payload.get("templates", []))})
    state["history"] = state["history"][-100:]
    save_state(artifacts_dir, state)
    return {"status": "templates_upserted", "template_count": len(templates)}


def generate_candidates(artifacts_dir: Path, payload: dict):
    state = load_state(artifacts_dir)
    routing = state["routing"]
    for key in ["default_market", "promotion_score_threshold", "min_backtest_win_rate", "min_edge_score", "max_live_risk_budget_pct", "auto_promote"]:
        if key in payload and payload[key] is not None:
            routing[key] = payload[key]

    templates = state.get("templates", [])
    batch_size = max(int(payload.get("batch_size") or 3), 1)
    generated = []
    start_index = len(state.get("candidates", [])) + 1

    for idx in range(batch_size):
        template = templates[idx % len(templates)] if templates else {
            "template_id": "template_default",
            "name": "Default Momentum Template",
            "market": routing["default_market"],
            "signal_family": "momentum",
            "timeframe": "1h",
            "mutation_bias": "balanced",
        }
        mutation_bias = template.get("mutation_bias", "balanced")
        novelty_boost = {"conservative": 48.0, "balanced": 56.0, "aggressive": 68.0}.get(mutation_bias, 55.0)
        edge_score = 54.0 + idx * 4.0 + (6.0 if template.get("signal_family") in ("mean_reversion", "stat_arb") else 3.0)
        candidate = {
            "candidate_id": f"cand_{start_index + idx:04d}",
            "template_id": template.get("template_id"),
            "strategy_name": f"{template.get('name')} Variant {idx+1}",
            "market": template.get("market", routing["default_market"]),
            "signal_family": template.get("signal_family", "momentum"),
            "timeframe": template.get("timeframe", "1h"),
            "generation_mode": payload.get("generation_mode") or "mutation",
            "backtest_sharpe": round(1.05 + idx * 0.22, 2),
            "backtest_win_rate": round(0.53 + idx * 0.018, 3),
            "backtest_pnl": round(12500 + idx * 3400, 2),
            "max_drawdown": round(8.5 + idx * 1.4, 2),
            "edge_score": round(edge_score, 2),
            "regime_fit": round(0.57 + idx * 0.05, 3),
            "stability_score": round(61 + idx * 5.5, 2),
            "novelty_score": round(novelty_boost + idx * 3.0, 2),
            "risk_budget_pct": round(min(routing["max_live_risk_budget_pct"], 0.6 + idx * 0.35), 2),
            "status": "generated",
            "generated_at": now_iso(),
        }
        candidate["promotion_score"] = _score_candidate(candidate)
        generated.append(candidate)

    state.setdefault("candidates", []).extend(generated)
    state["strategy_factory"]["last_generation_at"] = now_iso()
    state["strategy_factory"]["factory_cycles"] += 1
    state["strategy_factory"]["candidates_count"] = len(state["candidates"])
    state["strategy_factory"]["last_updated_at"] = now_iso()
    state["strategy_factory"]["telemetry"].append({
        "timestamp": now_iso(),
        "event": "candidates.generated",
        "count": len(generated),
        "generation_mode": payload.get("generation_mode") or "mutation",
    })
    state["strategy_factory"]["telemetry"] = state["strategy_factory"]["telemetry"][-50:]
    state["history"].append({"timestamp": now_iso(), "event": "candidates.generated", "count": len(generated)})
    state["history"] = state["history"][-100:]
    save_state(artifacts_dir, state)
    return {"status": "candidates_generated", "generated": generated, "candidate_count": len(state["candidates"])}


def backtest_candidates(artifacts_dir: Path, payload: dict):
    state = load_state(artifacts_dir)
    routing = state["routing"]
    candidate_ids = set(payload.get("candidate_ids") or [])
    evaluated = []
    for c in state.get("candidates", []):
        if candidate_ids and c.get("candidate_id") not in candidate_ids:
            continue
        c["backtest_status"] = "passed" if (
            _safe_float(c.get("backtest_win_rate"), 0.0) >= _safe_float(routing.get("min_backtest_win_rate"), 0.54)
            and _safe_float(c.get("edge_score"), 0.0) >= _safe_float(routing.get("min_edge_score"), 58.0)
        ) else "failed"
        c["promotion_score"] = _score_candidate(c)
        c["status"] = "backtested"
        evaluated.append({
            "candidate_id": c.get("candidate_id"),
            "strategy_name": c.get("strategy_name"),
            "backtest_status": c.get("backtest_status"),
            "promotion_score": c.get("promotion_score"),
        })
    state["strategy_factory"]["last_backtest_at"] = now_iso()
    state["strategy_factory"]["last_updated_at"] = now_iso()
    state["history"].append({"timestamp": now_iso(), "event": "candidates.backtested", "count": len(evaluated)})
    state["history"] = state["history"][-100:]
    save_state(artifacts_dir, state)
    return {"status": "candidates_backtested", "evaluated": evaluated}


def promote_candidates(artifacts_dir: Path, payload: dict):
    state = load_state(artifacts_dir)
    routing = state["routing"]
    threshold = _safe_float(payload.get("promotion_score_threshold"), routing.get("promotion_score_threshold"))
    promoted = []
    rejected = []
    for c in state.get("candidates", []):
        if c.get("status") not in ("backtested", "generated"):
            continue
        score = _safe_float(c.get("promotion_score"), _score_candidate(c))
        passed = c.get("backtest_status") == "passed" and score >= threshold
        if passed:
            c["status"] = "promoted"
            promoted_strategy = {
                "strategy_id": f"auto_{c.get('candidate_id')}",
                "strategy_name": c.get("strategy_name"),
                "market": c.get("market"),
                "signal_family": c.get("signal_family"),
                "timeframe": c.get("timeframe"),
                "risk_budget_pct": c.get("risk_budget_pct"),
                "promotion_score": score,
                "promoted_at": now_iso(),
            }
            promoted.append(promoted_strategy)
        else:
            c["status"] = "rejected"
            rejected.append({
                "candidate_id": c.get("candidate_id"),
                "strategy_name": c.get("strategy_name"),
                "promotion_score": score,
            })
    existing_ids = {p.get("strategy_id") for p in state.get("promoted_strategies", [])}
    for item in promoted:
        if item["strategy_id"] not in existing_ids:
            state.setdefault("promoted_strategies", []).append(item)
            existing_ids.add(item["strategy_id"])
    state["strategy_factory"]["last_promotion_at"] = now_iso()
    state["strategy_factory"]["last_updated_at"] = now_iso()
    state["strategy_factory"]["promoted_count"] = len(state.get("promoted_strategies", []))
    state["strategy_factory"]["rejected_count"] = len([c for c in state.get("candidates", []) if c.get("status") == "rejected"])
    state["strategy_factory"]["telemetry"].append({
        "timestamp": now_iso(),
        "event": "candidates.promoted",
        "promoted": len(promoted),
        "rejected": len(rejected),
    })
    state["strategy_factory"]["telemetry"] = state["strategy_factory"]["telemetry"][-50:]
    state["history"].append({"timestamp": now_iso(), "event": "candidates.promoted", "promoted": len(promoted), "rejected": len(rejected)})
    state["history"] = state["history"][-100:]
    save_state(artifacts_dir, state)
    return {
        "status": "promotion_completed",
        "promoted": promoted,
        "rejected": rejected[:10],
        "promoted_count": len(promoted),
    }
