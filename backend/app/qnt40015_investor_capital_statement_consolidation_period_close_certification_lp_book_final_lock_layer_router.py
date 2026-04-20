from fastapi import APIRouter, Body, Depends
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json

router = APIRouter(
    prefix="/api/investor-capital-statement-consolidation-period-close-certification-lp-book-final-lock-layer",
    tags=["investor-capital-statement-consolidation-period-close-certification-lp-book-final-lock-layer"],
)

PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
ENGINE_DIR = ARTIFACTS_DIR / "investor_capital_statement_consolidation_period_close_certification_lp_book_final_lock_layer"
DEFAULT_POLICY = {
    "retain_cycles": 365,
    "minimum_score": 95.0,
    "minimum_statement_consolidation_readiness": 0.95,
    "minimum_period_close_certification_readiness": 0.96,
    "minimum_lp_book_lock_readiness": 0.96,
    "maximum_pending_statement_exceptions": 0,
    "maximum_open_close_breaks": 0,
}


def _mu():
    from backend.app import qnt30557_multi_user_router as mu
    return mu


def _require_user():
    return _mu()._require_session()


def _release_governance():
    from backend.app import qnt40014_investor_nav_statement_finalization_delivery_acknowledgement_release_governance_layer_router as module
    return module


def _capital():
    from backend.app import qnt30624_capital_ledger_router as module
    return module


def _rollforward():
    from backend.app import qnt30594_rollforward_router as module
    return module


def _statement_packs():
    from backend.app import qnt30588_statement_pack_router as module
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
            "statement_consolidations": [],
            "period_close_certifications": [],
            "lp_book_locks": [],
            "latest_run": None,
            "last_context": {},
        }
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return data
    return json.loads(path.read_text(encoding="utf-8"))


def _save(email: str, data: dict):
    _path(email).write_text(json.dumps(data, indent=2), encoding="utf-8")


def _context(email: str) -> dict:
    release = _release_governance()._summary_for_email(email)
    capital = _capital().capital_ledger_summary()
    rollforward = _rollforward().rollforward_summary()
    packs = _statement_packs().statement_packs_summary()
    delivery = _delivery_log().report_delivery_log_summary()
    latest_period = rollforward.get("latest_period") or {}
    latest_pack = packs.get("latest_pack") or {}
    latest_delivery = delivery.get("latest_event") or {}
    latest_release_run = release.get("latest_run") or {}
    return {
        "captured_at": _now_iso(),
        "release_governance_summary": {
            "posture": ((release.get("investor_nav_statement_finalization_delivery_acknowledgement_release_governance_layer_status") or {}).get("posture")),
            "score": latest_release_run.get("score"),
            "delivery_acknowledgement_count": len(release.get("delivery_acknowledgements") or []),
            "release_governance_action_count": len(release.get("release_governance_actions") or []),
        },
        "capital_ledger_summary": {
            "account_count": capital.get("account_count", 0),
            "entry_count": capital.get("entry_count", 0),
            "allocation_count": capital.get("allocation_count", 0),
            "total_nav": capital.get("total_nav", 0.0),
            "total_funded_capital": capital.get("total_funded_capital", 0.0),
        },
        "rollforward_summary": {
            "period_count": rollforward.get("period_count", 0),
            "locked_count": rollforward.get("locked_count", 0),
            "latest_period_id": latest_period.get("period_id"),
            "latest_period_status": latest_period.get("status"),
        },
        "statement_pack_summary": {
            "pack_count": packs.get("pack_count", 0),
            "delivered_count": packs.get("delivered_count", 0),
            "latest_pack_id": latest_pack.get("pack_id"),
            "latest_delivery_status": latest_pack.get("delivery_status"),
        },
        "delivery_log_summary": {
            "delivery_count": delivery.get("delivery_count", 0),
            "acknowledged_count": delivery.get("acknowledged_count", 0),
            "pending_ack_count": delivery.get("pending_ack_count", 0),
            "latest_event_id": latest_delivery.get("event_id"),
            "latest_ack_status": latest_delivery.get("ack_status"),
        },
    }


def _summary_for_email(email: str) -> dict:
    s = _load(email)
    latest = s.get("latest_run") or {}
    return {
        "investor_capital_statement_consolidation_period_close_certification_lp_book_final_lock_layer_status": {
            "posture": latest.get("posture", "UNINITIALIZED"),
            "latest_score": latest.get("score"),
            "band": latest.get("band", "UNSET"),
            "run_count": len(s.get("runs") or []),
            "alert_count": len(s.get("alerts") or []),
            "statement_consolidation_count": len(s.get("statement_consolidations") or []),
            "period_close_certification_count": len(s.get("period_close_certifications") or []),
            "lp_book_lock_count": len(s.get("lp_book_locks") or []),
            "operator_review_required": bool(latest.get("operator_review_required", False)),
        },
        "latest_run": latest,
        "alerts": s.get("alerts") or [],
        "policy": s.get("policy") or dict(DEFAULT_POLICY),
        "last_context": s.get("last_context") or {},
        "statement_consolidations": s.get("statement_consolidations") or [],
        "period_close_certifications": s.get("period_close_certifications") or [],
        "lp_book_locks": s.get("lp_book_locks") or [],
    }


