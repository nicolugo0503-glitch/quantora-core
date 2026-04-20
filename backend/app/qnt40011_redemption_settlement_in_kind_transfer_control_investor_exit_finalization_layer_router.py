from fastapi import APIRouter, Body, Depends
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json

router = APIRouter(
    prefix="/api/redemption-settlement-in-kind-transfer-control-investor-exit-finalization-layer",
    tags=["redemption-settlement-in-kind-transfer-control-investor-exit-finalization-layer"],
)

PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
ENGINE_DIR = ARTIFACTS_DIR / "redemption_settlement_in_kind_transfer_control_investor_exit_finalization_layer"
DEFAULT_POLICY = {
    "retain_cycles": 365,
    "minimum_score": 95.0,
    "minimum_settlement_readiness": 0.95,
    "minimum_in_kind_transfer_readiness": 0.92,
    "minimum_exit_finalization_readiness": 0.95,
    "maximum_unresolved_settlement_breaks": 0,
    "maximum_failed_delivery_events": 0,
}

def _mu():
    from backend.app import qnt30557_multi_user_router as mu
    return mu

def _require_user():
    return _mu()._require_session()

def _cash_ledger():
    from backend.app import qnt30591_cash_ledger_router as module
    return module

def _capital_ledger():
    from backend.app import qnt30624_capital_ledger_router as module
    return module

def _redemption_layer():
    from backend.app import qnt40010_redemption_queue_liquidity_gating_side_pocket_withdrawal_waterfall_control_layer_router as module
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
            "settlement_events": [],
            "in_kind_transfer_events": [],
            "exit_finalization_events": [],
            "latest_run": None,
            "last_context": {},
        }
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return data
    return json.loads(path.read_text(encoding="utf-8"))

def _save(email: str, data: dict):
    _path(email).write_text(json.dumps(data, indent=2), encoding="utf-8")

