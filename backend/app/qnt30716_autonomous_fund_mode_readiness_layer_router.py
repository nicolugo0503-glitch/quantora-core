from fastapi import APIRouter, Body, Depends
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import time

router = APIRouter(tags=["autonomous-fund-mode-readiness-layer"])

PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
ENGINE_DIR = ARTIFACTS_DIR / "autonomous_fund_mode_readiness_layer"
DEFAULT_POLICY = {
    "retain_runs": 180,
    "minimum_readiness_score": 86.0,
    "minimum_autonomy_governance_score": 84.0,
    "minimum_strategy_score": 78.0,
    "minimum_liquidity_score": 80.0,
    "minimum_regime_score": 78.0,
    "minimum_defense_score": 80.0,
    "maximum_open_exceptions": 1,
    "require_operator_clear": True,
    "require_release_clear": True,
    "require_recovery_clear": True,
    "require_fund_admin_ready": True,
    "require_reporting_approved": True,
    "require_transparency_approved": True,
}


def _mu():
    from backend.app import qnt30557_multi_user_router as mu
    return mu


def _operator():
    from backend.app import qnt30702_operator_command_console_router as operator
    return operator


def _release():
    from backend.app import qnt30700_institutional_release_control_router as release
    return release


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


def _strategy():
    from backend.app import qnt30708_strategy_evolution_engine_router as strategy
    return strategy


def _liquidity():
    from backend.app import qnt30709_liquidity_intelligence_system_router as liquidity
    return liquidity


def _regime():
    from backend.app import qnt30710_market_regime_intelligence_system_router as regime
    return regime


def _rotation():
    from backend.app import qnt30711_capital_rotation_command_system_router as rotation
    return rotation


def _defense():
    from backend.app import qnt30712_defensive_systems_command_layer_router as defense
    return defense


def _autonomy():
    from backend.app import qnt30713_autonomous_allocation_governance_layer_router as autonomy
    return autonomy


def _transparency():
    from backend.app import qnt30714_investor_transparency_engine_router as transparency
    return transparency


def _reporting():
    from backend.app import qnt30715_reporting_disclosure_automation_layer_router as reporting
    return reporting


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
            "runs": [],
            "exceptions": [],
            "readiness_book": [],
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
    operator = _operator()._summary_for_email(email)
    release = _release()._summary_for_email(email)
    safety = _safety()._summary_for_email(email)
    admin = _fund_admin()._summary_for_email(email)
    forensic = _forensic()._summary_for_email(email)
    recovery = _recovery()._summary_for_email(email)
    strategy = _strategy()._summary_for_email(email)
    liquidity = _liquidity()._summary_for_email(email)
    regime = _regime()._summary_for_email(email)
    rotation = _rotation()._summary_for_email(email)
    defense = _defense()._summary_for_email(email)
    autonomy = _autonomy()._summary_for_email(email)
    transparency = _transparency()._summary_for_email(email)
    reporting = _reporting()._summary_for_email(email)
    return {
        "captured_at": _now_iso(),
        "operator": {
            "posture": (operator.get("operator_console_status") or {}).get("posture"),
            "override_required": bool((operator.get("operator_console_status") or {}).get("override_required", False)),
        },
        "release": {
            "posture": (release.get("institutional_release_control_status") or {}).get("posture"),
            "current_version": (release.get("institutional_release_control_status") or {}).get("current_version") or release.get("active_version"),
        },
        "safety": {
            "posture": (safety.get("safety_layer_status") or {}).get("posture"),
            "production_ready": (safety.get("safety_layer_status") or {}).get("production_ready"),
        },
        "fund_admin": {
            "readiness": (admin.get("fund_admin_status") or {}).get("readiness"),
            "aum": float(admin.get("aum") or 0.0),
        },
        "forensic": {
            "posture": (forensic.get("forensic_status") or {}).get("posture"),
            "critical_open_count": (forensic.get("forensic_status") or {}).get("critical_open_count"),
        },
        "recovery": {
            "posture": (recovery.get("recovery_status") or {}).get("posture"),
            "safe_mode": (recovery.get("recovery_status") or {}).get("safe_mode"),
            "valid_state": (recovery.get("current_validation") or {}).get("valid_state"),
        },
        "strategy": {
            "posture": (strategy.get("strategy_evolution_status") or {}).get("posture"),
            "latest_score": (strategy.get("strategy_evolution_status") or {}).get("latest_score"),
        },
        "liquidity": {
            "posture": (liquidity.get("liquidity_intelligence_status") or {}).get("posture"),
            "latest_score": (liquidity.get("liquidity_intelligence_status") or {}).get("latest_score"),
        },
        "regime": {
            "posture": (regime.get("market_regime_intelligence_status") or {}).get("posture"),
            "latest_score": (regime.get("market_regime_intelligence_status") or {}).get("latest_score"),
        },
        "rotation": {
            "posture": (rotation.get("capital_rotation_command_status") or {}).get("posture"),
            "latest_score": (rotation.get("capital_rotation_command_status") or {}).get("latest_score"),
        },
        "defense": {
            "posture": (defense.get("defensive_systems_status") or {}).get("posture"),
            "latest_score": (defense.get("defensive_systems_status") or {}).get("latest_score"),
        },
        "autonomy": {
            "posture": (autonomy.get("autonomous_allocation_governance_status") or {}).get("posture"),
            "latest_score": (autonomy.get("autonomous_allocation_governance_status") or {}).get("latest_score"),
        },
        "transparency": {
            "posture": (transparency.get("investor_transparency_status") or {}).get("posture"),
            "latest_score": (transparency.get("investor_transparency_status") or {}).get("latest_score"),
        },
        "reporting": {
            "posture": (reporting.get("reporting_disclosure_automation_status") or {}).get("posture"),
            "latest_score": (reporting.get("reporting_disclosure_automation_status") or {}).get("latest_score"),
            "exception_count": (reporting.get("reporting_disclosure_automation_status") or {}).get("exception_count"),
        },
    }


