from fastapi import APIRouter, Body, Depends
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import time

router = APIRouter(tags=["autonomous-allocation-governance-layer"])

PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
ENGINE_DIR = ARTIFACTS_DIR / "autonomous_allocation_governance_layer"
DEFAULT_POLICY = {
    "retain_commands": 150,
    "min_governance_score": 80.0,
    "max_autonomy_band_pct": 18.0,
    "max_concentration_pct": 26.0,
    "min_explainability_score": 72.0,
    "min_operator_review_interval_hours": 24.0,
    "require_recovery_clear": True,
    "require_defense_not_armed": True,
    "require_liquidity_ready": True,
    "require_regime_ready": True,
    "require_operator_approval_for_live_allocate": True,
}


def _mu():
    from backend.app import qnt30557_multi_user_router as mu
    return mu


def _operator():
    from backend.app import qnt30702_operator_command_console_router as operator
    return operator


def _safety():
    from backend.app import qnt30703_live_broker_safety_layer_router as safety
    return safety


def _release():
    from backend.app import qnt30700_institutional_release_control_router as release
    return release


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
            "commands": [],
            "alerts": [],
            "governance_book": [],
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
    safety = _safety()._summary_for_email(email)
    release = _release()._summary_for_email(email)
    admin = _fund_admin()._summary_for_email(email)
    forensic = _forensic()._summary_for_email(email)
    recovery = _recovery()._summary_for_email(email)
    strategy = _strategy()._summary_for_email(email)
    liquidity = _liquidity()._summary_for_email(email)
    regime = _regime()._summary_for_email(email)
    rotation = _rotation()._summary_for_email(email)
    defense = _defense()._summary_for_email(email)
    return {
        "captured_at": _now_iso(),
        "operator": {
            "posture": (operator.get("operator_console_status") or {}).get("posture"),
            "override_required": bool((operator.get("operator_console_status") or {}).get("override_required", False)),
        },
        "safety": {
            "posture": (safety.get("safety_layer_status") or {}).get("posture"),
            "production_ready": (safety.get("safety_layer_status") or {}).get("production_ready"),
        },
        "release": {
            "posture": (release.get("institutional_release_control_status") or {}).get("posture"),
            "current_version": (release.get("institutional_release_control_status") or {}).get("current_version"),
        },
        "fund_admin": {
            "readiness": (admin.get("fund_admin_status") or {}).get("readiness"),
            "aum": float(admin.get("aum") or 0.0),
            "reported_nav": float((admin.get("nav") or {}).get("reported_nav") or 0.0),
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
            "promotable_count": (strategy.get("strategy_evolution_status") or {}).get("promotable_count"),
            "active_strategy": (strategy.get("strategy_evolution_status") or {}).get("active_strategy"),
        },
        "liquidity": {
            "posture": (liquidity.get("liquidity_status") or {}).get("posture"),
            "ready": (liquidity.get("liquidity_status") or {}).get("ready"),
            "score": (liquidity.get("liquidity_status") or {}).get("latest_score"),
        },
        "regime": {
            "posture": (regime.get("market_regime_status") or {}).get("posture"),
            "ready": (regime.get("market_regime_status") or {}).get("ready"),
            "active_regime": (regime.get("market_regime_status") or {}).get("active_regime"),
        },
        "rotation": {
            "posture": (rotation.get("capital_rotation_status") or {}).get("posture"),
            "approved": (rotation.get("capital_rotation_status") or {}).get("approved"),
            "active_target": (rotation.get("capital_rotation_status") or {}).get("active_target"),
        },
        "defense": {
            "posture": (defense.get("defensive_systems_status") or {}).get("posture"),
            "armed": bool((defense.get("defensive_systems_status") or {}).get("armed", False)),
            "active_mode": (defense.get("defensive_systems_status") or {}).get("active_mode"),
        },
    }


