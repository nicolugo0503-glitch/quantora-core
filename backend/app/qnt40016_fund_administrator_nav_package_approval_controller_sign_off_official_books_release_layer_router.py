from fastapi import APIRouter, Body, Depends
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json

router = APIRouter(
    prefix="/api/fund-administrator-nav-package-approval-controller-sign-off-official-books-release-layer",
    tags=["fund-administrator-nav-package-approval-controller-sign-off-official-books-release-layer"],
)

PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
ENGINE_DIR = ARTIFACTS_DIR / "fund_administrator_nav_package_approval_controller_sign_off_official_books_release_layer"
DEFAULT_POLICY = {
    "retain_cycles": 365,
    "minimum_score": 96.0,
    "minimum_nav_package_approval_readiness": 0.96,
    "minimum_controller_sign_off_readiness": 0.97,
    "minimum_official_books_release_readiness": 0.97,
    "maximum_open_nav_package_exceptions": 0,
    "maximum_open_release_breaks": 0,
}


def _mu():
    from backend.app import qnt30557_multi_user_router as mu
    return mu


def _require_user():
    return _mu()._require_session()


def _period_close():
    from backend.app import qnt40015_investor_capital_statement_consolidation_period_close_certification_lp_book_final_lock_layer_router as module
    return module


def _statement_packs():
    from backend.app import qnt30588_statement_pack_router as module
    return module


def _delivery_log():
    from backend.app import qnt30589_report_delivery_log_router as module
    return module


def _capital():
    from backend.app import qnt30624_capital_ledger_router as module
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
            "nav_package_approvals": [],
            "controller_sign_offs": [],
            "official_books_releases": [],
            "latest_run": None,
            "last_context": {},
        }
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return data
    return json.loads(path.read_text(encoding="utf-8"))


def _save(email: str, data: dict):
    _path(email).write_text(json.dumps(data, indent=2), encoding="utf-8")


