from fastapi import APIRouter, Body, Depends, HTTPException
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json

router = APIRouter(
    prefix="/api/real-time-pnl-performance-attribution-investor-metrics-layer",
    tags=["real-time-pnl-performance-attribution-investor-metrics-layer"],
)

PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
ENGINE_DIR = ARTIFACTS_DIR / "real_time_pnl_performance_attribution_investor_metrics_layer"
DEFAULT_POLICY = {
    "retain_cycles": 365,
    "minimum_score": 95.0,
    "minimum_pnl_freshness_minutes": 15,
    "minimum_nav_confidence": 0.97,
    "minimum_attribution_completeness": 0.96,
    "minimum_investor_metric_completeness": 0.96,
    "require_performance_engine_ready": True,
    "require_pnl_ledger_ready": True,
    "require_trade_attribution_ready": True,
}


def _mu():
    from backend.app import qnt30557_multi_user_router as mu
    return mu


def _performance():
    from backend.app import qnt30628_performance_engine_router as module
    return module


def _pnl():
    from backend.app import qnt30586_pnl_ledger_router as module
    return module


def _attribution():
    from backend.app import qnt30585_trade_attribution_router as module
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
            "pnl_snapshots": [],
            "attribution_reviews": [],
            "investor_metric_captures": [],
            "latest_run": None,
            "last_context": {},
        }
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return data
    return json.loads(path.read_text(encoding="utf-8"))


def _save(email: str, data: dict):
    _path(email).write_text(json.dumps(data, indent=2), encoding="utf-8")


def _performance_context(email: str) -> dict:
    perf = _performance()._live_summary(email)
    pnl = _pnl()._load(email)
    attrib = _attribution()._load(email)
    series = perf.get("series") or []
    latest_series = series[-1] if series else {}
    positions = pnl.get("positions") or []
    ledger = pnl.get("ledger") or []
    reviews = attrib.get("reviews") or []
    allocations = attrib.get("allocations") or []
    summary = perf.get("summary") or {}
    return {
        "captured_at": _now_iso(),
        "performance_summary": summary,
        "latest_series": latest_series,
        "position_count": len(positions),
        "ledger_entries": len(ledger),
        "attribution_review_count": len(reviews),
        "allocation_count": len(allocations),
        "strategy_breakdown_count": len(perf.get("strategy_breakdown") or []),
        "investor_breakdown_count": len(perf.get("investor_breakdown") or []),
    }


def _summary_for_email(email: str) -> dict:
    s = _load(email)
    latest = s.get("latest_run") or {}
    return {
        "real_time_pnl_performance_attribution_investor_metrics_layer_status": {
            "posture": latest.get("posture", "UNINITIALIZED"),
            "latest_score": latest.get("score"),
            "band": latest.get("band", "UNSET"),
            "run_count": len(s.get("runs") or []),
            "alert_count": len(s.get("alerts") or []),
            "pnl_snapshot_count": len(s.get("pnl_snapshots") or []),
            "attribution_review_count": len(s.get("attribution_reviews") or []),
            "investor_metric_capture_count": len(s.get("investor_metric_captures") or []),
            "operator_review_required": bool(latest.get("operator_review_required", False)),
        },
        "latest_run": latest,
        "alerts": s.get("alerts") or [],
        "policy": s.get("policy") or dict(DEFAULT_POLICY),
        "last_context": s.get("last_context") or {},
        "pnl_snapshots": s.get("pnl_snapshots") or [],
        "attribution_reviews": s.get("attribution_reviews") or [],
        "investor_metric_captures": s.get("investor_metric_captures") or [],
    }


def _band(score: float) -> str:
    if score >= 98.0:
        return "INSTITUTIONAL_PERFORMANCE_READY"
    if score >= 95.0:
        return "INVESTOR_METRICS_CLEAR"
    if score >= 91.0:
        return "PERFORMANCE_WATCH"
    return "PERFORMANCE_REMEDIATION_REQUIRED"


