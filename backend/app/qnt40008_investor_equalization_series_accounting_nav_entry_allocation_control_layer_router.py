from fastapi import APIRouter, Body, Depends
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json

router = APIRouter(
    prefix="/api/investor-equalization-series-accounting-nav-entry-allocation-control-layer",
    tags=["investor-equalization-series-accounting-nav-entry-allocation-control-layer"],
)

PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
ENGINE_DIR = ARTIFACTS_DIR / "investor_equalization_series_accounting_nav_entry_allocation_control_layer"
DEFAULT_POLICY = {
    "retain_cycles": 365,
    "minimum_score": 95.0,
    "minimum_nav_readiness": 0.95,
    "minimum_allocation_readiness": 0.95,
    "minimum_equalization_readiness": 0.95,
    "maximum_open_series_breaks": 0,
    "maximum_unallocated_nav_entries": 0,
    "require_official_nav": True,
    "require_funded_capital": True,
}

def _mu():
    from backend.app import qnt30557_multi_user_router as mu
    return mu

def _require_user():
    return _mu()._require_session()

def _equalization():
    from backend.app import qnt30593_equalization_router as module
    return module

def _nav_strike():
    from backend.app import qnt30597_nav_strike_router as module
    return module

def _pnl():
    from backend.app import qnt30586_pnl_ledger_router as module
    return module

def _capital_ledger():
    from backend.app import qnt30624_capital_ledger_router as module
    return module

def _funding_layer():
    from backend.app import qnt40007_investor_funding_settlement_subscription_reconciliation_capital_receipt_finalization_layer_router as module
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
            "series_events": [],
            "nav_entry_events": [],
            "performance_allocation_events": [],
            "equalization_adjustment_events": [],
            "latest_run": None,
            "last_context": {},
        }
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return data
    return json.loads(path.read_text(encoding="utf-8"))

def _save(email: str, data: dict):
    _path(email).write_text(json.dumps(data, indent=2), encoding="utf-8")

def _context(email: str) -> dict:
    funding = _funding_layer().summary({"email": email})
    eq = _equalization().equalization_series_summary()
    nav = _nav_strike().nav_strike_summary()
    pnl = _pnl().pnl_summary()
    ledger = _capital_ledger().capital_ledger_summary()

    latest_series = (eq.get("series") or [{}])[0]
    latest_val = nav.get("latest_valuation") or {}
    latest_pos = (pnl.get("positions") or [{}])[0]
    latest_entry = (ledger.get("entries") or [{}])[0]

    return {
        "captured_at": _now_iso(),
        "funding_layer_status": funding.get("investor_funding_settlement_subscription_reconciliation_capital_receipt_finalization_layer_status") or {},
        "equalization_series_summary": {
            "series_count": eq.get("series_count", 0),
            "active_series_count": eq.get("active_series", 0),
            "closed_series_count": eq.get("closed_series", 0),
            "total_subscription_capital": eq.get("total_subscription_capital", 0.0),
            "total_series_nav": eq.get("total_series_nav", 0.0),
            "latest_series_id": latest_series.get("series_id"),
        },
        "nav_strike_summary": {
            "valuation_count": nav.get("valuation_count", 0),
            "official_count": nav.get("official_count", 0),
            "draft_count": nav.get("draft_count", 0),
            "latest_valuation_id": latest_val.get("valuation_id"),
            "latest_official_nav": latest_val.get("official_nav", 0.0),
            "latest_nav_status": latest_val.get("status"),
        },
        "pnl_summary": {
            "position_count": pnl.get("position_count", 0),
            "ledger_count": pnl.get("ledger_count", 0),
            "total_realized_pnl": pnl.get("total_realized_pnl", 0.0),
            "total_unrealized_pnl": pnl.get("total_unrealized_pnl", 0.0),
            "total_pnl": pnl.get("total_pnl", 0.0),
            "latest_symbol": latest_pos.get("symbol"),
        },
        "capital_ledger_summary": {
            "account_count": ledger.get("account_count", 0),
            "entry_count": ledger.get("entry_count", 0),
            "allocation_count": ledger.get("allocation_count", 0),
            "total_funded_capital": ledger.get("total_funded_capital", 0.0),
            "total_nav": ledger.get("total_nav", 0.0),
            "latest_entry_id": latest_entry.get("entry_id"),
        },
    }

