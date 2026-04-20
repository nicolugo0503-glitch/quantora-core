from fastapi import APIRouter, Body, Depends
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json

router = APIRouter(prefix="/api/institutional-external-auditor-interface-layer", tags=["institutional-external-auditor-interface-layer"])
PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
ENGINE_DIR = ARTIFACTS_DIR / "institutional_external_auditor_interface_layer"
DEFAULT_POLICY = {
    "retain_cycles": 180,
    "minimum_score": 96.0,
    "require_audit_ready": True,
    "require_treasury_confirmed": True,
    "require_investor_confirmed": True,
    "minimum_auditor_package_score": 0.985,
    "minimum_access_control_score": 0.98,
    "minimum_traceability_score": 0.98,
    "max_open_requests": 3,
    "max_critical_gaps": 0,
}

def _mu():
    from backend.app import qnt30557_multi_user_router as mu
    return mu

def _audit_ready():
    from backend.app import qnt30747_institutional_audit_readiness_certification_layer_router as audit_ready
    return audit_ready

def _treasury():
    from backend.app import qnt30745_institutional_treasury_confirmation_layer_router as treasury
    return treasury

def _investor():
    from backend.app import qnt30746_institutional_investor_capital_confirmation_layer_router as investor
    return investor

def _forensic():
    from backend.app import qnt30706_forensic_audit_system_router as forensic
    return forensic

def _reporting():
    from backend.app import qnt30715_reporting_disclosure_automation_layer_router as reporting
    return reporting

def _safe(v: str) -> str:
    return hashlib.sha256((v or "").strip().lower().encode("utf-8")).hexdigest()[:24]

def _path(email: str) -> Path:
    ENGINE_DIR.mkdir(parents=True, exist_ok=True)
    return ENGINE_DIR / f"{_safe(email)}.json"

def _require_user():
    return _mu()._require_session()

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
            "auditor_requests": [],
            "access_logs": [],
            "latest_run": None,
            "last_context": {},
        }
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return data
    return json.loads(path.read_text(encoding="utf-8"))

def _save(email: str, data: dict):
    _path(email).write_text(json.dumps(data, indent=2), encoding="utf-8")

def _summary_for_email(email: str) -> dict:
    s = _load(email)
    latest = s.get("latest_run") or {}
    return {
        "institutional_external_auditor_interface_layer_status": {
            "posture": latest.get("posture", "UNINITIALIZED"),
            "latest_score": latest.get("score"),
            "band": latest.get("band", "UNSET"),
            "run_count": len(s.get("runs") or []),
            "alert_count": len(s.get("alerts") or []),
            "auditor_request_count": len(s.get("auditor_requests") or []),
            "operator_review_required": bool(latest.get("operator_review_required", False)),
        },
        "latest_run": latest,
        "alerts": s.get("alerts") or [],
        "policy": s.get("policy") or dict(DEFAULT_POLICY),
        "last_context": s.get("last_context") or {},
        "auditor_requests": s.get("auditor_requests") or [],
        "access_logs": s.get("access_logs") or [],
    }

def _cross_system_context(email: str) -> dict:
    return {
        "captured_at": _now_iso(),
        "audit_readiness": (_audit_ready()._summary_for_email(email).get("institutional_audit_readiness_certification_layer_status") or {}),
        "treasury": (_treasury()._summary_for_email(email).get("institutional_treasury_confirmation_layer_status") or {}),
        "investor": (_investor()._summary_for_email(email).get("institutional_investor_capital_confirmation_layer_status") or {}),
        "forensic": (_forensic()._summary_for_email(email).get("forensic_status") or {}),
        "reporting": (_reporting()._summary_for_email(email).get("reporting_disclosure_automation_layer_status") or {}),
    }

def _band(score: float) -> str:
    if score >= 98.0:
        return "EXTERNAL_AUDITOR_READY"
    if score >= 96.0:
        return "CONTROLLED_ACCESS"
    if score >= 92.0:
        return "LIMITED_ACCESS"
    return "BLOCKED"

