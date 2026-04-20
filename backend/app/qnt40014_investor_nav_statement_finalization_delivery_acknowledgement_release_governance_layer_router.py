from fastapi import APIRouter, Body, Depends
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json

router = APIRouter(
    prefix="/api/investor-nav-statement-finalization-delivery-acknowledgement-release-governance-layer",
    tags=["investor-nav-statement-finalization-delivery-acknowledgement-release-governance-layer"],
)

PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
ENGINE_DIR = ARTIFACTS_DIR / "investor_nav_statement_finalization_delivery_acknowledgement_release_governance_layer"
DEFAULT_POLICY = {
    "retain_cycles": 365,
    "minimum_score": 95.0,
    "minimum_statement_finalization_readiness": 0.95,
    "minimum_delivery_acknowledgement_readiness": 0.95,
    "minimum_release_governance_readiness": 0.96,
    "maximum_pending_delivery_acknowledgements": 0,
    "maximum_open_release_exceptions": 0,
}


def _mu():
    from backend.app import qnt30557_multi_user_router as mu
    return mu


def _require_user():
    return _mu()._require_session()


def _post_dealing():
    from backend.app import qnt40013_nav_publication_investor_notice_release_post_dealing_confirmation_distribution_layer_router as module
    return module


def _statement_packs():
    from backend.app import qnt30588_statement_pack_router as module
    return module


def _delivery_log():
    from backend.app import qnt30589_report_delivery_log_router as module
    return module


def _distribution():
    from backend.app import qnt40003_investor_statement_packs_capital_account_waterfalls_lp_performance_distribution_layer_router as module
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
            "nav_statement_finalizations": [],
            "delivery_acknowledgements": [],
            "release_governance_actions": [],
            "latest_run": None,
            "last_context": {},
        }
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return data
    return json.loads(path.read_text(encoding="utf-8"))


def _save(email: str, data: dict):
    _path(email).write_text(json.dumps(data, indent=2), encoding="utf-8")


def _context(email: str) -> dict:
    post = _post_dealing()._summary_for_email(email)
    packs = _statement_packs()._load(email)
    delivery = _delivery_log()._load(email)
    distro = _distribution()._summary_for_email(email)
    latest_pack = (packs.get("packs") or [None])[0]
    latest_delivery = (delivery.get("events") or [None])[0]
    return {
        "captured_at": _now_iso(),
        "post_dealing_summary": {
            "posture": ((post.get("nav_publication_investor_notice_release_post_dealing_confirmation_distribution_layer_status") or {}).get("posture")),
            "nav_publication_count": ((post.get("nav_publications") or []) and len(post.get("nav_publications") or [])) or 0,
            "notice_release_count": len(post.get("investor_notice_releases") or []),
            "confirmation_distribution_count": len(post.get("confirmation_distributions") or []),
        },
        "statement_pack_summary": {
            "pack_count": len(packs.get("packs") or []),
            "latest_pack_id": latest_pack.get("pack_id") if latest_pack else None,
            "latest_pack_title": latest_pack.get("title") if latest_pack else None,
            "latest_delivery_status": latest_pack.get("delivery_status") if latest_pack else None,
            "latest_sections": len((latest_pack or {}).get("sections") or []),
        },
        "delivery_log_summary": {
            "delivery_count": len(delivery.get("events") or []),
            "pending_ack_count": sum(1 for e in delivery.get("events") or [] if e.get("ack_status") == "pending"),
            "acknowledged_count": sum(1 for e in delivery.get("events") or [] if e.get("ack_status") == "acknowledged"),
            "latest_event_id": latest_delivery.get("event_id") if latest_delivery else None,
            "latest_ack_status": latest_delivery.get("ack_status") if latest_delivery else None,
        },
        "distribution_summary": {
            "posture": ((distro.get("investor_statement_packs_capital_account_waterfalls_lp_performance_distribution_layer_status") or {}).get("posture")),
            "distribution_count": len(distro.get("lp_distributions") or []),
            "acknowledgement_count": len(distro.get("distribution_acknowledgements") or []),
        },
    }


def _summary_for_email(email: str) -> dict:
    s = _load(email)
    latest = s.get("latest_run") or {}
    return {
        "investor_nav_statement_finalization_delivery_acknowledgement_release_governance_layer_status": {
            "posture": latest.get("posture", "UNINITIALIZED"),
            "latest_score": latest.get("score"),
            "band": latest.get("band", "UNSET"),
            "run_count": len(s.get("runs") or []),
            "alert_count": len(s.get("alerts") or []),
            "nav_statement_finalization_count": len(s.get("nav_statement_finalizations") or []),
            "delivery_acknowledgement_count": len(s.get("delivery_acknowledgements") or []),
            "release_governance_action_count": len(s.get("release_governance_actions") or []),
            "operator_review_required": bool(latest.get("operator_review_required", False)),
        },
        "latest_run": latest,
        "alerts": s.get("alerts") or [],
        "policy": s.get("policy") or dict(DEFAULT_POLICY),
        "last_context": s.get("last_context") or {},
        "nav_statement_finalizations": s.get("nav_statement_finalizations") or [],
        "delivery_acknowledgements": s.get("delivery_acknowledgements") or [],
        "release_governance_actions": s.get("release_governance_actions") or [],
    }


