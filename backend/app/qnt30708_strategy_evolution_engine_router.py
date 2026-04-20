from fastapi import APIRouter, Body, HTTPException
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import time

router = APIRouter(tags=["strategy-evolution-engine"])

PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
ENGINE_DIR = ARTIFACTS_DIR / "strategy_evolution_engine"
DEFAULT_POLICY = {
    "retain_cycles": 120,
    "retain_candidates": 120,
    "min_promotion_score": 78.0,
    "min_live_sharpe": 1.2,
    "max_live_drawdown_pct": 8.0,
    "require_recovery_clear": True,
    "require_forensic_clear": True,
    "require_release_stable": True,
    "require_operator_supervision": True,
}


def _mu():
    from backend.app import qnt30557_multi_user_router as mu
    return mu


def _release():
    from backend.app import qnt30700_institutional_release_control_router as release
    return release


def _operator():
    from backend.app import qnt30702_operator_command_console_router as operator
    return operator


def _safety():
    from backend.app import qnt30703_live_broker_safety_layer_router as safety
    return safety


def _fund_admin():
    from backend.app import qnt30705_fund_admin_control_center_router as admin
    return admin


def _forensic():
    from backend.app import qnt30706_forensic_audit_system_router as forensic
    return forensic


def _recovery():
    from backend.app import qnt30707_recovery_system_router as recovery
    return recovery


def _safe(v: str) -> str:
    return hashlib.sha256((v or "").strip().lower().encode("utf-8")).hexdigest()[:24]


def _path(email: str) -> Path:
    ENGINE_DIR.mkdir(parents=True, exist_ok=True)
    return ENGINE_DIR / f"{_safe(email)}.json"


def _require_user():
    return _mu()._require_session()


