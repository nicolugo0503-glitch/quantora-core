from fastapi import APIRouter, Body, Depends
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json

router = APIRouter(
    prefix="/api/auditor-pbc-package-assembly-valuation-support-binder-final-nav-evidence-delivery-layer",
    tags=["auditor-pbc-package-assembly-valuation-support-binder-final-nav-evidence-delivery-layer"],
)

PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
ENGINE_DIR = ARTIFACTS_DIR / "auditor_pbc_package_assembly_valuation_support_binder_final_nav_evidence_delivery_layer"
DEFAULT_POLICY = {
    "retain_cycles": 365,
    "minimum_score": 96.0,
    "minimum_pbc_package_readiness": 0.97,
    "minimum_valuation_support_binder_readiness": 0.97,
    "minimum_final_evidence_delivery_readiness": 0.96,
    "maximum_open_pbc_items": 0,
    "maximum_unmapped_evidence_requests": 0,
}


def _mu():
    from backend.app import qnt30557_multi_user_router as mu
    return mu


def _require_user():
    return _mu()._require_session()


def _final_nav_record():
    from backend.app import qnt40020_valuation_committee_minutes_challenge_resolution_evidence_final_nav_governance_record_layer_router as module
    return module


def _official_books():
    from backend.app import qnt40016_fund_administrator_nav_package_approval_controller_sign_off_official_books_release_layer_router as module
    return module


def _evidence_provenance():
    from backend.app import qnt30765_regulatory_data_lineage_evidence_provenance_attestation_fabric_router as module
    return module


def _records_retention():
    from backend.app import qnt30766_regulatory_records_retention_legal_hold_supervisory_retrieval_command_layer_router as module
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
            "auditor_pbc_packages": [],
            "valuation_support_binders": [],
            "final_nav_evidence_deliveries": [],
            "latest_run": None,
            "last_context": {},
        }
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return data
    return json.loads(path.read_text(encoding="utf-8"))


def _save(email: str, data: dict):
    _path(email).write_text(json.dumps(data, indent=2), encoding="utf-8")


def _context(email: str) -> dict:
    final_nav = _final_nav_record()._summary_for_email(email)
    books = _official_books()._summary_for_email(email)
    evidence = _evidence_provenance()._summary_for_email(email)
    records = _records_retention()._summary_for_email(email)
    latest_final_nav = final_nav.get("latest_run") or {}
    latest_books = books.get("latest_run") or {}
    latest_evidence = evidence.get("latest_run") or {}
    latest_records = records.get("latest_run") or {}
    return {
        "captured_at": _now_iso(),
        "final_nav_governance_summary": {
            "posture": ((final_nav.get("valuation_committee_minutes_challenge_resolution_evidence_final_nav_governance_record_layer_status") or {}).get("posture")),
            "score": latest_final_nav.get("score"),
            "final_record_count": len(final_nav.get("final_nav_governance_records") or []),
            "challenge_resolution_evidence_count": len(final_nav.get("challenge_resolution_evidence") or []),
        },
        "official_books_summary": {
            "posture": ((books.get("fund_administrator_nav_package_approval_controller_sign_off_official_books_release_layer_status") or {}).get("posture")),
            "score": latest_books.get("score"),
        },
        "evidence_provenance_summary": {
            "posture": ((evidence.get("regulatory_data_lineage_evidence_provenance_attestation_fabric_status") or {}).get("posture")),
            "score": latest_evidence.get("score"),
            "attestation_count": len(evidence.get("attestations") or []),
            "open_alerts": len(evidence.get("alerts") or []),
        },
        "records_retention_summary": {
            "posture": ((records.get("regulatory_records_retention_legal_hold_supervisory_retrieval_command_layer_status") or {}).get("posture")),
            "score": latest_records.get("score"),
            "legal_hold_count": len(records.get("legal_holds") or []),
            "retrieval_count": len(records.get("retrievals") or []),
        },
    }