def _score_governance(payload: dict, ctx: dict, policy: dict) -> dict:
    autonomy_band_pct = float(payload.get("autonomy_band_pct") or 0.0)
    concentration_pct = float(payload.get("concentration_pct") or 0.0)
    explainability_score = float(payload.get("explainability_score") or 0.0)
    review_interval_hours = float(payload.get("review_interval_hours") or 0.0)
    confidence_score = float(payload.get("confidence_score") or 0.0)
    scenario_coverage_pct = float(payload.get("scenario_coverage_pct") or 0.0)
    live_allocate = bool(payload.get("live_allocate", False))
    allocation_mode = str(payload.get("allocation_mode") or "supervised-autonomy").strip().lower()

    score = 54.0
    score += max(-16.0, min(16.0, (float(policy.get("max_autonomy_band_pct") or 18.0) - autonomy_band_pct) * 0.9))
    score += max(-18.0, min(14.0, (float(policy.get("max_concentration_pct") or 26.0) - concentration_pct) * 0.8))
    score += max(-12.0, min(18.0, (explainability_score - float(policy.get("min_explainability_score") or 72.0)) * 0.5))
    score += max(-10.0, min(10.0, (float(policy.get("min_operator_review_interval_hours") or 24.0) - review_interval_hours) * 0.3))
    score += max(-10.0, min(12.0, (confidence_score - 70.0) * 0.28))
    score += max(-8.0, min(10.0, (scenario_coverage_pct - 68.0) * 0.22))

    blockers = []
    needs_operator = False

    if policy.get("require_recovery_clear") and bool((ctx.get("recovery") or {}).get("safe_mode")):
        blockers.append("recovery safe mode active")
        score -= 18.0
    if policy.get("require_recovery_clear") and not bool((ctx.get("recovery") or {}).get("valid_state")):
        blockers.append("recovery state not validated")
        score -= 14.0
    if policy.get("require_defense_not_armed") and bool((ctx.get("defense") or {}).get("armed")):
        blockers.append("defensive systems currently armed")
        score -= 16.0
    if policy.get("require_liquidity_ready") and not bool((ctx.get("liquidity") or {}).get("ready")):
        blockers.append("liquidity posture not ready")
        score -= 16.0
    if policy.get("require_regime_ready") and not bool((ctx.get("regime") or {}).get("ready")):
        blockers.append("market regime not favorable")
        score -= 14.0
    if str((ctx.get("safety") or {}).get("posture") or "").upper() == "BLOCKED":
        blockers.append("safety posture blocked")
        score -= 16.0
    if str((ctx.get("forensic") or {}).get("posture") or "").lower() == "blocked":
        blockers.append("forensic posture blocked")
        score -= 14.0
    if str((ctx.get("fund_admin") or {}).get("readiness") or "").lower() == "blocked":
        blockers.append("fund admin readiness blocked")
        score -= 14.0

    if autonomy_band_pct > float(policy.get("max_autonomy_band_pct") or 18.0):
        blockers.append("autonomy band exceeds policy")
    if concentration_pct > float(policy.get("max_concentration_pct") or 26.0):
        blockers.append("allocation concentration exceeds policy")
    if explainability_score < float(policy.get("min_explainability_score") or 72.0):
        blockers.append("explainability score below threshold")
    if live_allocate and policy.get("require_operator_approval_for_live_allocate", True):
        needs_operator = True

    approved = (score >= float(policy.get("min_governance_score") or 80.0)) and (len(blockers) == 0)
    posture = "APPROVED" if approved and not needs_operator else ("REVIEW" if len(blockers) == 0 else "BLOCKED")
    if needs_operator and approved:
        posture = "OPERATOR_REVIEW"

    return {
        "score": round(max(0.0, min(100.0, score)), 2),
        "approved": bool(approved and not needs_operator),
        "operator_review_required": bool(needs_operator),
        "posture": posture,
        "blockers": blockers,
        "allocation_mode": allocation_mode,
        "recommended_autonomy_band_pct": round(min(autonomy_band_pct, float(policy.get("max_autonomy_band_pct") or 18.0)), 2),
        "recommended_target_sleeve": payload.get("target_sleeve") or "adaptive-alpha",
    }


def _summary_for_email(email: str) -> dict:
    store = _load(email)
    ctx = _cross_system_context(email)
    commands = store.get("commands") or []
    alerts = store.get("alerts") or []
    latest = commands[0] if commands else {}
    latest_eval = latest.get("evaluation") or {}
    posture = latest_eval.get("posture") or "WATCH"
    if bool((ctx.get("recovery") or {}).get("safe_mode")):
        posture = "SAFE_MODE"
    elif str((ctx.get("forensic") or {}).get("posture") or "").lower() == "blocked":
        posture = "BLOCKED"
    return {
        "mission": "QNT30713",
        "autonomous_allocation_governance_status": {
            "posture": posture,
            "latest_score": latest_eval.get("score"),
            "approved": latest_eval.get("approved"),
            "operator_review_required": latest_eval.get("operator_review_required"),
            "command_count": len(commands),
            "alert_count": len(alerts),
            "active_target": latest.get("target_sleeve"),
            "active_mode": latest.get("allocation_mode"),
        },
        "latest_command": latest,
        "current_context": ctx,
        "commands": commands[:25],
        "alerts": alerts[:25],
        "policy": store.get("policy") or dict(DEFAULT_POLICY),
    }


@router.get("/api/autonomous-allocation-governance-layer/summary")
def summary(user=Depends(_require_user)):
    return _summary_for_email(user["email"])