def _summary_for_email(email: str) -> dict:
    s = _load(email)
    latest = s.get("latest_run") or {}
    return {
        "investor_equalization_series_accounting_nav_entry_allocation_control_layer_status": {
            "posture": latest.get("posture", "UNINITIALIZED"),
            "latest_score": latest.get("score"),
            "band": latest.get("band", "UNSET"),
            "run_count": len(s.get("runs") or []),
            "alert_count": len(s.get("alerts") or []),
            "series_event_count": len(s.get("series_events") or []),
            "nav_entry_event_count": len(s.get("nav_entry_events") or []),
            "performance_allocation_event_count": len(s.get("performance_allocation_events") or []),
            "equalization_adjustment_event_count": len(s.get("equalization_adjustment_events") or []),
            "operator_review_required": bool(latest.get("operator_review_required", False)),
        },
        "latest_run": latest,
        "alerts": s.get("alerts") or [],
        "policy": s.get("policy") or dict(DEFAULT_POLICY),
        "last_context": s.get("last_context") or {},
        "series_events": s.get("series_events") or [],
        "nav_entry_events": s.get("nav_entry_events") or [],
        "performance_allocation_events": s.get("performance_allocation_events") or [],
        "equalization_adjustment_events": s.get("equalization_adjustment_events") or [],
    }

def _band(score: float) -> str:
    if score >= 98.0:
        return "INSTITUTIONAL_NAV_ALLOCATION_LOCKED"
    if score >= 95.0:
        return "NAV_ALLOCATION_CLEAR"
    if score >= 91.0:
        return "EQUALIZATION_WATCH"
    return "EQUALIZATION_REMEDIATION_REQUIRED"