def _summary_for_email(email: str) -> dict:
    s = _load(email)
    latest = s.get("latest_run") or {}
    return {
        "auditor_pbc_package_assembly_valuation_support_binder_final_nav_evidence_delivery_layer_status": {
            "posture": latest.get("posture", "UNINITIALIZED"),
            "latest_score": latest.get("score"),
            "band": latest.get("band", "UNSET"),
            "run_count": len(s.get("runs") or []),
            "alert_count": len(s.get("alerts") or []),
            "auditor_pbc_package_count": len(s.get("auditor_pbc_packages") or []),
            "valuation_support_binder_count": len(s.get("valuation_support_binders") or []),
            "final_nav_evidence_delivery_count": len(s.get("final_nav_evidence_deliveries") or []),
            "operator_review_required": bool(latest.get("operator_review_required", False)),
        },
        "latest_run": latest,
        "alerts": s.get("alerts") or [],
        "policy": s.get("policy") or dict(DEFAULT_POLICY),
        "last_context": s.get("last_context") or {},
        "auditor_pbc_packages": s.get("auditor_pbc_packages") or [],
        "valuation_support_binders": s.get("valuation_support_binders") or [],
        "final_nav_evidence_deliveries": s.get("final_nav_evidence_deliveries") or [],
    }


def _band(score: float) -> str:
    if score >= 98.0:
        return "AUDITOR_EVIDENCE_DELIVERY_STRONG"
    if score >= 96.0:
        return "AUDITOR_EVIDENCE_DELIVERY_CLEAR"
    if score >= 92.0:
        return "AUDITOR_EVIDENCE_DELIVERY_WATCH"
    return "AUDITOR_EVIDENCE_DELIVERY_REMEDIATION_REQUIRED"


