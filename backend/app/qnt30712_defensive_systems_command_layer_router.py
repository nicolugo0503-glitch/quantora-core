from fastapi import APIRouter, Body, Depends
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import time

router = APIRouter(tags=["defensive-systems-command-layer"])

PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
ENGINE_DIR = ARTIFACTS_DIR / "defensive_systems_command_layer"
DEFAULT_POLICY = {
    "retain_commands": 120,
    "min_defense_score": 78.0,
    "max_var_1d_pct": 3.2,
    "max_drawdown_velocity": 2.8,
    "min_hedge_coverage_pct": 55.0,
    "max_correlation_stress_score": 72.0,
    "require_recovery_clear": True,
    "require_liquidity_ready": True,
    "require_regime_clear": True,
    "require_operator_override_for_hard_defense": True,
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


def _liquidity():
    from backend.app import qnt30709_liquidity_intelligence_system_router as liquidity
    return liquidity


def _regime():
    from backend.app import qnt30710_market_regime_intelligence_system_router as regime
    return regime


def _rotation():
    from backend.app import qnt30711_capital_rotation_command_system_router as rotation
    return rotation


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
            "defense_book": [],
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
    liquidity = _liquidity()._summary_for_email(email)
    regime = _regime()._summary_for_email(email)
    rotation = _rotation()._summary_for_email(email)
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
        "rotation": {
            "posture": (rotation.get("capital_rotation_status") or {}).get("posture"),
            "score": (rotation.get("capital_rotation_status") or {}).get("latest_score"),
            "approved": (rotation.get("capital_rotation_status") or {}).get("approved"),
            "active_target": (rotation.get("capital_rotation_status") or {}).get("active_target"),
        },
        "fund_admin": {
            "readiness": (admin.get("fund_admin_status") or {}).get("readiness"),
            "aum": float(admin.get("aum") or 0.0),
            "nav": float((admin.get("nav") or {}).get("reported_nav") or 0.0),
        },
    }


