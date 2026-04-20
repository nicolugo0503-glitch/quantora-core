from fastapi import APIRouter, Body, Depends
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json

router = APIRouter(
    prefix="/api/nav-publication-investor-notice-release-post-dealing-confirmation-distribution-layer",
    tags=["nav-publication-investor-notice-release-post-dealing-confirmation-distribution-layer"],
)

PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
ENGINE_DIR = ARTIFACTS_DIR / "nav_publication_investor_notice_release_post_dealing_confirmation_distribution_layer"
DEFAULT_POLICY = {
    "retain_cycles": 365,
    "minimum_score": 95.0,
    "minimum_nav_publication_readiness": 0.95,
    "minimum_notice_release_readiness": 0.95,
    "minimum_confirmation_distribution_readiness": 0.95,
    "maximum_pending_confirmations": 0,
    "maximum_failed_notice_routes": 0,
}

def _mu():
    from backend.app import qnt30557_multi_user_router as mu
    return mu

def _require_user():
    return _mu()._require_session()

def _dealing_lock():
    from backend.app import qnt40012_dealing_day_lock_nav_cutoff_enforcement_investor_transaction_freeze_control_layer_router as module
    return module

def _nav_strike():
    from backend.app import qnt30597_nav_strike_router as module
    return module

def _alloc_confirmation():
    from backend.app import qnt30598_allocation_confirmation_router as module
    return module

def _notice_routing():
    from backend.app import qnt30618_notice_routing_router as module
    return module

def _delivery_log():
    from backend.app import qnt30589_report_delivery_log_router as module
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
            "nav_publications": [],
            "investor_notice_releases": [],
            "confirmation_distributions": [],
            "latest_run": None,
            "last_context": {},
        }
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return data
    return json.loads(path.read_text(encoding="utf-8"))

def _save(email: str, data: dict):
    _path(email).write_text(json.dumps(data, indent=2), encoding="utf-8")

def _context(email: str) -> dict:
    lock_summary = _dealing_lock()._summary_for_email(email)
    nav_data = _nav_strike()._load(email)
    conf_data = _alloc_confirmation()._load(email)
    notice_data = _notice_routing()._load(email)
    delivery_data = _delivery_log()._load(email)
    latest_nav = (nav_data.get("valuations") or [None])[0]
    latest_conf = (conf_data.get("notes") or [None])[0]
    latest_notice = (notice_data.get("event_log") or [None])[0]
    latest_delivery = (delivery_data.get("events") or [None])[0]
    return {
        "captured_at": _now_iso(),
        "dealing_day_lock_status": lock_summary.get("dealing_day_lock_nav_cutoff_enforcement_investor_transaction_freeze_control_layer_status") or {},
        "nav_strike_summary": {
            "valuation_count": len(nav_data.get("valuations") or []),
            "latest_valuation_id": latest_nav.get("valuation_id") if latest_nav else None,
            "latest_valuation_status": latest_nav.get("status") if latest_nav else None,
            "official_nav": latest_nav.get("official_nav") if latest_nav else None,
        },
        "allocation_confirmation_summary": {
            "note_count": len(conf_data.get("notes") or []),
            "latest_note_id": latest_conf.get("note_id") if latest_conf else None,
            "latest_note_status": latest_conf.get("status") if latest_conf else None,
            "latest_ack_status": latest_conf.get("ack_status") if latest_conf else None,
        },
        "notice_routing_summary": {
            "preference_count": len(notice_data.get("preferences") or []),
            "rule_count": len(notice_data.get("routing_rules") or []),
            "latest_notice_event_type": latest_notice.get("event_type") if latest_notice else None,
        },
        "delivery_log_summary": {
            "delivery_count": len(delivery_data.get("events") or []),
            "latest_event_id": latest_delivery.get("event_id") if latest_delivery else None,
            "latest_delivery_status": latest_delivery.get("delivery_status") if latest_delivery else None,
            "latest_ack_status": latest_delivery.get("ack_status") if latest_delivery else None,
        },
    }

