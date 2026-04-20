from fastapi import APIRouter, Body, Depends
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json

router = APIRouter(
    prefix="/api/regulatory-client-money-protection-reserve-formula-daily-safeguarding-control-layer",
    tags=["regulatory-client-money-protection-reserve-formula-daily-safeguarding-control-layer"],
)
PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
ENGINE_DIR = ARTIFACTS_DIR / "regulatory_client_money_protection_reserve_formula_daily_safeguarding_control_layer"
DEFAULT_POLICY = {
    "retain_cycles": 180,
    "minimum_score": 96.0,
    "require_client_asset_safeguarding_clear": True,
    "require_filing_clear": True,
    "require_records_retrievable": True,
    "require_breach_clear": True,
    "minimum_reserve_formula_coverage": 0.99,
    "minimum_daily_segregation_accuracy": 0.99,
    "minimum_bank_acknowledgement_quality": 0.98,
    "minimum_client_money_reconciliation_quality": 0.98,
}


def _mu():
    from backend.app import qnt30557_multi_user_router as mu
    return mu


def _custody():
    from backend.app import qnt30770_regulatory_client_asset_safeguarding_segregation_custody_assurance_layer_router as module
    return module


def _filing():
    from backend.app import qnt30755_regulatory_filing_submission_orchestration_layer_router as module
    return module


def _records():
    from backend.app import qnt30766_regulatory_records_retention_legal_hold_supervisory_retrieval_command_layer_router as module
    return module


def _breach():
    from backend.app import qnt30757_regulatory_breach_escalation_remediation_command_layer_router as module
    return module


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
            "reserve_formula_snapshots": [],
            "protected_bank_accounts": [],
            "daily_segregation_checks": [],
            "client_money_attestations": [],
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
        "regulatory_client_money_protection_reserve_formula_daily_safeguarding_control_layer_status": {
            "posture": latest.get("posture", "UNINITIALIZED"),
            "latest_score": latest.get("score"),
            "band": latest.get("band", "UNSET"),
            "run_count": len(s.get("runs") or []),
            "alert_count": len(s.get("alerts") or []),
            "reserve_formula_snapshot_count": len(s.get("reserve_formula_snapshots") or []),
            "protected_bank_account_count": len(s.get("protected_bank_accounts") or []),
            "daily_segregation_check_count": len(s.get("daily_segregation_checks") or []),
            "client_money_attestation_count": len(s.get("client_money_attestations") or []),
            "operator_review_required": bool(latest.get("operator_review_required", False)),
        },
        "latest_run": latest,
        "alerts": s.get("alerts") or [],
        "policy": s.get("policy") or dict(DEFAULT_POLICY),
        "last_context": s.get("last_context") or {},
        "reserve_formula_snapshots": s.get("reserve_formula_snapshots") or [],
        "protected_bank_accounts": s.get("protected_bank_accounts") or [],
        "daily_segregation_checks": s.get("daily_segregation_checks") or [],
        "client_money_attestations": s.get("client_money_attestations") or [],
    }


def _cross_system_context(email: str) -> dict:
    return {
        "captured_at": _now_iso(),
        "custody": (_custody()._summary_for_email(email).get("regulatory_client_asset_safeguarding_segregation_custody_assurance_layer_status") or {}),
        "filing": (_filing()._summary_for_email(email).get("regulatory_filing_submission_orchestration_layer_status") or {}),
        "records": (_records()._summary_for_email(email).get("regulatory_records_retention_legal_hold_supervisory_retrieval_command_layer_status") or {}),
        "breach": (_breach()._summary_for_email(email).get("regulatory_breach_escalation_remediation_command_layer_status") or {}),
    }


def _band(score: float) -> str:
    if score >= 98.0:
        return "CLIENT_MONEY_PROTECTION_READY"
    if score >= 96.0:
        return "DAILY_SAFEKEEPING_CLEAR"
    if score >= 92.0:
        return "SAFEGUARDING_WATCH"
    return "CLIENT_MONEY_REMEDIATION_REQUIRED"