def _context(email: str) -> dict:
    close = _period_close()._summary_for_email(email)
    packs = _statement_packs().statement_packs_summary()
    delivery = _delivery_log().report_delivery_log_summary()
    capital = _capital().capital_ledger_summary()
    latest_pack = packs.get("latest_pack") or {}
    latest_delivery = delivery.get("latest_event") or {}
    latest_close = close.get("latest_run") or {}
    return {
        "captured_at": _now_iso(),
        "period_close_summary": {
            "posture": ((close.get("investor_capital_statement_consolidation_period_close_certification_lp_book_final_lock_layer_status") or {}).get("posture")),
            "score": latest_close.get("score"),
            "lp_book_lock_count": len(close.get("lp_book_locks") or []),
            "period_close_certification_count": len(close.get("period_close_certifications") or []),
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
        "capital_ledger_summary": {
            "account_count": capital.get("account_count", 0),
            "entry_count": capital.get("entry_count", 0),
            "total_nav": capital.get("total_nav", 0.0),
            "total_funded_capital": capital.get("total_funded_capital", 0.0),
        },
    }


def _summary_for_email(email: str) -> dict:
    s = _load(email)
    latest = s.get("latest_run") or {}
    return {
        "fund_administrator_nav_package_approval_controller_sign_off_official_books_release_layer_status": {
            "posture": latest.get("posture", "UNINITIALIZED"),
            "latest_score": latest.get("score"),
            "band": latest.get("band", "UNSET"),
            "run_count": len(s.get("runs") or []),
            "alert_count": len(s.get("alerts") or []),
            "nav_package_approval_count": len(s.get("nav_package_approvals") or []),
            "controller_sign_off_count": len(s.get("controller_sign_offs") or []),
            "official_books_release_count": len(s.get("official_books_releases") or []),
            "operator_review_required": bool(latest.get("operator_review_required", False)),
        },
        "latest_run": latest,
        "alerts": s.get("alerts") or [],
        "policy": s.get("policy") or dict(DEFAULT_POLICY),
        "last_context": s.get("last_context") or {},
        "nav_package_approvals": s.get("nav_package_approvals") or [],
        "controller_sign_offs": s.get("controller_sign_offs") or [],
        "official_books_releases": s.get("official_books_releases") or [],
    }


def _band(score: float) -> str:
    if score >= 98.0:
        return "OFFICIAL_BOOKS_RELEASED"
    if score >= 96.0:
        return "OFFICIAL_RELEASE_CLEAR"
    if score >= 92.0:
        return "OFFICIAL_RELEASE_WATCH"
    return "OFFICIAL_RELEASE_REMEDIATION_REQUIRED"


def _evaluate(email: str, payload: dict) -> dict:
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get("policy") or {})}
    ctx = _context(email)

    nav_package_approval_readiness = float(payload.get("nav_package_approval_readiness", 0.0) or 0.0)
    controller_sign_off_readiness = float(payload.get("controller_sign_off_readiness", 0.0) or 0.0)
    official_books_release_readiness = float(payload.get("official_books_release_readiness", 0.0) or 0.0)
    open_nav_package_exceptions = int(payload.get("open_nav_package_exceptions", 0) or 0)
    open_release_breaks = int(payload.get("open_release_breaks", 0) or 0)

    score = 100.0
    reasons = []
    alerts = []

    def penalize(metric: float, minimum: float, weight: float, reason: str, code: str):
        nonlocal score
        if metric < minimum:
            score -= round((minimum - metric) * weight, 2)
            reasons.append(reason)
            alerts.append(code)

    penalize(nav_package_approval_readiness, float(policy.get("minimum_nav_package_approval_readiness", 0.96)), 120.0, "fund administrator nav package approval readiness is below policy", "NAV_PACKAGE_APPROVAL_READINESS_WEAK")
    penalize(controller_sign_off_readiness, float(policy.get("minimum_controller_sign_off_readiness", 0.97)), 120.0, "controller sign-off readiness is below policy", "CONTROLLER_SIGN_OFF_READINESS_WEAK")
    penalize(official_books_release_readiness, float(policy.get("minimum_official_books_release_readiness", 0.97)), 120.0, "official books release readiness is below policy", "OFFICIAL_BOOKS_RELEASE_READINESS_WEAK")

    max_nav_ex = int(policy.get("maximum_open_nav_package_exceptions", 0))
    if open_nav_package_exceptions > max_nav_ex:
        score -= 7.0 + (open_nav_package_exceptions - max_nav_ex) * 2.0
        reasons.append("open nav package exceptions exceed policy")
        alerts.append("OPEN_NAV_PACKAGE_EXCEPTIONS")
    max_release_breaks = int(policy.get("maximum_open_release_breaks", 0))
    if open_release_breaks > max_release_breaks:
        score -= 7.0 + (open_release_breaks - max_release_breaks) * 2.0
        reasons.append("open official release breaks exceed policy")
        alerts.append("OPEN_RELEASE_BREAKS")

    close_summary = ctx.get("period_close_summary") or {}
    pack_summary = ctx.get("statement_pack_summary") or {}
    delivery_summary = ctx.get("delivery_log_summary") or {}
    capital_summary = ctx.get("capital_ledger_summary") or {}

    if close_summary.get("posture") not in {"PERIOD_CLOSE_CLEAR", "LP_BOOK_FINAL_LOCKED"}:
        score -= 8.0
        reasons.append("period close posture must be clear before official books release")
        alerts.append("PERIOD_CLOSE_NOT_CLEAR")
    if close_summary.get("lp_book_lock_count", 0) < 1:
        score -= 6.0
        reasons.append("lp book final lock evidence is required before official books release")
        alerts.append("LP_BOOK_LOCK_EVIDENCE_MISSING")
    if pack_summary.get("pack_count", 0) < 1:
        score -= 5.0
        reasons.append("statement pack evidence is required for fund administrator nav package review")
        alerts.append("STATEMENT_PACK_MISSING")
    if delivery_summary.get("delivery_count", 0) < 1:
        score -= 4.0
        reasons.append("delivery log evidence is missing for official books release")
        alerts.append("DELIVERY_LOG_MISSING")
    if capital_summary.get("account_count", 0) < 1:
        score -= 4.0
        reasons.append("capital ledger has no investor accounts for official books release")
        alerts.append("CAPITAL_LEDGER_EMPTY")

    score = round(max(score, 0.0), 2)
    posture = _band(score)
    operator_review_required = bool(score < float(policy.get("minimum_score", 96.0)) or len(alerts) > 0)
    run = {
        "run_id": f"qnt40016_{int(datetime.now(timezone.utc).timestamp())}",
        "captured_at": _now_iso(),
        "score": score,
        "band": _band(score),
        "posture": posture,
        "operator_review_required": operator_review_required,
        "reasons": reasons,
        "alerts": alerts,
        "nav_package_approval_readiness": nav_package_approval_readiness,
        "controller_sign_off_readiness": controller_sign_off_readiness,
        "official_books_release_readiness": official_books_release_readiness,
        "open_nav_package_exceptions": open_nav_package_exceptions,
        "open_release_breaks": open_release_breaks,
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


@router.post('/approve-nav-package')
def approve_nav_package(payload: dict = Body(...), user=Depends(_require_user)):
    email = (user.get('email') or '').strip().lower()
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get('policy') or {})}
    packs = _statement_packs().statement_packs_summary()
    latest_pack = packs.get('latest_pack') or {}
    event = {
        "approval_id": payload.get('approval_id') or f"navpkg_{int(datetime.now(timezone.utc).timestamp())}",
        "captured_at": _now_iso(),
        "pack_id": payload.get('pack_id') or latest_pack.get('pack_id'),
        "administrator": payload.get('administrator') or 'Quantora Fund Administration',
        "status": payload.get('status') or 'approved',
        "notes": payload.get('notes') or 'fund administrator nav package reviewed and approved',
    }
    _append(store, 'nav_package_approvals', event, int(policy.get('retain_cycles', 365)))
    _save(email, store)
    return {"ok": True, "event": event, "summary": _summary_for_email(email)}


