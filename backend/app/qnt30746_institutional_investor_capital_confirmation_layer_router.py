from fastapi import APIRouter, Body, Depends
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json

router = APIRouter(prefix="/api/institutional-investor-capital-confirmation-layer", tags=["institutional-investor-capital-confirmation-layer"])
PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
ENGINE_DIR = ARTIFACTS_DIR / "institutional_investor_capital_confirmation_layer"
DEFAULT_POLICY = {
    "retain_cycles": 180,
    "minimum_score": 95.0,
    "require_treasury_confirmed": True,
    "require_fund_admin_ready": True,
    "require_transparency_clear": True,
    "require_reporting_clear": True,
    "minimum_confirmation_coverage": 0.9,
    "max_investor_discrepancies": 2,
    "max_critical_investor_discrepancies": 0,
    "minimum_statement_alignment_score": 0.98,
    "minimum_delivery_ack_score": 0.95,
    "minimum_dispute_resolution_score": 0.95,
}

def _mu():
    from backend.app import qnt30557_multi_user_router as mu
    return mu

def _treasury():
    from backend.app import qnt30745_institutional_treasury_confirmation_layer_router as treasury
    return treasury

def _fund_admin():
    from backend.app import qnt30705_fund_admin_control_center_router as fund_admin
    return fund_admin

def _transparency():
    from backend.app import qnt30714_investor_transparency_engine_router as transparency
    return transparency

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
            "investor_book": [],
            "confirmation_requests": [],
            "attestations": [],
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
        "institutional_investor_capital_confirmation_layer_status": {
            "posture": latest.get("posture", "UNINITIALIZED"),
            "latest_score": latest.get("score"),
            "band": latest.get("band", "UNSET"),
            "run_count": len(s.get("runs") or []),
            "alert_count": len(s.get("alerts") or []),
            "confirmation_request_count": len(s.get("confirmation_requests") or []),
            "operator_review_required": bool(latest.get("operator_review_required", False)),
        },
        "latest_run": latest,
        "alerts": s.get("alerts") or [],
        "policy": s.get("policy") or dict(DEFAULT_POLICY),
        "last_context": s.get("last_context") or {},
        "confirmation_requests": s.get("confirmation_requests") or [],
        "attestations": s.get("attestations") or [],
    }

def _cross_system_context(email: str) -> dict:
    return {
        "captured_at": _now_iso(),
        "treasury": (_treasury()._summary_for_email(email).get("institutional_treasury_confirmation_layer_status") or {}),
        "fund_admin": (_fund_admin()._summary_for_email(email).get("fund_admin_status") or {}),
        "transparency": (_transparency()._summary_for_email(email).get("investor_transparency_status") or {}),
        "reporting": (_reporting()._summary_for_email(email).get("reporting_disclosure_automation_status") or {}),
    }

def _band(score: float) -> str:
    if score >= 97.0:
        return "FULLY_CONFIRMED"
    if score >= 95.0:
        return "PARTIALLY_CONFIRMED"
    if score >= 92.0:
        return "DISCREPANCY_DETECTED"
    return "BLOCKED"

