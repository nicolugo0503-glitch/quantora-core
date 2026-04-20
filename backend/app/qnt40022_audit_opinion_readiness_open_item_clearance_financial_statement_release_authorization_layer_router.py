from fastapi import APIRouter, Body, Depends
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json

router = APIRouter(
    prefix="/api/audit-opinion-readiness-open-item-clearance-financial-statement-release-authorization-layer",
    tags=["audit-opinion-readiness-open-item-clearance-financial-statement-release-authorization-layer"],
)

PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
ENGINE_DIR = ARTIFACTS_DIR / "audit_opinion_readiness_open_item_clearance_financial_statement_release_authorization_layer"
DEFAULT_POLICY = {
    "retain_cycles": 365,
    "minimum_score": 96.0,
    "minimum_audit_opinion_readiness": 0.97,
    "minimum_release_authorization_readiness": 0.97,
    "maximum_open_items": 0,
    "maximum_critical_open_items": 0,
}


def _mu():
    from backend.app import qnt30557_multi_user_router as mu
    return mu


def _require_user():
    return _mu()._require_session()


def _auditor_delivery():
    from backend.app import qnt40021_auditor_pbc_package_assembly_valuation_support_binder_final_nav_evidence_delivery_layer_router as module
    return module


def _official_books():
    from backend.app import qnt40016_fund_administrator_nav_package_approval_controller_sign_off_official_books_release_layer_router as module
    return module


def _auditor_interface():
    from backend.app import qnt30748_institutional_external_auditor_interface_layer_router as module
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
            "audit_opinion_readiness_reviews": [],
            "open_item_clearances": [],
            "financial_statement_release_authorizations": [],
            "latest_run": None,
            "last_context": {},
        }
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return data
    return json.loads(path.read_text(encoding="utf-8"))


def _save(email: str, data: dict):
    _path(email).write_text(json.dumps(data, indent=2), encoding="utf-8")


def _context(email: str) -> dict:
    auditor_delivery = _auditor_delivery()._summary_for_email(email)
    books = _official_books()._summary_for_email(email)
    auditor_interface = _auditor_interface()._summary_for_email(email)
    latest_delivery = auditor_delivery.get("latest_run") or {}
    latest_books = books.get("latest_run") or {}
    latest_interface = auditor_interface.get("latest_run") or {}
    return {
        "captured_at": _now_iso(),
        "auditor_evidence_delivery_summary": {
            "posture": ((auditor_delivery.get("auditor_pbc_package_assembly_valuation_support_binder_final_nav_evidence_delivery_layer_status") or {}).get("posture")),
            "score": latest_delivery.get("score"),
            "auditor_pbc_package_count": len(auditor_delivery.get("auditor_pbc_packages") or []),
            "final_evidence_delivery_count": len(auditor_delivery.get("final_nav_evidence_deliveries") or []),
            "alert_count": len(auditor_delivery.get("alerts") or []),
        },
        "official_books_summary": {
            "posture": ((books.get("fund_administrator_nav_package_approval_controller_sign_off_official_books_release_layer_status") or {}).get("posture")),
            "score": latest_books.get("score"),
        },
        "external_auditor_interface_summary": {
            "posture": ((auditor_interface.get("institutional_external_auditor_interface_layer_status") or {}).get("posture")),
            "score": latest_interface.get("score"),
            "auditor_request_count": len(auditor_interface.get("auditor_requests") or []),
        },
    }


def _summary_for_email(email: str) -> dict:
    s = _load(email)
    latest = s.get("latest_run") or {}
    return {
        "audit_opinion_readiness_open_item_clearance_financial_statement_release_authorization_layer_status": {
            "posture": latest.get("posture", "UNINITIALIZED"),
            "latest_score": latest.get("score"),
            "band": latest.get("band", "UNSET"),
            "run_count": len(s.get("runs") or []),
            "alert_count": len(s.get("alerts") or []),
            "audit_opinion_readiness_review_count": len(s.get("audit_opinion_readiness_reviews") or []),
            "open_item_clearance_count": len(s.get("open_item_clearances") or []),
            "financial_statement_release_authorization_count": len(s.get("financial_statement_release_authorizations") or []),
            "operator_review_required": bool(latest.get("operator_review_required", False)),
        },
        "latest_run": latest,
        "alerts": s.get("alerts") or [],
        "policy": s.get("policy") or dict(DEFAULT_POLICY),
        "last_context": s.get("last_context") or {},
        "audit_opinion_readiness_reviews": s.get("audit_opinion_readiness_reviews") or [],
        "open_item_clearances": s.get("open_item_clearances") or [],
        "financial_statement_release_authorizations": s.get("financial_statement_release_authorizations") or [],
    }