def _score_defense(payload: dict, ctx: dict, policy: dict) -> dict:
    var_1d_pct = float(payload.get("var_1d_pct") or 0.0)
    drawdown_velocity = float(payload.get("drawdown_velocity") or 0.0)
    hedge_coverage_pct = float(payload.get("hedge_coverage_pct") or 0.0)
    correlation_stress_score = float(payload.get("correlation_stress_score") or 0.0)
    liquidity_gap_pct = float(payload.get("liquidity_gap_pct") or 0.0)
    kill_switch_ready = bool(payload.get("kill_switch_ready", False))
    defense_mode = str(payload.get("defense_mode") or "soft-hedge").strip().lower()

    score = 56.0
    score += max(-18.0, min(14.0, (float(policy.get("max_var_1d_pct") or 3.2) - var_1d_pct) * 5.0))
    score += max(-16.0, min(12.0, (float(policy.get("max_drawdown_velocity") or 2.8) - drawdown_velocity) * 4.6))
    score += max(-10.0, min(16.0, (hedge_coverage_pct - float(policy.get("min_hedge_coverage_pct") or 55.0)) * 0.45))
    score += max(-14.0, min(10.0, (float(policy.get("max_correlation_stress_score") or 72.0) - correlation_stress_score) * 0.32))
    score += max(-8.0, min(8.0, (8.0 - liquidity_gap_pct) * 0.8))
    if kill_switch_ready:
        score += 6.0

    blockers = []
    needs_override = False

    if policy.get("require_recovery_clear") and bool((ctx.get("recovery") or {}).get("safe_mode")):
        blockers.append("recovery safe mode active")
        score -= 18.0
    if policy.get("require_recovery_clear") and not bool((ctx.get("recovery") or {}).get("valid_state")):
        blockers.append("recovery state not validated")
        score -= 16.0
    if policy.get("require_liquidity_ready") and not bool((ctx.get("liquidity") or {}).get("ready")):
        blockers.append("liquidity posture not ready")
        score -= 16.0
    if policy.get("require_regime_clear") and str((ctx.get("regime") or {}).get("posture") or "").upper() == "BLOCKED":
        blockers.append("market regime blocked")
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

    if var_1d_pct > float(policy.get("max_var_1d_pct") or 3.2):
        blockers.append("one-day var above policy ceiling")
    if drawdown_velocity > float(policy.get("max_drawdown_velocity") or 2.8):
        blockers.append("drawdown velocity above policy ceiling")
    if hedge_coverage_pct < float(policy.get("min_hedge_coverage_pct") or 55.0):
        blockers.append("hedge coverage below policy floor")
    if correlation_stress_score > float(policy.get("max_correlation_stress_score") or 72.0):
        blockers.append("correlation stress above policy ceiling")
    if liquidity_gap_pct > 12.0:
        blockers.append("liquidity gap too large for defensive deployment")
    if not kill_switch_ready:
        blockers.append("kill switch not armed")

    if defense_mode in {"hard-stop", "crisis-lockdown", "forced-deleveraging"}:
        needs_override = True
        if policy.get("require_operator_override_for_hard_defense") and bool((ctx.get("operator") or {}).get("override_required")):
            blockers.append("operator override required for hard defense mode")
            score -= 10.0

    score = max(0.0, round(score, 2))
    approved = score >= float(policy.get("min_defense_score") or 78.0) and len(blockers) == 0
    posture = "ARMED" if approved else ("WATCH" if score >= 64.0 else "BLOCKED")
    return {
        "score": score,
        "posture": posture,
        "approved": approved,
        "needs_operator_override": needs_override,
        "blockers": blockers,
        "thresholds": {
            "min_defense_score": float(policy.get("min_defense_score") or 78.0),
            "max_var_1d_pct": float(policy.get("max_var_1d_pct") or 3.2),
            "max_drawdown_velocity": float(policy.get("max_drawdown_velocity") or 2.8),
            "min_hedge_coverage_pct": float(policy.get("min_hedge_coverage_pct") or 55.0),
            "max_correlation_stress_score": float(policy.get("max_correlation_stress_score") or 72.0),
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
        "mission": "QNT30712",
        "defensive_systems_status": {
            "posture": posture,
            "command_count": len(commands),
            "alert_count": len(alerts),
            "latest_score": latest_eval.get("score"),
            "approved": latest_eval.get("approved"),
            "active_mode": latest.get("defense_mode"),
        },
        "current_context": ctx,
        "latest_command": latest,
        "commands": commands[:25],
        "alerts": alerts[:25],
        "defense_book": (store.get("defense_book") or [])[:25],
        "policy": policy,
    }


@router.get("/api/defensive-systems-command-layer/summary")
def summary(user=Depends(_require_user)):
    return _summary_for_email(user["email"])


@router.post("/api/defensive-systems-command-layer/evaluate")
def evaluate(payload: dict = Body(...), user=Depends(_require_user)):
    email = user["email"]
    store = _load(email)
    policy = store.get("policy") or dict(DEFAULT_POLICY)
    ctx = _cross_system_context(email)
    evaluation = _score_defense(payload, ctx, policy)
    command = {
        "command_id": f"defense-{_now_ts()}",
        "created_at": _now_iso(),
        "defense_mode": payload.get("defense_mode") or "soft-hedge",
        "target_book": payload.get("target_book") or "global-book",
        "var_1d_pct": float(payload.get("var_1d_pct") or 0.0),
        "drawdown_velocity": float(payload.get("drawdown_velocity") or 0.0),
        "hedge_coverage_pct": float(payload.get("hedge_coverage_pct") or 0.0),
        "correlation_stress_score": float(payload.get("correlation_stress_score") or 0.0),
        "liquidity_gap_pct": float(payload.get("liquidity_gap_pct") or 0.0),
        "kill_switch_ready": bool(payload.get("kill_switch_ready", False)),
        "evaluation": evaluation,
        "context": ctx,
    }
    _append(store, "commands", command, int(policy.get("retain_commands") or 120))
    _append(store, "defense_book", {
        "recorded_at": _now_iso(),
        "defense_mode": command["defense_mode"],
        "target_book": command["target_book"],
        "score": evaluation.get("score"),
        "approved": evaluation.get("approved"),
        "needs_operator_override": evaluation.get("needs_operator_override"),
    }, int(policy.get("retain_commands") or 120))
    if not evaluation.get("approved"):
        _append(store, "alerts", {
            "alert_id": f"defense-alert-{_now_ts()}",
            "created_at": _now_iso(),
            "defense_mode": command["defense_mode"],
            "target_book": command["target_book"],
            "score": evaluation.get("score"),
            "blockers": evaluation.get("blockers") or [],
        }, int(policy.get("retain_commands") or 120))
    _save(email, store)
    return {"ok": True, "command": command, "summary": _summary_for_email(email)}


@router.post("/api/defensive-systems-command-layer/policy")
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


@router.post("/api/defensive-systems-command-layer/bootstrap-demo")
def bootstrap_demo(user=Depends(_require_user)):
    email = user["email"]
    store = _load(email)
    store["commands"] = []
    store["alerts"] = []
    store["defense_book"] = []
    _save(email, store)
    payload = {
        "defense_mode": "soft-hedge",
        "target_book": "macro-book",
        "var_1d_pct": 2.4,
        "drawdown_velocity": 1.9,
        "hedge_coverage_pct": 67.0,
        "correlation_stress_score": 61.0,
        "liquidity_gap_pct": 4.5,
        "kill_switch_ready": True,
    }
    return evaluate(payload, user)