def _band(score: float) -> str:
    if score >= 98.0:
        return "LP_BOOK_FINAL_LOCKED"
    if score >= 95.0:
        return "PERIOD_CLOSE_CLEAR"
    if score >= 91.0:
        return "PERIOD_CLOSE_WATCH"
    return "PERIOD_CLOSE_REMEDIATION_REQUIRED"


def _evaluate(email: str, payload: dict) -> dict:
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get("policy") or {})}
    ctx = _context(email)

    statement_consolidation_readiness = float(payload.get("statement_consolidation_readiness", 0.0) or 0.0)
    period_close_certification_readiness = float(payload.get("period_close_certification_readiness", 0.0) or 0.0)
    lp_book_lock_readiness = float(payload.get("lp_book_lock_readiness", 0.0) or 0.0)
    pending_statement_exceptions = int(payload.get("pending_statement_exceptions", 0) or 0)
    open_close_breaks = int(payload.get("open_close_breaks", 0) or 0)

    score = 100.0
    reasons = []
    alerts = []

    def penalize(metric: float, minimum: float, weight: float, reason: str, code: str):
        nonlocal score
        if metric < minimum:
            score -= round((minimum - metric) * weight, 2)
            reasons.append(reason)
            alerts.append(code)

    penalize(statement_consolidation_readiness, float(policy.get("minimum_statement_consolidation_readiness", 0.95)), 120.0, "statement consolidation readiness is below policy", "STATEMENT_CONSOLIDATION_READINESS_WEAK")
    penalize(period_close_certification_readiness, float(policy.get("minimum_period_close_certification_readiness", 0.96)), 120.0, "period close certification readiness is below policy", "PERIOD_CLOSE_CERTIFICATION_READINESS_WEAK")
    penalize(lp_book_lock_readiness, float(policy.get("minimum_lp_book_lock_readiness", 0.96)), 120.0, "lp book final lock readiness is below policy", "LP_BOOK_LOCK_READINESS_WEAK")

    max_pending = int(policy.get("maximum_pending_statement_exceptions", 0))
    if pending_statement_exceptions > max_pending:
        score -= 7.0 + (pending_statement_exceptions - max_pending) * 2.0
        reasons.append("pending statement exceptions exceed policy")
        alerts.append("PENDING_STATEMENT_EXCEPTIONS_EXCESS")
    max_open = int(policy.get("maximum_open_close_breaks", 0))
    if open_close_breaks > max_open:
        score -= 7.0 + (open_close_breaks - max_open) * 2.0
        reasons.append("open period close breaks exceed policy")
        alerts.append("OPEN_PERIOD_CLOSE_BREAKS")

    release_summary = ctx.get("release_governance_summary") or {}
    capital_summary = ctx.get("capital_ledger_summary") or {}
    rollforward_summary = ctx.get("rollforward_summary") or {}
    pack_summary = ctx.get("statement_pack_summary") or {}
    delivery_summary = ctx.get("delivery_log_summary") or {}

    if release_summary.get("posture") not in {"INVESTOR_RELEASE_CLEAR", "INVESTOR_RELEASE_GOVERNANCE_LOCKED"}:
        score -= 8.0
        reasons.append("investor release governance posture must be clear before final close")
        alerts.append("RELEASE_GOVERNANCE_NOT_CLEAR")
    if pack_summary.get("pack_count", 0) < 1 or pack_summary.get("delivered_count", 0) < 1:
        score -= 8.0
        reasons.append("delivered investor statement pack evidence is required before period close final lock")
        alerts.append("STATEMENT_PACK_DELIVERY_INCOMPLETE")
    if delivery_summary.get("acknowledged_count", 0) < 1:
        score -= 6.0
        reasons.append("delivery acknowledgement evidence is required before lp book final lock")
        alerts.append("DELIVERY_ACK_EVIDENCE_MISSING")
    if rollforward_summary.get("period_count", 0) < 1:
        score -= 6.0
        reasons.append("period rollforward evidence is missing")
        alerts.append("ROLLFORWARD_MISSING")
    elif rollforward_summary.get("locked_count", 0) < 1 and rollforward_summary.get("latest_period_status") != "locked":
        score -= 4.0
        reasons.append("latest rollforward period is not yet locked")
        alerts.append("ROLLFORWARD_NOT_LOCKED")
    if capital_summary.get("account_count", 0) < 1:
        score -= 4.0
        reasons.append("capital ledger has no investor accounts for close certification")
        alerts.append("CAPITAL_LEDGER_EMPTY")

    score = round(max(score, 0.0), 2)
    posture = _band(score)
    operator_review_required = bool(score < float(policy.get("minimum_score", 95.0)) or len(alerts) > 0)
    run = {
        "run_id": f"qnt40015_{int(datetime.now(timezone.utc).timestamp())}",
        "captured_at": _now_iso(),
        "score": score,
        "band": _band(score),
        "posture": posture,
        "operator_review_required": operator_review_required,
        "reasons": reasons,
        "alerts": alerts,
        "statement_consolidation_readiness": statement_consolidation_readiness,
        "period_close_certification_readiness": period_close_certification_readiness,
        "lp_book_lock_readiness": lp_book_lock_readiness,
        "pending_statement_exceptions": pending_statement_exceptions,
        "open_close_breaks": open_close_breaks,
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


@router.post('/record-statement-consolidation')
def record_statement_consolidation(payload: dict = Body(...), user=Depends(_require_user)):
    email = (user.get('email') or '').strip().lower()
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get('policy') or {})}
    packs = _statement_packs().statement_packs_summary()
    latest_pack = packs.get('latest_pack') or {}
    event = {
        "consolidation_id": payload.get('consolidation_id') or f"con_{int(datetime.now(timezone.utc).timestamp())}",
        "captured_at": _now_iso(),
        "pack_id": payload.get('pack_id') or latest_pack.get('pack_id'),
        "statement_scope": payload.get('statement_scope') or 'capital_nav_fee_redemption',
        "status": payload.get('status') or 'consolidated',
        "notes": payload.get('notes') or 'capital statements consolidated for period close',
    }
    _append(store, 'statement_consolidations', event, int(policy.get('retain_cycles', 365)))
    _save(email, store)
    return {"ok": True, "event": event, "summary": _summary_for_email(email)}