def _summary_for_email(email: str) -> dict:
    s = _load(email)
    latest = s.get("latest_run") or {}
    return {
        "nav_publication_investor_notice_release_post_dealing_confirmation_distribution_layer_status": {
            "posture": latest.get("posture", "UNINITIALIZED"),
            "latest_score": latest.get("score"),
            "band": latest.get("band", "UNSET"),
            "run_count": len(s.get("runs") or []),
            "alert_count": len(s.get("alerts") or []),
            "nav_publication_count": len(s.get("nav_publications") or []),
            "investor_notice_release_count": len(s.get("investor_notice_releases") or []),
            "confirmation_distribution_count": len(s.get("confirmation_distributions") or []),
            "operator_review_required": bool(latest.get("operator_review_required", False)),
        },
        "latest_run": latest,
        "alerts": s.get("alerts") or [],
        "policy": s.get("policy") or dict(DEFAULT_POLICY),
        "last_context": s.get("last_context") or {},
        "nav_publications": s.get("nav_publications") or [],
        "investor_notice_releases": s.get("investor_notice_releases") or [],
        "confirmation_distributions": s.get("confirmation_distributions") or [],
    }

def _band(score: float) -> str:
    if score >= 98.0:
        return "POST_DEALING_PUBLICATION_LOCKED"
    if score >= 95.0:
        return "POST_DEALING_NOTICE_CLEAR"
    if score >= 91.0:
        return "POST_DEALING_NOTICE_WATCH"
    return "POST_DEALING_NOTICE_REMEDIATION_REQUIRED"