def _evaluate(email: str, payload: dict) -> dict:
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get("policy") or {})}
    ctx = _context(email)

    pbc_package_readiness = float(payload.get("pbc_package_readiness", 0.0) or 0.0)
    valuation_support_binder_readiness = float(payload.get("valuation_support_binder_readiness", 0.0) or 0.0)
    final_evidence_delivery_readiness = float(payload.get("final_evidence_delivery_readiness", 0.0) or 0.0)
    open_pbc_items = int(payload.get("open_pbc_items", 0) or 0)
    unmapped_evidence_requests = int(payload.get("unmapped_evidence_requests", 0) or 0)

    score = 100.0
    reasons = []
    alerts = []

    def penalize(metric: float, minimum: float, weight: float, reason: str, code: str):
        nonlocal score
        if metric < minimum:
            score -= round((minimum - metric) * weight, 2)
            reasons.append(reason)
            alerts.append(code)

    penalize(pbc_package_readiness, float(policy.get("minimum_pbc_package_readiness", 0.97)), 120.0, "auditor pbc package readiness is below policy", "PBC_PACKAGE_READINESS_WEAK")
    penalize(valuation_support_binder_readiness, float(policy.get("minimum_valuation_support_binder_readiness", 0.97)), 120.0, "valuation support binder readiness is below policy", "VALUATION_BINDER_READINESS_WEAK")
    penalize(final_evidence_delivery_readiness, float(policy.get("minimum_final_evidence_delivery_readiness", 0.96)), 120.0, "final nav evidence delivery readiness is below policy", "FINAL_EVIDENCE_DELIVERY_READINESS_WEAK")

    max_open = int(policy.get("maximum_open_pbc_items", 0))
    if open_pbc_items > max_open:
        score -= 8.0 + (open_pbc_items - max_open) * 2.0
        reasons.append("open pbc items exceed policy")
        alerts.append("OPEN_PBC_ITEMS")

    max_unmapped = int(policy.get("maximum_unmapped_evidence_requests", 0))
    if unmapped_evidence_requests > max_unmapped:
        score -= 8.0 + (unmapped_evidence_requests - max_unmapped) * 2.0
        reasons.append("unmapped auditor evidence requests exceed policy")
        alerts.append("UNMAPPED_EVIDENCE_REQUESTS")

    final_nav = ctx.get("final_nav_governance_summary") or {}
    books = ctx.get("official_books_summary") or {}
    evidence = ctx.get("evidence_provenance_summary") or {}
    records = ctx.get("records_retention_summary") or {}

    if final_nav.get("posture") not in {"FINAL_NAV_GOVERNANCE_STRONG", "FINAL_NAV_GOVERNANCE_CLEAR", "FINAL_NAV_GOVERNANCE_WATCH"}:
        score -= 8.0
        reasons.append("final nav governance posture must be established before auditor evidence delivery")
        alerts.append("FINAL_NAV_GOVERNANCE_NOT_ESTABLISHED")
    if final_nav.get("final_record_count", 0) < 1:
        score -= 6.0
        reasons.append("final nav governance record evidence is required before auditor package delivery")
        alerts.append("FINAL_NAV_GOVERNANCE_RECORD_MISSING")
    if books.get("posture") not in {"OFFICIAL_BOOKS_RELEASE_READY", "OFFICIAL_BOOKS_CLEAR"}:
        score -= 7.0
        reasons.append("official books release posture must be clear before auditor evidence delivery")
        alerts.append("OFFICIAL_BOOKS_POSTURE_NOT_CLEAR")
    if evidence.get("posture") not in {"ATTESTATION_FABRIC_STRONG", "ATTESTATION_FABRIC_CLEAR", "ATTESTATION_FABRIC_WATCH"}:
        score -= 7.0
        reasons.append("evidence provenance posture must be established before auditor evidence delivery")
        alerts.append("EVIDENCE_PROVENANCE_NOT_ESTABLISHED")
    if evidence.get("attestation_count", 0) < 1:
        score -= 5.0
        reasons.append("attestation evidence is required before auditor pbc delivery")
        alerts.append("ATTESTATION_EVIDENCE_MISSING")
    if records.get("posture") not in {"RETRIEVAL_READY", "RETRIEVAL_DISCIPLINED", "RETRIEVAL_WATCH"}:
        score -= 6.0
        reasons.append("records retention and supervisory retrieval posture must be established before auditor delivery")
        alerts.append("RECORDS_RETRIEVAL_NOT_ESTABLISHED")
    if records.get("retrieval_count", 0) < 1:
        score -= 5.0
        reasons.append("retrieval evidence is required before final nav evidence delivery")
        alerts.append("RETRIEVAL_EVIDENCE_MISSING")

    score = round(max(score, 0.0), 2)
    posture = _band(score)
    operator_review_required = bool(score < float(policy.get("minimum_score", 96.0)) or len(alerts) > 0)
    run = {
        "run_id": f"qnt40021_{int(datetime.now(timezone.utc).timestamp())}",
        "captured_at": _now_iso(),
        "score": score,
        "band": posture,
        "posture": posture,
        "operator_review_required": operator_review_required,
        "reasons": reasons,
        "alerts": alerts,
        "pbc_package_readiness": pbc_package_readiness,
        "valuation_support_binder_readiness": valuation_support_binder_readiness,
        "final_evidence_delivery_readiness": final_evidence_delivery_readiness,
        "open_pbc_items": open_pbc_items,
        "unmapped_evidence_requests": unmapped_evidence_requests,
        "context": ctx,
    }
    _append(store, "runs", run, int(policy.get("retain_cycles", 365)))
    store["latest_run"] = run
    store["alerts"] = alerts
    store["last_context"] = ctx
    _save(email, store)
    return {"ok": True, **run}


@router.get('/summary')
def summary(user=Depends(_require_user)):
    return _summary_for_email(user["email"])


@router.post('/evaluate')
def evaluate(payload: dict = Body(...), user=Depends(_require_user)):
    return _evaluate(user["email"], payload or {})