def _band(score: float) -> str:
    if score >= 98.0:
        return "AUDIT_RELEASE_GOVERNANCE_STRONG"
    if score >= 96.0:
        return "AUDIT_RELEASE_GOVERNANCE_CLEAR"
    if score >= 92.0:
        return "AUDIT_RELEASE_GOVERNANCE_WATCH"
    return "AUDIT_RELEASE_GOVERNANCE_REMEDIATION_REQUIRED"


def _evaluate(email: str, payload: dict) -> dict:
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get("policy") or {})}
    ctx = _context(email)

    audit_opinion_readiness = float(payload.get("audit_opinion_readiness", 0.0) or 0.0)
    release_authorization_readiness = float(payload.get("release_authorization_readiness", 0.0) or 0.0)
    open_items = int(payload.get("open_items", 0) or 0)
    critical_open_items = int(payload.get("critical_open_items", 0) or 0)

    score = 100.0
    reasons = []
    alerts = []

    def penalize(metric: float, minimum: float, weight: float, reason: str, code: str):
        nonlocal score
        if metric < minimum:
            score -= round((minimum - metric) * weight, 2)
            reasons.append(reason)
            alerts.append(code)

    penalize(audit_opinion_readiness, float(policy.get("minimum_audit_opinion_readiness", 0.97)), 120.0, "audit opinion readiness is below policy", "AUDIT_OPINION_READINESS_WEAK")
    penalize(release_authorization_readiness, float(policy.get("minimum_release_authorization_readiness", 0.97)), 120.0, "financial statement release authorization readiness is below policy", "RELEASE_AUTHORIZATION_READINESS_WEAK")

    max_open = int(policy.get("maximum_open_items", 0))
    if open_items > max_open:
        score -= 8.0 + (open_items - max_open) * 2.0
        reasons.append("open audit items exceed policy")
        alerts.append("OPEN_ITEMS_EXCEED_POLICY")

    max_critical = int(policy.get("maximum_critical_open_items", 0))
    if critical_open_items > max_critical:
        score -= 12.0 + (critical_open_items - max_critical) * 4.0
        reasons.append("critical open audit items exceed policy")
        alerts.append("CRITICAL_OPEN_ITEMS_EXCEED_POLICY")

    delivery = ctx.get("auditor_evidence_delivery_summary") or {}
    books = ctx.get("official_books_summary") or {}
    interface = ctx.get("external_auditor_interface_summary") or {}

    if delivery.get("posture") not in {"AUDITOR_EVIDENCE_DELIVERY_STRONG", "AUDITOR_EVIDENCE_DELIVERY_CLEAR", "AUDITOR_EVIDENCE_DELIVERY_WATCH"}:
        score -= 8.0
        reasons.append("auditor evidence delivery posture must be established before audit opinion readiness signoff")
        alerts.append("AUDITOR_EVIDENCE_DELIVERY_NOT_ESTABLISHED")
    if delivery.get("final_evidence_delivery_count", 0) < 1:
        score -= 6.0
        reasons.append("final nav evidence delivery record is required before financial statement release authorization")
        alerts.append("FINAL_NAV_EVIDENCE_DELIVERY_MISSING")
    if books.get("posture") not in {"OFFICIAL_BOOKS_RELEASE_READY", "OFFICIAL_BOOKS_CLEAR"}:
        score -= 7.0
        reasons.append("official books release posture must be clear before financial statement release authorization")
        alerts.append("OFFICIAL_BOOKS_NOT_READY")
    if interface.get("auditor_request_count", 0) < 1:
        score -= 4.0
        reasons.append("external auditor interface evidence should exist before opinion readiness is asserted")
        alerts.append("AUDITOR_INTERFACE_EVIDENCE_THIN")

    score = max(0.0, round(score, 2))
    posture = _band(score)
    operator_review_required = bool(score < float(policy.get("minimum_score", 96.0)) or critical_open_items > 0)
    run = {
        "run_id": f"qnt40022_{int(datetime.now(timezone.utc).timestamp())}",
        "captured_at": _now_iso(),
        "audit_opinion_readiness": audit_opinion_readiness,
        "release_authorization_readiness": release_authorization_readiness,
        "open_items": open_items,
        "critical_open_items": critical_open_items,
        "score": score,
        "band": posture,
        "posture": posture,
        "reasons": reasons,
        "alerts": alerts,
        "operator_review_required": operator_review_required,
    }
    _append(store, "runs", run, int(policy.get("retain_cycles", 365)))
    store["latest_run"] = run
    store["alerts"] = [{"captured_at": _now_iso(), "code": code} for code in alerts]
    store["last_context"] = ctx
    _save(email, store)
    return run