def _context(email: str) -> dict:
    redemption = _redemption_layer()._summary_for_email(email)
    cash = _cash_ledger()._load(email)
    ledger = _capital_ledger().capital_ledger_summary()
    latest_cash = (cash.get("entries") or [None])[0]
    latest_account = (ledger.get("accounts") or [None])[0]
    return {
        "captured_at": _now_iso(),
        "redemption_status": redemption.get("redemption_queue_liquidity_gating_side_pocket_withdrawal_waterfall_control_layer_status") or {},
        "cash_ledger_summary": {
            "entry_count": len(cash.get("entries") or []),
            "latest_entry_type": latest_cash.get("type") if latest_cash else None,
            "latest_entry_status": latest_cash.get("status") if latest_cash else None,
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
        "redemption_settlement_in_kind_transfer_control_investor_exit_finalization_layer_status": {
            "posture": latest.get("posture", "UNINITIALIZED"),
            "latest_score": latest.get("score"),
            "band": latest.get("band", "UNSET"),
            "run_count": len(s.get("runs") or []),
            "alert_count": len(s.get("alerts") or []),
            "settlement_event_count": len(s.get("settlement_events") or []),
            "in_kind_transfer_event_count": len(s.get("in_kind_transfer_events") or []),
            "exit_finalization_event_count": len(s.get("exit_finalization_events") or []),
            "operator_review_required": bool(latest.get("operator_review_required", False)),
        },
        "latest_run": latest,
        "alerts": s.get("alerts") or [],
        "policy": s.get("policy") or dict(DEFAULT_POLICY),
        "last_context": s.get("last_context") or {},
        "settlement_events": s.get("settlement_events") or [],
        "in_kind_transfer_events": s.get("in_kind_transfer_events") or [],
        "exit_finalization_events": s.get("exit_finalization_events") or [],
    }

def _band(score: float) -> str:
    if score >= 98.0:
        return "INSTITUTIONAL_EXIT_LOCKED"
    if score >= 95.0:
        return "EXIT_FINALIZATION_CLEAR"
    if score >= 91.0:
        return "EXIT_FINALIZATION_WATCH"
    return "EXIT_FINALIZATION_REMEDIATION_REQUIRED"

def _evaluate(email: str, payload: dict) -> dict:
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get("policy") or {})}
    ctx = _context(email)

    settlement_readiness = float(payload.get("settlement_readiness", 0.0) or 0.0)
    in_kind_transfer_readiness = float(payload.get("in_kind_transfer_readiness", 0.0) or 0.0)
    exit_finalization_readiness = float(payload.get("exit_finalization_readiness", 0.0) or 0.0)
    unresolved_settlement_breaks = int(payload.get("unresolved_settlement_breaks", 0) or 0)
    failed_delivery_events = int(payload.get("failed_delivery_events", 0) or 0)

    score = 100.0
    reasons = []
    alerts = []

    def penalize(metric: float, minimum: float, weight: float, reason: str, code: str):
        nonlocal score
        if metric < minimum:
            score -= round((minimum - metric) * weight, 2)
            reasons.append(reason)
            alerts.append(code)

    penalize(settlement_readiness, float(policy.get("minimum_settlement_readiness", 0.95)), 120.0, "settlement readiness is below policy", "SETTLEMENT_READINESS_WEAK")
    penalize(in_kind_transfer_readiness, float(policy.get("minimum_in_kind_transfer_readiness", 0.92)), 110.0, "in-kind transfer readiness is below policy", "IN_KIND_TRANSFER_READINESS_WEAK")
    penalize(exit_finalization_readiness, float(policy.get("minimum_exit_finalization_readiness", 0.95)), 120.0, "exit finalization readiness is below policy", "EXIT_FINALIZATION_READINESS_WEAK")

    if unresolved_settlement_breaks > int(policy.get("maximum_unresolved_settlement_breaks", 0)):
        score -= 7.0 + (unresolved_settlement_breaks - int(policy.get("maximum_unresolved_settlement_breaks", 0))) * 2.0
        reasons.append("unresolved settlement breaks exceed policy")
        alerts.append("SETTLEMENT_BREAKS_EXCESS")
    if failed_delivery_events > int(policy.get("maximum_failed_delivery_events", 0)):
        score -= 7.0 + (failed_delivery_events - int(policy.get("maximum_failed_delivery_events", 0))) * 2.0
        reasons.append("failed delivery events exceed policy")
        alerts.append("FAILED_DELIVERY_EVENTS_EXCESS")

    redemption_status = (ctx.get("redemption_status") or {}).get("posture")
    if redemption_status not in {"REDEMPTION_CONTROL_CLEAR", "INSTITUTIONAL_LIQUIDITY_LOCKED"}:
        score -= 8.0
        reasons.append("redemption control posture must clear before exit finalization")
        alerts.append("REDEMPTION_CONTROL_NOT_CLEAR")
    if float((ctx.get("capital_ledger_summary") or {}).get("total_funded_capital", 0.0) or 0.0) <= 0.0:
        score -= 8.0
        reasons.append("funded capital is required before exit settlement can clear")
        alerts.append("FUNDED_CAPITAL_REQUIRED")

    score = round(max(score, 0.0), 2)
    posture = _band(score)
    operator_review_required = bool(score < float(policy.get("minimum_score", 95.0)) or len(alerts) > 0)

    run = {
        "run_id": f"qnt40011_{int(datetime.now(timezone.utc).timestamp())}",
        "captured_at": _now_iso(),
        "score": score,
        "band": _band(score),
        "posture": posture,
        "operator_review_required": operator_review_required,
        "reasons": reasons,
        "alerts": alerts,
        "settlement_readiness": settlement_readiness,
        "in_kind_transfer_readiness": in_kind_transfer_readiness,
        "exit_finalization_readiness": exit_finalization_readiness,
        "unresolved_settlement_breaks": unresolved_settlement_breaks,
        "failed_delivery_events": failed_delivery_events,
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

@router.post('/record-settlement')
def record_settlement(payload: dict = Body(...), user=Depends(_require_user)):
    email = (user.get('email') or '').strip().lower()
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get('policy') or {})}
    event = {
        "settlement_id": payload.get('settlement_id') or f"stl_{int(datetime.now(timezone.utc).timestamp())}",
        "captured_at": _now_iso(),
        "investor_id": payload.get('investor_id') or 'lp_main',
        "cash_amount": round(float(payload.get('cash_amount', 0.0) or 0.0), 2),
        "settlement_date": payload.get('settlement_date') or _now_iso()[:10],
        "status": payload.get('status') or 'matched',
        "notes": payload.get('notes') or '',
    }
    _append(store, 'settlement_events', event, int(policy.get('retain_cycles', 365)))
    _save(email, store)
    return {"ok": True, "event": event, "summary": _summary_for_email(email)}