def _score_readiness(payload: dict, ctx: dict, policy: dict) -> dict:
    runbook_completeness_pct = float(payload.get("runbook_completeness_pct") or 0.0)
    autonomy_band_score = float(payload.get("autonomy_band_score") or 0.0)
    human_supervision_coverage_pct = float(payload.get("human_supervision_coverage_pct") or 0.0)
    scenario_coverage_pct = float(payload.get("scenario_coverage_pct") or 0.0)
    resilience_score = float(payload.get("resilience_score") or 0.0)
    open_exceptions = int(payload.get("open_exceptions") or 0)

    strategy_score = float((ctx.get("strategy") or {}).get("latest_score") or 0.0)
    liquidity_score = float((ctx.get("liquidity") or {}).get("latest_score") or 0.0)
    regime_score = float((ctx.get("regime") or {}).get("latest_score") or 0.0)
    defense_score = float((ctx.get("defense") or {}).get("latest_score") or 0.0)
    autonomy_score = float((ctx.get("autonomy") or {}).get("latest_score") or 0.0)
    transparency_score = float((ctx.get("transparency") or {}).get("latest_score") or 0.0)
    reporting_score = float((ctx.get("reporting") or {}).get("latest_score") or 0.0)

    score = 52.0
    score += max(-14.0, min(14.0, (runbook_completeness_pct - 85.0) * 0.24))
    score += max(-14.0, min(14.0, (autonomy_band_score - float(policy.get("minimum_autonomy_governance_score") or 84.0)) * 0.33))
    score += max(-10.0, min(10.0, (human_supervision_coverage_pct - 90.0) * 0.20))
    score += max(-10.0, min(10.0, (scenario_coverage_pct - 88.0) * 0.18))
    score += max(-12.0, min(12.0, (resilience_score - 84.0) * 0.25))
    score += max(-8.0, min(8.0, (strategy_score - float(policy.get("minimum_strategy_score") or 78.0)) * 0.18))
    score += max(-8.0, min(8.0, (liquidity_score - float(policy.get("minimum_liquidity_score") or 80.0)) * 0.18))
    score += max(-8.0, min(8.0, (regime_score - float(policy.get("minimum_regime_score") or 78.0)) * 0.18))
    score += max(-8.0, min(8.0, (defense_score - float(policy.get("minimum_defense_score") or 80.0)) * 0.18))
    score += max(-8.0, min(8.0, (transparency_score - 82.0) * 0.14))
    score += max(-8.0, min(8.0, (reporting_score - 82.0) * 0.14))
    score -= min(14.0, open_exceptions * 4.5)

    blockers = []
    needs_operator = False

    if policy.get("require_operator_clear") and str((ctx.get("operator") or {}).get("posture") or "").upper() == "BLOCKED":
        blockers.append("operator posture blocked")
        score -= 18.0
    if bool((ctx.get("operator") or {}).get("override_required")):
        needs_operator = True
    if policy.get("require_release_clear") and str((ctx.get("release") or {}).get("posture") or "").lower() == "blocked":
        blockers.append("release posture blocked")
        score -= 18.0
    if str((ctx.get("safety") or {}).get("posture") or "").upper() == "BLOCKED":
        blockers.append("safety posture blocked")
        score -= 18.0
    if not bool((ctx.get("safety") or {}).get("production_ready")):
        blockers.append("production readiness not established")
        score -= 16.0
    if policy.get("require_fund_admin_ready") and str((ctx.get("fund_admin") or {}).get("readiness") or "").lower() == "blocked":
        blockers.append("fund admin readiness blocked")
        score -= 14.0
    if str((ctx.get("forensic") or {}).get("posture") or "").lower() == "blocked":
        blockers.append("forensic posture blocked")
        score -= 14.0
    if policy.get("require_recovery_clear") and (bool((ctx.get("recovery") or {}).get("safe_mode")) or not bool((ctx.get("recovery") or {}).get("valid_state"))):
        blockers.append("recovery posture not clear")
        score -= 18.0
    if str((ctx.get("liquidity") or {}).get("posture") or "").upper() not in {"APPROVED", "OPERATOR_REVIEW"}:
        blockers.append("liquidity posture not approved")
        score -= 12.0
    if str((ctx.get("defense") or {}).get("posture") or "").upper() == "BLOCKED":
        blockers.append("defensive posture blocked")
        score -= 12.0
    if policy.get("require_transparency_approved") and str((ctx.get("transparency") or {}).get("posture") or "").upper() not in {"APPROVED", "OPERATOR_REVIEW"}:
        blockers.append("transparency posture not approved")
        score -= 12.0
    if policy.get("require_reporting_approved") and str((ctx.get("reporting") or {}).get("posture") or "").upper() not in {"APPROVED", "OPERATOR_REVIEW"}:
        blockers.append("reporting posture not approved")
        score -= 12.0

    score = max(0.0, min(100.0, round(score, 2)))
    posture = "APPROVED"
    if blockers:
        posture = "BLOCKED"
    elif needs_operator or open_exceptions > int(policy.get("maximum_open_exceptions") or 1) or score < float(policy.get("minimum_readiness_score") or 86.0):
        posture = "OPERATOR_REVIEW"

    return {
        "score": score,
        "posture": posture,
        "blockers": blockers,
        "needs_operator_review": needs_operator,
        "strategy_score": round(strategy_score, 2),
        "liquidity_score": round(liquidity_score, 2),
        "regime_score": round(regime_score, 2),
        "defense_score": round(defense_score, 2),
        "autonomy_score": round(autonomy_score, 2),
        "transparency_score": round(transparency_score, 2),
        "reporting_score": round(reporting_score, 2),
    }


