from fastapi import APIRouter, Body, Depends
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json

router = APIRouter(
    prefix="/api/dealing-day-lock-nav-cutoff-enforcement-investor-transaction-freeze-control-layer",
    tags=["dealing-day-lock-nav-cutoff-enforcement-investor-transaction-freeze-control-layer"],
)

PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
ENGINE_DIR = ARTIFACTS_DIR / "dealing_day_lock_nav_cutoff_enforcement_investor_transaction_freeze_control_layer"
DEFAULT_POLICY = {
    "retain_cycles": 365,
    "minimum_score": 95.0,
    "minimum_lock_readiness": 0.95,
    "minimum_nav_cutoff_readiness": 0.95,
    "minimum_freeze_enforcement_readiness": 0.95,
    "maximum_pending_post_cutoff_requests": 0,
    "maximum_manual_override_events": 0,
}

def _mu():
    from backend.app import qnt30557_multi_user_router as mu
    return mu

def _require_user():
    return _mu()._require_session()

def _dealing_day():
    from backend.app import qnt30596_dealing_day_router as module
    return module

def _nav_strike():
    from backend.app import qnt30597_nav_strike_router as module
    return module

def _redemption_settlement():
    from backend.app import qnt40011_redemption_settlement_in_kind_transfer_control_investor_exit_finalization_layer_router as module
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
            "lock_events": [],
            "nav_cutoff_events": [],
            "transaction_freeze_events": [],
            "latest_run": None,
            "last_context": {},
        }
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return data
    return json.loads(path.read_text(encoding="utf-8"))

def _save(email: str, data: dict):
    _path(email).write_text(json.dumps(data, indent=2), encoding="utf-8")

def _context(email: str) -> dict:
    dealing = _dealing_day()._load(email)
    nav = _nav_strike()._load(email)
    exit_layer = _redemption_settlement()._summary_for_email(email)
    latest_day = (dealing.get("dealing_days") or [None])[0]
    latest_val = (nav.get("valuations") or [None])[0]
    return {
        "captured_at": _now_iso(),
        "dealing_day_summary": {
            "dealing_day_count": len(dealing.get("dealing_days") or []),
            "latest_day_id": latest_day.get("day_id") if latest_day else None,
            "latest_cutoff_status": latest_day.get("cutoff_status") if latest_day else None,
            "latest_day_status": latest_day.get("status") if latest_day else None,
            "pending_request_count": latest_day.get("pending_request_count") if latest_day else 0,
        },
        "nav_strike_summary": {
            "valuation_count": len(nav.get("valuations") or []),
            "latest_valuation_id": latest_val.get("valuation_id") if latest_val else None,
            "latest_valuation_status": latest_val.get("status") if latest_val else None,
            "latest_cutoff_status": latest_val.get("cutoff_status") if latest_val else None,
        },
        "exit_finalization_status": exit_layer.get("redemption_settlement_in_kind_transfer_control_investor_exit_finalization_layer_status") or {},
    }

def _summary_for_email(email: str) -> dict:
    s = _load(email)
    latest = s.get("latest_run") or {}
    return {
        "dealing_day_lock_nav_cutoff_enforcement_investor_transaction_freeze_control_layer_status": {
            "posture": latest.get("posture", "UNINITIALIZED"),
            "latest_score": latest.get("score"),
            "band": latest.get("band", "UNSET"),
            "run_count": len(s.get("runs") or []),
            "alert_count": len(s.get("alerts") or []),
            "lock_event_count": len(s.get("lock_events") or []),
            "nav_cutoff_event_count": len(s.get("nav_cutoff_events") or []),
            "transaction_freeze_event_count": len(s.get("transaction_freeze_events") or []),
            "operator_review_required": bool(latest.get("operator_review_required", False)),
        },
        "latest_run": latest,
        "alerts": s.get("alerts") or [],
        "policy": s.get("policy") or dict(DEFAULT_POLICY),
        "last_context": s.get("last_context") or {},
        "lock_events": s.get("lock_events") or [],
        "nav_cutoff_events": s.get("nav_cutoff_events") or [],
        "transaction_freeze_events": s.get("transaction_freeze_events") or [],
    }

def _band(score: float) -> str:
    if score >= 98.0:
        return "DEALING_DAY_LOCKED"
    if score >= 95.0:
        return "TRANSACTION_FREEZE_CLEAR"
    if score >= 91.0:
        return "TRANSACTION_FREEZE_WATCH"
    return "TRANSACTION_FREEZE_REMEDIATION_REQUIRED"