def _evaluate(email: str, payload: dict) -> dict:
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get("policy") or {})}
    ctx = _cross_system_context(email)
    auditor_package_score = float(payload.get("auditor_package_score", 0.0) or 0.0)
    access_control_score = float(payload.get("access_control_score", 0.0) or 0.0)
    traceability_score = float(payload.get("traceability_score", 0.0) or 0.0)
    open_requests = int(payload.get("open_requests", 0) or 0)
    critical_gaps = int(payload.get("critical_gaps", 0) or 0)
    signed_nda = bool(payload.get("signed_nda", False))
    evidence_room_ready = bool(payload.get("evidence_room_ready", False))

    score = 100.0
    reasons = []
    alerts = []
    checks = [
        (auditor_package_score, float(policy.get("minimum_auditor_package_score", 0.985)), 130.0, "auditor package quality is below policy", "AUDITOR_PACKAGE_WEAK"),
        (access_control_score, float(policy.get("minimum_access_control_score", 0.98)), 120.0, "access control quality is below policy", "ACCESS_CONTROL_WEAK"),
        (traceability_score, float(policy.get("minimum_traceability_score", 0.98)), 110.0, "traceability is below policy", "TRACEABILITY_WEAK"),
    ]
    for val, threshold, mult, reason, code in checks:
        if val < threshold:
            score -= round((threshold - val) * mult, 2)
            reasons.append(reason)
            alerts.append(code)
    if open_requests > int(policy.get("max_open_requests", 3)):
        score -= min((open_requests - int(policy.get("max_open_requests", 3))) * 4.0, 16.0)
        reasons.append("open auditor requests exceed policy")
        alerts.append("OPEN_REQUESTS_HIGH")
    if critical_gaps > int(policy.get("max_critical_gaps", 0)):
        score -= min(critical_gaps * 15.0, 35.0)
        reasons.append("critical external audit gaps remain open")
        alerts.append("CRITICAL_GAPS_OPEN")
    if not signed_nda:
        score -= 6.0
        reasons.append("auditor NDA is not signed")
        alerts.append("NDA_NOT_SIGNED")
    if not evidence_room_ready:
        score -= 6.0
        reasons.append("evidence room is not ready")
        alerts.append("EVIDENCE_ROOM_NOT_READY")

    audit_posture = str(ctx.get("audit_readiness", {}).get("posture", "UNINITIALIZED"))
    treasury_posture = str(ctx.get("treasury", {}).get("posture", "UNINITIALIZED"))
    investor_posture = str(ctx.get("investor", {}).get("posture", "UNINITIALIZED"))
    forensic_posture = str(ctx.get("forensic", {}).get("posture", "UNINITIALIZED"))
    reporting_posture = str(ctx.get("reporting", {}).get("posture", "UNINITIALIZED"))

    if policy.get("require_audit_ready", True) and audit_posture not in {"AUDIT_READY", "UNINITIALIZED"}:
        score -= 12.0; reasons.append("audit readiness posture is not clear"); alerts.append("AUDIT_READINESS_NOT_CLEAR")
    if policy.get("require_treasury_confirmed", True) and treasury_posture not in {"CONFIRMED", "TREASURY_CONFIRMED", "TREASURY_CONTROLLED", "UNINITIALIZED"}:
        score -= 10.0; reasons.append("treasury posture is not external-audit clear"); alerts.append("TREASURY_NOT_CLEAR")
    if policy.get("require_investor_confirmed", True) and investor_posture not in {"CONFIRMED", "FULLY_CONFIRMED", "UNINITIALIZED"}:
        score -= 10.0; reasons.append("investor confirmation posture is not external-audit clear"); alerts.append("INVESTOR_NOT_CLEAR")
    if forensic_posture not in {"ready", "attention", "UNINITIALIZED"}:
        score -= 8.0; reasons.append("forensic posture is not external-audit clear"); alerts.append("FORENSIC_NOT_CLEAR")
    if reporting_posture not in {"AUTOMATED_CLEAR", "CONTROLLED", "UNINITIALIZED", "APPROVED"}:
        score -= 6.0; reasons.append("reporting posture is not external-audit clear"); alerts.append("REPORTING_NOT_CLEAR")

    score = max(round(score, 2), 0.0)
    band = _band(score)
    posture = "EXTERNAL_AUDITOR_READY" if score >= float(policy.get("minimum_score", 96.0)) else ("WATCH" if score >= 92.0 else "BLOCKED")
    operator_review_required = posture != "EXTERNAL_AUDITOR_READY" or critical_gaps > 0 or open_requests > int(policy.get("max_open_requests", 3))
    row = {
        "mission": "QNT30748",
        "evaluated_at": _now_iso(),
        "score": score,
        "band": band,
        "posture": posture,
        "operator_review_required": operator_review_required,
        "auditor_package_score": auditor_package_score,
        "access_control_score": access_control_score,
        "traceability_score": traceability_score,
        "open_requests": open_requests,
        "critical_gaps": critical_gaps,
        "signed_nda": signed_nda,
        "evidence_room_ready": evidence_room_ready,
        "reasons": reasons,
        "alerts": alerts,
        "context": ctx,
    }
    _append(store, "runs", row, policy.get("retain_cycles", 180))
    for a in alerts:
        _append(store, "alerts", {"at": _now_iso(), "code": a, "score": score}, policy.get("retain_cycles", 180))
    store["latest_run"] = row
    store["last_context"] = ctx
    _save(email, store)
    return row

