from fastapi import APIRouter, Body, Depends, HTTPException
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json

router = APIRouter(
    prefix="/api/investor-statement-packs-capital-account-waterfalls-lp-performance-distribution-layer",
    tags=["investor-statement-packs-capital-account-waterfalls-lp-performance-distribution-layer"],
)

PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
ENGINE_DIR = ARTIFACTS_DIR / "investor_statement_packs_capital_account_waterfalls_lp_performance_distribution_layer"
DEFAULT_POLICY = {
    "retain_cycles": 365,
    "minimum_score": 95.0,
    "minimum_capital_account_coverage": 0.95,
    "minimum_distribution_readiness": 0.96,
    "minimum_lp_metric_completeness": 0.96,
    "maximum_pending_acknowledgements": 1,
    "maximum_open_investor_exceptions": 0,
    "maximum_statement_stale_days": 31,
    "require_capital_ledger_ready": True,
    "require_waterfall_ready": True,
    "require_statement_pack_ready": True,
    "require_delivery_log_ready": True,
    "require_pnl_metrics_ready": True,
}


def _mu():
    from backend.app import qnt30557_multi_user_router as mu
    return mu


def _capital():
    from backend.app import qnt30624_capital_ledger_router as module
    return module


def _waterfall():
    from backend.app import qnt30587_waterfall_router as module
    return module


def _packs():
    from backend.app import qnt30588_statement_pack_router as module
    return module


def _delivery():
    from backend.app import qnt30589_report_delivery_log_router as module
    return module


def _metrics():
    from backend.app import qnt40002_real_time_pnl_performance_attribution_investor_metrics_layer_router as module
    return module


def _safe(v: str) -> str:
    return hashlib.sha256((v or "").strip().lower().encode("utf-8")).hexdigest()[:24]


def _path(email: str) -> Path:
    ENGINE_DIR.mkdir(parents=True, exist_ok=True)
    return ENGINE_DIR / f"{_safe(email)}.json"


def _require_user():
    return _mu()._require_session()


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
            "statement_pack_runs": [],
            "capital_waterfalls": [],
            "lp_distributions": [],
            "distribution_acknowledgements": [],
            "latest_run": None,
            "last_context": {},
        }
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return data
    return json.loads(path.read_text(encoding="utf-8"))


def _save(email: str, data: dict):
    _path(email).write_text(json.dumps(data, indent=2), encoding="utf-8")


def _distribution_context(email: str) -> dict:
    capital = _capital().capital_ledger_summary()
    waterfall = _waterfall().performance_waterfall_summary()
    packs = _packs().statement_packs_summary()
    delivery = _delivery().report_delivery_log_summary()
    metrics_summary = _metrics()._summary_for_email(email)
    latest_pack = packs.get("latest_pack") or {}
    latest_waterfall = waterfall.get("latest_snapshot") or {}
    live_metrics = metrics_summary.get("latest_run") or {}
    return {
        "captured_at": _now_iso(),
        "capital_summary": {
            "account_count": capital.get("account_count", 0),
            "entry_count": capital.get("entry_count", 0),
            "allocation_count": capital.get("allocation_count", 0),
            "total_committed_capital": capital.get("total_committed_capital", 0.0),
            "total_funded_capital": capital.get("total_funded_capital", 0.0),
            "total_nav": capital.get("total_nav", 0.0),
        },
        "waterfall_summary": {
            "snapshot_count": waterfall.get("snapshot_count", 0),
            "net_pnl_after_fees": latest_waterfall.get("net_pnl_after_fees", 0.0),
            "gross_total_pnl": latest_waterfall.get("gross_total_pnl", 0.0),
        },
        "statement_pack_summary": {
            "pack_count": packs.get("pack_count", 0),
            "delivered_count": packs.get("delivered_count", 0),
            "latest_pack_id": latest_pack.get("pack_id"),
            "latest_pack_sections": len(latest_pack.get("sections") or []),
            "latest_delivery_status": latest_pack.get("delivery_status"),
        },
        "delivery_summary": {
            "delivery_count": delivery.get("delivery_count", 0),
            "acknowledged_count": delivery.get("acknowledged_count", 0),
            "pending_ack_count": delivery.get("pending_ack_count", 0),
            "latest_event": delivery.get("latest_event"),
        },
        "investor_metrics_summary": {
            "posture": live_metrics.get("posture", "UNINITIALIZED"),
            "score": live_metrics.get("score"),
            "net_pnl": live_metrics.get("net_pnl", 0.0),
            "portfolio_return_pct": live_metrics.get("portfolio_return_pct", 0.0),
            "max_drawdown_pct": live_metrics.get("max_drawdown_pct", 0.0),
            "sharpe_ratio": live_metrics.get("sharpe_ratio", 0.0),
        },
    }