def _evaluate(email: str, payload: dict) -> dict:
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get("policy") or {})}
    ctx = _cross_system_context(email)
    confirmation_coverage = float(payload.get("confirmation_coverage", 0.0) or 0.0)
    statement_alignment_score = float(payload.get("statement_alignment_score", 0.0) or 0.0)
    delivery_ack_score = float(payload.get("delivery_ack_score", 0.0) or 0.0)
    dispute_resolution_score = float(payload.get("dispute_resolution_score", 0.0) or 0.0)
    investor_discrepancies = int(payload.get("investor_discrepancies", 0) or 0)
    critical_investor_discrepancies = int(payload.get("critical_investor_discrepancies", 0) or 0)
    investor_statement_cycle_complete = bool(payload.get("investor_statement_cycle_complete", False))

    score = 100.0
    reasons = []
    alerts = []
    if confirmation_coverage < float(policy.get("minimum_confirmation_coverage", 0.9)):
        score -= round((float(policy.get("minimum_confirmation_coverage", 0.9)) - confirmation_coverage) * 60.0, 2)
        reasons.append("investor confirmation coverage is below policy")
        alerts.append("CONFIRMATION_COVERAGE_WEAK")
    if statement_alignment_score < float(policy.get("minimum_statement_alignment_score", 0.98)):
        score -= round((float(policy.get("minimum_statement_alignment_score", 0.98)) - statement_alignment_score) * 120.0, 2)
        reasons.append("statement alignment is below policy")
        alerts.append("STATEMENT_ALIGNMENT_WEAK")
    if delivery_ack_score < float(policy.get("minimum_delivery_ack_score", 0.95)):
        score -= round((float(policy.get("minimum_delivery_ack_score", 0.95)) - delivery_ack_score) * 90.0, 2)
        reasons.append("investor acknowledgement coverage is below policy")
        alerts.append("DELIVERY_ACK_WEAK")
    if dispute_resolution_score < float(policy.get("minimum_dispute_resolution_score", 0.95)):
        score -= round((float(policy.get("minimum_dispute_resolution_score", 0.95)) - dispute_resolution_score) * 80.0, 2)
        reasons.append("investor dispute resolution quality is below policy")
        alerts.append("DISPUTE_RESOLUTION_WEAK")
    if investor_discrepancies > int(policy.get("max_investor_discrepancies", 2)):
        score -= min((investor_discrepancies - int(policy.get("max_investor_discrepancies", 2))) * 4.0, 16.0)
        reasons.append("investor discrepancies exceed policy")
        alerts.append("INVESTOR_DISCREPANCIES_HIGH")
    if critical_investor_discrepancies > int(policy.get("max_critical_investor_discrepancies", 0)):
        score -= min(critical_investor_discrepancies * 12.0, 30.0)
        reasons.append("critical investor discrepancies remain unresolved")
        alerts.append("CRITICAL_INVESTOR_DISCREPANCIES")
    if not investor_statement_cycle_complete:
        score -= 6.0
        reasons.append("investor statement cycle is incomplete")
        alerts.append("STATEMENT_CYCLE_INCOMPLETE")

    treasury_posture = str(ctx.get("treasury", {}).get("posture", "UNINITIALIZED"))
    fund_admin_posture = str(ctx.get("fund_admin", {}).get("readiness", "UNINITIALIZED"))
    transparency_posture = str(ctx.get("transparency", {}).get("posture", "UNINITIALIZED"))
    reporting_posture = str(ctx.get("reporting", {}).get("posture", "UNINITIALIZED"))
    if policy.get("require_treasury_confirmed", True) and treasury_posture not in {"CONFIRMED", "TREASURY_CONFIRMED", "TREASURY_CONTROLLED", "UNINITIALIZED"}:
        score -= 12.0; reasons.append("treasury confirmation posture is not clear"); alerts.append("TREASURY_NOT_CONFIRMED")
    if policy.get("require_fund_admin_ready", True) and fund_admin_posture not in {"ready", "READY", "UNINITIALIZED"}:
        score -= 8.0; reasons.append("fund admin readiness is not clear"); alerts.append("FUND_ADMIN_NOT_READY")
    if policy.get("require_transparency_clear", True) and transparency_posture not in {"APPROVED", "WATCH", "UNINITIALIZED"}:
        score -= 8.0; reasons.append("transparency posture is not clear"); alerts.append("TRANSPARENCY_NOT_CLEAR")
    if policy.get("require_reporting_clear", True) and reporting_posture not in {"APPROVED", "UNCONFIGURED", "UNINITIALIZED"}:
        score -= 8.0; reasons.append("reporting posture is not clear"); alerts.append("REPORTING_NOT_CLEAR")

    score = max(round(score, 2), 0.0)
    band = _band(score)
    posture = "CONFIRMED" if score >= float(policy.get("minimum_score", 95.0)) else ("WATCH" if score >= 92.0 else "BLOCKED")
    operator_review_required = posture != "CONFIRMED" or critical_investor_discrepancies > 0
    row = {
        "mission": "QNT30746",
        "evaluated_at": _now_iso(),
        "score": score,
        "band": band,
        "posture": posture,
        "operator_review_required": operator_review_required,
        "confirmation_coverage": confirmation_coverage,
        "statement_alignment_score": statement_alignment_score,
        "delivery_ack_score": delivery_ack_score,
        "dispute_resolution_score": dispute_resolution_score,
        "investor_discrepancies": investor_discrepancies,
        "critical_investor_discrepancies": critical_investor_discrepancies,
        "reasons": reasons,
        "alerts": alerts,
        "context": ctx,
    }
    _append(store, "runs", row, policy.get("retain_cycles", 180))
    _append(store, "investor_book", {"at": _now_iso(), "score": score, "band": band, "posture": posture}, policy.get("retain_cycles", 180))
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

@router.post("/request-confirmation")
def request_confirmation(payload: dict = Body(default={}), user=Depends(_require_user)):
    email = user["email"]
    store = _load(email)
    row = {
        "at": _now_iso(),
        "cycle": str(payload.get("cycle") or "current"),
        "recipient_count": int(payload.get("recipient_count", 1) or 1),
        "mode": str(payload.get("mode") or "statement-ack"),
        "status": "requested",
    }
    _append(store, "confirmation_requests", row, (store.get("policy") or {}).get("retain_cycles", 180))
    _save(email, store)
    return {"ok": True, "request": row, "summary": _summary_for_email(email)}

@router.post("/attest")
def attest(payload: dict = Body(default={}), user=Depends(_require_user)):
    email = user["email"]
    store = _load(email)
    row = {
        "at": _now_iso(),
        "status": str(payload.get("status") or "FULLY_CONFIRMED"),
        "coverage": float(payload.get("coverage", 1.0) or 0.0),
        "note": str(payload.get("note") or "investor confirmations logged"),
    }
    _append(store, "attestations", row, (store.get("policy") or {}).get("retain_cycles", 180))
    _save(email, store)
    return {"ok": True, "attestation": row, "summary": _summary_for_email(email)}

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
        "confirmation_coverage": 0.96,
        "statement_alignment_score": 0.992,
        "delivery_ack_score": 0.978,
        "dispute_resolution_score": 0.985,
        "investor_discrepancies": 1,
        "critical_investor_discrepancies": 0,
        "investor_statement_cycle_complete": True,
    })
    return {"ok": True, "run": run, "summary": _summary_for_email(email)}
