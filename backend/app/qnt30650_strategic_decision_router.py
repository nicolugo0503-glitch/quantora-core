from fastapi import APIRouter, Body, HTTPException
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import time

router = APIRouter(tags=["strategic-decision-layer"])

PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
DECISION_DIR = ARTIFACTS_DIR / "strategic_decision_layer"


def _mu():
    from backend.app import qnt30557_multi_user_router as mu
    return mu


def _allocation():
    from backend.app import qnt30630_allocation_engine_router as allocation
    return allocation


def _performance():
    from backend.app import qnt30628_performance_engine_router as performance
    return performance


def _pipeline():
    from backend.app import qnt30621_pipeline_router as pipeline
    return pipeline


def _ledger():
    from backend.app import qnt30624_capital_ledger_router as ledger
    return ledger


def _safe(v: str) -> str:
    return hashlib.sha256((v or "").strip().lower().encode("utf-8")).hexdigest()[:24]


def _path(email: str) -> Path:
    DECISION_DIR.mkdir(parents=True, exist_ok=True)
    return DECISION_DIR / f"{_safe(email)}.json"


def _require_user():
    return _mu()._require_session()


def _now_ts() -> int:
    return int(time.time())


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _round_money(v) -> float:
    return round(float(v or 0.0), 2)


def _round_pct(v) -> float:
    return round(float(v or 0.0), 4)


def _load(email: str) -> dict:
    path = _path(email)
    if not path.exists():
        data = {
            "email": email,
            "policy": {
                "product_scale_score": 70.0,
                "product_retire_score": 38.0,
                "high_confidence_threshold": 82.0,
                "distribution_priority_floor": 55.0,
                "max_directives": 5,
            },
            "runs": [],
            "created_at": _now_ts(),
            "updated_at": _now_ts(),
        }
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return data
    return json.loads(path.read_text(encoding="utf-8"))


def _save(email: str, data: dict) -> dict:
    data["updated_at"] = _now_ts()
    _path(email).write_text(json.dumps(data, indent=2), encoding="utf-8")
    return data


def _fallback_strategy_rows(email: str):
    live = _performance()._live_summary(email)
    rows = []
    for item in live.get("strategy_breakdown", []) or []:
        ret = float(item.get("return_pct") or 0.0)
        vol = float(item.get("volatility_pct") or 0.0)
        score = max(min(50.0 + ret * 1.8 - max(vol - 12.0, 0.0) * 0.5, 100.0), 0.0)
        rows.append({
            "strategy_id": (str(item.get("strategy") or "core").lower().replace(" ", "_")),
            "strategy_name": item.get("strategy") or "Core",
            "score": _round_pct(score),
            "status": "eligible" if score >= 45.0 else "blocked",
            "invested_capital": _round_money(item.get("invested_capital") or 0.0),
            "pnl_amount": _round_money(item.get("pnl_amount") or 0.0),
            "return_pct": _round_pct(ret),
            "volatility_pct": _round_pct(vol),
            "exposure_pct": _round_pct(item.get("exposure_pct") or 0.0),
            "trade_count": int(item.get("position_count") or 0),
            "reasons": ["performance-derived fallback scoring"],
            "blocked_reasons": [] if score >= 45.0 else ["score below operating floor"],
        })
    rows.sort(key=lambda x: (x.get("status") != "eligible", -(x.get("score") or 0.0)))
    return rows, live


def _gather_context(email: str):
    try:
        scoreboard, live, alloc_policy = _allocation()._scoreboard(email)
    except Exception:
        scoreboard, live = _fallback_strategy_rows(email)
        alloc_policy = {}

    try:
        plan = _allocation()._build_plan(email)
    except Exception:
        plan = {
            "period": datetime.now(timezone.utc).strftime("%Y-%m"),
            "total_nav": _round_money(live.get("total_nav") or 0.0),
            "cash_reserve": _round_money((live.get("total_nav") or 0.0) * 0.10),
            "deployable_capital": _round_money((live.get("total_nav") or 0.0) * 0.90),
            "rows": [],
        }

    try:
        pipeline_summary = _pipeline().pipeline_summary()
    except Exception:
        pipeline_summary = {
            "opportunity_count": 0,
            "open_count": 0,
            "committed_count": 0,
            "total_target_amount": 0.0,
            "weighted_pipeline_amount": 0.0,
            "stage_counts": {},
            "opportunities": [],
        }

    ledger = _ledger()._load(email)
    accounts = ledger.get("accounts", []) or []
    total_nav = _round_money(sum(float(a.get("nav") or 0.0) for a in accounts))
    return scoreboard, live, alloc_policy, plan, pipeline_summary, total_nav