def _summary_for_email(email: str) -> dict:
    s = _load(email)
    latest = s.get("latest_run") or {}
    return {
        "investor_statement_packs_capital_account_waterfalls_lp_performance_distribution_layer_status": {
            "posture": latest.get("posture", "UNINITIALIZED"),
            "latest_score": latest.get("score"),
            "band": latest.get("band", "UNSET"),
            "run_count": len(s.get("runs") or []),
            "alert_count": len(s.get("alerts") or []),
            "statement_pack_run_count": len(s.get("statement_pack_runs") or []),
            "capital_waterfall_count": len(s.get("capital_waterfalls") or []),
            "distribution_count": len(s.get("lp_distributions") or []),
            "acknowledgement_count": len(s.get("distribution_acknowledgements") or []),
            "operator_review_required": bool(latest.get("operator_review_required", False)),
        },
        "latest_run": latest,
        "alerts": s.get("alerts") or [],
        "policy": s.get("policy") or dict(DEFAULT_POLICY),
        "last_context": s.get("last_context") or {},
        "statement_pack_runs": s.get("statement_pack_runs") or [],
        "capital_waterfalls": s.get("capital_waterfalls") or [],
        "lp_distributions": s.get("lp_distributions") or [],
        "distribution_acknowledgements": s.get("distribution_acknowledgements") or [],
    }


def _band(score: float) -> str:
    if score >= 98.0:
        return "INSTITUTIONAL_LP_DISTRIBUTION_READY"
    if score >= 95.0:
        return "LP_DISTRIBUTION_CLEAR"
    if score >= 91.0:
        return "LP_DISTRIBUTION_WATCH"
    return "LP_DISTRIBUTION_REMEDIATION_REQUIRED"


