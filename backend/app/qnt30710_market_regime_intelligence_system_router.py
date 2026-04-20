from fastapi import APIRouter, Body, Depends
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import time

router = APIRouter(tags=["market-regime-intelligence-system"])

PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
ENGINE_DIR = ARTIFACTS_DIR / "market_regime_intelligence_system"
DEFAULT_POLICY = {
    "retain_cycles": 120,
    "min_regime_score": 74.0,
    "max_volatility_spike_pct": 22.0,
    "min_trend_breadth_score": 58.0,
    "max_cross_asset_stress_score": 68.0,
    "require_liquidity_ready": True,
    "require_recovery_clear": True,
    "require_safety_clear": True,
    "require_strategy_clear": True,
}


def _mu():
    from backend.app import qnt30557_multi_user_router as mu
    return mu


def _safety():
    from backend.app import qnt30703_live_broker_safety_layer_router as safety
    return safety


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
            "alerts": [],
            "watch": [],
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
    forensic = _forensic()._summary_for_email(email)
    recovery = _recovery()._summary_for_email(email)
    strategy = _strategy()._summary_for_email(email)
    liquidity = _liquidity()._summary_for_email(email)
    return {
        "captured_at": _now_iso(),
        "safety": {
            "posture": (safety.get("safety_layer_status") or {}).get("posture"),
            "production_ready": (safety.get("safety_layer_status") or {}).get("production_ready"),
            "blocked_trade_count": safety.get("blocked_trade_count"),
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
        "liquidity": {
            "posture": (liquidity.get("liquidity_status") or {}).get("posture"),
            "score": (liquidity.get("liquidity_status") or {}).get("latest_score"),
            "ready": (liquidity.get("liquidity_status") or {}).get("ready"),
            "alert_count": (liquidity.get("liquidity_status") or {}).get("alert_count"),
        },
    }


def _score_regime(payload: dict, ctx: dict, policy: dict) -> dict:
    volatility_spike_pct = float(payload.get("volatility_spike_pct") or 0.0)
    trend_breadth_score = float(payload.get("trend_breadth_score") or 0.0)
    cross_asset_stress_score = float(payload.get("cross_asset_stress_score") or 0.0)
    dispersion_score = float(payload.get("dispersion_score") or 0.0)
    macro_alignment_score = float(payload.get("macro_alignment_score") or 0.0)

    score = 56.0
    score += max(-18.0, min(10.0, (float(policy.get("max_volatility_spike_pct") or 22.0) - volatility_spike_pct) * 1.15))
    score += max(-10.0, min(16.0, (trend_breadth_score - float(policy.get("min_trend_breadth_score") or 58.0)) * 0.65))
    score += max(-15.0, min(8.0, (float(policy.get("max_cross_asset_stress_score") or 68.0) - cross_asset_stress_score) * 0.55))
    score += max(-6.0, min(10.0, (dispersion_score - 50.0) * 0.25))
    score += max(-6.0, min(12.0, (macro_alignment_score - 50.0) * 0.24))

    blockers = []
    if policy.get("require_recovery_clear") and bool((ctx.get("recovery") or {}).get("safe_mode")):
        blockers.append("recovery safe mode active")
        score -= 18.0
    if policy.get("require_recovery_clear") and not bool((ctx.get("recovery") or {}).get("valid_state")):
        blockers.append("recovery state not validated")
        score -= 16.0
    if policy.get("require_safety_clear") and str((ctx.get("safety") or {}).get("posture") or "").upper() == "BLOCKED":
        blockers.append("safety posture blocked")
        score -= 16.0
    if policy.get("require_strategy_clear") and str((ctx.get("strategy") or {}).get("posture") or "").lower() == "blocked":
        blockers.append("strategy posture blocked")
        score -= 14.0
    if policy.get("require_liquidity_ready") and not bool((ctx.get("liquidity") or {}).get("ready")):
        blockers.append("liquidity posture not ready")
        score -= 16.0
    if str((ctx.get("forensic") or {}).get("posture") or "").lower() == "blocked":
        blockers.append("forensic posture blocked")
        score -= 14.0

    if volatility_spike_pct > float(policy.get("max_volatility_spike_pct") or 22.0):
        blockers.append("volatility spike above policy ceiling")
    if trend_breadth_score < float(policy.get("min_trend_breadth_score") or 58.0):
        blockers.append("trend breadth below policy floor")
    if cross_asset_stress_score > float(policy.get("max_cross_asset_stress_score") or 68.0):
        blockers.append("cross-asset stress above policy ceiling")

    score = max(0.0, round(score, 2))
    ready = score >= float(policy.get("min_regime_score") or 74.0) and len(blockers) == 0
    posture = "FAVORABLE" if ready else ("WATCH" if score >= 60.0 else "BLOCKED")
    regime_label = payload.get("candidate_regime") or ("risk-on" if score >= 80 else "transitional" if score >= 60 else "risk-off")
    return {
        "score": score,
        "posture": posture,
        "ready": ready,
        "regime_label": regime_label,
        "blockers": blockers,
        "thresholds": {
            "min_regime_score": float(policy.get("min_regime_score") or 74.0),
            "max_volatility_spike_pct": float(policy.get("max_volatility_spike_pct") or 22.0),
            "min_trend_breadth_score": float(policy.get("min_trend_breadth_score") or 58.0),
            "max_cross_asset_stress_score": float(policy.get("max_cross_asset_stress_score") or 68.0),
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
    posture = latest_eval.get("posture") or "WATCH"
    if bool((ctx.get("recovery") or {}).get("safe_mode")):
        posture = "SAFE_MODE"
    elif str((ctx.get("forensic") or {}).get("posture") or "").lower() == "blocked":
        posture = "BLOCKED"
    return {
        "mission": "QNT30710",
        "market_regime_status": {
            "posture": posture,
            "cycle_count": len(cycles),
            "alert_count": len(alerts),
            "latest_score": latest_eval.get("score"),
            "ready": latest_eval.get("ready"),
            "active_regime": latest_eval.get("regime_label"),
        },
        "current_context": ctx,
        "latest_cycle": latest_cycle,
        "policy": policy,
        "cycles": cycles[:25],
        "alerts": alerts[:25],
        "watch": (store.get("watch") or [])[:25],
    }


@router.get("/api/market-regime-intelligence-system/summary")
def market_regime_summary(session=Depends(_require_user)):
    return _summary_for_email(session.get("email"))


@router.post("/api/market-regime-intelligence-system/evaluate")
def evaluate_market_regime(payload: dict = Body(...), session=Depends(_require_user)):
    email = session.get("email")
    store = _load(email)
    policy = store.get("policy") or dict(DEFAULT_POLICY)
    ctx = _cross_system_context(email)
    evaluation = _score_regime(payload, ctx, policy)
    cycle = {
        "cycle_id": f"regime-{_now_ts()}",
        "created_at": _now_iso(),
        "candidate_regime": payload.get("candidate_regime") or evaluation.get("regime_label"),
        "volatility_spike_pct": float(payload.get("volatility_spike_pct") or 0.0),
        "trend_breadth_score": float(payload.get("trend_breadth_score") or 0.0),
        "cross_asset_stress_score": float(payload.get("cross_asset_stress_score") or 0.0),
        "dispersion_score": float(payload.get("dispersion_score") or 0.0),
        "macro_alignment_score": float(payload.get("macro_alignment_score") or 0.0),
        "evaluation": evaluation,
        "context": ctx,
    }
    _append(store, "cycles", cycle, int(policy.get("retain_cycles") or 120))
    if not evaluation.get("ready"):
        alert = {
            "alert_id": f"regime-alert-{_now_ts()}",
            "created_at": _now_iso(),
            "posture": evaluation.get("posture"),
            "score": evaluation.get("score"),
            "regime_label": evaluation.get("regime_label"),
            "blockers": list(evaluation.get("blockers") or []),
        }
        _append(store, "alerts", alert, int(policy.get("retain_cycles") or 120))
    else:
        _append(store, "watch", {
            "watch_id": f"regime-watch-{_now_ts()}",
            "created_at": _now_iso(),
            "regime_label": evaluation.get("regime_label"),
            "score": evaluation.get("score"),
            "note": "favorable regime recorded",
        }, int(policy.get("retain_cycles") or 120))
    _save(email, store)
    return {"ok": True, "cycle": cycle, "summary": _summary_for_email(email)}


@router.post("/api/market-regime-intelligence-system/policy")
def update_market_regime_policy(payload: dict = Body(...), session=Depends(_require_user)):
    email = session.get("email")
    store = _load(email)
    policy = store.get("policy") or dict(DEFAULT_POLICY)
    for key in DEFAULT_POLICY.keys():
        if key in payload:
            policy[key] = payload.get(key)
    store["policy"] = policy
    _save(email, store)
    return {"ok": True, "policy": policy}


@router.post("/api/market-regime-intelligence-system/bootstrap-demo")
def bootstrap_market_regime_demo(session=Depends(_require_user)):
    email = session.get("email")
    store = _load(email)
    store["policy"] = dict(DEFAULT_POLICY)
    store["cycles"] = []
    store["alerts"] = []
    store["watch"] = []
    _save(email, store)
    payloads = [
        {
            "candidate_regime": "risk-on",
            "volatility_spike_pct": 11.0,
            "trend_breadth_score": 72.0,
            "cross_asset_stress_score": 38.0,
            "dispersion_score": 64.0,
            "macro_alignment_score": 69.0,
        },
        {
            "candidate_regime": "transitional",
            "volatility_spike_pct": 19.0,
            "trend_breadth_score": 55.0,
            "cross_asset_stress_score": 61.0,
            "dispersion_score": 52.0,
            "macro_alignment_score": 57.0,
        },
    ]
    out = []
    for payload in payloads:
        out.append(evaluate_market_regime(payload, {"email": email}))
    return {"ok": True, "runs": len(out), "summary": _summary_for_email(email)}