def _now_ts() -> int:
    return int(time.time())


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load(email: str) -> dict:
    path = _path(email)
    if not path.exists():
        data = {
            "email": email,
            "policy": dict(DEFAULT_POLICY),
            "cycles": [],
            "candidate_strategies": [],
            "promotion_events": [],
            "retirement_events": [],
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


def _append(store: dict, key: str, row: dict, limit: int):
    store.setdefault(key, []).insert(0, row)
    store[key] = store.get(key, [])[:limit]


def _cross_system_context(email: str) -> dict:
    release = _release()._summary_for_email(email)
    operator = _operator()._summary_for_email(email)
    safety = _safety()._summary_for_email(email)
    fund_admin = _fund_admin()._summary_for_email(email)
    forensic = _forensic()._summary_for_email(email)
    recovery = _recovery()._summary_for_email(email)
    return {
        "captured_at": _now_iso(),
        "release": {
            "active_version": release.get("active_version"),
            "stable_version": release.get("stable_version"),
            "pending_release_count": release.get("pending_release_count"),
        },
        "operator": {
            "active_mode": operator.get("active_mode"),
            "kill_switch": operator.get("kill_switch"),
            "watchlist_count": operator.get("watchlist_count"),
        },
        "safety": {
            "posture": (safety.get("safety_layer_status") or {}).get("posture"),
            "production_ready": (safety.get("safety_layer_status") or {}).get("production_ready"),
            "blocked_trade_count": safety.get("blocked_trade_count"),
            "latest_decision": safety.get("latest_decision"),
        },
        "fund_admin": {
            "readiness": (fund_admin.get("fund_admin_status") or {}).get("readiness"),
            "aum": fund_admin.get("aum"),
            "reconciliation": fund_admin.get("reconciliation"),
            "latest_close": fund_admin.get("latest_close"),
        },
        "forensic": {
            "posture": (forensic.get("forensic_status") or {}).get("posture"),
            "critical_open_count": (forensic.get("forensic_status") or {}).get("critical_open_count"),
        },
        "recovery": {
            "posture": (recovery.get("recovery_status") or {}).get("posture"),
            "safe_mode": (recovery.get("recovery_status") or {}).get("safe_mode"),
            "valid_state": (recovery.get("current_validation") or {}).get("valid_state"),
            "score": (recovery.get("current_validation") or {}).get("score"),
        },
    }


def _score_candidate(candidate: dict, ctx: dict, policy: dict) -> dict:
    live_return_pct = float(candidate.get("live_return_pct") or 0.0)
    live_sharpe = float(candidate.get("live_sharpe") or 0.0)
    drawdown_pct = float(candidate.get("max_drawdown_pct") or 0.0)
    win_rate_pct = float(candidate.get("win_rate_pct") or 0.0)
    stability_score = float(candidate.get("stability_score") or 0.0)
    coverage_score = float(candidate.get("coverage_score") or 0.0)

    score = 45.0
    score += max(-8.0, min(18.0, live_return_pct * 0.6))
    score += max(-10.0, min(18.0, (live_sharpe - 1.0) * 14.0))
    score += max(-16.0, min(8.0, (8.0 - drawdown_pct) * 1.5))
    score += max(0.0, min(8.0, (win_rate_pct - 45.0) * 0.35))
    score += max(0.0, min(8.0, stability_score * 0.08))
    score += max(0.0, min(6.0, coverage_score * 0.06))

    blockers = []
    if str((ctx.get("safety") or {}).get("posture") or "").upper() == "BLOCKED":
        blockers.append("live safety posture blocked")
        score -= 20.0
    if policy.get("require_recovery_clear") and bool((ctx.get("recovery") or {}).get("safe_mode")):
        blockers.append("recovery safe mode active")
        score -= 18.0
    if policy.get("require_recovery_clear") and not bool((ctx.get("recovery") or {}).get("valid_state")):
        blockers.append("recovery state not validated")
        score -= 16.0
    if policy.get("require_forensic_clear") and str((ctx.get("forensic") or {}).get("posture") or "").lower() == "blocked":
        blockers.append("forensic posture blocked")
        score -= 15.0
    if policy.get("require_release_stable") and int((ctx.get("release") or {}).get("pending_release_count") or 0) > 0:
        blockers.append("pending release queue not empty")
        score -= 8.0
    if policy.get("require_operator_supervision") and str((ctx.get("operator") or {}).get("active_mode") or "").lower() not in {"supervised", "normal", "active"}:
        blockers.append("operator not in supervised mode")
        score -= 8.0
    if str((ctx.get("fund_admin") or {}).get("readiness") or "").lower() == "blocked":
        blockers.append("fund admin blocked")
        score -= 12.0

    if live_sharpe < float(policy.get("min_live_sharpe") or 1.2):
        blockers.append("live sharpe below policy floor")
    if drawdown_pct > float(policy.get("max_live_drawdown_pct") or 8.0):
        blockers.append("drawdown above policy ceiling")

    score = max(0.0, round(score, 2))
    promotable = score >= float(policy.get("min_promotion_score") or 78.0) and len(blockers) == 0
    posture = "PROMOTABLE" if promotable else ("ATTENTION" if score >= 60.0 else "BLOCKED")
    return {
        "score": score,
        "posture": posture,
        "promotable": promotable,
        "blockers": blockers,
        "thresholds": {
            "min_promotion_score": float(policy.get("min_promotion_score") or 78.0),
            "min_live_sharpe": float(policy.get("min_live_sharpe") or 1.2),
            "max_live_drawdown_pct": float(policy.get("max_live_drawdown_pct") or 8.0),
        },
    }


def _summary_for_email(email: str) -> dict:
    store = _load(email)
    policy = store.get("policy") or dict(DEFAULT_POLICY)
    ctx = _cross_system_context(email)
    candidates = store.get("candidate_strategies") or []
    cycles = store.get("cycles") or []
    promotions = store.get("promotion_events") or []
    retirements = store.get("retirement_events") or []
    promotable = [c for c in candidates if ((c.get("latest_evaluation") or {}).get("promotable"))]
    blocked = [c for c in candidates if str(((c.get("latest_evaluation") or {}).get("posture") or "")).upper() == "BLOCKED"]
    engine_posture = "READY"
    blockers = []
    if bool((ctx.get("recovery") or {}).get("safe_mode")):
        engine_posture = "SAFE_MODE"
        blockers.append("recovery safe mode active")
    elif str((ctx.get("forensic") or {}).get("posture") or "").lower() == "blocked":
        engine_posture = "BLOCKED"
        blockers.append("forensic posture blocked")
    elif str((ctx.get("safety") or {}).get("posture") or "").upper() == "BLOCKED":
        engine_posture = "BLOCKED"
        blockers.append("safety posture blocked")
    elif int((ctx.get("release") or {}).get("pending_release_count") or 0) > 0:
        engine_posture = "ATTENTION"
        blockers.append("pending releases require supervision")
    return {
        "mission": "QNT30708",
        "generated_at": _now_iso(),
        "policy": policy,
        "strategy_evolution_status": {
            "posture": engine_posture,
            "blockers": blockers,
            "candidate_count": len(candidates),
            "promotable_count": len(promotable),
            "blocked_count": len(blocked),
            "cycle_count": len(cycles),
        },
        "current_context": ctx,
        "latest_cycle": cycles[0] if cycles else None,
        "latest_candidate": candidates[0] if candidates else None,
        "latest_promotion_event": promotions[0] if promotions else None,
        "latest_retirement_event": retirements[0] if retirements else None,
        "cycles": cycles[:20],
        "candidate_strategies": candidates[:20],
        "promotion_events": promotions[:20],
        "retirement_events": retirements[:20],
    }


@router.get("/api/strategy-evolution-engine/summary")
def strategy_evolution_engine_summary():
    session = _require_user()
    return _summary_for_email(session.get("email"))


@router.post("/api/strategy-evolution-engine/propose-cycle")
def strategy_evolution_engine_propose_cycle(payload: dict = Body(default=None)):
    session = _require_user()
    body = payload or {}
    email = str(body.get("email") or session.get("email"))
    name = str(body.get("name") or "").strip() or f"cycle-{_now_ts()}"
    hypotheses = body.get("hypotheses") or ["improve risk-adjusted returns", "reduce drawdown drift"]
    store = _load(email)
    policy = store.get("policy") or dict(DEFAULT_POLICY)
    ctx = _cross_system_context(email)
    cycle = {
        "cycle_id": f"evo_cycle_{_now_ts()}_{len(store.get('cycles') or []) + 1}",
        "name": name,
        "status": "proposed",
        "proposed_at": _now_iso(),
        "hypotheses": hypotheses,
        "context": ctx,
        "supervision_mode": (ctx.get("operator") or {}).get("active_mode"),
    }
    _append(store, "cycles", cycle, int(policy.get("retain_cycles") or 120))
    _save(email, store)
    return {"status": "proposed", "cycle": cycle, "summary": _summary_for_email(email)}


@router.post("/api/strategy-evolution-engine/evaluate")
def strategy_evolution_engine_evaluate(payload: dict = Body(default=None)):
    session = _require_user()
    body = payload or {}
    email = str(body.get("email") or session.get("email"))
    strategy_name = str(body.get("strategy_name") or "").strip()
    if not strategy_name:
        raise HTTPException(status_code=400, detail="strategy_name is required")
    candidate = {
        "candidate_id": f"candidate_{_now_ts()}_{int(time.time_ns() % 100000)}",
        "strategy_name": strategy_name,
        "strategy_family": str(body.get("strategy_family") or "multi-asset"),
        "live_return_pct": float(body.get("live_return_pct") or 0.0),
        "live_sharpe": float(body.get("live_sharpe") or 0.0),
        "max_drawdown_pct": float(body.get("max_drawdown_pct") or 0.0),
        "win_rate_pct": float(body.get("win_rate_pct") or 0.0),
        "stability_score": float(body.get("stability_score") or 0.0),
        "coverage_score": float(body.get("coverage_score") or 0.0),
        "notes": body.get("notes") or [],
        "evaluated_at": _now_iso(),
    }
    store = _load(email)
    policy = store.get("policy") or dict(DEFAULT_POLICY)
    ctx = _cross_system_context(email)
    evaluation = _score_candidate(candidate, ctx, policy)
    candidate["context_snapshot"] = ctx
    candidate["latest_evaluation"] = evaluation
    _append(store, "candidate_strategies", candidate, int(policy.get("retain_candidates") or 120))
    _save(email, store)
    return {"status": "evaluated", "candidate": candidate, "summary": _summary_for_email(email)}


@router.post("/api/strategy-evolution-engine/promote")
def strategy_evolution_engine_promote(payload: dict = Body(default=None)):
    session = _require_user()
    body = payload or {}
    email = str(body.get("email") or session.get("email"))
    candidate_id = str(body.get("candidate_id") or "").strip()
    action = str(body.get("action") or "promote").strip().lower()
    store = _load(email)
    candidates = store.get("candidate_strategies") or []
    candidate = next((c for c in candidates if c.get("candidate_id") == candidate_id), None)
    if not candidate:
        raise HTTPException(status_code=404, detail="candidate not found")
    latest = candidate.get("latest_evaluation") or {}
    if action == "promote":
        if not latest.get("promotable"):
            raise HTTPException(status_code=400, detail="candidate is not promotable under current policy")
        event = {
            "event_id": f"promotion_{_now_ts()}_{len(store.get('promotion_events') or []) + 1}",
            "candidate_id": candidate_id,
            "strategy_name": candidate.get("strategy_name"),
            "status": "promoted",
            "promoted_at": _now_iso(),
            "score": latest.get("score"),
            "posture": latest.get("posture"),
            "notes": body.get("notes") or [],
        }
        _append(store, "promotion_events", event, 120)
    elif action == "retire":
        event = {
            "event_id": f"retirement_{_now_ts()}_{len(store.get('retirement_events') or []) + 1}",
            "candidate_id": candidate_id,
            "strategy_name": candidate.get("strategy_name"),
            "status": "retired",
            "retired_at": _now_iso(),
            "reason": str(body.get("reason") or "risk or performance drift"),
            "score": latest.get("score"),
            "posture": latest.get("posture"),
        }
        _append(store, "retirement_events", event, 120)
    else:
        raise HTTPException(status_code=400, detail="action must be promote or retire")
    _save(email, store)
    return {"status": "processed", "action": action, "summary": _summary_for_email(email)}


@router.post("/api/strategy-evolution-engine/policy")
def strategy_evolution_engine_policy(payload: dict = Body(default=None)):
    session = _require_user()
    body = payload or {}
    email = str(body.get("email") or session.get("email"))
    store = _load(email)
    policy = store.get("policy") or dict(DEFAULT_POLICY)
    for key in DEFAULT_POLICY:
        if key in body:
            policy[key] = body[key]
    store["policy"] = policy
    _save(email, store)
    return {"status": "updated", "policy": policy, "summary": _summary_for_email(email)}


@router.post("/api/strategy-evolution-engine/bootstrap-demo")
def strategy_evolution_engine_bootstrap_demo(payload: dict = Body(default=None)):
    session = _require_user()
    body = payload or {}
    email = str(body.get("email") or session.get("email"))
    store = _load(email)
    policy = store.get("policy") or dict(DEFAULT_POLICY)
    cycle = {
        "cycle_id": f"evo_cycle_{_now_ts()}_1",
        "name": "adaptive momentum volatility refinement",
        "status": "proposed",
        "proposed_at": _now_iso(),
        "hypotheses": [
            "increase return persistence with tighter volatility targeting",
            "retire unstable sleeves before capital erosion compounds",
        ],
        "context": _cross_system_context(email),
        "supervision_mode": "supervised",
    }
    candidate = {
        "candidate_id": f"candidate_{_now_ts()}_1",
        "strategy_name": "adaptive-momentum-v2",
        "strategy_family": "futures-macro",
        "live_return_pct": 18.4,
        "live_sharpe": 1.68,
        "max_drawdown_pct": 5.4,
        "win_rate_pct": 57.0,
        "stability_score": 88.0,
        "coverage_score": 82.0,
        "notes": ["validated across regime shift", "operator-supervised release required"],
        "evaluated_at": _now_iso(),
    }
    candidate["context_snapshot"] = _cross_system_context(email)
    candidate["latest_evaluation"] = _score_candidate(candidate, candidate["context_snapshot"], policy)
    store["cycles"] = [cycle]
    store["candidate_strategies"] = [candidate]
    store["promotion_events"] = []
    store["retirement_events"] = []
    _save(email, store)
    return {"status": "bootstrapped", "summary": _summary_for_email(email)}