@router.post('/record-in-kind-transfer')
def record_in_kind_transfer(payload: dict = Body(...), user=Depends(_require_user)):
    email = (user.get('email') or '').strip().lower()
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get('policy') or {})}
    event = {
        "transfer_id": payload.get('transfer_id') or f"ikt_{int(datetime.now(timezone.utc).timestamp())}",
        "captured_at": _now_iso(),
        "asset_bucket": payload.get('asset_bucket') or 'side_pocket_distribution',
        "market_value": round(float(payload.get('market_value', 0.0) or 0.0), 2),
        "delivery_method": payload.get('delivery_method') or 'in_kind_distribution',
        "status": payload.get('status') or 'prepared',
    }
    _append(store, 'in_kind_transfer_events', event, int(policy.get('retain_cycles', 365)))
    _save(email, store)
    return {"ok": True, "event": event, "summary": _summary_for_email(email)}

@router.post('/finalize-investor-exit')
def finalize_investor_exit(payload: dict = Body(...), user=Depends(_require_user)):
    email = (user.get('email') or '').strip().lower()
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get('policy') or {})}
    event = {
        "exit_id": payload.get('exit_id') or f"exit_{int(datetime.now(timezone.utc).timestamp())}",
        "captured_at": _now_iso(),
        "investor_id": payload.get('investor_id') or 'lp_main',
        "gross_redemption_amount": round(float(payload.get('gross_redemption_amount', 0.0) or 0.0), 2),
        "cash_paid_amount": round(float(payload.get('cash_paid_amount', 0.0) or 0.0), 2),
        "in_kind_paid_amount": round(float(payload.get('in_kind_paid_amount', 0.0) or 0.0), 2),
        "status": payload.get('status') or 'finalized',
    }
    _append(store, 'exit_finalization_events', event, int(policy.get('retain_cycles', 365)))
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
    _redemption_layer().bootstrap_demo(user)
    record_settlement({
        'investor_id': 'lp_foundation',
        'cash_amount': 140000.0,
        'status': 'matched',
        'notes': 'cash leg released after gate holdback review',
    }, user)
    record_in_kind_transfer({
        'asset_bucket': 'private_credit_recovery_book',
        'market_value': 20000.0,
        'delivery_method': 'in_kind_distribution',
        'status': 'prepared',
    }, user)
    finalize_investor_exit({
        'investor_id': 'lp_foundation',
        'gross_redemption_amount': 185000.0,
        'cash_paid_amount': 140000.0,
        'in_kind_paid_amount': 20000.0,
        'status': 'finalized',
    }, user)
    run = _evaluate(email, {
        'settlement_readiness': 0.98,
        'in_kind_transfer_readiness': 0.95,
        'exit_finalization_readiness': 0.98,
        'unresolved_settlement_breaks': 0,
        'failed_delivery_events': 0,
    })
    return {"ok": True, "run": run, "summary": _summary_for_email(email)}