def _evaluate(email: str, payload: dict) -> dict:
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get("policy") or {})}
    ctx = _cross_system_context(email)

    reserve_formula_coverage = float(payload.get("reserve_formula_coverage", 0.0) or 0.0)
    daily_segregation_accuracy = float(payload.get("daily_segregation_accuracy", 0.0) or 0.0)
    bank_acknowledgement_quality = float(payload.get("bank_acknowledgement_quality", 0.0) or 0.0)
    client_money_reconciliation_quality = float(payload.get("client_money_reconciliation_quality", 0.0) or 0.0)
    unresolved_reserve_formula_breaks = int(payload.get("unresolved_reserve_formula_breaks", 0) or 0)
    unresolved_client_money_exceptions = int(payload.get("unresolved_client_money_exceptions", 0) or 0)

    score = 100.0
    reasons = []
    alerts = []

    if reserve_formula_coverage < float(policy.get("minimum_reserve_formula_coverage", 0.99)):
        score -= round((float(policy.get("minimum_reserve_formula_coverage", 0.99)) - reserve_formula_coverage) * 130.0, 2)
        reasons.append("reserve formula coverage is below safeguarding threshold")
        alerts.append("RESERVE_FORMULA_COVERAGE_WEAK")
    if daily_segregation_accuracy < float(policy.get("minimum_daily_segregation_accuracy", 0.99)):
        score -= round((float(policy.get("minimum_daily_segregation_accuracy", 0.99)) - daily_segregation_accuracy) * 120.0, 2)
        reasons.append("daily segregation accuracy is below policy")
        alerts.append("DAILY_SEGREGATION_ACCURACY_WEAK")
    if bank_acknowledgement_quality < float(policy.get("minimum_bank_acknowledgement_quality", 0.98)):
        score -= round((float(policy.get("minimum_bank_acknowledgement_quality", 0.98)) - bank_acknowledgement_quality) * 100.0, 2)
        reasons.append("bank acknowledgement quality is below protected-account threshold")
        alerts.append("BANK_ACKNOWLEDGEMENT_WEAK")
    if client_money_reconciliation_quality < float(policy.get("minimum_client_money_reconciliation_quality", 0.98)):
        score -= round((float(policy.get("minimum_client_money_reconciliation_quality", 0.98)) - client_money_reconciliation_quality) * 100.0, 2)
        reasons.append("client money reconciliation quality is below daily safeguarding threshold")
        alerts.append("CLIENT_MONEY_RECONCILIATION_WEAK")
    if unresolved_reserve_formula_breaks > 0:
        score -= min(unresolved_reserve_formula_breaks * 6.0, 24.0)
        reasons.append("reserve formula breaks remain unresolved")
        alerts.append("OPEN_RESERVE_FORMULA_BREAKS")
    if unresolved_client_money_exceptions > 0:
        score -= min(unresolved_client_money_exceptions * 5.0, 20.0)
        reasons.append("client money exceptions remain unresolved")
        alerts.append("OPEN_CLIENT_MONEY_EXCEPTIONS")

    custody_posture = str(ctx.get("custody", {}).get("posture", "UNINITIALIZED"))
    filing_posture = str(ctx.get("filing", {}).get("posture", "UNINITIALIZED"))
    records_posture = str(ctx.get("records", {}).get("posture", "UNINITIALIZED"))
    breach_posture = str(ctx.get("breach", {}).get("posture", "UNINITIALIZED"))

    if policy.get("require_client_asset_safeguarding_clear", True) and custody_posture not in {"CUSTODY_ASSURANCE_CLEAR", "SAFEGUARDING_WATCH", "UNINITIALIZED"}:
        score -= 9.0; reasons.append("client asset safeguarding posture is not client-money clear"); alerts.append("CUSTODY_NOT_CLEAR")
    if policy.get("require_filing_clear", True) and filing_posture not in {"FILING_RELEASE_READY", "FILING_SUBMISSION_WATCH", "UNINITIALIZED"}:
        score -= 7.0; reasons.append("filing posture is not disclosure-clear"); alerts.append("FILING_NOT_CLEAR")
    if policy.get("require_records_retrievable", True) and records_posture not in {"SUPERVISORY_RETRIEVAL_READY", "RECORD_RETRIEVAL_WATCH", "UNINITIALIZED"}:
        score -= 8.0; reasons.append("records posture is not retrieval-ready"); alerts.append("RECORDS_NOT_RETRIEVABLE")
    if policy.get("require_breach_clear", True) and breach_posture not in {"REMEDIATION_COMMAND_CLEAR", "REMEDIATION_WATCH", "UNINITIALIZED"}:
        score -= 7.0; reasons.append("breach posture is not client-money clear"); alerts.append("BREACH_NOT_CLEAR")

    score = max(round(score, 2), 0.0)
    band = _band(score)
    posture = "DAILY_SAFEKEEPING_CLEAR" if score >= float(policy.get("minimum_score", 96.0)) else ("SAFEGUARDING_WATCH" if score >= 92.0 else "CLIENT_MONEY_REMEDIATION_REQUIRED")
    operator_review_required = posture != "DAILY_SAFEKEEPING_CLEAR" or unresolved_reserve_formula_breaks > 0 or unresolved_client_money_exceptions > 0
    row = {
        "mission": "QNT30771",
        "evaluated_at": _now_iso(),
        "score": score,
        "band": band,
        "posture": posture,
        "operator_review_required": operator_review_required,
        "reserve_formula_coverage": reserve_formula_coverage,
        "daily_segregation_accuracy": daily_segregation_accuracy,
        "bank_acknowledgement_quality": bank_acknowledgement_quality,
        "client_money_reconciliation_quality": client_money_reconciliation_quality,
        "unresolved_reserve_formula_breaks": unresolved_reserve_formula_breaks,
        "unresolved_client_money_exceptions": unresolved_client_money_exceptions,
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


@router.post("/record-reserve-formula-snapshot")
def record_reserve_formula_snapshot(payload: dict = Body(...), user=Depends(_require_user)):
    email = user["email"]
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get("policy") or {})}
    row = {
        "recorded_at": _now_iso(),
        "snapshot_code": payload.get("snapshot_code", "CMR_2026_Q4_RESERVE_FORMULA_001"),
        "scope": payload.get("scope", "CLIENT_MONEY_REQUIREMENT_RESERVE_BALANCE"),
        "status": payload.get("status", "RECORDED"),
    }
    _append(store, "reserve_formula_snapshots", row, policy.get("retain_cycles", 180))
    _save(email, store)
    return {"ok": True, "reserve_formula_snapshot": row, "summary": _summary_for_email(email)}


