from fastapi import APIRouter, Body, Depends
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json

router = APIRouter(prefix="/api/institutional-audit-readiness-certification-layer", tags=["institutional-audit-readiness-certification-layer"])
PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
ENGINE_DIR = ARTIFACTS_DIR / "institutional_audit_readiness_certification_layer"
DEFAULT_POLICY = {
    "retain_cycles": 180,
    "minimum_score": 96.0,
    "require_treasury_confirmed": True,
    "require_investor_confirmed": True,
    "require_forensic_clear": True,
    "require_fund_admin_ready": True,
    "minimum_audit_coverage_score": 0.985,
    "minimum_evidence_completeness_score": 0.985,
    "minimum_traceability_score": 0.98,
    "max_critical_gaps": 0,
    "max_material_gaps": 1,
}

def _mu():
    from backend.app import qnt30557_multi_user_router as mu
    return mu

def _treasury():
    from backend.app import qnt30745_institutional_treasury_confirmation_layer_router as treasury
    return treasury

def _investor():
    from backend.app import qnt30746_institutional_investor_capital_confirmation_layer_router as investor
    return investor

def _forensic():
    from backend.app import qnt30706_forensic_audit_system_router as forensic
    return forensic

def _fund_admin():
    from backend.app import qnt30705_fund_admin_control_center_router as fund_admin
    return fund_admin

def _cash_closure():
    from backend.app import qnt30744_institutional_cash_reconciliation_closure_layer_router as cash_closure
    return cash_closure

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
            "evidence_snapshots": [],
            "certifications": [],
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
        "institutional_audit_readiness_certification_layer_status": {
            "posture": latest.get("posture", "UNINITIALIZED"),
            "latest_score": latest.get("score"),
            "band": latest.get("band", "UNSET"),
            "run_count": len(s.get("runs") or []),
            "alert_count": len(s.get("alerts") or []),
            "certification_count": len(s.get("certifications") or []),
            "operator_review_required": bool(latest.get("operator_review_required", False)),
        },
        "latest_run": latest,
        "alerts": s.get("alerts") or [],
        "policy": s.get("policy") or dict(DEFAULT_POLICY),
        "last_context": s.get("last_context") or {},
        "evidence_snapshots": s.get("evidence_snapshots") or [],
        "certifications": s.get("certifications") or [],
    }

def _cross_system_context(email: str) -> dict:
    return {
        "captured_at": _now_iso(),
        "treasury": (_treasury()._summary_for_email(email).get("institutional_treasury_confirmation_layer_status") or {}),
        "investor": (_investor()._summary_for_email(email).get("institutional_investor_capital_confirmation_layer_status") or {}),
        "forensic": (_forensic()._summary_for_email(email).get("forensic_status") or {}),
        "fund_admin": (_fund_admin()._summary_for_email(email).get("fund_admin_status") or {}),
        "cash_closure": (_cash_closure()._summary_for_email(email).get("institutional_cash_reconciliation_closure_layer_status") or {}),
    }

def _band(score: float) -> str:
    if score >= 98.0:
        return "AUDIT_READY"
    if score >= 96.0:
        return "MINOR_GAPS"
    if score >= 92.0:
        return "MATERIAL_GAPS"
    return "BLOCKED"

