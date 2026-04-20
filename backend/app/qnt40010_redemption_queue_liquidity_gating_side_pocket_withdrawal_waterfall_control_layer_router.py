from fastapi import APIRouter, Body, Depends
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json

router = APIRouter(
    prefix="/api/redemption-queue-liquidity-gating-side-pocket-withdrawal-waterfall-control-layer",
    tags=["redemption-queue-liquidity-gating-side-pocket-withdrawal-waterfall-control-layer"],
)

PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
ENGINE_DIR = ARTIFACTS_DIR / "redemption_queue_liquidity_gating_side_pocket_withdrawal_waterfall_control_layer"
DEFAULT_POLICY = {
    "retain_cycles": 365,
    "minimum_score": 95.0,
    "minimum_queue_readiness": 0.95,
    "minimum_liquidity_gate_readiness": 0.95,
    "minimum_side_pocket_readiness": 0.90,
    "minimum_withdrawal_waterfall_readiness": 0.95,
    "maximum_unresolved_redemption_breaks": 0,
    "maximum_gate_breaches": 0,
    "default_gate_pct": 25.0,
}

def _mu():
    from backend.app import qnt30557_multi_user_router as mu
    return mu

def _require_user():
    return _mu()._require_session()

def _cash_ledger():
    from backend.app import qnt30591_cash_ledger_router as module
    return module

def _dealing_day():
    from backend.app import qnt30596_dealing_day_router as module
    return module

def _nav_strike():
    from backend.app import qnt30597_nav_strike_router as module
    return module

def _capital_ledger():
    from backend.app import qnt30624_capital_ledger_router as module
    return module

def _funding_layer():
    from backend.app import qnt40007_investor_funding_settlement_subscription_reconciliation_capital_receipt_finalization_layer_router as module
    return module

def _equalization_layer():
    from backend.app import qnt40008_investor_equalization_series_accounting_nav_entry_allocation_control_layer_router as module
    return module

def _fee_layer():
    from backend.app import qnt40009_fee_engine_management_fee_performance_fee_hwm_hurdle_rate_incentive_allocation_layer_router as module
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
            "redemption_request_events": [],
            "liquidity_gate_events": [],
            "side_pocket_events": [],
            "withdrawal_waterfall_events": [],
            "latest_run": None,
            "last_context": {},
        }
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return data
    return json.loads(path.read_text(encoding="utf-8"))

def _save(email: str, data: dict):
    _path(email).write_text(json.dumps(data, indent=2), encoding="utf-8")

def _context(email: str) -> dict:
    fee = _fee_layer()._summary_for_email(email)
    eq = _equalization_layer()._summary_for_email(email)
    fund = _funding_layer()._summary_for_email(email)
    cash = _cash_ledger()._load(email)
    deal = _dealing_day()._load(email)
    nav = _nav_strike()._load(email)
    ledger = _capital_ledger().capital_ledger_summary()

    latest_day = (deal.get("dealing_days") or [None])[0]
    latest_val = (nav.get("valuations") or [None])[0]
    latest_cash = (cash.get("entries") or [None])[0]
    latest_account = (ledger.get("accounts") or [None])[0]

    return {
        "captured_at": _now_iso(),
        "fee_engine_status": fee.get("fee_engine_management_fee_performance_fee_hwm_hurdle_rate_incentive_allocation_layer_status") or {},
        "equalization_status": eq.get("investor_equalization_series_accounting_nav_entry_allocation_control_layer_status") or {},
        "funding_status": fund.get("investor_funding_settlement_subscription_reconciliation_capital_receipt_finalization_layer_status") or {},
        "cash_ledger_summary": {
            "entry_count": len(cash.get("entries") or []),
            "latest_entry_type": latest_cash.get("type") if latest_cash else None,
            "latest_entry_status": latest_cash.get("status") if latest_cash else None,
        },
        "dealing_day_summary": {
            "day_count": len(deal.get("dealing_days") or []),
            "latest_day_id": latest_day.get("day_id") if latest_day else None,
            "cutoff_status": latest_day.get("cutoff_status") if latest_day else None,
            "pending_redemption_amount": latest_day.get("pending_redemption_amount", 0.0) if latest_day else 0.0,
        },
        "nav_summary": {
            "valuation_count": len(nav.get("valuations") or []),
            "latest_valuation_id": latest_val.get("valuation_id") if latest_val else None,
            "latest_official_nav": latest_val.get("official_nav", 0.0) if latest_val else 0.0,
            "latest_status": latest_val.get("status") if latest_val else None,
        },
        "capital_ledger_summary": {
            "account_count": ledger.get("account_count", 0),
            "total_funded_capital": ledger.get("total_funded_capital", 0.0),
            "total_nav": ledger.get("total_nav", 0.0),
            "latest_account_id": latest_account.get("account_id") if latest_account else None,
        },
    }