def _evaluate(email: str, payload: dict) -> dict:
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get("policy") or {})}
    ctx = _context(email)

    nav_publication_readiness = float(payload.get("nav_publication_readiness", 0.0) or 0.0)
    notice_release_readiness = float(payload.get("notice_release_readiness", 0.0) or 0.0)
    confirmation_distribution_readiness = float(payload.get("confirmation_distribution_readiness", 0.0) or 0.0)
    pending_confirmations = int(payload.get("pending_confirmations", 0) or 0)
    failed_notice_routes = int(payload.get("failed_notice_routes", 0) or 0)

    score = 100.0
    reasons = []
    alerts = []

    def penalize(metric: float, minimum: float, weight: float, reason: str, code: str):
        nonlocal score
        if metric < minimum:
            score -= round((minimum - metric) * weight, 2)
            reasons.append(reason)
            alerts.append(code)

    penalize(nav_publication_readiness, float(policy.get("minimum_nav_publication_readiness", 0.95)), 120.0, "nav publication readiness is below policy", "NAV_PUBLICATION_READINESS_WEAK")
    penalize(notice_release_readiness, float(policy.get("minimum_notice_release_readiness", 0.95)), 120.0, "investor notice release readiness is below policy", "NOTICE_RELEASE_READINESS_WEAK")
    penalize(confirmation_distribution_readiness, float(policy.get("minimum_confirmation_distribution_readiness", 0.95)), 120.0, "post-dealing confirmation distribution readiness is below policy", "CONFIRMATION_DISTRIBUTION_READINESS_WEAK")

    max_pending = int(policy.get("maximum_pending_confirmations", 0))
    if pending_confirmations > max_pending:
        score -= 7.0 + (pending_confirmations - max_pending) * 2.0
        reasons.append("pending confirmations exceed policy")
        alerts.append("PENDING_CONFIRMATIONS_EXCESS")
    max_failed_routes = int(policy.get("maximum_failed_notice_routes", 0))
    if failed_notice_routes > max_failed_routes:
        score -= 7.0 + (failed_notice_routes - max_failed_routes) * 2.0
        reasons.append("failed notice routes exceed policy")
        alerts.append("FAILED_NOTICE_ROUTES_EXCESS")

    dealing_status = ctx.get("dealing_day_lock_status") or {}
    nav_summary = ctx.get("nav_strike_summary") or {}
    conf_summary = ctx.get("allocation_confirmation_summary") or {}
    notice_summary = ctx.get("notice_routing_summary") or {}
    delivery_summary = ctx.get("delivery_log_summary") or {}

    if dealing_status.get("posture") not in {"TRANSACTION_FREEZE_CLEAR", "DEALING_DAY_LOCKED"}:
        score -= 8.0
        reasons.append("dealing-day lock posture must be clear before nav publication and investor notice release")
        alerts.append("DEALING_DAY_LOCK_POSTURE_NOT_CLEAR")
    if nav_summary.get("latest_valuation_status") != "official":
        score -= 8.0
        reasons.append("official nav strike is required before nav publication")
        alerts.append("NAV_NOT_OFFICIAL")
    if conf_summary.get("note_count", 0) < 1:
        score -= 6.0
        reasons.append("at least one post-dealing confirmation must be generated before distribution")
        alerts.append("NO_CONFIRMATION_NOTE_AVAILABLE")
    if notice_summary.get("rule_count", 0) < 1:
        score -= 4.0
        reasons.append("notice routing rules must exist before investor notice release")
        alerts.append("NO_NOTICE_ROUTING_RULE")
    if delivery_summary.get("delivery_count", 0) < 1:
        score -= 4.0
        reasons.append("delivery log must show at least one delivered event before post-dealing confirmation can clear")
        alerts.append("NO_DELIVERY_LOG_EVENT")

    score = round(max(score, 0.0), 2)
    posture = _band(score)
    operator_review_required = bool(score < float(policy.get("minimum_score", 95.0)) or len(alerts) > 0)
    run = {
        "run_id": f"qnt40013_{int(datetime.now(timezone.utc).timestamp())}",
        "captured_at": _now_iso(),
        "score": score,
        "band": _band(score),
        "posture": posture,
        "operator_review_required": operator_review_required,
        "reasons": reasons,
        "alerts": alerts,
        "nav_publication_readiness": nav_publication_readiness,
        "notice_release_readiness": notice_release_readiness,
        "confirmation_distribution_readiness": confirmation_distribution_readiness,
        "pending_confirmations": pending_confirmations,
        "failed_notice_routes": failed_notice_routes,
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

@router.post('/publish-nav')
def publish_nav(payload: dict = Body(...), user=Depends(_require_user)):
    email = (user.get('email') or '').strip().lower()
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get('policy') or {})}
    nav_data = _nav_strike()._load(email)
    latest = (nav_data.get('valuations') or [None])[0]
    event = {
        "publication_id": payload.get('publication_id') or f"navpub_{int(datetime.now(timezone.utc).timestamp())}",
        "captured_at": _now_iso(),
        "valuation_id": payload.get('valuation_id') or (latest.get('valuation_id') if latest else None),
        "valuation_date": payload.get('valuation_date') or (latest.get('valuation_date') if latest else _now_iso()[:10]),
        "official_nav": payload.get('official_nav') if payload.get('official_nav') is not None else (latest.get('official_nav') if latest else 0.0),
        "status": payload.get('status') or 'published',
        "channel": payload.get('channel') or 'investor_portal',
    }
    _append(store, 'nav_publications', event, int(policy.get('retain_cycles', 365)))
    _save(email, store)
    return {"ok": True, "event": event, "summary": _summary_for_email(email)}

@router.post('/release-investor-notice')
def release_investor_notice(payload: dict = Body(...), user=Depends(_require_user)):
    email = (user.get('email') or '').strip().lower()
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get('policy') or {})}
    investor_id = payload.get('investor_id') or 'all_investors'
    route_result = _notice_routing().resolve_notice_route({
        'investor_id': investor_id,
        'notice_type': payload.get('notice_type') or 'nav_publication',
        'urgency': payload.get('urgency') or 'normal',
    })
    route = (route_result or {}).get('route') or {}
    event = {
        "notice_release_id": payload.get('notice_release_id') or f"notice_{int(datetime.now(timezone.utc).timestamp())}",
        "captured_at": _now_iso(),
        "investor_id": investor_id,
        "notice_type": payload.get('notice_type') or 'nav_publication',
        "resolved_channel": route.get('resolved_channel') or payload.get('channel') or 'portal',
        "urgency": route.get('urgency') or payload.get('urgency') or 'normal',
        "status": payload.get('status') or 'released',
    }
    _append(store, 'investor_notice_releases', event, int(policy.get('retain_cycles', 365)))
    _save(email, store)
    return {"ok": True, "event": event, "route": route, "summary": _summary_for_email(email)}