def _summary_for_email(email: str) -> dict:
    store = _load(email)
    runs = store.get("runs") or []
    latest = runs[0] if runs else {}
    latest_eval = latest.get("evaluation") or {}
    ctx = _cross_system_context(email)
    return {
        "autonomous_fund_mode_readiness_status": {
            "posture": latest_eval.get("posture") or "NOT_RUN",
            "latest_score": latest_eval.get("score"),
            "run_count": len(runs),
            "exception_count": len(store.get("exceptions") or []),
            "needs_operator_review": latest_eval.get("needs_operator_review", False),
        },
        "current_context": ctx,
        "latest_run": latest,
        "runs": runs[:20],
        "exceptions": (store.get("exceptions") or [])[:20],
        "policy": store.get("policy") or dict(DEFAULT_POLICY),
    }


@router.get("/api/autonomous-fund-mode-readiness-layer/summary")
def summary(session=Depends(_require_user)):
    return _summary_for_email(session["email"])


@router.post("/api/autonomous-fund-mode-readiness-layer/evaluate")
def evaluate(payload: dict = Body(...), session=Depends(_require_user)):
    email = session["email"]
    store = _load(email)
    ctx = _cross_system_context(email)
    evaluation = _score_readiness(payload, ctx, store.get("policy") or DEFAULT_POLICY)
    run = {
        "run_id": f"AFM-{_now_ts()}",
        "evaluated_at": _now_iso(),
        "mode_scope": payload.get("mode_scope") or "AUTONOMOUS_FUND_MODE",
        "inputs": {
            "runbook_completeness_pct": float(payload.get("runbook_completeness_pct") or 0.0),
            "autonomy_band_score": float(payload.get("autonomy_band_score") or 0.0),
            "human_supervision_coverage_pct": float(payload.get("human_supervision_coverage_pct") or 0.0),
            "scenario_coverage_pct": float(payload.get("scenario_coverage_pct") or 0.0),
            "resilience_score": float(payload.get("resilience_score") or 0.0),
            "open_exceptions": int(payload.get("open_exceptions") or 0),
        },
        "context": ctx,
        "evaluation": evaluation,
    }
    _append(store, "runs", run, int((store.get("policy") or {}).get("retain_runs") or 180))
    if evaluation.get("posture") != "APPROVED":
        exception_row = {
            "exception_id": f"AFMX-{_now_ts()}",
            "opened_at": _now_iso(),
            "mode_scope": run["mode_scope"],
            "score": evaluation.get("score"),
            "posture": evaluation.get("posture"),
            "blockers": evaluation.get("blockers") or [],
        }
        _append(store, "exceptions", exception_row, 100)
    _append(store, "readiness_book", {
        "recorded_at": _now_iso(),
        "run_id": run["run_id"],
        "posture": evaluation.get("posture"),
        "score": evaluation.get("score"),
    }, 240)
    _save(email, store)
    return {"ok": True, "run": run, "summary": _summary_for_email(email)}