def _evaluate(email: str, payload: dict) -> dict:
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get("policy") or {})}
    ctx = _distribution_context(email)

    capital_account_coverage = float(payload.get("capital_account_coverage", 0.0) or 0.0)
    distribution_readiness = float(payload.get("distribution_readiness", 0.0) or 0.0)
    lp_metric_completeness = float(payload.get("lp_metric_completeness", 0.0) or 0.0)
    pending_acknowledgements = int(payload.get("pending_acknowledgements", 0) or 0)
    open_investor_exceptions = int(payload.get("open_investor_exceptions", 0) or 0)
    stale_days = int(payload.get("stale_days", 0) or 0)
    undelivered_packs = int(payload.get("undelivered_packs", 0) or 0)

    score = 100.0
    reasons = []
    alerts = []

    if capital_account_coverage < float(policy.get("minimum_capital_account_coverage", 0.95)):
        score -= round((float(policy.get("minimum_capital_account_coverage", 0.95)) - capital_account_coverage) * 120.0, 2)
        reasons.append("capital account coverage is below policy")
        alerts.append("CAPITAL_ACCOUNT_COVERAGE_WEAK")
    if distribution_readiness < float(policy.get("minimum_distribution_readiness", 0.96)):
        score -= round((float(policy.get("minimum_distribution_readiness", 0.96)) - distribution_readiness) * 115.0, 2)
        reasons.append("distribution readiness is below policy")
        alerts.append("DISTRIBUTION_READINESS_WEAK")
    if lp_metric_completeness < float(policy.get("minimum_lp_metric_completeness", 0.96)):
        score -= round((float(policy.get("minimum_lp_metric_completeness", 0.96)) - lp_metric_completeness) * 110.0, 2)
        reasons.append("lp metric completeness is below policy")
        alerts.append("LP_METRIC_COMPLETENESS_WEAK")
    if pending_acknowledgements > int(policy.get("maximum_pending_acknowledgements", 1)):
        score -= min((pending_acknowledgements - int(policy.get("maximum_pending_acknowledgements", 1))) * 6.0, 24.0)
        reasons.append("pending investor acknowledgements exceed policy")
        alerts.append("PENDING_ACKS_EXCEED_POLICY")
    if open_investor_exceptions > int(policy.get("maximum_open_investor_exceptions", 0)):
        score -= min(open_investor_exceptions * 8.0, 24.0)
        reasons.append("open investor exceptions remain unresolved")
        alerts.append("OPEN_INVESTOR_EXCEPTIONS")
    if stale_days > int(policy.get("maximum_statement_stale_days", 31)):
        score -= min((stale_days - int(policy.get("maximum_statement_stale_days", 31))) * 1.25, 18.0)
        reasons.append("statement or distribution cycle is stale")
        alerts.append("STATEMENT_CYCLE_STALE")
    if undelivered_packs > 0:
        score -= min(undelivered_packs * 5.0, 20.0)
        reasons.append("undelivered statement packs remain open")
        alerts.append("UNDELIVERED_PACKS_OPEN")

    capital_ready = (ctx.get("capital_summary") or {}).get("account_count", 0) > 0 and (ctx.get("capital_summary") or {}).get("entry_count", 0) > 0
    waterfall_ready = (ctx.get("waterfall_summary") or {}).get("snapshot_count", 0) > 0
    pack_ready = (ctx.get("statement_pack_summary") or {}).get("pack_count", 0) > 0 and (ctx.get("statement_pack_summary") or {}).get("latest_pack_sections", 0) >= 3
    delivery_ready = (ctx.get("delivery_summary") or {}).get("delivery_count", 0) > 0
    pnl_metrics_ready = (ctx.get("investor_metrics_summary") or {}).get("posture", "UNINITIALIZED") != "UNINITIALIZED"

    if policy.get("require_capital_ledger_ready", True) and not capital_ready:
        score -= 8.0
        reasons.append("capital ledger is not sufficiently initialized")
        alerts.append("CAPITAL_LEDGER_NOT_READY")
    if policy.get("require_waterfall_ready", True) and not waterfall_ready:
        score -= 8.0
        reasons.append("capital account waterfall is not sufficiently initialized")
        alerts.append("WATERFALL_NOT_READY")
    if policy.get("require_statement_pack_ready", True) and not pack_ready:
        score -= 8.0
        reasons.append("statement pack generation is not sufficiently initialized")
        alerts.append("STATEMENT_PACK_NOT_READY")
    if policy.get("require_delivery_log_ready", True) and not delivery_ready:
        score -= 8.0
        reasons.append("distribution delivery evidence is not sufficiently initialized")
        alerts.append("DELIVERY_LOG_NOT_READY")
    if policy.get("require_pnl_metrics_ready", True) and not pnl_metrics_ready:
        score -= 8.0
        reasons.append("pnl and investor metric layer is not sufficiently initialized")
        alerts.append("INVESTOR_METRICS_NOT_READY")

    score = max(round(score, 2), 0.0)
    band = _band(score)
    posture = "LP_DISTRIBUTION_CLEAR" if score >= float(policy.get("minimum_score", 95.0)) else ("LP_DISTRIBUTION_WATCH" if score >= 91.0 else "LP_DISTRIBUTION_REMEDIATION_REQUIRED")
    operator_review_required = posture != "LP_DISTRIBUTION_CLEAR" or open_investor_exceptions > 0 or pending_acknowledgements > int(policy.get("maximum_pending_acknowledgements", 1))

    row = {
        "mission": "QNT40003",
        "evaluated_at": _now_iso(),
        "score": score,
        "band": band,
        "posture": posture,
        "operator_review_required": operator_review_required,
        "capital_account_coverage": capital_account_coverage,
        "distribution_readiness": distribution_readiness,
        "lp_metric_completeness": lp_metric_completeness,
        "pending_acknowledgements": pending_acknowledgements,
        "open_investor_exceptions": open_investor_exceptions,
        "stale_days": stale_days,
        "undelivered_packs": undelivered_packs,
        "reasons": reasons,
        "alerts": alerts,
        "context": ctx,
    }
    _append(store, "runs", row, policy.get("retain_cycles", 365))
    for code in alerts:
        _append(store, "alerts", {"code": code, "at": row["evaluated_at"]}, policy.get("retain_cycles", 365))
    store["latest_run"] = row
    store["last_context"] = ctx
    _save(email, store)
    return row


