from fastapi import APIRouter, Body, Depends
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import time

router = APIRouter(tags=["capital-rotation-command-system"])

PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
ENGINE_DIR = ARTIFACTS_DIR / "capital_rotation_command_system"
DEFAULT_POLICY = {
    "retain_commands": 120,
    "min_rotation_score": 76.0,
    "max_capital_shift_pct": 22.0,
    "min_target_conviction_score": 68.0,
    "max_execution_risk_score": 35.0,
    "require_regime_favorable": True,
    "require_liquidity_ready": True,
    "require_recovery_clear": True,
    "require_safety_clear": True,
    "require_operator_override_for_large_shift": True,
    "operator_override_shift_pct": 14.0,
}


def _mu():
    from backend.app import qnt30557_multi_user_router as mu
    return mu


def _safety():
    from backend.app import qnt30703_live_broker_safety_layer_router as safety
    return safety


def _operator():
    from backend.app import qnt30702_operator_command_console_router as operator
    return operator


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


def _fund_admin():
    from backend.app import qnt30705_fund_admin_control_center_router as admin
    return admin


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
            "rotation_book": [],
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
    safety = _safety()._summary_for_email(email)
    operator = _operator()._summary_for_email(email)
    forensic = _forensic()._summary_for_email(email)
    recovery = _recovery()._summary_for_email(email)
    strategy = _strategy()._summary_for_email(email)
    liquidity = _liquidity()._summary_for_email(email)
    regime = _regime()._summary_for_email(email)
    admin = _fund_admin()._summary_for_email(email)
    return {
        "captured_at": _now_iso(),
        "safety": {
            "posture": (safety.get("safety_layer_status") or {}).get("posture"),
            "production_ready": (safety.get("safety_layer_status") or {}).get("production_ready"),
            "blocked_trade_count": safety.get("blocked_trade_count"),
        },
        "operator": {
            "posture": (operator.get("operator_console_status") or {}).get("posture"),
            "override_required": bool((operator.get("operator_console_status") or {}).get("override_required", False)),
            "incident_count": (operator.get("operator_console_status") or {}).get("incident_count"),
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
            "blocked_count": (strategy.get("strategy_evolution_status") or {}).get("blocked_count"),
        },
        "liquidity": {
            "posture": (liquidity.get("liquidity_status") or {}).get("posture"),
            "score": (liquidity.get("liquidity_status") or {}).get("latest_score"),
            "ready": (liquidity.get("liquidity_status") or {}).get("ready"),
        },
        "regime": {
            "posture": (regime.get("market_regime_status") or {}).get("posture"),
            "score": (regime.get("market_regime_status") or {}).get("latest_score"),
            "ready": (regime.get("market_regime_status") or {}).get("ready"),
            "active_regime": (regime.get("market_regime_status") or {}).get("active_regime"),
        },
        "fund_admin": {
            "readiness": (admin.get("fund_admin_status") or {}).get("readiness"),
            "aum": float(admin.get("aum") or 0.0),
            "nav": float((admin.get("nav") or {}).get("reported_nav") or 0.0),
        },
    }


def _score_rotation(payload: dict, ctx: dict, policy: dict) -> dict:
    capital_shift_pct = float(payload.get("capital_shift_pct") or 0.0)
    target_conviction_score = float(payload.get("target_conviction_score") or 0.0)
    execution_risk_score = float(payload.get("execution_risk_score") or 0.0)
    source_decay_score = float(payload.get("source_decay_score") or 0.0)
    diversification_gain_score = float(payload.get("diversification_gain_score") or 0.0)

    score = 58.0
    score += max(-14.0, min(10.0, (float(policy.get("max_capital_shift_pct") or 22.0) - capital_shift_pct) * 0.9))
    score += max(-8.0, min(18.0, (target_conviction_score - float(policy.get("min_target_conviction_score") or 68.0)) * 0.55))
    score += max(-16.0, min(9.0, (float(policy.get("max_execution_risk_score") or 35.0) - execution_risk_score) * 0.6))
    score += max(-6.0, min(10.0, (source_decay_score - 50.0) * 0.22))
    score += max(-4.0, min(10.0, (diversification_gain_score - 50.0) * 0.20))

    blockers = []
    needs_override = False

    if policy.get("require_recovery_clear") and bool((ctx.get("recovery") or {}).get("safe_mode")):
        blockers.append("recovery safe mode active")
        score -= 18.0
    if policy.get("require_recovery_clear") and not bool((ctx.get("recovery") or {}).get("valid_state")):
        blockers.append("recovery state not validated")
        score -= 16.0
    if policy.get("require_safety_clear") and str((ctx.get("safety") or {}).get("posture") or "").upper() == "BLOCKED":
        blockers.append("safety posture blocked")
        score -= 16.0
    if policy.get("require_liquidity_ready") and not bool((ctx.get("liquidity") or {}).get("ready")):
        blockers.append("liquidity posture not ready")
        score -= 16.0
    if policy.get("require_regime_favorable") and not bool((ctx.get("regime") or {}).get("ready")):
        blockers.append("market regime not favorable")
        score -= 15.0
    if str((ctx.get("forensic") or {}).get("posture") or "").lower() == "blocked":
        blockers.append("forensic posture blocked")
        score -= 14.0
    if str((ctx.get("fund_admin") or {}).get("readiness") or "").lower() == "blocked":
        blockers.append("fund admin readiness blocked")
        score -= 14.0

    if capital_shift_pct > float(policy.get("max_capital_shift_pct") or 22.0):
        blockers.append("capital shift above policy ceiling")
    if target_conviction_score < float(policy.get("min_target_conviction_score") or 68.0):
        blockers.append("target conviction below policy floor")
    if execution_risk_score > float(policy.get("max_execution_risk_score") or 35.0):
        blockers.append("execution risk above policy ceiling")

    if policy.get("require_operator_override_for_large_shift") and capital_shift_pct >= float(policy.get("operator_override_shift_pct") or 14.0):
        needs_override = True
        if bool((ctx.get("operator") or {}).get("override_required")):
            blockers.append("operator override required for large capital shift")
            score -= 10.0

    score = max(0.0, round(score, 2))
    approved = score >= float(policy.get("min_rotation_score") or 76.0) and len(blockers) == 0
    posture = "APPROVED" if approved else ("WATCH" if score >= 62.0 else "BLOCKED")
    return {
        "score": score,
        "posture": posture,
        "approved": approved,
        "needs_operator_override": needs_override,
        "blockers": blockers,
        "thresholds": {
            "min_rotation_score": float(policy.get("min_rotation_score") or 76.0),
            "max_capital_shift_pct": float(policy.get("max_capital_shift_pct") or 22.0),
            "min_target_conviction_score": float(policy.get("min_target_conviction_score") or 68.0),
            "max_execution_risk_score": float(policy.get("max_execution_risk_score") or 35.0),
            "operator_override_shift_pct": float(policy.get("operator_override_shift_pct") or 14.0),
        },
    }