@router.post("/register-protected-bank-account")
def register_protected_bank_account(payload: dict = Body(...), user=Depends(_require_user)):
    email = user["email"]
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get("policy") or {})}
    row = {
        "registered_at": _now_iso(),
        "account_code": payload.get("account_code", "CLIENT_MONEY_BANK_001"),
        "bank_name": payload.get("bank_name", "INSTITUTIONAL_TIER1_BANK"),
        "status": payload.get("status", "ACTIVE"),
    }
    _append(store, "protected_bank_accounts", row, policy.get("retain_cycles", 180))
    _save(email, store)
    return {"ok": True, "protected_bank_account": row, "summary": _summary_for_email(email)}


@router.post("/record-daily-segregation-check")
def record_daily_segregation_check(payload: dict = Body(...), user=Depends(_require_user)):
    email = user["email"]
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get("policy") or {})}
    row = {
        "recorded_at": _now_iso(),
        "check_code": payload.get("check_code", "DSEG_2026_11_18_001"),
        "coverage_scope": payload.get("coverage_scope", "LEDGER_BANK_ACKNOWLEDGEMENT_RESERVE_FORMULA"),
        "status": payload.get("status", "MATCHED"),
    }
    _append(store, "daily_segregation_checks", row, policy.get("retain_cycles", 180))
    _save(email, store)
    return {"ok": True, "daily_segregation_check": row, "summary": _summary_for_email(email)}


@router.post("/issue-client-money-attestation")
def issue_client_money_attestation(payload: dict = Body(...), user=Depends(_require_user)):
    email = user["email"]
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get("policy") or {})}
    row = {
        "issued_at": _now_iso(),
        "attestation_code": payload.get("attestation_code", "ATT_2026_Q4_CLIENT_MONEY_DAILY_SAFEKEEPING"),
        "scope": payload.get("scope", "RESERVE_FORMULA_DAILY_SEGREGATION_RECONCILIATION"),
        "status": payload.get("status", "ISSUED"),
    }
    _append(store, "client_money_attestations", row, policy.get("retain_cycles", 180))
    _save(email, store)
    return {"ok": True, "client_money_attestation": row, "summary": _summary_for_email(email)}


@router.get("/policy")
def policy(user=Depends(_require_user)):
    return {"ok": True, "policy": _load(user["email"]).get("policy") or dict(DEFAULT_POLICY)}


@router.post("/bootstrap-demo")
def bootstrap_demo(user=Depends(_require_user)):
    email = user["email"]
    record_reserve_formula_snapshot({}, user)
    register_protected_bank_account({}, user)
    record_daily_segregation_check({}, user)
    issue_client_money_attestation({}, user)
    run = _evaluate(email, {
        "reserve_formula_coverage": 0.995,
        "daily_segregation_accuracy": 0.994,
        "bank_acknowledgement_quality": 0.99,
        "client_money_reconciliation_quality": 0.99,
        "unresolved_reserve_formula_breaks": 0,
        "unresolved_client_money_exceptions": 0,
    })
    return {"ok": True, "run": run, "summary": _summary_for_email(email)}