@router.post('/assemble-auditor-pbc-package')
def assemble_auditor_pbc_package(payload: dict = Body(...), user=Depends(_require_user)):
    store = _load(user['email'])
    policy = {**dict(DEFAULT_POLICY), **(store.get('policy') or {})}
    event = {
        "recorded_at": _now_iso(),
        "package_id": payload.get('package_id', 'PBC-PACK-001'),
        "audit_period": payload.get('audit_period', _now_iso()[:7]),
        "prepared_by": payload.get('prepared_by', user.get('display_name') or user['email']),
        "request_count": payload.get('request_count', 12),
        "linked_final_nav_record": payload.get('linked_final_nav_record', 'FINAL-NAV-GOV-001'),
    }
    _append(store, 'auditor_pbc_packages', event, int(policy.get('retain_cycles', 365)))
    _save(user['email'], store)
    return {"ok": True, "event": event}


@router.post('/record-valuation-support-binder')
def record_valuation_support_binder(payload: dict = Body(...), user=Depends(_require_user)):
    store = _load(user['email'])
    policy = {**dict(DEFAULT_POLICY), **(store.get('policy') or {})}
    event = {
        "recorded_at": _now_iso(),
        "binder_id": payload.get('binder_id', 'VAL-BINDER-001'),
        "valuation_cycle_id": payload.get('valuation_cycle_id', 'NAV-CYCLE-001'),
        "document_count": payload.get('document_count', 24),
        "reviewed_by": payload.get('reviewed_by', user.get('display_name') or user['email']),
        "support_scope": payload.get('support_scope', ['independent-price-verification', 'shadow-nav', 'source-override']),
    }
    _append(store, 'valuation_support_binders', event, int(policy.get('retain_cycles', 365)))
    _save(user['email'], store)
    return {"ok": True, "event": event}


@router.post('/deliver-final-nav-evidence')
def deliver_final_nav_evidence(payload: dict = Body(...), user=Depends(_require_user)):
    store = _load(user['email'])
    policy = {**dict(DEFAULT_POLICY), **(store.get('policy') or {})}
    event = {
        "recorded_at": _now_iso(),
        "delivery_id": payload.get('delivery_id', 'AUDIT-DELIVERY-001'),
        "recipient": payload.get('recipient', 'external_auditor'),
        "delivery_channel": payload.get('delivery_channel', 'secure-data-room'),
        "package_id": payload.get('package_id', 'PBC-PACK-001'),
        "binder_id": payload.get('binder_id', 'VAL-BINDER-001'),
        "released_by": payload.get('released_by', user.get('display_name') or user['email']),
    }
    _append(store, 'final_nav_evidence_deliveries', event, int(policy.get('retain_cycles', 365)))
    _save(user['email'], store)
    return {"ok": True, "event": event}


@router.get('/policy')
def policy(user=Depends(_require_user)):
    store = _load(user['email'])
    return {"ok": True, "policy": {**dict(DEFAULT_POLICY), **(store.get('policy') or {})}}


@router.post('/bootstrap-demo')
def bootstrap_demo(user=Depends(_require_user)):
    email = user['email']
    assemble_auditor_pbc_package({
        'package_id': 'PBC-PACK-DEMO',
        'audit_period': _now_iso()[:7],
        'request_count': 18,
        'linked_final_nav_record': 'FINAL-NAV-GOV-DEMO',
    }, user)
    record_valuation_support_binder({
        'binder_id': 'VAL-BINDER-DEMO',
        'valuation_cycle_id': 'NAV-CYCLE-DEMO',
        'document_count': 31,
        'support_scope': ['price-verification', 'nav-break-review', 'source-hierarchy'],
    }, user)
    deliver_final_nav_evidence({
        'delivery_id': 'AUDIT-DELIVERY-DEMO',
        'recipient': 'external_auditor',
        'delivery_channel': 'secure-data-room',
        'package_id': 'PBC-PACK-DEMO',
        'binder_id': 'VAL-BINDER-DEMO',
    }, user)
    result = _evaluate(email, {
        'pbc_package_readiness': 0.99,
        'valuation_support_binder_readiness': 0.988,
        'final_evidence_delivery_readiness': 0.987,
        'open_pbc_items': 0,
        'unmapped_evidence_requests': 0,
    })
    return {"ok": True, "result": result, "summary": _summary_for_email(email)}