def _band(score: float) -> str:
    if score >= 98.0:
        return "INVESTOR_RELEASE_GOVERNANCE_LOCKED"
    if score >= 95.0:
        return "INVESTOR_RELEASE_CLEAR"
    if score >= 91.0:
        return "INVESTOR_RELEASE_WATCH"
    return "INVESTOR_RELEASE_REMEDIATION_REQUIRED"


def _evaluate(email: str, payload: dict) -> dict:
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get("policy") or {})}
    ctx = _context(email)

    statement_finalization_readiness = float(payload.get("statement_finalization_readiness", 0.0) or 0.0)
    delivery_acknowledgement_readiness = float(payload.get("delivery_acknowledgement_readiness", 0.0) or 0.0)
    release_governance_readiness = float(payload.get("release_governance_readiness", 0.0) or 0.0)
    pending_delivery_acknowledgements = int(payload.get("pending_delivery_acknowledgements", 0) or 0)
    open_release_exceptions = int(payload.get("open_release_exceptions", 0) or 0)

    score = 100.0
    reasons = []
    alerts = []

    def penalize(metric: float, minimum: float, weight: float, reason: str, code: str):
        nonlocal score
        if metric < minimum:
            score -= round((minimum - metric) * weight, 2)
            reasons.append(reason)
            alerts.append(code)

    penalize(statement_finalization_readiness, float(policy.get("minimum_statement_finalization_readiness", 0.95)), 120.0, "nav statement finalization readiness is below policy", "STATEMENT_FINALIZATION_READINESS_WEAK")
    penalize(delivery_acknowledgement_readiness, float(policy.get("minimum_delivery_acknowledgement_readiness", 0.95)), 120.0, "delivery acknowledgement readiness is below policy", "DELIVERY_ACK_READINESS_WEAK")
    penalize(release_governance_readiness, float(policy.get("minimum_release_governance_readiness", 0.96)), 120.0, "release governance readiness is below policy", "RELEASE_GOVERNANCE_READINESS_WEAK")

    max_pending = int(policy.get("maximum_pending_delivery_acknowledgements", 0))
    if pending_delivery_acknowledgements > max_pending:
        score -= 7.0 + (pending_delivery_acknowledgements - max_pending) * 2.0
        reasons.append("pending delivery acknowledgements exceed policy")
        alerts.append("PENDING_DELIVERY_ACKS_EXCESS")
    max_open = int(policy.get("maximum_open_release_exceptions", 0))
    if open_release_exceptions > max_open:
        score -= 7.0 + (open_release_exceptions - max_open) * 2.0
        reasons.append("open investor release exceptions exceed policy")
        alerts.append("OPEN_RELEASE_EXCEPTIONS")

    post_summary = ctx.get("post_dealing_summary") or {}
    pack_summary = ctx.get("statement_pack_summary") or {}
    log_summary = ctx.get("delivery_log_summary") or {}
    distribution_summary = ctx.get("distribution_summary") or {}

    if post_summary.get("posture") not in {"POST_DEALING_NOTICE_CLEAR", "POST_DEALING_PUBLICATION_LOCKED"}:
        score -= 8.0
        reasons.append("post-dealing release posture must be clear before investor nav statement finalization")
        alerts.append("POST_DEALING_POSTURE_NOT_CLEAR")
    if pack_summary.get("pack_count", 0) < 1 or pack_summary.get("latest_sections", 0) < 3:
        score -= 8.0
        reasons.append("statement pack must exist before nav statement finalization")
        alerts.append("STATEMENT_PACK_NOT_READY")
    if log_summary.get("delivery_count", 0) < 1:
        score -= 6.0
        reasons.append("delivery log must show at least one delivered statement or confirmation")
        alerts.append("NO_DELIVERY_EVIDENCE")
    if distribution_summary.get("posture") in {None, "UNINITIALIZED"}:
        score -= 6.0
        reasons.append("lp performance distribution posture is not initialized")
        alerts.append("LP_DISTRIBUTION_NOT_READY")

    score = round(max(score, 0.0), 2)
    posture = _band(score)
    operator_review_required = bool(score < float(policy.get("minimum_score", 95.0)) or len(alerts) > 0)
    run = {
        "run_id": f"qnt40014_{int(datetime.now(timezone.utc).timestamp())}",
        "captured_at": _now_iso(),
        "score": score,
        "band": _band(score),
        "posture": posture,
        "operator_review_required": operator_review_required,
        "reasons": reasons,
        "alerts": alerts,
        "statement_finalization_readiness": statement_finalization_readiness,
        "delivery_acknowledgement_readiness": delivery_acknowledgement_readiness,
        "release_governance_readiness": release_governance_readiness,
        "pending_delivery_acknowledgements": pending_delivery_acknowledgements,
        "open_release_exceptions": open_release_exceptions,
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


@router.post('/finalize-nav-statement')
def finalize_nav_statement(payload: dict = Body(...), user=Depends(_require_user)):
    email = (user.get('email') or '').strip().lower()
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get('policy') or {})}
    packs = _statement_packs()._load(email)
    latest = (packs.get('packs') or [None])[0]
    event = {
        "finalization_id": payload.get('finalization_id') or f"navstmt_{int(datetime.now(timezone.utc).timestamp())}",
        "captured_at": _now_iso(),
        "pack_id": payload.get('pack_id') or (latest.get('pack_id') if latest else None),
        "statement_date": payload.get('statement_date') or _now_iso()[:10],
        "statement_version": payload.get('statement_version') or 'final',
        "status": payload.get('status') or 'finalized',
    }
    _append(store, 'nav_statement_finalizations', event, int(policy.get('retain_cycles', 365)))
    _save(email, store)
    return {"ok": True, "event": event, "summary": _summary_for_email(email)}


