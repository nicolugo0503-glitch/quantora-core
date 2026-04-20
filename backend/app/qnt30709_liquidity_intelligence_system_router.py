from fastapi import APIRouter, Body, Depends
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import time

router = APIRouter(tags=["liquidity-intelligence-system"])

PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
ENGINE_DIR = ARTIFACTS_DIR / "liquidity_intelligence_system"
DEFAULT_POLICY = {
    "retain_cycles": 120,
    "min_liquidity_score": 72.0,
    "max_redemption_pressure_pct": 18.0,
    "min_cash_buffer_pct": 8.0,
    "max_settlement_stress_pct": 12.0,
    "require_recovery_clear": True,
    "require_forensic_clear": True,
    "require_safety_ready": True,
    "require_fund_admin_ready": True,
}


def _mu():
    from backend.app import qnt30557_multi_user_router as mu
    return mu


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
            "stress_tests": [],
            "alerts": [],
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
    fund_admin = _fund_admin()._summary_for_email(email)
    forensic = _forensic()._summary_for_email(email)
    recovery = _recovery()._summary_for_email(email)
    strategy = _strategy()._summary_for_email(email)
    return {
        "captured_at": _now_iso(),
        "safety": {
            "posture": (safety.get("safety_layer_status") or {}).get("posture"),
            "production_ready": (safety.get("safety_layer_status") or {}).get("production_ready"),
            "blocked_trade_count": safety.get("blocked_trade_count"),
        },
        "fund_admin": {
            "readiness": (fund_admin.get("fund_admin_status") or {}).get("readiness"),
            "aum": float(fund_admin.get("aum") or 0.0),
            "cash_buffer_pct": float(((fund_admin.get("capital_posture") or {}).get("cash_buffer_pct") or 0.0)),
            "reconciliation_ok": bool((fund_admin.get("reconciliation") or {}).get("balanced", False)),
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
        "strategy": {
            "posture": (strategy.get("strategy_evolution_status") or {}).get("posture"),
            "promotable_count": (strategy.get("strategy_evolution_status") or {}).get("promotable_count"),
            "blocked_count": (strategy.get("strategy_evolution_status") or {}).get("blocked_count"),
        },
    }


def _score_liquidity(payload: dict, ctx: dict, policy: dict) -> dict:
    cash_buffer_pct = float(payload.get("cash_buffer_pct") or 0.0)
    redemption_pressure_pct = float(payload.get("redemption_pressure_pct") or 0.0)
    settlement_stress_pct = float(payload.get("settlement_stress_pct") or 0.0)
    concentration_pct = float(payload.get("concentration_pct") or 0.0)
    execution_depth_score = float(payload.get("execution_depth_score") or 0.0)

    score = 55.0
    score += max(-20.0, min(16.0, (cash_buffer_pct - float(policy.get("min_cash_buffer_pct") or 8.0)) * 1.8))
    score += max(-18.0, min(8.0, (float(policy.get("max_redemption_pressure_pct") or 18.0) - redemption_pressure_pct) * 1.1))
    score += max(-14.0, min(6.0, (float(policy.get("max_settlement_stress_pct") or 12.0) - settlement_stress_pct) * 1.2))
    score += max(-10.0, min(5.0, (30.0 - concentration_pct) * 0.35))
    score += max(0.0, min(12.0, execution_depth_score * 0.12))

    blockers = []
    if policy.get("require_recovery_clear") and bool((ctx.get("recovery") or {}).get("safe_mode")):
        blockers.append("recovery safe mode active")
        score -= 18.0
    if policy.get("require_recovery_clear") and not bool((ctx.get("recovery") or {}).get("valid_state")):
        blockers.append("recovery state not validated")
        score -= 16.0
    if policy.get("require_forensic_clear") and str((ctx.get("forensic") or {}).get("posture") or "").lower() == "blocked":
        blockers.append("forensic posture blocked")
        score -= 14.0
    if policy.get("require_safety_ready") and str((ctx.get("safety") or {}).get("posture") or "").upper() == "BLOCKED":
        blockers.append("safety posture blocked")
        score -= 16.0
    if policy.get("require_fund_admin_ready") and str((ctx.get("fund_admin") or {}).get("readiness") or "").lower() == "blocked":
        blockers.append("fund admin readiness blocked")
        score -= 14.0

    if redemption_pressure_pct > float(policy.get("max_redemption_pressure_pct") or 18.0):
        blockers.append("redemption pressure above policy ceiling")
    if cash_buffer_pct < float(policy.get("min_cash_buffer_pct") or 8.0):
        blockers.append("cash buffer below policy floor")
    if settlement_stress_pct > float(policy.get("max_settlement_stress_pct") or 12.0):
        blockers.append("settlement stress above policy ceiling")

    score = max(0.0, round(score, 2))
    ready = score >= float(policy.get("min_liquidity_score") or 72.0) and len(blockers) == 0
    posture = "READY" if ready else ("ATTENTION" if score >= 60.0 else "BLOCKED")
    return {
        "score": score,
        "posture": posture,
        "ready": ready,
        "blockers": blockers,
        "thresholds": {
            "min_liquidity_score": float(policy.get("min_liquidity_score") or 72.0),
            "max_redemption_pressure_pct": float(policy.get("max_redemption_pressure_pct") or 18.0),
            "min_cash_buffer_pct": float(policy.get("min_cash_buffer_pct") or 8.0),
            "max_settlement_stress_pct": float(policy.get("max_settlement_stress_pct") or 12.0),
        },
    }


def _summary_for_email(email: str) -> dict:
    store = _load(email)
    policy = store.get("policy") or dict(DEFAULT_POLICY)
    ctx = _cross_system_context(email)
    cycles = store.get("cycles") or []
    alerts = store.get("alerts") or []
    latest_cycle = cycles[0] if cycles else {}
    latest_eval = latest_cycle.get("evaluation") or {}
    posture = latest_eval.get("posture") or "ATTENTION"
    if bool((ctx.get("recovery") or {}).get("safe_mode")):
        posture = "SAFE_MODE"
    elif str((ctx.get("forensic") or {}).get("posture") or "").lower() == "blocked":
        posture = "BLOCKED"
    return {
        "mission": "QNT30709",
        "liquidity_status": {
            "posture": posture,
            "cycle_count": len(cycles),
            "alert_count": len(alerts),
            "latest_score": latest_eval.get("score"),
            "ready": latest_eval.get("ready"),
        },
        "current_context": ctx,
        "latest_cycle": latest_cycle,
        "cycles": cycles[:12],
        "alerts": alerts[:12],
        "policy": policy,
    }


@router.get("/api/liquidity-intelligence-system/summary")
def summary(user=Depends(_require_user)):
    return _summary_for_email(user["email"])


@router.post("/api/liquidity-intelligence-system/evaluate")
def evaluate(payload: dict = Body(...), user=Depends(_require_user)):
    email = user["email"]
    store = _load(email)
    policy = store.get("policy") or dict(DEFAULT_POLICY)
    ctx = _cross_system_context(email)
    evaluation = _score_liquidity(payload, ctx, policy)
    cycle = {
        "cycle_id": f"liq_{_now_ts()}",
        "captured_at": _now_iso(),
        **payload,
        "evaluation": evaluation,
        "context": ctx,
    }
    _append(store, "cycles", cycle, int(policy.get("retain_cycles") or 120))
    if not evaluation.get("ready"):
        _append(store, "alerts", {
            "alert_id": f"alert_{_now_ts()}",
            "captured_at": _now_iso(),
            "posture": evaluation.get("posture"),
            "score": evaluation.get("score"),
            "blockers": evaluation.get("blockers") or [],
        }, 120)
    _save(email, store)
    return {"ok": True, "cycle": cycle, "summary": _summary_for_email(email)}


@router.post("/api/liquidity-intelligence-system/policy")
def policy(payload: dict = Body(...), user=Depends(_require_user)):
    email = user["email"]
    store = _load(email)
    merged = dict(DEFAULT_POLICY)
    merged.update(store.get("policy") or {})
    merged.update(payload or {})
    store["policy"] = merged
    _save(email, store)
    return {"ok": True, "policy": merged}


@router.post("/api/liquidity-intelligence-system/bootstrap-demo")
def bootstrap_demo(user=Depends(_require_user)):
    email = user["email"]
    store = _load(email)
    demo = {
        "cash_buffer_pct": 12.5,
        "redemption_pressure_pct": 7.2,
        "settlement_stress_pct": 4.8,
        "concentration_pct": 22.0,
        "execution_depth_score": 86.0,
        "notes": "bootstrap demo liquidity posture",
    }
    return evaluate(demo, user)