def _summary_for_email(email: str) -> dict:
    s = _load(email)
    latest = s.get("latest_run") or {}
    return {
        "redemption_queue_liquidity_gating_side_pocket_withdrawal_waterfall_control_layer_status": {
            "posture": latest.get("posture", "UNINITIALIZED"),
            "latest_score": latest.get("score"),
            "band": latest.get("band", "UNSET"),
            "run_count": len(s.get("runs") or []),
            "alert_count": len(s.get("alerts") or []),
            "redemption_request_event_count": len(s.get("redemption_request_events") or []),
            "liquidity_gate_event_count": len(s.get("liquidity_gate_events") or []),
            "side_pocket_event_count": len(s.get("side_pocket_events") or []),
            "withdrawal_waterfall_event_count": len(s.get("withdrawal_waterfall_events") or []),
            "operator_review_required": bool(latest.get("operator_review_required", False)),
        },
        "latest_run": latest,
        "alerts": s.get("alerts") or [],
        "policy": s.get("policy") or dict(DEFAULT_POLICY),
        "last_context": s.get("last_context") or {},
        "redemption_request_events": s.get("redemption_request_events") or [],
        "liquidity_gate_events": s.get("liquidity_gate_events") or [],
        "side_pocket_events": s.get("side_pocket_events") or [],
        "withdrawal_waterfall_events": s.get("withdrawal_waterfall_events") or [],
    }

def _band(score: float) -> str:
    if score >= 98.0:
        return "INSTITUTIONAL_LIQUIDITY_LOCKED"
    if score >= 95.0:
        return "REDEMPTION_CONTROL_CLEAR"
    if score >= 91.0:
        return "REDEMPTION_CONTROL_WATCH"
    return "REDEMPTION_CONTROL_REMEDIATION_REQUIRED"