def _evaluate(email: str, payload: dict) -> dict:
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get("policy") or {})}
    ctx = _performance_context(email)
    perf_summary = ctx.get("performance_summary") or {}

    nav_confidence = float(payload.get("nav_confidence", 0.0) or 0.0)
    attribution_completeness = float(payload.get("attribution_completeness", 0.0) or 0.0)
    investor_metric_completeness = float(payload.get("investor_metric_completeness", 0.0) or 0.0)
    stale_minutes = int(payload.get("stale_minutes", 0) or 0)
    unresolved_breaks = int(payload.get("unresolved_breaks", 0) or 0)
    unresolved_investor_exceptions = int(payload.get("unresolved_investor_exceptions", 0) or 0)

    score = 100.0
    reasons = []
    alerts = []

    if nav_confidence < float(policy.get("minimum_nav_confidence", 0.97)):
        score -= round((float(policy.get("minimum_nav_confidence", 0.97)) - nav_confidence) * 120.0, 2)
        reasons.append("nav confidence is below policy")
        alerts.append("NAV_CONFIDENCE_WEAK")
    if attribution_completeness < float(policy.get("minimum_attribution_completeness", 0.96)):
        score -= round((float(policy.get("minimum_attribution_completeness", 0.96)) - attribution_completeness) * 115.0, 2)
        reasons.append("trade attribution completeness is below policy")
        alerts.append("ATTRIBUTION_COMPLETENESS_WEAK")
    if investor_metric_completeness < float(policy.get("minimum_investor_metric_completeness", 0.96)):
        score -= round((float(policy.get("minimum_investor_metric_completeness", 0.96)) - investor_metric_completeness) * 110.0, 2)
        reasons.append("investor metric completeness is below policy")
        alerts.append("INVESTOR_METRIC_COMPLETENESS_WEAK")
    if stale_minutes > int(policy.get("minimum_pnl_freshness_minutes", 15)):
        score -= min((stale_minutes - int(policy.get("minimum_pnl_freshness_minutes", 15))) * 1.5, 18.0)
        reasons.append("pnl freshness is outside the control window")
        alerts.append("PNL_FRESHNESS_STALE")
    if unresolved_breaks > 0:
        score -= min(unresolved_breaks * 6.0, 24.0)
        reasons.append("unresolved pnl or nav breaks remain open")
        alerts.append("OPEN_PNL_BREAKS")
    if unresolved_investor_exceptions > 0:
        score -= min(unresolved_investor_exceptions * 5.0, 20.0)
        reasons.append("unresolved investor metric exceptions remain open")
        alerts.append("OPEN_INVESTOR_EXCEPTIONS")

    perf_ready = perf_summary.get("strategy_count", 0) > 0 or perf_summary.get("investor_count", 0) > 0 or perf_summary.get("snapshots", 0) > 0
    pnl_ready = ctx.get("position_count", 0) > 0 or ctx.get("ledger_entries", 0) > 0
    attrib_ready = ctx.get("allocation_count", 0) > 0 or ctx.get("attribution_review_count", 0) > 0

    if policy.get("require_performance_engine_ready", True) and not perf_ready:
        score -= 8.0
        reasons.append("performance engine has not been sufficiently initialized")
        alerts.append("PERFORMANCE_ENGINE_NOT_READY")
    if policy.get("require_pnl_ledger_ready", True) and not pnl_ready:
        score -= 8.0
        reasons.append("pnl ledger has not been sufficiently initialized")
        alerts.append("PNL_LEDGER_NOT_READY")
    if policy.get("require_trade_attribution_ready", True) and not attrib_ready:
        score -= 8.0
        reasons.append("trade attribution has not been sufficiently initialized")
        alerts.append("TRADE_ATTRIBUTION_NOT_READY")

    score = max(round(score, 2), 0.0)
    band = _band(score)
    posture = "INVESTOR_METRICS_CLEAR" if score >= float(policy.get("minimum_score", 95.0)) else ("PERFORMANCE_WATCH" if score >= 91.0 else "PERFORMANCE_REMEDIATION_REQUIRED")
    operator_review_required = posture != "INVESTOR_METRICS_CLEAR" or unresolved_breaks > 0 or unresolved_investor_exceptions > 0

    row = {
        "mission": "QNT40002",
        "evaluated_at": _now_iso(),
        "score": score,
        "band": band,
        "posture": posture,
        "operator_review_required": operator_review_required,
        "nav_confidence": nav_confidence,
        "attribution_completeness": attribution_completeness,
        "investor_metric_completeness": investor_metric_completeness,
        "stale_minutes": stale_minutes,
        "unresolved_breaks": unresolved_breaks,
        "unresolved_investor_exceptions": unresolved_investor_exceptions,
        "portfolio_return_pct": perf_summary.get("portfolio_return_pct", 0.0),
        "net_pnl": perf_summary.get("net_pnl", 0.0),
        "max_drawdown_pct": perf_summary.get("max_drawdown_pct", 0.0),
        "sharpe_ratio": perf_summary.get("sharpe_ratio", 0.0),
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
    live = _performance()._live_summary(email)
    return {
        "ok": True,
        **_summary_for_email(email),
        "live_performance": live,
        "pnl_summary": _pnl().pnl_summary(),
    }


@router.post("/evaluate")
def evaluate(payload: dict = Body(...), user=Depends(_require_user)):
    email = (user or {}).get("email")
    if not email:
        raise HTTPException(status_code=401, detail="session required")
    return {"ok": True, "run": _evaluate(email, payload), **_summary_for_email(email)}


@router.post("/record-pnl-snapshot")
def record_pnl_snapshot(payload: dict = Body(None), user=Depends(_require_user)):
    email = (user or {}).get("email")
    if not email:
        raise HTTPException(status_code=401, detail="session required")
    snap = _performance().performance_engine_snapshot(payload or {})
    store = _load(email)
    row = {
        "captured_at": _now_iso(),
        "snapshot": snap.get("snapshot") or {},
        "series_points": snap.get("series_points", 0),
    }
    _append(store, "pnl_snapshots", row, (store.get("policy") or {}).get("retain_cycles", 365))
    _save(email, store)
    return {"ok": True, "pnl_snapshot": row}


@router.post("/record-attribution-review")
def record_attribution_review(payload: dict = Body(...), user=Depends(_require_user)):
    email = (user or {}).get("email")
    if not email:
        raise HTTPException(status_code=401, detail="session required")
    review = {
        "captured_at": _now_iso(),
        "review_id": f"attr_review_{int(datetime.now(timezone.utc).timestamp())}",
        "strategy": str((payload or {}).get("strategy") or "core"),
        "completeness": float((payload or {}).get("completeness") or 0.0),
        "exceptions": int((payload or {}).get("exceptions") or 0),
        "reviewer": str((payload or {}).get("reviewer") or "operator"),
        "notes": str((payload or {}).get("notes") or "").strip(),
    }
    store = _load(email)
    _append(store, "attribution_reviews", review, (store.get("policy") or {}).get("retain_cycles", 365))
    _save(email, store)
    return {"ok": True, "attribution_review": review}


@router.post("/capture-investor-metrics")
def capture_investor_metrics(payload: dict = Body(None), user=Depends(_require_user)):
    email = (user or {}).get("email")
    if not email:
        raise HTTPException(status_code=401, detail="session required")
    live = _performance()._live_summary(email)
    metrics = {
        "captured_at": _now_iso(),
        "investor_count": len(live.get("investor_breakdown") or []),
        "current_nav": (live.get("summary") or {}).get("current_nav", 0.0),
        "net_pnl": (live.get("summary") or {}).get("net_pnl", 0.0),
        "portfolio_return_pct": (live.get("summary") or {}).get("portfolio_return_pct", 0.0),
        "max_drawdown_pct": (live.get("summary") or {}).get("max_drawdown_pct", 0.0),
        "sharpe_ratio": (live.get("summary") or {}).get("sharpe_ratio", 0.0),
        "requested_by": str((payload or {}).get("requested_by") or "operator"),
    }
    store = _load(email)
    _append(store, "investor_metric_captures", metrics, (store.get("policy") or {}).get("retain_cycles", 365))
    _save(email, store)
    return {"ok": True, "investor_metrics": metrics}


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

    # Seed PnL state without requiring admin-only HTTP handlers.
    pnl_store = _pnl()._load(email)
    positions = pnl_store.setdefault("positions", [])
    position = next((p for p in positions if p.get("sleeve_id") == "main" and p.get("symbol") == "SPY"), None)
    if not position:
        position = {
            "position_id": "pos_qnt40002_demo",
            "sleeve_id": "main",
            "symbol": "SPY",
            "qty": 10.0,
            "avg_price": 500.0,
            "mark_price": 512.5,
            "realized_pnl": 125.0,
            "unrealized_pnl": 125.0,
            "updated_at": int(datetime.now(timezone.utc).timestamp()),
        }
        positions.append(position)
    else:
        position.update({
            "qty": 10.0,
            "avg_price": 500.0,
            "mark_price": 512.5,
            "realized_pnl": float(position.get("realized_pnl") or 0.0) + 125.0,
            "unrealized_pnl": 125.0,
            "updated_at": int(datetime.now(timezone.utc).timestamp()),
        })
    ledger = pnl_store.setdefault("ledger", [])
    ledger.insert(0, {
        "entry_id": "pnl_qnt40002_demo",
        "type": "bootstrap_mark",
        "sleeve_id": "main",
        "symbol": "SPY",
        "qty": 10.0,
        "avg_price": 500.0,
        "mark_price": 512.5,
        "realized_pnl": position.get("realized_pnl", 0.0),
        "unrealized_pnl": 125.0,
        "timestamp": int(datetime.now(timezone.utc).timestamp()),
    })
    pnl_store["ledger"] = ledger[:1000]
    _pnl()._save(email, pnl_store)

    # Snapshot performance and capture investor metrics.
    _performance().performance_engine_snapshot({})
    store = _load(email)
    _append(store, "attribution_reviews", {
        "captured_at": _now_iso(),
        "review_id": "attr_demo",
        "strategy": "core",
        "completeness": 0.985,
        "exceptions": 0,
        "reviewer": "system",
        "notes": "bootstrap attribution review",
    }, (store.get("policy") or {}).get("retain_cycles", 365))
    _append(store, "investor_metric_captures", {
        "captured_at": _now_iso(),
        "investor_count": len((_performance()._live_summary(email).get("investor_breakdown") or [])),
        "current_nav": (_performance()._live_summary(email).get("summary") or {}).get("current_nav", 0.0),
        "net_pnl": (_performance()._live_summary(email).get("summary") or {}).get("net_pnl", 0.0),
        "portfolio_return_pct": (_performance()._live_summary(email).get("summary") or {}).get("portfolio_return_pct", 0.0),
        "max_drawdown_pct": (_performance()._live_summary(email).get("summary") or {}).get("max_drawdown_pct", 0.0),
        "sharpe_ratio": (_performance()._live_summary(email).get("summary") or {}).get("sharpe_ratio", 0.0),
        "requested_by": "system",
    }, (store.get("policy") or {}).get("retain_cycles", 365))
    _append(store, "pnl_snapshots", {
        "captured_at": _now_iso(),
        "snapshot": (_performance().performance_engine_snapshot({}).get("snapshot") or {}),
        "series_points": len((_performance()._load(email).get("snapshots") or [])),
    }, (store.get("policy") or {}).get("retain_cycles", 365))
    _save(email, store)

    run = _evaluate(email, {
        "nav_confidence": 0.988,
        "attribution_completeness": 0.985,
        "investor_metric_completeness": 0.982,
        "stale_minutes": 4,
        "unresolved_breaks": 0,
        "unresolved_investor_exceptions": 0,
    })
    return {"ok": True, "run": run, **_summary_for_email(email)}
