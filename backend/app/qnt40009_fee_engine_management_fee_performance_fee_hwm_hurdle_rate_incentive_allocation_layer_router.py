from fastapi import APIRouter, Body, Depends
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json

router = APIRouter(
    prefix="/api/fee-engine-management-fee-performance-fee-hwm-hurdle-rate-incentive-allocation-layer",
    tags=["fee-engine-management-fee-performance-fee-hwm-hurdle-rate-incentive-allocation-layer"],
)

PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
ENGINE_DIR = ARTIFACTS_DIR / "fee_engine_management_fee_performance_fee_hwm_hurdle_rate_incentive_allocation_layer"
DEFAULT_POLICY = {
    "retain_cycles": 365,
    "minimum_score": 95.0,
    "minimum_fee_readiness": 0.95,
    "minimum_hwm_readiness": 0.95,
    "minimum_incentive_readiness": 0.95,
    "maximum_uncrystallized_fee_exceptions": 0,
    "maximum_hwm_breaks": 0,
    "default_management_fee_pct": 2.0,
    "default_performance_fee_pct": 20.0,
    "default_hurdle_rate_pct": 5.0,
}

def _mu():
    from backend.app import qnt30557_multi_user_router as mu
    return mu

def _require_user():
    return _mu()._require_session()

def _pnl():
    from backend.app import qnt30586_pnl_ledger_router as module
    return module

def _capital_ledger():
    from backend.app import qnt30624_capital_ledger_router as module
    return module

def _waterfall():
    from backend.app import qnt30625_waterfall_router as module
    return module

def _investor_distribution_layer():
    from backend.app import qnt40003_investor_statement_packs_capital_account_waterfalls_lp_performance_distribution_layer_router as module
    return module

def _equalization_layer():
    from backend.app import qnt40008_investor_equalization_series_accounting_nav_entry_allocation_control_layer_router as module
    return module

def _safe(v: str) -> str:
    return hashlib.sha256((v or "").strip().lower().encode("utf-8")).hexdigest()[:24]

def _path(email: str) -> Path:
    ENGINE_DIR.mkdir(parents=True, exist_ok=True)
    return ENGINE_DIR / f"{_safe(email)}.json"

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def _append(store: dict, key: str, row: dict, retain: int):
    arr = list(store.get(key) or [])
    arr.insert(0, row)
    store[key] = arr[: max(int(retain or 1), 1)]

def _load(email: str) -> dict:
    path = _path(email)
    if not path.exists():
        data = {
            "email": email,
            "policy": dict(DEFAULT_POLICY),
            "runs": [],
            "alerts": [],
            "fee_term_events": [],
            "fee_snapshot_events": [],
            "fee_crystallization_events": [],
            "incentive_allocation_events": [],
            "latest_run": None,
            "last_context": {},
            "high_water_mark": 0.0,
        }
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return data
    return json.loads(path.read_text(encoding="utf-8"))

def _save(email: str, data: dict):
    _path(email).write_text(json.dumps(data, indent=2), encoding="utf-8")

def _context(email: str) -> dict:
    eq = _equalization_layer().summary({"email": email})
    pnl = _pnl().pnl_summary()
    ledger = _capital_ledger().capital_ledger_summary()
    wf = _waterfall().waterfall_summary()
    dist = _investor_distribution_layer().summary({"email": email})

    latest_run = wf.get("latest_run") or {}
    latest_notice = wf.get("latest_notice") or {}
    latest_position = (pnl.get("positions") or [{}])[0]
    latest_account = (ledger.get("accounts") or [{}])[0]

    return {
        "captured_at": _now_iso(),
        "equalization_layer_status": eq.get("investor_equalization_series_accounting_nav_entry_allocation_control_layer_status") or {},
        "pnl_summary": {
            "position_count": pnl.get("position_count", 0),
            "total_realized_pnl": pnl.get("total_realized_pnl", 0.0),
            "total_unrealized_pnl": pnl.get("total_unrealized_pnl", 0.0),
            "total_pnl": pnl.get("total_pnl", 0.0),
            "latest_symbol": latest_position.get("symbol"),
        },
        "capital_ledger_summary": {
            "account_count": ledger.get("account_count", 0),
            "total_funded_capital": ledger.get("total_funded_capital", 0.0),
            "total_nav": ledger.get("total_nav", 0.0),
            "latest_account_id": latest_account.get("account_id"),
        },
        "waterfall_summary": {
            "run_count": wf.get("run_count", 0),
            "notice_count": wf.get("notice_count", 0),
            "published_notice_count": wf.get("published_notice_count", 0),
            "latest_run_id": latest_run.get("run_id"),
            "latest_notice_id": latest_notice.get("notice_id"),
            "latest_lp_distribution_pool": latest_run.get("lp_distribution_pool", 0.0),
            "latest_gp_carry_amount": latest_run.get("gp_carry_amount", 0.0),
        },
        "investor_distribution_status": dist.get("investor_statement_packs_capital_account_waterfalls_lp_performance_distribution_layer_status") or {},
    }