@router.post("/api/autonomous-allocation-governance-layer/evaluate")
def evaluate(payload: dict = Body(...), user=Depends(_require_user)):
    email = user["email"]
    store = _load(email)
    policy = store.get("policy") or dict(DEFAULT_POLICY)
    ctx = _cross_system_context(email)
    evaluation = _score_governance(payload, ctx, policy)
    command = {
        "command_id": f"allocation-governance-{_now_ts()}",
        "created_at": _now_iso(),
        "allocation_mode": payload.get("allocation_mode") or "supervised-autonomy",
        "target_sleeve": payload.get("target_sleeve") or evaluation.get("recommended_target_sleeve"),
        "autonomy_band_pct": float(payload.get("autonomy_band_pct") or 0.0),
        "concentration_pct": float(payload.get("concentration_pct") or 0.0),
        "explainability_score": float(payload.get("explainability_score") or 0.0),
        "review_interval_hours": float(payload.get("review_interval_hours") or 0.0),
        "confidence_score": float(payload.get("confidence_score") or 0.0),
        "scenario_coverage_pct": float(payload.get("scenario_coverage_pct") or 0.0),
        "live_allocate": bool(payload.get("live_allocate", False)),
        "evaluation": evaluation,
        "context": ctx,
    }
    _append(store, "commands", command, int(policy.get("retain_commands") or 150))
    if evaluation.get("posture") in ("BLOCKED", "OPERATOR_REVIEW"):
        _append(store, "alerts", {
            "alert_id": f"allocgov-alert-{_now_ts()}",
            "created_at": _now_iso(),
            "allocation_mode": command["allocation_mode"],
            "score": evaluation.get("score"),
            "blockers": evaluation.get("blockers") or [],
            "operator_review_required": evaluation.get("operator_review_required"),
        }, int(policy.get("retain_commands") or 150))
    _append(store, "governance_book", {
        "entry_id": f"allocgov-book-{_now_ts()}",
        "created_at": _now_iso(),
        "target_sleeve": command["target_sleeve"],
        "allocation_mode": command["allocation_mode"],
        "posture": evaluation.get("posture"),
        "score": evaluation.get("score"),
    }, int(policy.get("retain_commands") or 150))
    _save(email, store)
    return {"ok": True, "command": command, "summary": _summary_for_email(email)}


@router.post("/api/autonomous-allocation-governance-layer/policy")
def update_policy(payload: dict = Body(...), user=Depends(_require_user)):
    email = user["email"]
    store = _load(email)
    policy = store.get("policy") or dict(DEFAULT_POLICY)
    for key in DEFAULT_POLICY:
        if key in payload:
            policy[key] = payload[key]
    store["policy"] = policy
    _save(email, store)
    return {"ok": True, "policy": policy}


@router.post("/api/autonomous-allocation-governance-layer/bootstrap-demo")
def bootstrap_demo(user=Depends(_require_user)):
    email = user["email"]
    store = _load(email)
    payload = {
        "allocation_mode": "supervised-autonomy",
        "target_sleeve": "adaptive-alpha",
        "autonomy_band_pct": 14.0,
        "concentration_pct": 18.5,
        "explainability_score": 84.0,
        "review_interval_hours": 12.0,
        "confidence_score": 82.0,
        "scenario_coverage_pct": 77.0,
        "live_allocate": True,
    }
    policy = store.get("policy") or dict(DEFAULT_POLICY)
    ctx = _cross_system_context(email)
    evaluation = _score_governance(payload, ctx, policy)
    command = {
        "command_id": f"allocation-governance-{_now_ts()}",
        "created_at": _now_iso(),
        **payload,
        "evaluation": evaluation,
        "context": ctx,
    }
    _append(store, "commands", command, int(policy.get("retain_commands") or 150))
    if evaluation.get("posture") in ("BLOCKED", "OPERATOR_REVIEW"):
        _append(store, "alerts", {
            "alert_id": f"allocgov-alert-{_now_ts()}",
            "created_at": _now_iso(),
            "allocation_mode": payload["allocation_mode"],
            "score": evaluation.get("score"),
            "blockers": evaluation.get("blockers") or [],
            "operator_review_required": evaluation.get("operator_review_required"),
        }, int(policy.get("retain_commands") or 150))
    _append(store, "governance_book", {
        "entry_id": f"allocgov-book-{_now_ts()}",
        "created_at": _now_iso(),
        "target_sleeve": payload["target_sleeve"],
        "allocation_mode": payload["allocation_mode"],
        "posture": evaluation.get("posture"),
        "score": evaluation.get("score"),
    }, int(policy.get("retain_commands") or 150))
    _save(email, store)
    return {"ok": True, "summary": _summary_for_email(email)}