def _evaluate(email: str, payload: dict) -> dict:
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get("policy") or {})}
    ctx = _cross_system_context(email)
    audit_coverage_score = float(payload.get("audit_coverage_score", 0.0) or 0.0)
    evidence_completeness_score = float(payload.get("evidence_completeness_score", 0.0) or 0.0)
    traceability_score = float(payload.get("traceability_score", 0.0) or 0.0)
    material_gaps = int(payload.get("material_gaps", 0) or 0)
    critical_gaps = int(payload.get("critical_gaps", 0) or 0)
    external_audit_pack_complete = bool(payload.get("external_audit_pack_complete", False))

    score = 100.0
    reasons = []
    alerts = []
    for val, threshold, mult, reason, code in [
        (audit_coverage_score, float(policy.get("minimum_audit_coverage_score", 0.985)), 130.0, "audit coverage is below policy", "AUDIT_COVERAGE_WEAK"),
        (evidence_completeness_score, float(policy.get("minimum_evidence_completeness_score", 0.985)), 120.0, "evidence completeness is below policy", "EVIDENCE_COMPLETENESS_WEAK"),
        (traceability_score, float(policy.get("minimum_traceability_score", 0.98)), 110.0, "traceability is below policy", "TRACEABILITY_WEAK"),
    ]:
        if val < threshold:
            score -= round((threshold - val) * mult, 2)
            reasons.append(reason)
            alerts.append(code)
    if material_gaps > int(policy.get("max_material_gaps", 1)):
        score -= min((material_gaps - int(policy.get("max_material_gaps", 1))) * 5.0, 20.0)
        reasons.append("material audit gaps exceed policy")
        alerts.append("MATERIAL_GAPS_HIGH")
    if critical_gaps > int(policy.get("max_critical_gaps", 0)):
        score -= min(critical_gaps * 15.0, 35.0)
        reasons.append("critical audit gaps remain open")
        alerts.append("CRITICAL_GAPS_OPEN")
    if not external_audit_pack_complete:
        score -= 6.0
        reasons.append("external audit package is incomplete")
        alerts.append("EXTERNAL_AUDIT_PACK_INCOMPLETE")

    treasury_posture = str(ctx.get("treasury", {}).get("posture", "UNINITIALIZED"))
    investor_posture = str(ctx.get("investor", {}).get("posture", "UNINITIALIZED"))
    forensic_posture = str(ctx.get("forensic", {}).get("posture", "UNINITIALIZED"))
    fund_admin_posture = str(ctx.get("fund_admin", {}).get("readiness", "UNINITIALIZED"))
    cash_closure_posture = str(ctx.get("cash_closure", {}).get("posture", "UNINITIALIZED"))
    if policy.get("require_treasury_confirmed", True) and treasury_posture not in {"CONFIRMED", "TREASURY_CONFIRMED", "TREASURY_CONTROLLED", "UNINITIALIZED"}:
        score -= 10.0; reasons.append("treasury posture is not audit clear"); alerts.append("TREASURY_NOT_CLEAR")
    if policy.get("require_investor_confirmed", True) and investor_posture not in {"CONFIRMED", "UNINITIALIZED"}:
        score -= 10.0; reasons.append("investor confirmation posture is not audit clear"); alerts.append("INVESTOR_NOT_CLEAR")
    if policy.get("require_forensic_clear", True) and forensic_posture not in {"ready", "attention", "UNINITIALIZED"}:
        score -= 12.0; reasons.append("forensic posture is not audit clear"); alerts.append("FORENSIC_NOT_CLEAR")
    if policy.get("require_fund_admin_ready", True) and fund_admin_posture not in {"ready", "READY", "UNINITIALIZED"}:
        score -= 8.0; reasons.append("fund admin readiness is not clear"); alerts.append("FUND_ADMIN_NOT_READY")
    if cash_closure_posture not in {"CASH_CLOSED", "CASH_CONTROLLED", "UNINITIALIZED"}:
        score -= 8.0; reasons.append("cash closure posture is not clear"); alerts.append("CASH_CLOSURE_NOT_CLEAR")

    score = max(round(score, 2), 0.0)
    band = _band(score)
    posture = "AUDIT_READY" if score >= float(policy.get("minimum_score", 96.0)) else ("WATCH" if score >= 92.0 else "BLOCKED")
    operator_review_required = posture != "AUDIT_READY" or critical_gaps > 0
    row = {
        "mission": "QNT30747",
        "evaluated_at": _now_iso(),
        "score": score,
        "band": band,
        "posture": posture,
        "operator_review_required": operator_review_required,
        "audit_coverage_score": audit_coverage_score,
        "evidence_completeness_score": evidence_completeness_score,
        "traceability_score": traceability_score,
        "material_gaps": material_gaps,
        "critical_gaps": critical_gaps,
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

@router.post("/collect-evidence")
def collect_evidence(payload: dict = Body(default={}), user=Depends(_require_user)):
    email = user["email"]
    store = _load(email)
    row = {
        "at": _now_iso(),
        "scope": str(payload.get("scope") or "full-audit-pack"),
        "evidence_items": int(payload.get("evidence_items", 12) or 0),
        "status": "collected",
    }
    _append(store, "evidence_snapshots", row, (store.get("policy") or {}).get("retain_cycles", 180))
    _save(email, store)
    return {"ok": True, "evidence_snapshot": row, "summary": _summary_for_email(email)}

@router.post("/certify")
def certify(payload: dict = Body(default={}), user=Depends(_require_user)):
    email = user["email"]
    store = _load(email)
    row = {
        "at": _now_iso(),
        "status": str(payload.get("status") or "AUDIT_READY"),
        "signed_by": str(payload.get("signed_by") or user.get("email") or email),
        "note": str(payload.get("note") or "audit readiness certified"),
    }
    _append(store, "certifications", row, (store.get("policy") or {}).get("retain_cycles", 180))
    _save(email, store)
    return {"ok": True, "certification": row, "summary": _summary_for_email(email)}

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
    run = _evaluate(email, {
        "audit_coverage_score": 0.993,
        "evidence_completeness_score": 0.992,
        "traceability_score": 0.989,
        "material_gaps": 1,
        "critical_gaps": 0,
        "external_audit_pack_complete": True,
    })
    return {"ok": True, "run": run, "summary": _summary_for_email(email)}