def _capital_directives(plan_rows, limit: int):
    directives = []
    for row in plan_rows[:limit]:
        action = (row.get("action") or "hold").upper()
        if action == "HOLD":
            continue
        reasons = []
        if float(row.get("score") or 0.0) >= 70.0:
            reasons.append("high strategic score")
        if float(row.get("target_weight_pct") or 0.0) > float(row.get("current_weight_pct") or 0.0):
            reasons.append("target weight above current weight")
        if float(row.get("return_pct") or 0.0) > 0:
            reasons.append("positive realized edge")
        if float(row.get("volatility_pct") or 0.0) <= 15.0:
            reasons.append("volatility within controlled band")
        directives.append({
            "strategy_id": row.get("strategy_id"),
            "strategy_name": row.get("strategy_name"),
            "action": action,
            "allocation_delta": _round_money(row.get("delta_capital") or 0.0),
            "target_weight_pct": _round_pct(row.get("target_weight_pct") or 0.0),
            "current_weight_pct": _round_pct(row.get("current_weight_pct") or 0.0),
            "confidence": _round_pct(min(max((float(row.get("score") or 0.0) / 100.0) * 0.92, 0.18), 0.97)),
            "reason": ", ".join(reasons[:3]) or "rebalance directive generated by allocation authority",
        })
    return directives


def _strategy_rankings(scoreboard):
    rankings = []
    for idx, row in enumerate(scoreboard[:8], start=1):
        score = float(row.get("score") or 0.0)
        action = "retain"
        if row.get("status") != "eligible" or score < 40.0:
            action = "retire"
        elif score >= 72.0:
            action = "scale"
        elif score >= 58.0:
            action = "maintain"
        else:
            action = "watch"
        rankings.append({
            "rank": idx,
            "strategy_id": row.get("strategy_id"),
            "strategy_name": row.get("strategy_name"),
            "score": _round_pct(score),
            "return_pct": _round_pct(row.get("return_pct") or 0.0),
            "volatility_pct": _round_pct(row.get("volatility_pct") or 0.0),
            "exposure_pct": _round_pct(row.get("exposure_pct") or 0.0),
            "status": row.get("status") or "watch",
            "executive_action": action,
            "rationale": (row.get("reasons") or row.get("blocked_reasons") or ["strategy review generated"])[0],
        })
    return rankings


def _product_decisions(scoreboard, pipeline_summary, policy):
    weighted_pipeline = float(pipeline_summary.get("weighted_pipeline_amount") or 0.0)
    opportunity_count = int(pipeline_summary.get("open_count") or 0)
    stage_counts = pipeline_summary.get("stage_counts") or {}
    commitment_ratio = 0.0
    total_target = float(pipeline_summary.get("total_target_amount") or 0.0)
    committed = float(stage_counts.get("committed", 0) or 0)
    if opportunity_count > 0:
        commitment_ratio = committed / max(opportunity_count, 1)
    demand_boost = min(weighted_pipeline / 250000.0, 20.0) + min(commitment_ratio * 20.0, 10.0)

    decisions = []
    for row in scoreboard[:5]:
        score = float(row.get("score") or 0.0)
        exposure = float(row.get("exposure_pct") or 0.0)
        product_score = min(max(score + demand_boost - max(exposure - 38.0, 0.0) * 0.25, 0.0), 100.0)
        action = "OBSERVE"
        if product_score >= float(policy.get("product_scale_score") or 70.0):
            action = "SCALE"
        elif product_score <= float(policy.get("product_retire_score") or 38.0):
            action = "RETIRE"
        elif score >= 55.0:
            action = "INCUBATE"
        rationale = []
        if score >= 70.0:
            rationale.append("strategy quality supports institutional packaging")
        if weighted_pipeline > 0:
            rationale.append("investor demand signal present in pipeline")
        if exposure > 38.0:
            rationale.append("distribution should manage concentration optics")
        decisions.append({
            "product_id": f"PROD_{str(row.get('strategy_id') or 'core').upper()}",
            "linked_strategy_id": row.get("strategy_id"),
            "linked_strategy_name": row.get("strategy_name"),
            "product_score": _round_pct(product_score),
            "action": action,
            "distribution_priority": "HIGH" if action == "SCALE" else ("MEDIUM" if action == "INCUBATE" else "LOW"),
            "reason": ", ".join(rationale[:3]) or "product lifecycle review generated",
        })
    return decisions