def _evaluate(email: str, payload: dict) -> dict:
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get("policy") or {})}
    ctx = _context(email)

    lock_readiness = float(payload.get("lock_readiness", 0.0) or 0.0)
    nav_cutoff_readiness = float(payload.get("nav_cutoff_readiness", 0.0) or 0.0)
    freeze_enforcement_readiness = float(payload.get("freeze_enforcement_readiness", 0.0) or 0.0)
    pending_post_cutoff_requests = int(payload.get("pending_post_cutoff_requests", 0) or 0)
    manual_override_events = int(payload.get("manual_override_events", 0) or 0)

    score = 100.0
    reasons = []
    alerts = []

    def penalize(metric: float, minimum: float, weight: float, reason: str, code: str):
        nonlocal score
        if metric < minimum:
            score -= round((minimum - metric) * weight, 2)
            reasons.append(reason)
            alerts.append(code)

    penalize(lock_readiness, float(policy.get("minimum_lock_readiness", 0.95)), 120.0, "dealing-day lock readiness is below policy", "LOCK_READINESS_WEAK")
    penalize(nav_cutoff_readiness, float(policy.get("minimum_nav_cutoff_readiness", 0.95)), 120.0, "nav cutoff readiness is below policy", "NAV_CUTOFF_READINESS_WEAK")
    penalize(freeze_enforcement_readiness, float(policy.get("minimum_freeze_enforcement_readiness", 0.95)), 120.0, "transaction freeze enforcement readiness is below policy", "FREEZE_ENFORCEMENT_READINESS_WEAK")

    max_pending = int(policy.get("maximum_pending_post_cutoff_requests", 0))
    if pending_post_cutoff_requests > max_pending:
        score -= 7.0 + (pending_post_cutoff_requests - max_pending) * 2.0
        reasons.append("pending post-cutoff requests exceed policy")
        alerts.append("PENDING_POST_CUTOFF_REQUESTS_EXCESS")
    max_overrides = int(policy.get("maximum_manual_override_events", 0))
    if manual_override_events > max_overrides:
        score -= 7.0 + (manual_override_events - max_overrides) * 2.0
        reasons.append("manual override events exceed policy")
        alerts.append("MANUAL_OVERRIDE_EVENTS_EXCESS")

    dealing = ctx.get("dealing_day_summary") or {}
    nav = ctx.get("nav_strike_summary") or {}
    exit_status = ctx.get("exit_finalization_status") or {}
    if dealing.get("latest_cutoff_status") != "applied":
        score -= 8.0
        reasons.append("dealing-day cutoff must be applied before transaction freeze can clear")
        alerts.append("DEALING_DAY_CUTOFF_NOT_APPLIED")
    if nav.get("latest_valuation_status") != "official":
        score -= 8.0
        reasons.append("official nav strike is required before investor transaction freeze can clear")
        alerts.append("NAV_NOT_OFFICIAL")
    if exit_status.get("posture") not in {"EXIT_FINALIZATION_CLEAR", "INSTITUTIONAL_EXIT_LOCKED"}:
        score -= 6.0
        reasons.append("investor exit finalization posture must be clear before full freeze release")
        alerts.append("EXIT_FINALIZATION_NOT_CLEAR")

    score = round(max(score, 0.0), 2)
    posture = _band(score)
    operator_review_required = bool(score < float(policy.get("minimum_score", 95.0)) or len(alerts) > 0)
    run = {
        "run_id": f"qnt40012_{int(datetime.now(timezone.utc).timestamp())}",
        "captured_at": _now_iso(),
        "score": score,
        "band": _band(score),
        "posture": posture,
        "operator_review_required": operator_review_required,
        "reasons": reasons,
        "alerts": alerts,
        "lock_readiness": lock_readiness,
        "nav_cutoff_readiness": nav_cutoff_readiness,
        "freeze_enforcement_readiness": freeze_enforcement_readiness,
        "pending_post_cutoff_requests": pending_post_cutoff_requests,
        "manual_override_events": manual_override_events,
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

@router.post('/record-dealing-day-lock')
def record_dealing_day_lock(payload: dict = Body(...), user=Depends(_require_user)):
    email = (user.get('email') or '').strip().lower()
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get('policy') or {})}
    event = {
        "lock_id": payload.get('lock_id') or f"lock_{int(datetime.now(timezone.utc).timestamp())}",
        "captured_at": _now_iso(),
        "dealing_date": payload.get('dealing_date') or _now_iso()[:10],
        "scope": payload.get('scope') or 'subscriptions_and_redemptions',
        "status": payload.get('status') or 'locked',
        "notes": payload.get('notes') or '',
    }
    _append(store, 'lock_events', event, int(policy.get('retain_cycles', 365)))
    _save(email, store)
    return {"ok": True, "event": event, "summary": _summary_for_email(email)}