def _summary_for_email(email: str) -> dict:
    s = _load(email)
    latest = s.get("latest_run") or {}
    return {
        "fee_engine_management_fee_performance_fee_hwm_hurdle_rate_incentive_allocation_layer_status": {
            "posture": latest.get("posture", "UNINITIALIZED"),
            "latest_score": latest.get("score"),
            "band": latest.get("band", "UNSET"),
            "run_count": len(s.get("runs") or []),
            "alert_count": len(s.get("alerts") or []),
            "fee_term_event_count": len(s.get("fee_term_events") or []),
            "fee_snapshot_event_count": len(s.get("fee_snapshot_events") or []),
            "fee_crystallization_event_count": len(s.get("fee_crystallization_events") or []),
            "incentive_allocation_event_count": len(s.get("incentive_allocation_events") or []),
            "operator_review_required": bool(latest.get("operator_review_required", False)),
        },
        "latest_run": latest,
        "alerts": s.get("alerts") or [],
        "policy": s.get("policy") or dict(DEFAULT_POLICY),
        "high_water_mark": s.get("high_water_mark", 0.0),
        "last_context": s.get("last_context") or {},
        "fee_term_events": s.get("fee_term_events") or [],
        "fee_snapshot_events": s.get("fee_snapshot_events") or [],
        "fee_crystallization_events": s.get("fee_crystallization_events") or [],
        "incentive_allocation_events": s.get("incentive_allocation_events") or [],
    }

def _band(score: float) -> str:
    if score >= 98.0:
        return "INSTITUTIONAL_INCENTIVE_LOCKED"
    if score >= 95.0:
        return "FEE_ENGINE_CLEAR"
    if score >= 91.0:
        return "FEE_ENGINE_WATCH"
    return "FEE_ENGINE_REMEDIATION_REQUIRED"

def _evaluate(email: str, payload: dict) -> dict:
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get("policy") or {})}
    ctx = _context(email)

    fee_readiness = float(payload.get("fee_readiness", 0.0) or 0.0)
    hwm_readiness = float(payload.get("hwm_readiness", 0.0) or 0.0)
    incentive_readiness = float(payload.get("incentive_readiness", 0.0) or 0.0)
    uncrystallized_fee_exceptions = int(payload.get("uncrystallized_fee_exceptions", 0) or 0)
    hwm_breaks = int(payload.get("hwm_breaks", 0) or 0)

    score = 100.0
    reasons = []
    alerts = []

    def penalize(metric: float, minimum: float, weight: float, reason: str, code: str):
        nonlocal score
        if metric < minimum:
            score -= round((minimum - metric) * weight, 2)
            reasons.append(reason)
            alerts.append(code)

    penalize(fee_readiness, float(policy.get("minimum_fee_readiness", 0.95)), 120.0, "fee readiness is below policy", "FEE_READINESS_WEAK")
    penalize(hwm_readiness, float(policy.get("minimum_hwm_readiness", 0.95)), 120.0, "high-water mark readiness is below policy", "HWM_READINESS_WEAK")
    penalize(incentive_readiness, float(policy.get("minimum_incentive_readiness", 0.95)), 125.0, "incentive allocation readiness is below policy", "INCENTIVE_READINESS_WEAK")

    if uncrystallized_fee_exceptions > int(policy.get("maximum_uncrystallized_fee_exceptions", 0)):
        score -= 7.0 + (uncrystallized_fee_exceptions - int(policy.get("maximum_uncrystallized_fee_exceptions", 0))) * 2.0
        reasons.append("uncrystallized fee exceptions exceed policy")
        alerts.append("FEE_EXCEPTIONS_EXCESS")
    if hwm_breaks > int(policy.get("maximum_hwm_breaks", 0)):
        score -= 7.0 + (hwm_breaks - int(policy.get("maximum_hwm_breaks", 0))) * 2.0
        reasons.append("high-water mark breaks exceed policy")
        alerts.append("HWM_BREAKS_EXCESS")

    if float((ctx.get("capital_ledger_summary") or {}).get("total_funded_capital", 0.0) or 0.0) <= 0.0:
        score -= 8.0
        reasons.append("funded capital is required before fee crystallization can clear")
        alerts.append("FUNDED_CAPITAL_REQUIRED")

    score = round(max(score, 0.0), 2)
    posture = _band(score)
    operator_review_required = bool(score < float(policy.get("minimum_score", 95.0)) or len(alerts) > 0)

    run = {
        "run_id": f"qnt40009_{int(datetime.now(timezone.utc).timestamp())}",
        "captured_at": _now_iso(),
        "score": score,
        "band": _band(score),
        "posture": posture,
        "operator_review_required": operator_review_required,
        "reasons": reasons,
        "alerts": alerts,
        "inputs": {
            "fee_readiness": fee_readiness,
            "hwm_readiness": hwm_readiness,
            "incentive_readiness": incentive_readiness,
            "uncrystallized_fee_exceptions": uncrystallized_fee_exceptions,
            "hwm_breaks": hwm_breaks,
        },
        "context": ctx,
    }
    _append(store, "runs", run, int(policy.get("retain_cycles", 365)))
    store["latest_run"] = run
    store["last_context"] = ctx
    if alerts:
        _append(store, "alerts", {
            "captured_at": _now_iso(),
            "alerts": alerts,
            "score": score,
            "posture": posture,
        }, int(policy.get("retain_cycles", 365)))
    _save(email, store)
    return run