@router.get("/summary")
def summary(user=Depends(_require_user)):
    email = (user or {}).get("email")
    if not email:
        raise HTTPException(status_code=401, detail="session required")
    return {
        "ok": True,
        **_summary_for_email(email),
        "capital_ledger": _capital().capital_ledger_summary(),
        "waterfall": _waterfall().performance_waterfall_summary(),
        "statement_packs": _packs().statement_packs_summary(),
        "delivery_log": _delivery().report_delivery_log_summary(),
        "investor_metrics": _metrics()._summary_for_email(email),
    }


@router.post("/evaluate")
def evaluate(payload: dict = Body(...), user=Depends(_require_user)):
    email = (user or {}).get("email")
    if not email:
        raise HTTPException(status_code=401, detail="session required")
    return {"ok": True, "run": _evaluate(email, payload), **_summary_for_email(email)}


@router.post("/prepare-statement-pack")
def prepare_statement_pack(payload: dict = Body(None), user=Depends(_require_user)):
    email = (user or {}).get("email")
    if not email:
        raise HTTPException(status_code=401, detail="session required")
    result = _packs().statement_packs_generate(payload or {})
    pack = result.get("pack") or {}
    row = {
        "captured_at": _now_iso(),
        "pack_id": pack.get("pack_id"),
        "title": pack.get("title"),
        "section_count": len(pack.get("sections") or []),
        "delivery_status": pack.get("delivery_status"),
    }
    store = _load(email)
    _append(store, "statement_pack_runs", row, (store.get("policy") or {}).get("retain_cycles", 365))
    _save(email, store)
    return {"ok": True, "statement_pack": row, "pack": pack}


@router.post("/capture-capital-waterfall")
def capture_capital_waterfall(payload: dict = Body(None), user=Depends(_require_user)):
    email = (user or {}).get("email")
    if not email:
        raise HTTPException(status_code=401, detail="session required")
    result = _waterfall().performance_waterfall_calculate(payload or {})
    snap = result.get("snapshot") or {}
    row = {
        "captured_at": _now_iso(),
        "snapshot_id": snap.get("snapshot_id"),
        "gross_total_pnl": snap.get("gross_total_pnl", 0.0),
        "management_fee_value": snap.get("management_fee_value", 0.0),
        "performance_fee_value": snap.get("performance_fee_value", 0.0),
        "net_pnl_after_fees": snap.get("net_pnl_after_fees", 0.0),
    }
    store = _load(email)
    _append(store, "capital_waterfalls", row, (store.get("policy") or {}).get("retain_cycles", 365))
    _save(email, store)
    return {"ok": True, "capital_waterfall": row, "snapshot": snap}