def _summary_for_email(email: str) -> dict:
    store = _load(email)
    policy = store.get("policy") or dict(DEFAULT_POLICY)
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
        "mission": "QNT30711",
        "capital_rotation_status": {
            "posture": posture,
            "command_count": len(commands),
            "alert_count": len(alerts),
            "latest_score": latest_eval.get("score"),
            "approved": latest_eval.get("approved"),
            "active_target": latest.get("target_sleeve"),
        },
        "current_context": ctx,
        "latest_command": latest,
        "commands": commands[:25],
        "alerts": alerts[:25],
        "rotation_book": (store.get("rotation_book") or [])[:25],
        "policy": policy,
    }


@router.get("/api/capital-rotation-command-system/summary")
def summary(user=Depends(_require_user)):
    return _summary_for_email(user["email"])


@router.post("/api/capital-rotation-command-system/evaluate")
def evaluate(payload: dict = Body(...), user=Depends(_require_user)):
    email = user["email"]
    store = _load(email)
    policy = store.get("policy") or dict(DEFAULT_POLICY)
    ctx = _cross_system_context(email)
    evaluation = _score_rotation(payload, ctx, policy)
    command = {
        "command_id": f"rotation-{_now_ts()}",
        "created_at": _now_iso(),
        "source_sleeve": payload.get("source_sleeve") or "reserve-sleeve",
        "target_sleeve": payload.get("target_sleeve") or "alpha-sleeve",
        "capital_shift_pct": float(payload.get("capital_shift_pct") or 0.0),
        "target_conviction_score": float(payload.get("target_conviction_score") or 0.0),
        "execution_risk_score": float(payload.get("execution_risk_score") or 0.0),
        "source_decay_score": float(payload.get("source_decay_score") or 0.0),
        "diversification_gain_score": float(payload.get("diversification_gain_score") or 0.0),
        "evaluation": evaluation,
        "context": ctx,
    }
    _append(store, "commands", command, int(policy.get("retain_commands") or 120))
    _append(store, "rotation_book", {
        "recorded_at": _now_iso(),
        "source_sleeve": command["source_sleeve"],
        "target_sleeve": command["target_sleeve"],
        "capital_shift_pct": command["capital_shift_pct"],
        "approved": evaluation.get("approved"),
        "score": evaluation.get("score"),
    }, int(policy.get("retain_commands") or 120))
    if not evaluation.get("approved"):
        _append(store, "alerts", {
            "alert_id": f"rotation-alert-{_now_ts()}",
            "created_at": _now_iso(),
            "source_sleeve": command["source_sleeve"],
            "target_sleeve": command["target_sleeve"],
            "score": evaluation.get("score"),
            "blockers": evaluation.get("blockers") or [],
        }, int(policy.get("retain_commands") or 120))
    _save(email, store)
    return {"ok": True, "command": command, "summary": _summary_for_email(email)}


@router.post("/api/capital-rotation-command-system/policy")
def update_policy(payload: dict = Body(...), user=Depends(_require_user)):
    email = user["email"]
    store = _load(email)
    policy = dict(store.get("policy") or DEFAULT_POLICY)
    for key in DEFAULT_POLICY.keys():
        if key in payload:
            policy[key] = payload.get(key)
    store["policy"] = policy
    _save(email, store)
    return {"ok": True, "policy": policy, "summary": _summary_for_email(email)}


@router.post("/api/capital-rotation-command-system/bootstrap-demo")
def bootstrap_demo(user=Depends(_require_user)):
    email = user["email"]
    store = _load(email)
    store["commands"] = []
    store["alerts"] = []
    store["rotation_book"] = []
    _save(email, store)
    payload = {
        "source_sleeve": "defensive-carry",
        "target_sleeve": "trend-alpha",
        "capital_shift_pct": 11.5,
        "target_conviction_score": 79.0,
        "execution_risk_score": 21.0,
        "source_decay_score": 71.0,
        "diversification_gain_score": 73.0,
    }
    return evaluate(payload, user)