@router.post("/api/autonomous-fund-mode-readiness-layer/policy")
def update_policy(payload: dict = Body(...), session=Depends(_require_user)):
    email = session["email"]
    store = _load(email)
    policy = dict(store.get("policy") or DEFAULT_POLICY)
    for key, value in payload.items():
        if key in DEFAULT_POLICY:
            policy[key] = value
    store["policy"] = policy
    _save(email, store)
    return {"ok": True, "policy": policy}


@router.post("/api/autonomous-fund-mode-readiness-layer/bootstrap-demo")
def bootstrap_demo(session=Depends(_require_user)):
    email = session["email"]
    store = _load(email)
    payload = {
        "mode_scope": "AUTONOMOUS_FUND_MODE",
        "runbook_completeness_pct": 94.0,
        "autonomy_band_score": 89.0,
        "human_supervision_coverage_pct": 96.0,
        "scenario_coverage_pct": 93.0,
        "resilience_score": 91.0,
        "open_exceptions": 0,
    }
    ctx = _cross_system_context(email)
    evaluation = _score_readiness(payload, ctx, store.get("policy") or DEFAULT_POLICY)
    run = {
        "run_id": f"AFMBOOT-{_now_ts()}",
        "evaluated_at": _now_iso(),
        "mode_scope": payload["mode_scope"],
        "inputs": payload,
        "context": ctx,
        "evaluation": evaluation,
    }
    _append(store, "runs", run, int((store.get("policy") or {}).get("retain_runs") or 180))
    _append(store, "readiness_book", {
        "recorded_at": _now_iso(),
        "run_id": run["run_id"],
        "posture": evaluation.get("posture"),
        "score": evaluation.get("score"),
    }, 240)
    _save(email, store)
    return {"ok": True, "summary": _summary_for_email(email)}