@router.post("/distribute-pack")
def distribute_pack(payload: dict = Body(None), user=Depends(_require_user)):
    email = (user or {}).get("email")
    if not email:
        raise HTTPException(status_code=401, detail="session required")
    packs = _packs()._load(email)
    latest = (packs.get("packs") or [None])[0]
    if not latest:
        latest = (_packs().statement_packs_generate({"title": "LP Performance Distribution Pack"}).get("pack") or {})
    delivered = _packs().statement_packs_deliver({
        "pack_id": latest.get("pack_id"),
        "channel": str((payload or {}).get("channel") or "portal_simulated"),
    })
    log_result = _delivery().report_delivery_log_latest({
        "channel": str((payload or {}).get("channel") or "portal_simulated"),
        "notes": str((payload or {}).get("notes") or "lp distribution package released"),
    })
    event = log_result.get("event") or {}
    row = {
        "captured_at": _now_iso(),
        "pack_id": latest.get("pack_id"),
        "delivery_status": (delivered.get("pack") or {}).get("delivery_status"),
        "channel": event.get("channel"),
        "event_id": event.get("event_id"),
        "ack_status": event.get("ack_status"),
    }
    store = _load(email)
    _append(store, "lp_distributions", row, (store.get("policy") or {}).get("retain_cycles", 365))
    _save(email, store)
    return {"ok": True, "distribution": row, "delivery": delivered, "log": log_result}


@router.post("/acknowledge-distribution")
def acknowledge_distribution(payload: dict = Body(None), user=Depends(_require_user)):
    email = (user or {}).get("email")
    if not email:
        raise HTTPException(status_code=401, detail="session required")
    delivery = _delivery().report_delivery_log_summary()
    event = delivery.get("latest_event") or {}
    event_id = str((payload or {}).get("event_id") or event.get("event_id") or "")
    if not event_id:
        raise HTTPException(status_code=404, detail="distribution event not found")
    ack = _delivery().report_delivery_log_ack({
        "event_id": event_id,
        "notes": str((payload or {}).get("notes") or "lp acknowledgement recorded"),
    })
    event = ack.get("event") or {}
    row = {
        "captured_at": _now_iso(),
        "event_id": event.get("event_id"),
        "pack_id": event.get("pack_id"),
        "ack_status": event.get("ack_status"),
        "acknowledged_at": event.get("acknowledged_at"),
    }
    store = _load(email)
    _append(store, "distribution_acknowledgements", row, (store.get("policy") or {}).get("retain_cycles", 365))
    _save(email, store)
    return {"ok": True, "acknowledgement": row, "event": event}


@router.get("/policy")
def policy(user=Depends(_require_user)):
    email = (user or {}).get("email")
    if not email:
        raise HTTPException(status_code=401, detail="session required")
    return {"ok": True, "policy": _load(email).get("policy") or dict(DEFAULT_POLICY)}


@router.post("/bootstrap-demo")
def bootstrap_demo(user=Depends(_require_user)):
    email = (user or {}).get("email")
    if not email:
        raise HTTPException(status_code=401, detail="session required")

    # Ensure the live pnl / investor metric layer is already seeded.
    _metrics().bootstrap_demo(user)

    investor_id = "lp_demo_001"
    _capital().create_account({
        "investor_id": investor_id,
        "committed_capital": 250000.0,
    })
    _capital().add_entry({
        "investor_id": investor_id,
        "amount": 150000.0,
        "entry_type": "funding",
        "description": "bootstrap funding",
    })
    _capital().allocate_capital({
        "investor_id": investor_id,
        "strategy": "core",
        "sleeve": "main",
        "amount": 90000.0,
    })
    _capital().recalculate()

    waterfall_result = capture_capital_waterfall({}, user)
    pack_result = prepare_statement_pack({"title": "LP Performance Distribution Pack"}, user)
    distribution_result = distribute_pack({"channel": "portal_simulated", "notes": "bootstrap lp distribution"}, user)
    acknowledge_result = acknowledge_distribution({"notes": "bootstrap acknowledgement"}, user)

    run = _evaluate(email, {
        "capital_account_coverage": 0.99,
        "distribution_readiness": 0.985,
        "lp_metric_completeness": 0.982,
        "pending_acknowledgements": 0,
        "open_investor_exceptions": 0,
        "stale_days": 2,
        "undelivered_packs": 0,
    })
    return {
        "ok": True,
        "run": run,
        "capital_waterfall": waterfall_result.get("capital_waterfall"),
        "statement_pack": pack_result.get("statement_pack"),
        "distribution": distribution_result.get("distribution"),
        "acknowledgement": acknowledge_result.get("acknowledgement"),
        **_summary_for_email(email),
    }
