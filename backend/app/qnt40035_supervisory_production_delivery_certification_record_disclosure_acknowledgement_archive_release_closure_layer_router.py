from fastapi import APIRouter, Body, Depends
from pathlib import Path
from datetime import datetime, timezone
import hashlib, json

router = APIRouter(
    prefix="/api/supervisory-production-delivery-certification-record-disclosure-acknowledgement-archive-release-closure-layer",
    tags=["supervisory-production-delivery-certification-record-disclosure-acknowledgement-archive-release-closure-layer"],
)
PROJECT_DIR = Path(__file__).resolve().parents[2]
ENGINE_DIR = PROJECT_DIR / "backend" / "artifacts" / "supervisory_production_delivery_certification_record_disclosure_acknowledgement_archive_release_closure_layer"
DEFAULT_POLICY = {
    "retain_cycles": 365,
    "minimum_score": 96.0,
    "minimum_delivery_certification_readiness": 0.97,
    "minimum_disclosure_acknowledgement_readiness": 0.97,
    "minimum_archive_release_closure_readiness": 0.97,
    "maximum_open_closure_issues": 0,
}


def _mu():
    from backend.app import qnt30557_multi_user_router as mu
    return mu


def _require_user():
    return _mu()._require_session()


def _dep_a():
    from backend.app import qnt40034_supervisory_production_packet_assembly_governance_archive_release_approval_official_record_disclosure_ledger_layer_router as module
    return module


def _safe(v: str) -> str:
    return hashlib.sha256((v or "").strip().lower().encode()).hexdigest()[:24]


def _path(email: str) -> Path:
    ENGINE_DIR.mkdir(parents=True, exist_ok=True)
    return ENGINE_DIR / f"{_safe(email)}.json"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _append(store, key, row, retain):
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
            "delivery_certifications": [],
            "disclosure_acknowledgements": [],
            "archive_release_closures": [],
            "latest_run": None,
            "last_context": {},
        }
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return data
    return json.loads(path.read_text(encoding="utf-8"))


def _save(email: str, data: dict):
    _path(email).write_text(json.dumps(data, indent=2), encoding="utf-8")


def _context(email: str) -> dict:
    a = _dep_a()._summary_for_email(email)
    la = a.get("latest_run") or {}
    return {
        "captured_at": _now_iso(),
        "dep_a_summary": {
            "posture": ((a.get("supervisory_production_packet_assembly_governance_archive_release_approval_official_record_disclosure_ledger_layer_status") or {}).get("posture")),
            "score": la.get("score"),
        },
    }


def _summary_for_email(email: str) -> dict:
    s = _load(email)
    latest = s.get("latest_run") or {}
    return {
        "supervisory_production_delivery_certification_record_disclosure_acknowledgement_archive_release_closure_layer_status": {
            "posture": latest.get("posture", "UNINITIALIZED"),
            "latest_score": latest.get("score"),
            "band": latest.get("band", "UNSET"),
            "run_count": len(s.get("runs") or []),
            "alert_count": len(s.get("alerts") or []),
            "delivery_certification_count": len(s.get("delivery_certifications") or []),
            "disclosure_acknowledgement_count": len(s.get("disclosure_acknowledgements") or []),
            "archive_release_closure_count": len(s.get("archive_release_closures") or []),
            "operator_review_required": bool(latest.get("operator_review_required", False)),
        },
        "latest_run": latest,
        "alerts": s.get("alerts") or [],
        "policy": s.get("policy") or dict(DEFAULT_POLICY),
        "last_context": s.get("last_context") or {},
        "delivery_certifications": s.get("delivery_certifications") or [],
        "disclosure_acknowledgements": s.get("disclosure_acknowledgements") or [],
        "archive_release_closures": s.get("archive_release_closures") or [],
    }


def _band(score: float) -> str:
    if score >= 98.0:
        return "ARCHIVE_RELEASE_CLOSURE_STRONG"
    if score >= 96.0:
        return "ARCHIVE_RELEASE_CLOSURE_CLEAR"
    if score >= 92.0:
        return "ARCHIVE_RELEASE_CLOSURE_WATCH"
    return "ARCHIVE_RELEASE_CLOSURE_REMEDIATION_REQUIRED"