@router.post('/controller-sign-off')
def controller_sign_off(payload: dict = Body(...), user=Depends(_require_user)):
    email = (user.get('email') or '').strip().lower()
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get('policy') or {})}
    event = {
        "signoff_id": payload.get('signoff_id') or f"ctrl_{int(datetime.now(timezone.utc).timestamp())}",
        "captured_at": _now_iso(),
        "controller": payload.get('controller') or user.get('display_name') or 'Quantora Controller',
        "scope": payload.get('scope') or 'nav_package_and_official_books',
        "status": payload.get('status') or 'signed_off',
    }
    _append(store, 'controller_sign_offs', event, int(policy.get('retain_cycles', 365)))
    _save(email, store)
    return {"ok": True, "event": event, "summary": _summary_for_email(email)}


@router.post('/release-official-books')
def release_official_books(payload: dict = Body(...), user=Depends(_require_user)):
    email = (user.get('email') or '').strip().lower()
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get('policy') or {})}
    event = {
        "release_id": payload.get('release_id') or f"books_{int(datetime.now(timezone.utc).timestamp())}",
        "captured_at": _now_iso(),
        "book_scope": payload.get('book_scope') or 'official_fund_books_period_close',
        "approver": payload.get('approver') or user.get('display_name') or 'Quantora Controller',
        "status": payload.get('status') or 'released',
        "notes": payload.get('notes') or 'official books released after nav package approval and controller sign-off',
    }
    _append(store, 'official_books_releases', event, int(policy.get('retain_cycles', 365)))
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
    session.setdefault('display_name', 'Quantora Controller')
    from backend.app import main as app_main
    app_main.save_session(session)

    _period_close().bootstrap_demo(user)
    approve_nav_package({'status': 'approved'}, user)
    controller_sign_off({'status': 'signed_off'}, user)
    release_official_books({'status': 'released'}, user)

    run = _evaluate(email, {
        'nav_package_approval_readiness': 0.98,
        'controller_sign_off_readiness': 0.99,
        'official_books_release_readiness': 0.99,
        'open_nav_package_exceptions': 0,
        'open_release_breaks': 0,
    })
    return {"ok": True, "run": run, "summary": _summary_for_email(email)}