@router.get("/summary")
def summary(user=Depends(_require_user)):
    return _summary_for_email(user["email"])

@router.post("/evaluate")
def evaluate(payload: dict = Body(...), user=Depends(_require_user)):
    email = user["email"]
    run = _evaluate(email, payload)
    return {"ok": True, "run": run, "summary": _summary_for_email(email)}

@router.post("/request-access")
def request_access(payload: dict = Body(default={}), user=Depends(_require_user)):
    email = user["email"]
    store = _load(email)
    row = {
        "at": _now_iso(),
        "auditor_name": str(payload.get("auditor_name") or "external-auditor"),
        "scope": str(payload.get("scope") or "full-audit-room"),
        "status": str(payload.get("status") or "requested"),
    }
    _append(store, "auditor_requests", row, (store.get("policy") or {}).get("retain_cycles", 180))
    _append(store, "access_logs", {"at": _now_iso(), "event": "request_access", "scope": row["scope"]}, (store.get("policy") or {}).get("retain_cycles", 180))
    _save(email, store)
    return {"ok": True, "auditor_request": row, "summary": _summary_for_email(email)}

@router.post("/grant-interface")
def grant_interface(payload: dict = Body(default={}), user=Depends(_require_user)):
    email = user["email"]
    store = _load(email)
    row = {
        "at": _now_iso(),
        "auditor_name": str(payload.get("auditor_name") or "external-auditor"),
        "interface_mode": str(payload.get("interface_mode") or "read-only"),
        "status": str(payload.get("status") or "granted"),
    }
    _append(store, "access_logs", {"at": _now_iso(), "event": "grant_interface", **row}, (store.get("policy") or {}).get("retain_cycles", 180))
    _save(email, store)
    return {"ok": True, "granted": row, "summary": _summary_for_email(email)}

@router.post("/policy")
def policy(payload: dict = Body(...), user=Depends(_require_user)):
    email = user["email"]
    store = _load(email)
    store["policy"] = {**dict(DEFAULT_POLICY), **(store.get("policy") or {}), **payload}
    _save(email, store)
    return {"ok": True, "policy": store["policy"], "summary": _summary_for_email(email)}

@router.post("/bootstrap-demo")
def bootstrap_demo(user=Depends(_require_user)):
    email = user["email"]
    _load(email)
    _ = _evaluate(email, {
        "auditor_package_score": 0.992,
        "access_control_score": 0.989,
        "traceability_score": 0.989,
        "open_requests": 1,
        "critical_gaps": 0,
        "signed_nda": True,
        "evidence_room_ready": True,
    })
    request_access({"auditor_name": "Big Four Sample", "scope": "full-audit-room", "status": "requested"}, {"email": email})
    grant_interface({"auditor_name": "Big Four Sample", "interface_mode": "read-only", "status": "granted"}, {"email": email})
    return {"ok": True, "summary": _summary_for_email(email)}