def _distribution_priorities(scoreboard, pipeline_summary, policy):
    weighted = float(pipeline_summary.get("weighted_pipeline_amount") or 0.0)
    stage_counts = pipeline_summary.get("stage_counts") or {}
    soft_circle = float(stage_counts.get("soft_commit", 0) or stage_counts.get("soft_circle", 0) or 0)
    committed = float(stage_counts.get("committed", 0) or 0)
    top_score = float((scoreboard[0] or {}).get("score") or 0.0) if scoreboard else 0.0
    base = min(top_score, 80.0)

    channels = [
        ("family_offices", base + min(weighted / 300000.0, 18.0) + soft_circle * 2.0),
        ("ria_platforms", base - 4.0 + min(weighted / 450000.0, 12.0) + committed * 1.5),
        ("institutional_allocators", base - 8.0 + committed * 4.0 + min(weighted / 600000.0, 18.0)),
        ("private_placements", 46.0 + soft_circle * 3.0 + min(weighted / 500000.0, 16.0)),
    ]
    out = []
    floor = float(policy.get("distribution_priority_floor") or 55.0)
    for channel, score in channels:
        score = min(max(score, 0.0), 100.0)
        priority = "high" if score >= max(floor + 10.0, 65.0) else ("medium" if score >= floor else "watch")
        out.append({
            "channel": channel,
            "priority": priority,
            "score": _round_pct(score),
            "recommended_focus": "activate" if priority == "high" else ("prepare" if priority == "medium" else "monitor"),
        })
    out.sort(key=lambda x: x.get("score") or 0.0, reverse=True)
    return out


def _risk_alerts(scoreboard):
    alerts = []
    for row in scoreboard[:6]:
        exposure = float(row.get("exposure_pct") or 0.0)
        vol = float(row.get("volatility_pct") or 0.0)
        if exposure >= 35.0:
            alerts.append({
                "severity": "warning",
                "type": "concentration",
                "strategy_id": row.get("strategy_id"),
                "message": f"Exposure elevated at {exposure:.2f}%.",
            })
        if vol >= 22.0:
            alerts.append({
                "severity": "warning",
                "type": "volatility",
                "strategy_id": row.get("strategy_id"),
                "message": f"Volatility regime elevated at {vol:.2f}%.",
            })
        if row.get("status") != "eligible":
            alerts.append({
                "severity": "critical",
                "type": "governance",
                "strategy_id": row.get("strategy_id"),
                "message": "; ".join((row.get("blocked_reasons") or ["allocation block active"])[:2]),
            })
    return alerts[:10]


def _confidence(scoreboard, directives, alerts):
    if not scoreboard:
        return 0.0
    avg_score = sum(float(r.get("score") or 0.0) for r in scoreboard[:5]) / max(min(len(scoreboard), 5), 1)
    directive_signal = min(len(directives) * 3.0, 12.0)
    alert_penalty = sum(10.0 if a.get("severity") == "critical" else 4.0 for a in alerts[:5])
    raw = avg_score + directive_signal - alert_penalty
    return _round_pct(min(max(raw, 0.0), 100.0))


def _operating_posture(confidence, alerts, total_nav):
    if total_nav <= 0:
        return "capitalization-pending"
    if any(a.get("severity") == "critical" for a in alerts):
        return "governed-watch"
    if confidence >= 78.0:
        return "scale-authorized"
    if confidence >= 60.0:
        return "measured-expansion"
    return "defensive-observation"