@router.post('/record-nav-cutoff-enforcement')
def record_nav_cutoff_enforcement(payload: dict = Body(...), user=Depends(_require_user)):
    email = (user.get('email') or '').strip().lower()
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get('policy') or {})}
    event = {
        "cutoff_id": payload.get('cutoff_id') or f"cut_{int(datetime.now(timezone.utc).timestamp())}",
        "captured_at": _now_iso(),
        "valuation_date": payload.get('valuation_date') or _now_iso()[:10],
        "cutoff_rule": payload.get('cutoff_rule') or 'nav_cutoff_enforced',
        "status": payload.get('status') or 'enforced',
    }
    _append(store, 'nav_cutoff_events', event, int(policy.get('retain_cycles', 365)))
    _save(email, store)
    return {"ok": True, "event": event, "summary": _summary_for_email(email)}

@router.post('/enforce-investor-transaction-freeze')
def enforce_investor_transaction_freeze(payload: dict = Body(...), user=Depends(_require_user)):
    email = (user.get('email') or '').strip().lower()
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get('policy') or {})}
    event = {
        "freeze_id": payload.get('freeze_id') or f"frz_{int(datetime.now(timezone.utc).timestamp())}",
        "captured_at": _now_iso(),
        "transaction_scope": payload.get('transaction_scope') or 'investor_transactions',
        "freeze_reason": payload.get('freeze_reason') or 'dealing_day_lock_and_nav_cutoff',
        "status": payload.get('status') or 'active',
    }
    _append(store, 'transaction_freeze_events', event, int(policy.get('retain_cycles', 365)))
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
    session = dict(user)
    session.setdefault('logged_in', True)
    session.setdefault('is_admin', True)
    from backend.app import main as app_main
    app_main.save_session(session)
    dd = _dealing_day()
    nav = _nav_strike()
    data = dd._load(email)
    if not data.get('dealing_days'):
        dd.dealing_day_create({'dealing_date': _now_iso()[:10]})
        data = dd._load(email)
    day = data['dealing_days'][0]
    if day.get('cutoff_status') != 'applied':
        dd.dealing_day_apply_cutoff({'email': email, 'day_id': day['day_id'], 'notes': 'locked for nav strike and transaction freeze enforcement'})
    nav_data = nav._load(email)
    if not nav_data.get('valuations'):
        nav.nav_strike_create({'valuation_date': _now_iso()[:10]})
        nav_data = nav._load(email)
    latest_val = nav_data['valuations'][0]
    if latest_val.get('status') != 'official':
        nav.nav_strike_finalize({'email': email, 'valuation_id': latest_val['valuation_id'], 'notes': 'official nav finalized for dealing day lock'})
    _redemption_settlement().bootstrap_demo(user)
    record_dealing_day_lock({
        'dealing_date': _now_iso()[:10],
        'scope': 'subscriptions_redemptions_transfers',
        'status': 'locked',
        'notes': 'investor transaction window locked after cutoff',
    }, user)
    record_nav_cutoff_enforcement({
        'valuation_date': _now_iso()[:10],
        'cutoff_rule': 'hard_nav_cutoff',
        'status': 'enforced',
    }, user)
    enforce_investor_transaction_freeze({
        'transaction_scope': 'subscriptions_redemptions_switches',
        'freeze_reason': 'official_nav_pending_release_window',
        'status': 'active',
    }, user)
    run = _evaluate(email, {
        'lock_readiness': 0.98,
        'nav_cutoff_readiness': 0.98,
        'freeze_enforcement_readiness': 0.97,
        'pending_post_cutoff_requests': 0,
        'manual_override_events': 0,
    })
    return {"ok": True, "run": run, "summary": _summary_for_email(email)}