def _evaluate(email: str, payload: dict) -> dict:
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get("policy") or {})}
    ctx = _context(email)

    queue_readiness = float(payload.get("queue_readiness", 0.0) or 0.0)
    liquidity_gate_readiness = float(payload.get("liquidity_gate_readiness", 0.0) or 0.0)
    side_pocket_readiness = float(payload.get("side_pocket_readiness", 0.0) or 0.0)
    withdrawal_waterfall_readiness = float(payload.get("withdrawal_waterfall_readiness", 0.0) or 0.0)
    unresolved_redemption_breaks = int(payload.get("unresolved_redemption_breaks", 0) or 0)
    gate_breaches = int(payload.get("gate_breaches", 0) or 0)

    score = 100.0
    reasons = []
    alerts = []

    def penalize(metric: float, minimum: float, weight: float, reason: str, code: str):
        nonlocal score
        if metric < minimum:
            score -= round((minimum - metric) * weight, 2)
            reasons.append(reason)
            alerts.append(code)

    penalize(queue_readiness, float(policy.get("minimum_queue_readiness", 0.95)), 120.0, "redemption queue readiness is below policy", "QUEUE_READINESS_WEAK")
    penalize(liquidity_gate_readiness, float(policy.get("minimum_liquidity_gate_readiness", 0.95)), 120.0, "liquidity gate readiness is below policy", "LIQUIDITY_GATE_READINESS_WEAK")
    penalize(side_pocket_readiness, float(policy.get("minimum_side_pocket_readiness", 0.90)), 110.0, "side pocket readiness is below policy", "SIDE_POCKET_READINESS_WEAK")
    penalize(withdrawal_waterfall_readiness, float(policy.get("minimum_withdrawal_waterfall_readiness", 0.95)), 125.0, "withdrawal waterfall readiness is below policy", "WITHDRAWAL_WATERFALL_READINESS_WEAK")

    if unresolved_redemption_breaks > int(policy.get("maximum_unresolved_redemption_breaks", 0)):
        score -= 7.0 + (unresolved_redemption_breaks - int(policy.get("maximum_unresolved_redemption_breaks", 0))) * 2.0
        reasons.append("unresolved redemption breaks exceed policy")
        alerts.append("REDEMPTION_BREAKS_EXCESS")
    if gate_breaches > int(policy.get("maximum_gate_breaches", 0)):
        score -= 7.0 + (gate_breaches - int(policy.get("maximum_gate_breaches", 0))) * 2.0
        reasons.append("gate breaches exceed policy")
        alerts.append("GATE_BREACHES_EXCESS")

    if float((ctx.get("capital_ledger_summary") or {}).get("total_funded_capital", 0.0) or 0.0) <= 0.0:
        score -= 8.0
        reasons.append("funded capital is required before withdrawal controls can clear")
        alerts.append("FUNDED_CAPITAL_REQUIRED")
    if float((ctx.get("nav_summary") or {}).get("latest_official_nav", 0.0) or 0.0) <= 0.0:
        score -= 8.0
        reasons.append("official nav is required before waterfall release can clear")
        alerts.append("OFFICIAL_NAV_REQUIRED")

    score = round(max(score, 0.0), 2)
    posture = _band(score)
    operator_review_required = bool(score < float(policy.get("minimum_score", 95.0)) or len(alerts) > 0)

    run = {
        "run_id": f"qnt40010_{int(datetime.now(timezone.utc).timestamp())}",
        "captured_at": _now_iso(),
        "score": score,
        "band": _band(score),
        "posture": posture,
        "operator_review_required": operator_review_required,
        "reasons": reasons,
        "alerts": alerts,
        "queue_readiness": queue_readiness,
        "liquidity_gate_readiness": liquidity_gate_readiness,
        "side_pocket_readiness": side_pocket_readiness,
        "withdrawal_waterfall_readiness": withdrawal_waterfall_readiness,
        "unresolved_redemption_breaks": unresolved_redemption_breaks,
        "gate_breaches": gate_breaches,
    }
    _append(store, "runs", run, int(policy.get("retain_cycles", 365)))
    store["latest_run"] = run
    store["alerts"] = alerts
    store["last_context"] = ctx
    _save(email, store)
    return run

@router.get('/summary')
def summary(user=Depends(_require_user)):
    return _summary_for_email((user.get('email') or '').strip().lower())

@router.post('/evaluate')
def evaluate(payload: dict = Body(...), user=Depends(_require_user)):
    email = (user.get('email') or '').strip().lower()
    return {"ok": True, "run": _evaluate(email, payload), "summary": _summary_for_email(email)}

@router.post('/register-redemption-request')
def register_redemption_request(payload: dict = Body(...), user=Depends(_require_user)):
    email = (user.get('email') or '').strip().lower()
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get('policy') or {})}
    event = {
        "request_id": payload.get('request_id') or f"red_{int(datetime.now(timezone.utc).timestamp())}",
        "captured_at": _now_iso(),
        "investor_id": payload.get('investor_id') or 'lp_main',
        "requested_amount": round(float(payload.get('requested_amount', 0.0) or 0.0), 2),
        "share_class": payload.get('share_class') or 'Series A',
        "dealing_day_id": payload.get('dealing_day_id'),
        "queue_status": payload.get('queue_status') or 'queued',
        "notes": payload.get('notes') or '',
    }
    _append(store, 'redemption_request_events', event, int(policy.get('retain_cycles', 365)))
    _save(email, store)
    return {"ok": True, "event": event, "summary": _summary_for_email(email)}