@router.post('/certify-period-close')
def certify_period_close(payload: dict = Body(...), user=Depends(_require_user)):
    email = (user.get('email') or '').strip().lower()
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get('policy') or {})}
    roll = _rollforward().rollforward_summary()
    latest_period = roll.get('latest_period') or {}
    event = {
        "certification_id": payload.get('certification_id') or f"cert_{int(datetime.now(timezone.utc).timestamp())}",
        "captured_at": _now_iso(),
        "period_id": payload.get('period_id') or latest_period.get('period_id'),
        "period_name": payload.get('period_name') or latest_period.get('period_name') or 'Current Period Rollforward',
        "certifier": payload.get('certifier') or user.get('display_name') or 'Quantora Operator',
        "status": payload.get('status') or 'certified',
    }
    _append(store, 'period_close_certifications', event, int(policy.get('retain_cycles', 365)))
    _save(email, store)
    return {"ok": True, "event": event, "summary": _summary_for_email(email)}


@router.post('/lock-lp-book')
def lock_lp_book(payload: dict = Body(...), user=Depends(_require_user)):
    email = (user.get('email') or '').strip().lower()
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get('policy') or {})}
    event = {
        "lock_id": payload.get('lock_id') or f"lock_{int(datetime.now(timezone.utc).timestamp())}",
        "captured_at": _now_iso(),
        "book_scope": payload.get('book_scope') or 'lp_book_period_close',
        "approver": payload.get('approver') or user.get('display_name') or 'Quantora Operator',
        "status": payload.get('status') or 'locked',
        "notes": payload.get('notes') or 'lp book locked after close certification',
    }
    _append(store, 'lp_book_locks', event, int(policy.get('retain_cycles', 365)))
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

    _release_governance().bootstrap_demo(user)
    roll = _rollforward().rollforward_summary()
    latest_period = roll.get('latest_period') or {}
    if latest_period and latest_period.get('status') != 'locked':
        try:
            _rollforward().lock_period({'email': email, 'period_id': latest_period.get('period_id')})
        except Exception:
            pass

    record_statement_consolidation({'statement_scope': 'capital_nav_fee_redemption', 'status': 'consolidated'}, user)
    certify_period_close({'period_id': (latest_period or {}).get('period_id'), 'status': 'certified'}, user)
    lock_lp_book({'book_scope': 'lp_book_period_close', 'status': 'locked'}, user)

    run = _evaluate(email, {
        'statement_consolidation_readiness': 0.98,
        'period_close_certification_readiness': 0.98,
        'lp_book_lock_readiness': 0.98,
        'pending_statement_exceptions': 0,
        'open_close_breaks': 0,
    })
    return {"ok": True, "run": run, "summary": _summary_for_email(email)}