def _build_summary(email: str):
    store = _load(email)
    policy = store.get("policy") or {}
    scoreboard, live, alloc_policy, plan, pipeline_summary, total_nav = _gather_context(email)
    directives = _capital_directives(plan.get("rows") or [], int(policy.get("max_directives") or 5))
    rankings = _strategy_rankings(scoreboard)
    products = _product_decisions(scoreboard, pipeline_summary, policy)
    channels = _distribution_priorities(scoreboard, pipeline_summary, policy)
    alerts = _risk_alerts(scoreboard)
    confidence = _confidence(scoreboard, directives, alerts)
    posture = _operating_posture(confidence, alerts, total_nav)

    summary = {
        "mission": "QNT30650",
        "generated_at": _now_iso(),
        "operating_posture": posture,
        "confidence_score": confidence,
        "capital_overview": {
            "total_nav": _round_money(total_nav),
            "deployable_capital": _round_money(plan.get("deployable_capital") or 0.0),
            "cash_reserve": _round_money(plan.get("cash_reserve") or 0.0),
            "directive_count": len(directives),
        },
        "pipeline_overview": {
            "open_opportunities": int(pipeline_summary.get("open_count") or 0),
            "weighted_pipeline_amount": _round_money(pipeline_summary.get("weighted_pipeline_amount") or 0.0),
            "total_target_amount": _round_money(pipeline_summary.get("total_target_amount") or 0.0),
            "committed_count": int(pipeline_summary.get("committed_count") or 0),
        },
        "capital_directives": directives,
        "strategy_rankings": rankings,
        "product_decisions": products,
        "distribution_priorities": channels,
        "risk_alerts": alerts,
        "market_snapshot": {
            "firm_return_pct": _round_pct(live.get("return_pct") or 0.0),
            "firm_drawdown_pct": _round_pct(live.get("drawdown_pct") or 0.0),
            "firm_sharpe": _round_pct(live.get("sharpe_ratio") or 0.0),
            "active_strategies": len(live.get("strategy_breakdown", []) or []),
        },
        "allocation_policy": alloc_policy,
    }
    return summary


def _log_run(email: str, summary: dict, trigger: str):
    store = _load(email)
    run = {
        "run_id": f"sdl_{_now_ts()}",
        "trigger": trigger,
        "timestamp": _now_iso(),
        "operating_posture": summary.get("operating_posture"),
        "confidence_score": summary.get("confidence_score"),
        "directive_count": len(summary.get("capital_directives", []) or []),
        "risk_alert_count": len(summary.get("risk_alerts", []) or []),
        "capital_overview": summary.get("capital_overview") or {},
        "capital_directives": summary.get("capital_directives") or [],
        "strategy_rankings": summary.get("strategy_rankings") or [],
        "product_decisions": summary.get("product_decisions") or [],
        "distribution_priorities": summary.get("distribution_priorities") or [],
    }
    store.setdefault("runs", []).insert(0, run)
    store["runs"] = store.get("runs", [])[:100]
    _save(email, store)
    return run


@router.get("/api/strategic-decision-layer/summary")
def strategic_decision_layer_summary():
    session = _require_user()
    email = session.get("email")
    summary = _build_summary(email)
    return summary


@router.post("/api/strategic-decision-layer/run")
def strategic_decision_layer_run(payload: dict = Body(default={})):  # noqa: B008
    session = _require_user()
    email = session.get("email")
    trigger = str(payload.get("trigger") or "manual").strip() or "manual"
    summary = _build_summary(email)
    run = _log_run(email, summary, trigger)
    return {"status": "executed", "summary": summary, "run": run}


@router.get("/api/strategic-decision-layer/audit")
def strategic_decision_layer_audit():
    session = _require_user()
    email = session.get("email")
    store = _load(email)
    return {
        "mission": "QNT30650",
        "email": email,
        "run_count": len(store.get("runs", []) or []),
        "latest_run": (store.get("runs") or [None])[0],
        "runs": (store.get("runs") or [])[:25],
        "policy": store.get("policy") or {},
    }


@router.post("/api/strategic-decision-layer/policy")
def strategic_decision_layer_policy(payload: dict = Body(...)):
    session = _require_user()
    email = session.get("email")
    store = _load(email)
    policy = store.get("policy") or {}
    for key in ["product_scale_score", "product_retire_score", "high_confidence_threshold", "distribution_priority_floor", "max_directives"]:
        if key in payload:
            policy[key] = float(payload.get(key)) if key != "max_directives" else int(payload.get(key))
    store["policy"] = policy
    _save(email, store)
    return {"status": "updated", "policy": policy}