@router.get("/summary")
def summary(user=Depends(_require_user)):
    return _summary_for_email(user.get("email"))

@router.post("/evaluate")
def evaluate(payload: dict = Body(...), user=Depends(_require_user)):
    return _evaluate(user.get("email"), payload)

@router.post("/set-fee-terms")
def set_fee_terms(payload: dict = Body(...), user=Depends(_require_user)):
    email = user.get("email")
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get("policy") or {}), **payload}
    store["policy"] = policy
    event = {
        "fee_term_event_id": f"terms_{int(datetime.now(timezone.utc).timestamp())}",
        "management_fee_pct": round(float(policy.get("default_management_fee_pct", 2.0)), 4),
        "performance_fee_pct": round(float(policy.get("default_performance_fee_pct", 20.0)), 4),
        "hurdle_rate_pct": round(float(policy.get("default_hurdle_rate_pct", 5.0)), 4),
        "captured_at": _now_iso(),
        "notes": str(payload.get("notes") or ""),
    }
    _append(store, "fee_term_events", event, int(policy.get("retain_cycles", 365)))
    _save(email, store)
    return {"ok": True, "policy": policy, "event": event}

@router.post("/record-fee-snapshot")
def record_fee_snapshot(payload: dict = Body(...), user=Depends(_require_user)):
    email = user.get("email")
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get("policy") or {})}
    total_pnl = float((_pnl().pnl_summary() or {}).get("total_pnl", 0.0) or 0.0)
    total_funded = float((_capital_ledger().capital_ledger_summary() or {}).get("total_funded_capital", 0.0) or 0.0)
    management_fee_pct = round(float(payload.get("management_fee_pct") or policy.get("default_management_fee_pct", 2.0)), 4)
    performance_fee_pct = round(float(payload.get("performance_fee_pct") or policy.get("default_performance_fee_pct", 20.0)), 4)
    hurdle_rate_pct = round(float(payload.get("hurdle_rate_pct") or policy.get("default_hurdle_rate_pct", 5.0)), 4)
    hwm_before = round(float(store.get("high_water_mark", 0.0) or 0.0), 2)
    gross_base = round(max(total_pnl, 0.0), 2)
    management_fee_value = round(total_funded * (management_fee_pct / 100.0) / 12.0, 2)
    hurdle_value = round(total_funded * (hurdle_rate_pct / 100.0), 2)
    eligible_perf_base = round(max(gross_base - max(hwm_before, hurdle_value), 0.0), 2)
    performance_fee_value = round(eligible_perf_base * (performance_fee_pct / 100.0), 2)
    net_after_fees = round(gross_base - management_fee_value - performance_fee_value, 2)
    high_water_mark_after = round(max(hwm_before, gross_base), 2)
    event = {
        "fee_snapshot_event_id": f"snap_{int(datetime.now(timezone.utc).timestamp())}",
        "gross_pnl_base": gross_base,
        "funded_capital_base": total_funded,
        "management_fee_pct": management_fee_pct,
        "performance_fee_pct": performance_fee_pct,
        "hurdle_rate_pct": hurdle_rate_pct,
        "management_fee_value": management_fee_value,
        "hurdle_value": hurdle_value,
        "performance_fee_value": performance_fee_value,
        "net_after_fees": net_after_fees,
        "high_water_mark_before": hwm_before,
        "high_water_mark_after": high_water_mark_after,
        "captured_at": _now_iso(),
        "notes": str(payload.get("notes") or ""),
    }
    store["high_water_mark"] = high_water_mark_after
    _append(store, "fee_snapshot_events", event, int(policy.get("retain_cycles", 365)))
    _save(email, store)
    return {"ok": True, "event": event}