@router.post('/record-delivery-acknowledgement')
def record_delivery_acknowledgement(payload: dict = Body(...), user=Depends(_require_user)):
    email = (user.get('email') or '').strip().lower()
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get('policy') or {})}
    delivery_data = _delivery_log()._load(email)
    latest = (delivery_data.get('events') or [None])[0]
    event_id = payload.get('event_id') or (latest.get('event_id') if latest else None)
    ack_event = None
    if event_id:
        ack_result = _delivery_log().report_delivery_log_ack({'event_id': event_id, 'notes': payload.get('notes') or 'investor acknowledgement recorded'})
        ack_event = ack_result.get('event')
    event = {
        "acknowledgement_id": payload.get('acknowledgement_id') or f"ack_{int(datetime.now(timezone.utc).timestamp())}",
        "captured_at": _now_iso(),
        "event_id": event_id,
        "ack_status": payload.get('ack_status') or ((ack_event or {}).get('ack_status') or 'acknowledged'),
        "acknowledged_by": payload.get('acknowledged_by') or 'investor',
    }
    _append(store, 'delivery_acknowledgements', event, int(policy.get('retain_cycles', 365)))
    _save(email, store)
    return {"ok": True, "event": event, "delivery_event": ack_event, "summary": _summary_for_email(email)}


@router.post('/approve-release-governance')
def approve_release_governance(payload: dict = Body(...), user=Depends(_require_user)):
    email = (user.get('email') or '').strip().lower()
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get('policy') or {})}
    event = {
        "governance_action_id": payload.get('governance_action_id') or f"gov_{int(datetime.now(timezone.utc).timestamp())}",
        "captured_at": _now_iso(),
        "release_scope": payload.get('release_scope') or 'investor_nav_statements',
        "approver": payload.get('approver') or user.get('display_name') or 'Quantora Operator',
        "status": payload.get('status') or 'approved',
        "notes": payload.get('notes') or 'release governance approved',
    }
    _append(store, 'release_governance_actions', event, int(policy.get('retain_cycles', 365)))
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

    _post_dealing().bootstrap_demo(user)
    _distribution().bootstrap_demo(user)

    packs = _statement_packs()._load(email)
    if not packs.get('packs'):
        _statement_packs().statement_packs_generate({'title': 'Investor NAV Statement Pack'})
        packs = _statement_packs()._load(email)
    latest_pack = packs['packs'][0]
    if latest_pack.get('delivery_status') != 'delivered_simulated':
        _statement_packs().statement_packs_deliver({'pack_id': latest_pack['pack_id'], 'channel': 'portal_simulated'})

    if not _delivery_log()._load(email).get('events'):
        _delivery_log().report_delivery_log_latest({'channel': 'portal_simulated', 'notes': 'investor nav statement delivery'})

    finalize_nav_statement({'pack_id': latest_pack['pack_id'], 'statement_version': 'final', 'status': 'finalized'}, user)
    record_delivery_acknowledgement({'notes': 'investor viewed and acknowledged release'}, user)
    approve_release_governance({'release_scope': 'investor_nav_statements', 'status': 'approved'}, user)

    run = _evaluate(email, {
        'statement_finalization_readiness': 0.98,
        'delivery_acknowledgement_readiness': 0.98,
        'release_governance_readiness': 0.98,
        'pending_delivery_acknowledgements': 0,
        'open_release_exceptions': 0,
    })
    return {"ok": True, "run": run, "summary": _summary_for_email(email)}