@router.get('/summary')
def summary(user=Depends(_require_user)):
    return _summary_for_email(user["email"])


@router.post('/evaluate')
def evaluate(payload: dict = Body(...), user=Depends(_require_user)):
    return {"ok": True, "run": _evaluate(user["email"], payload), "summary": _summary_for_email(user["email"])}


@router.post('/record-audit-opinion-readiness')
def record_audit_opinion_readiness(payload: dict = Body(...), user=Depends(_require_user)):
    email = user["email"]
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get("policy") or {})}
    row = {
        "captured_at": _now_iso(),
        "audit_cycle": payload.get("audit_cycle", "FY-END"),
        "opinion_target": payload.get("opinion_target", "unqualified"),
        "audit_opinion_readiness": float(payload.get("audit_opinion_readiness", 0.98) or 0.98),
        "open_items": int(payload.get("open_items", 0) or 0),
        "critical_open_items": int(payload.get("critical_open_items", 0) or 0),
        "operator": user.get("display_name") or email,
    }
    _append(store, "audit_opinion_readiness_reviews", row, int(policy.get("retain_cycles", 365)))
    _save(email, store)
    return {"ok": True, "audit_opinion_readiness_review": row, "summary": _summary_for_email(email)}


@router.post('/clear-open-item')
def clear_open_item(payload: dict = Body(...), user=Depends(_require_user)):
    email = user["email"]
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get("policy") or {})}
    row = {
        "captured_at": _now_iso(),
        "item_id": payload.get("item_id", f"audit-item-{int(datetime.now(timezone.utc).timestamp())}"),
        "severity": payload.get("severity", "standard"),
        "resolution_status": payload.get("resolution_status", "cleared"),
        "evidence_linked": bool(payload.get("evidence_linked", True)),
        "operator": user.get("display_name") or email,
    }
    _append(store, "open_item_clearances", row, int(policy.get("retain_cycles", 365)))
    _save(email, store)
    return {"ok": True, "open_item_clearance": row, "summary": _summary_for_email(email)}


@router.post('/authorize-financial-statement-release')
def authorize_financial_statement_release(payload: dict = Body(...), user=Depends(_require_user)):
    email = user["email"]
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get("policy") or {})}
    row = {
        "captured_at": _now_iso(),
        "release_scope": payload.get("release_scope", "annual_financial_statements"),
        "release_channel": payload.get("release_channel", "lp_portal_and_auditor_distribution"),
        "release_authorization_readiness": float(payload.get("release_authorization_readiness", 0.98) or 0.98),
        "authorized": bool(payload.get("authorized", True)),
        "operator": user.get("display_name") or email,
    }
    _append(store, "financial_statement_release_authorizations", row, int(policy.get("retain_cycles", 365)))
    _save(email, store)
    return {"ok": True, "financial_statement_release_authorization": row, "summary": _summary_for_email(email)}


@router.get('/policy')
def policy(user=Depends(_require_user)):
    return {"ok": True, "policy": _load(user["email"]).get("policy") or dict(DEFAULT_POLICY)}


@router.post('/bootstrap-demo')
def bootstrap_demo(user=Depends(_require_user)):
    _auditor_interface().bootstrap_demo(user)
    _official_books().bootstrap_demo(user)
    _auditor_delivery().bootstrap_demo(user)
    record_audit_opinion_readiness({
        "audit_cycle": "FY-END",
        "opinion_target": "unqualified",
        "audit_opinion_readiness": 0.99,
        "open_items": 0,
        "critical_open_items": 0,
    }, user)
    clear_open_item({
        "item_id": "audit-item-final-nav-1",
        "severity": "standard",
        "resolution_status": "cleared",
        "evidence_linked": True,
    }, user)
    authorize_financial_statement_release({
        "release_scope": "annual_financial_statements",
        "release_channel": "lp_portal_and_auditor_distribution",
        "release_authorization_readiness": 0.99,
        "authorized": True,
    }, user)
    run = _evaluate(user["email"], {
        "audit_opinion_readiness": 0.99,
        "release_authorization_readiness": 0.99,
        "open_items": 0,
        "critical_open_items": 0,
    })
    return {"ok": True, "run": run, "summary": _summary_for_email(user["email"])}