@router.post('/distribute-post-dealing-confirmation')
def distribute_post_dealing_confirmation(payload: dict = Body(...), user=Depends(_require_user)):
    email = (user.get('email') or '').strip().lower()
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get('policy') or {})}
    conf_data = _alloc_confirmation()._load(email)
    latest = (conf_data.get('notes') or [None])[0]
    note_id = payload.get('note_id') or (latest.get('note_id') if latest else None)
    if latest and latest.get('status') != 'delivered':
        _alloc_confirmation().allocation_confirmations_deliver({'note_id': latest['note_id'], 'notes': 'post-dealing confirmation released'})
    event = {
        "distribution_id": payload.get('distribution_id') or f"dist_{int(datetime.now(timezone.utc).timestamp())}",
        "captured_at": _now_iso(),
        "note_id": note_id,
        "distribution_channel": payload.get('distribution_channel') or 'portal',
        "status": payload.get('status') or 'distributed',
        "ack_status": payload.get('ack_status') or 'pending',
    }
    if note_id:
        session_user = dict(user)
        session_user.setdefault('email', email)
        from backend.app import main as app_main
        app_main.save_session({**session_user, 'logged_in': True})
        from backend.app import qnt30588_statement_pack_router as _packs_mod
        if not _packs_mod._load(email).get('packs'):
            _packs_mod.statement_packs_generate({'title': 'Post-Dealing Confirmation Support Pack'})
        _delivery_log().report_delivery_log_latest({'channel': event['distribution_channel'], 'notes': 'post-dealing confirmation distribution'})
    _append(store, 'confirmation_distributions', event, int(policy.get('retain_cycles', 365)))
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
    session.setdefault('display_name', 'Quantora Operator')
    from backend.app import main as app_main
    app_main.save_session(session)

    _dealing_lock().bootstrap_demo(user)

    conf = _alloc_confirmation()
    conf_data = conf._load(email)
    if not conf_data.get('notes'):
        conf.allocation_confirmations_generate({'title': 'Post-Dealing Confirmation'})
        conf_data = conf._load(email)
    latest_note = conf_data['notes'][0]
    if latest_note.get('status') != 'delivered':
        conf.allocation_confirmations_deliver({'note_id': latest_note['note_id'], 'notes': 'released after nav publication'})

    nr = _notice_routing()
    nr.set_preferences({'investor_id': 'all_investors', 'preferences': {'preferred_channels': ['portal', 'email_simulated'], 'urgent_notice_channel': 'email_simulated'}})
    if not nr._load(email).get('routing_rules'):
        nr.add_rule({'rule_name': 'NAV Publication Release Rule', 'notice_type': 'nav_publication', 'channel': 'portal', 'priority': 'high', 'scope': 'all_investors'})

    publish_nav({'channel': 'investor_portal', 'status': 'published'}, user)
    release_investor_notice({'investor_id': 'all_investors', 'notice_type': 'nav_publication', 'urgency': 'normal', 'status': 'released'}, user)
    distribute_post_dealing_confirmation({'distribution_channel': 'portal', 'status': 'distributed', 'ack_status': 'pending'}, user)

    run = _evaluate(email, {
        'nav_publication_readiness': 0.98,
        'notice_release_readiness': 0.98,
        'confirmation_distribution_readiness': 0.97,
        'pending_confirmations': 0,
        'failed_notice_routes': 0,
    })
    return {"ok": True, "run": run, "summary": _summary_for_email(email)}