def _evaluate(email: str, payload: dict) -> dict:
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get("policy") or {})}
    ctx = _context(email)
    delivery_certification_readiness = float(payload.get("delivery_certification_readiness", 0.0) or 0.0)
    disclosure_acknowledgement_readiness = float(payload.get("disclosure_acknowledgement_readiness", 0.0) or 0.0)
    archive_release_closure_readiness = float(payload.get("archive_release_closure_readiness", 0.0) or 0.0)
    open_closure_issues = int(payload.get("open_closure_issues", 0) or 0)
    score = 100.0
    reasons = []
    alerts = []

    def penalize(metric, minimum, weight, reason, code):
        nonlocal score
        if metric < minimum:
            score -= round((minimum - metric) * weight, 2)
            reasons.append(reason)
            alerts.append(code)

    penalize(delivery_certification_readiness, float(policy.get("minimum_delivery_certification_readiness", 0.97)), 120.0, "supervisory production delivery certification readiness is below policy", "DELIVERY_CERTIFICATION_READINESS_WEAK")
    penalize(disclosure_acknowledgement_readiness, float(policy.get("minimum_disclosure_acknowledgement_readiness", 0.97)), 120.0, "record disclosure acknowledgement readiness is below policy", "DISCLOSURE_ACKNOWLEDGEMENT_READINESS_WEAK")
    penalize(archive_release_closure_readiness, float(policy.get("minimum_archive_release_closure_readiness", 0.97)), 120.0, "archive release closure readiness is below policy", "ARCHIVE_RELEASE_CLOSURE_READINESS_WEAK")
    if open_closure_issues > int(policy.get("maximum_open_closure_issues", 0)):
        score -= 8.0 + (open_closure_issues - int(policy.get("maximum_open_closure_issues", 0))) * 2.0
        reasons.append("open archive release closure issues exceed policy")
        alerts.append("OPEN_ARCHIVE_RELEASE_CLOSURE_ISSUES_EXCEED_POLICY")
    if ctx.get("dep_a_summary", {}).get("posture") not in {
        "OFFICIAL_RECORD_DISCLOSURE_LEDGER_STRONG",
        "OFFICIAL_RECORD_DISCLOSURE_LEDGER_CLEAR",
        "OFFICIAL_RECORD_DISCLOSURE_LEDGER_WATCH",
    }:
        score -= 8.0
        reasons.append("official record disclosure ledger posture must be established before supervisory production delivery closure")
        alerts.append("OFFICIAL_RECORD_DISCLOSURE_LEDGER_POSTURE_NOT_ESTABLISHED")
    score = max(0.0, round(score, 2))
    posture = _band(score)
    operator_review_required = bool(score < float(policy.get("minimum_score", 96.0)) or open_closure_issues > 0)
    run = {
        "run_id": f"qnt40035_{int(datetime.now(timezone.utc).timestamp())}",
        "captured_at": _now_iso(),
        "delivery_certification_readiness": delivery_certification_readiness,
        "disclosure_acknowledgement_readiness": disclosure_acknowledgement_readiness,
        "archive_release_closure_readiness": archive_release_closure_readiness,
        "open_closure_issues": open_closure_issues,
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


def _create_row(kind: str, payload: dict) -> dict:
    return {"id": f"{kind}_{int(datetime.now(timezone.utc).timestamp())}", "captured_at": _now_iso(), **payload}


@router.get("/summary")
def summary(user=Depends(_require_user)):
    return _summary_for_email(user["email"])


@router.post("/evaluate")
def evaluate(payload: dict = Body(...), user=Depends(_require_user)):
    return {"ok": True, "run": _evaluate(user["email"], payload), "summary": _summary_for_email(user["email"])}


@router.post("/record-delivery-certification")
def record_delivery_certification(payload: dict = Body(...), user=Depends(_require_user)):
    email = user["email"]
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get("policy") or {})}
    row = _create_row("delivery_certification", payload)
    _append(store, "delivery_certifications", row, int(policy.get("retain_cycles", 365)))
    _save(email, store)
    return {"ok": True, "delivery_certification": row, "summary": _summary_for_email(email)}


@router.post("/record-disclosure-acknowledgement")
def record_disclosure_acknowledgement(payload: dict = Body(...), user=Depends(_require_user)):
    email = user["email"]
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get("policy") or {})}
    row = _create_row("disclosure_acknowledgement", payload)
    _append(store, "disclosure_acknowledgements", row, int(policy.get("retain_cycles", 365)))
    _save(email, store)
    return {"ok": True, "disclosure_acknowledgement": row, "summary": _summary_for_email(email)}


@router.post("/record-archive-release-closure")
def record_archive_release_closure(payload: dict = Body(...), user=Depends(_require_user)):
    email = user["email"]
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get("policy") or {})}
    row = _create_row("archive_release_closure", payload)
    _append(store, "archive_release_closures", row, int(policy.get("retain_cycles", 365)))
    _save(email, store)
    return {"ok": True, "archive_release_closure": row, "summary": _summary_for_email(email)}


@router.get("/policy")
def policy(user=Depends(_require_user)):
    return {"ok": True, "policy": _load(user["email"]).get("policy") or dict(DEFAULT_POLICY)}


@router.post("/policy")
def set_policy(payload: dict = Body(...), user=Depends(_require_user)):
    email = user["email"]
    store = _load(email)
    store["policy"] = {**dict(DEFAULT_POLICY), **(store.get("policy") or {}), **payload}
    _save(email, store)
    return {"ok": True, "policy": store["policy"]}


@router.post("/bootstrap-demo")
def bootstrap_demo(user=Depends(_require_user)):
    email = user["email"]
    _dep_a().bootstrap_demo(user)
    record_delivery_certification({"certification_name": "supervisory production delivery certification FY2025", "delivery_certification_readiness": 0.99}, user)
    record_disclosure_acknowledgement({"acknowledgement_name": "official record disclosure acknowledgement FY2025", "disclosure_acknowledgement_readiness": 0.99}, user)
    record_archive_release_closure({"closure_name": "archive release closure FY2025", "archive_release_closure_readiness": 0.99}, user)
    run = _evaluate(email, {
        "delivery_certification_readiness": 0.99,
        "disclosure_acknowledgement_readiness": 0.99,
        "archive_release_closure_readiness": 0.99,
        "open_closure_issues": 0,
    })
    return {"ok": True, "run": run, "summary": _summary_for_email(email)}