@router.post('/apply-liquidity-gate')
def apply_liquidity_gate(payload: dict = Body(...), user=Depends(_require_user)):
    email = (user.get('email') or '').strip().lower()
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get('policy') or {})}
    gate_pct = round(float(payload.get('gate_pct', policy.get('default_gate_pct', 25.0)) or 0.0), 2)
    event = {
        "gate_id": payload.get('gate_id') or f"gate_{int(datetime.now(timezone.utc).timestamp())}",
        "captured_at": _now_iso(),
        "gate_pct": gate_pct,
        "gate_reason": payload.get('gate_reason') or 'orderly liquidity protection',
        "affected_queue_amount": round(float(payload.get('affected_queue_amount', 0.0) or 0.0), 2),
        "release_status": payload.get('release_status') or 'active',
    }
    _append(store, 'liquidity_gate_events', event, int(policy.get('retain_cycles', 365)))
    _save(email, store)
    return {"ok": True, "event": event, "summary": _summary_for_email(email)}

@router.post('/create-side-pocket')
def create_side_pocket(payload: dict = Body(...), user=Depends(_require_user)):
    email = (user.get('email') or '').strip().lower()
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get('policy') or {})}
    event = {
        "side_pocket_id": payload.get('side_pocket_id') or f"sp_{int(datetime.now(timezone.utc).timestamp())}",
        "captured_at": _now_iso(),
        "asset_bucket": payload.get('asset_bucket') or 'illiquid_special_situations',
        "marked_value": round(float(payload.get('marked_value', 0.0) or 0.0), 2),
        "allocation_basis": payload.get('allocation_basis') or 'record_date_nav',
        "status": payload.get('status') or 'established',
    }
    _append(store, 'side_pocket_events', event, int(policy.get('retain_cycles', 365)))
    _save(email, store)
    return {"ok": True, "event": event, "summary": _summary_for_email(email)}

@router.post('/launch-withdrawal-waterfall')
def launch_withdrawal_waterfall(payload: dict = Body(...), user=Depends(_require_user)):
    email = (user.get('email') or '').strip().lower()
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get('policy') or {})}
    event = {
        "waterfall_id": payload.get('waterfall_id') or f"wdf_{int(datetime.now(timezone.utc).timestamp())}",
        "captured_at": _now_iso(),
        "gross_redemption_amount": round(float(payload.get('gross_redemption_amount', 0.0) or 0.0), 2),
        "holdback_amount": round(float(payload.get('holdback_amount', 0.0) or 0.0), 2),
        "cash_release_amount": round(float(payload.get('cash_release_amount', 0.0) or 0.0), 2),
        "in_kind_amount": round(float(payload.get('in_kind_amount', 0.0) or 0.0), 2),
        "status": payload.get('status') or 'launched',
    }
    _append(store, 'withdrawal_waterfall_events', event, int(policy.get('retain_cycles', 365)))
    _save(email, store)
    return {"ok": True, "event": event, "summary": _summary_for_email(email)}

@router.get('/policy')
def policy(user=Depends(_require_user)):
    email = (user.get('email') or '').strip().lower()
    store = _load(email)
    return {"ok": True, "policy": {**dict(DEFAULT_POLICY), **(store.get('policy') or {})}}

@router.post('/bootstrap-demo')
def bootstrap_demo(user=Depends(_require_user)):
    email = (user.get('email') or '').strip().lower()
    register_redemption_request({
        'investor_id': 'lp_foundation',
        'requested_amount': 185000.0,
        'share_class': 'Series A',
        'queue_status': 'queued',
        'notes': 'quarter-end redemption window',
    }, user)
    apply_liquidity_gate({
        'gate_pct': 20.0,
        'affected_queue_amount': 185000.0,
        'gate_reason': 'protect orderly liquidity under concentrated withdrawal conditions',
        'release_status': 'active',
    }, user)
    create_side_pocket({
        'asset_bucket': 'private_credit_recovery_book',
        'marked_value': 42000.0,
        'allocation_basis': 'record_date_nav',
        'status': 'established',
    }, user)
    launch_withdrawal_waterfall({
        'gross_redemption_amount': 185000.0,
        'holdback_amount': 25000.0,
        'cash_release_amount': 140000.0,
        'in_kind_amount': 20000.0,
        'status': 'launched',
    }, user)
    run = _evaluate(email, {
        'queue_readiness': 0.98,
        'liquidity_gate_readiness': 0.97,
        'side_pocket_readiness': 0.94,
        'withdrawal_waterfall_readiness': 0.98,
        'unresolved_redemption_breaks': 0,
        'gate_breaches': 0,
    })
    return {"ok": True, "run": run, "summary": _summary_for_email(email)}