def _evaluate(email: str, payload: dict) -> dict:
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get("policy") or {})}
    ctx = _context(email)

    nav_readiness = float(payload.get("nav_readiness", 0.0) or 0.0)
    allocation_readiness = float(payload.get("allocation_readiness", 0.0) or 0.0)
    equalization_readiness = float(payload.get("equalization_readiness", 0.0) or 0.0)
    open_series_breaks = int(payload.get("open_series_breaks", 0) or 0)
    unallocated_nav_entries = int(payload.get("unallocated_nav_entries", 0) or 0)

    score = 100.0
    reasons = []
    alerts = []

    def penalize(metric: float, minimum: float, weight: float, reason: str, code: str):
        nonlocal score
        if metric < minimum:
            score -= round((minimum - metric) * weight, 2)
            reasons.append(reason)
            alerts.append(code)

    penalize(nav_readiness, float(policy.get("minimum_nav_readiness", 0.95)), 120.0, "nav readiness is below policy", "NAV_READINESS_WEAK")
    penalize(allocation_readiness, float(policy.get("minimum_allocation_readiness", 0.95)), 120.0, "allocation readiness is below policy", "ALLOCATION_READINESS_WEAK")
    penalize(equalization_readiness, float(policy.get("minimum_equalization_readiness", 0.95)), 125.0, "equalization readiness is below policy", "EQUALIZATION_READINESS_WEAK")

    if open_series_breaks > int(policy.get("maximum_open_series_breaks", 0)):
        score -= 7.0 + (open_series_breaks - int(policy.get("maximum_open_series_breaks", 0))) * 2.0
        reasons.append("open series breaks exceed policy")
        alerts.append("SERIES_BREAKS_EXCESS")
    if unallocated_nav_entries > int(policy.get("maximum_unallocated_nav_entries", 0)):
        score -= 6.0 + (unallocated_nav_entries - int(policy.get("maximum_unallocated_nav_entries", 0))) * 2.0
        reasons.append("unallocated nav entries exceed policy")
        alerts.append("UNALLOCATED_NAV_ENTRIES")

    if bool(policy.get("require_official_nav", True)) and (ctx.get("nav_strike_summary") or {}).get("official_count", 0) <= 0:
        score -= 8.0
        reasons.append("official nav is required before allocation control can clear")
        alerts.append("OFFICIAL_NAV_REQUIRED")
    if bool(policy.get("require_funded_capital", True)) and float((ctx.get("capital_ledger_summary") or {}).get("total_funded_capital", 0.0) or 0.0) <= 0.0:
        score -= 8.0
        reasons.append("funded capital is required before equalization control can clear")
        alerts.append("FUNDED_CAPITAL_REQUIRED")

    score = round(max(score, 0.0), 2)
    posture = _band(score)
    operator_review_required = bool(score < float(policy.get("minimum_score", 95.0)) or len(alerts) > 0)

    run = {
        "run_id": f"qnt40008_{int(datetime.now(timezone.utc).timestamp())}",
        "captured_at": _now_iso(),
        "score": score,
        "band": _band(score),
        "posture": posture,
        "operator_review_required": operator_review_required,
        "reasons": reasons,
        "alerts": alerts,
        "inputs": {
            "nav_readiness": nav_readiness,
            "allocation_readiness": allocation_readiness,
            "equalization_readiness": equalization_readiness,
            "open_series_breaks": open_series_breaks,
            "unallocated_nav_entries": unallocated_nav_entries,
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

@router.post("/create-series")
def create_series(payload: dict = Body(...), user=Depends(_require_user)):
    email = user.get("email")
    store = _load(email)
    series_name = str(payload.get("series_name") or "Series A")
    subscription_capital = round(float(payload.get("subscription_capital") or 0.0), 2)
    units = round(float(payload.get("units") or max(subscription_capital, 1.0)), 6)
    event = {
        "series_event_id": f"series_evt_{int(datetime.now(timezone.utc).timestamp())}",
        "series_name": series_name,
        "subscription_capital": subscription_capital,
        "units": units,
        "captured_at": _now_iso(),
        "notes": str(payload.get("notes") or ""),
    }
    _equalization().equalization_series_create({
        "email": email,
        "series_name": series_name,
        "subscription_capital": subscription_capital,
        "units": units,
        "notes": event["notes"],
    })
    _append(store, "series_events", event, int((store.get("policy") or DEFAULT_POLICY).get("retain_cycles", 365)))
    _save(email, store)
    return {"ok": True, "event": event}

@router.post("/record-nav-entry")
def record_nav_entry(payload: dict = Body(...), user=Depends(_require_user)):
    email = user.get("email")
    store = _load(email)
    valuation_date = str(payload.get("valuation_date") or "current")
    nav_res = _nav_strike().nav_strike_create({"valuation_date": valuation_date})
    event = {
        "nav_entry_event_id": f"nav_evt_{int(datetime.now(timezone.utc).timestamp())}",
        "valuation_date": valuation_date,
        "official_nav": ((nav_res or {}).get("valuation") or {}).get("official_nav", 0.0),
        "valuation_id": ((nav_res or {}).get("valuation") or {}).get("valuation_id"),
        "captured_at": _now_iso(),
        "notes": str(payload.get("notes") or ""),
    }
    _append(store, "nav_entry_events", event, int((store.get("policy") or DEFAULT_POLICY).get("retain_cycles", 365)))
    _save(email, store)
    return {"ok": True, "event": event, "valuation": (nav_res or {}).get("valuation")}

@router.post("/allocate-performance")
def allocate_performance(payload: dict = Body(...), user=Depends(_require_user)):
    email = user.get("email")
    store = _load(email)
    sleeve_id = str(payload.get("sleeve_id") or "core")
    symbol = str(payload.get("symbol") or "QNT")
    qty = round(float(payload.get("qty") or 100.0), 6)
    avg_price = round(float(payload.get("avg_price") or 100.0), 6)
    mark_price = round(float(payload.get("mark_price") or (avg_price * 1.02)), 6)
    _pnl().pnl_mark({
        "email": email,
        "sleeve_id": sleeve_id,
        "symbol": symbol,
        "qty": qty,
        "avg_price": avg_price,
        "mark_price": mark_price,
    })
    realized_pnl = round(float(payload.get("realized_pnl") or 0.0), 2)
    if realized_pnl != 0.0:
        _pnl().pnl_realize({
            "email": email,
            "sleeve_id": sleeve_id,
            "symbol": symbol,
            "realized_pnl": realized_pnl,
        })
    event = {
        "performance_allocation_event_id": f"alloc_evt_{int(datetime.now(timezone.utc).timestamp())}",
        "sleeve_id": sleeve_id,
        "symbol": symbol,
        "qty": qty,
        "avg_price": avg_price,
        "mark_price": mark_price,
        "realized_pnl": realized_pnl,
        "captured_at": _now_iso(),
        "notes": str(payload.get("notes") or ""),
    }
    _append(store, "performance_allocation_events", event, int((store.get("policy") or DEFAULT_POLICY).get("retain_cycles", 365)))
    _save(email, store)
    return {"ok": True, "event": event}

@router.post("/adjust-equalization")
def adjust_equalization(payload: dict = Body(...), user=Depends(_require_user)):
    email = user.get("email")
    store = _load(email)
    event = {
        "equalization_adjustment_event_id": f"eq_evt_{int(datetime.now(timezone.utc).timestamp())}",
        "series_id": str(payload.get("series_id") or "latest"),
        "adjustment_amount": round(float(payload.get("adjustment_amount") or 0.0), 2),
        "reason": str(payload.get("reason") or "equalization_review"),
        "captured_at": _now_iso(),
        "notes": str(payload.get("notes") or ""),
    }
    _append(store, "equalization_adjustment_events", event, int((store.get("policy") or DEFAULT_POLICY).get("retain_cycles", 365)))
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
    from backend.app import qnt30623_onboarding_router as onboarding
    inv = onboarding.create_investor({"investor_id": "inv_qnt40008", "name": "Quantora Series LP", "commitment": 125000.0})
    investor_id = inv["investor"]["investor_id"]
    _capital_ledger().create_account({"investor_id": investor_id, "committed_capital": 125000.0})
    _capital_ledger().add_entry({"investor_id": investor_id, "amount": 50000.0, "entry_type": "funding", "description": "bootstrap funding"})
    _capital_ledger().recalculate()
    create_series({"series_name": "Series A", "subscription_capital": 50000.0, "units": 50000.0, "notes": "bootstrap series"}, user)
    nav_res = record_nav_entry({"valuation_date": "2026-04-15", "notes": "bootstrap nav"}, user)
    valuation_id = ((nav_res or {}).get("valuation") or {}).get("valuation_id")
    if valuation_id:
        _nav_strike().nav_strike_finalize({"email": email, "valuation_id": valuation_id, "notes": "bootstrap official nav"})
    allocate_performance({"sleeve_id": "core", "symbol": "QNT", "qty": 100.0, "avg_price": 100.0, "mark_price": 103.5, "realized_pnl": 250.0, "notes": "bootstrap allocation"}, user)
    adjust_equalization({"series_id": "latest", "adjustment_amount": 125.0, "reason": "entry_nav_offset", "notes": "bootstrap equalization"}, user)
    run = _evaluate(email, {
        "nav_readiness": 1.0,
        "allocation_readiness": 0.99,
        "equalization_readiness": 0.98,
        "open_series_breaks": 0,
        "unallocated_nav_entries": 0,
    })
    return {"ok": True, "run": run, "summary": _summary_for_email(email)}