@router.post("/crystallize-fees")
def crystallize_fees(payload: dict = Body(...), user=Depends(_require_user)):
    email = user.get("email")
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get("policy") or {})}
    latest_snapshot = (store.get("fee_snapshot_events") or [{}])[0]
    distributable_profit = round(float(latest_snapshot.get("net_after_fees", 0.0) or 0.0), 2)
    hurdle_rate_pct = round(float(latest_snapshot.get("hurdle_rate_pct", policy.get("default_hurdle_rate_pct", 5.0)) or 0.0), 4)
    gp_carry_pct = round(float(latest_snapshot.get("performance_fee_pct", policy.get("default_performance_fee_pct", 20.0)) or 0.0), 4)
    wf_res = _waterfall().waterfall_run({
        "distributable_profit": distributable_profit,
        "hurdle_rate_pct": hurdle_rate_pct,
        "gp_carry_pct": gp_carry_pct,
    })
    event = {
        "fee_crystallization_event_id": f"cryst_{int(datetime.now(timezone.utc).timestamp())}",
        "waterfall_run_id": ((wf_res or {}).get("run") or {}).get("run_id"),
        "distributable_profit": distributable_profit,
        "hurdle_rate_pct": hurdle_rate_pct,
        "gp_carry_pct": gp_carry_pct,
        "captured_at": _now_iso(),
        "notes": str(payload.get("notes") or ""),
    }
    _append(store, "fee_crystallization_events", event, int(policy.get("retain_cycles", 365)))
    _save(email, store)
    return {"ok": True, "event": event, "waterfall": wf_res}

@router.post("/allocate-incentive")
def allocate_incentive(payload: dict = Body(...), user=Depends(_require_user)):
    email = user.get("email")
    store = _load(email)
    notices = (_waterfall().waterfall_summary() or {}).get("distribution_notices") or []
    published_ids = []
    for notice in notices[: min(len(notices), 10)]:
        res = _waterfall().publish_notice({"notice_id": notice.get("notice_id")})
        if (res or {}).get("status") == "published":
            published_ids.append(notice.get("notice_id"))
    event = {
        "incentive_allocation_event_id": f"incent_{int(datetime.now(timezone.utc).timestamp())}",
        "published_notice_ids": published_ids,
        "published_count": len(published_ids),
        "captured_at": _now_iso(),
        "notes": str(payload.get("notes") or ""),
    }
    _append(store, "incentive_allocation_events", event, int((store.get("policy") or DEFAULT_POLICY).get("retain_cycles", 365)))
    _save(email, store)
    return {"ok": True, "event": event}

@router.get("/policy")
def policy(user=Depends(_require_user)):
    return {"policy": _load(user.get("email")).get("policy") or dict(DEFAULT_POLICY)}

@router.post("/policy")
def update_policy(payload: dict = Body(...), user=Depends(_require_user)):
    email = user.get("email")
    store = _load(email)
    store["policy"] = {**dict(DEFAULT_POLICY), **(store.get("policy") or {}), **payload}
    _save(email, store)
    return {"ok": True, "policy": store["policy"]}

@router.post("/bootstrap-demo")
def bootstrap_demo(user=Depends(_require_user)):
    email = user.get("email")
    _equalization_layer().bootstrap_demo({"email": email})
    set_fee_terms({
        "default_management_fee_pct": 2.0,
        "default_performance_fee_pct": 20.0,
        "default_hurdle_rate_pct": 5.0,
        "notes": "bootstrap terms",
    }, user)
    record_fee_snapshot({"notes": "bootstrap fee snapshot"}, user)
    crystallize_fees({"notes": "bootstrap crystallization"}, user)
    allocate_incentive({"notes": "bootstrap incentive allocation"}, user)
    run = _evaluate(email, {
        "fee_readiness": 0.99,
        "hwm_readiness": 0.98,
        "incentive_readiness": 0.98,
        "uncrystallized_fee_exceptions": 0,
        "hwm_breaks": 0,
    })
    return {"ok": True, "run": run, "summary": _summary_for_email(email)}
