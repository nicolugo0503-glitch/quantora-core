from fastapi import APIRouter, Body, Depends
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json

router = APIRouter(prefix="/api/regulatory-client-asset-safeguarding-segregation-custody-assurance-layer", tags=["regulatory-client-asset-safeguarding-segregation-custody-assurance-layer"])
PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
ENGINE_DIR = ARTIFACTS_DIR / "regulatory_client_asset_safeguarding_segregation_custody_assurance_layer"
DEFAULT_POLICY = {
    "retain_cycles": 180,
    "minimum_score": 96.0,
    "require_reporting_clear": True,
    "require_records_retrievable": True,
    "require_provenance_clear": True,
    "minimum_asset_segregation_integrity": 0.99,
    "minimum_reconciliation_coverage": 0.98,
    "minimum_custody_confirmation_quality": 0.98,
    "minimum_client_asset_disclosure_readiness": 0.97,
}


def _mu():
    from backend.app import qnt30557_multi_user_router as mu
    return mu


def _reporting():
    from backend.app import qnt30769_cross_market_transaction_reporting_regulatory_disclosure_layer_router as module
    return module


def _records():
    from backend.app import qnt30766_regulatory_records_retention_legal_hold_supervisory_retrieval_command_layer_router as module
    return module


def _provenance():
    from backend.app import qnt30765_regulatory_data_lineage_evidence_provenance_attestation_fabric_router as module
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
            "segregation_snapshots": [],
            "custody_accounts": [],
            "reconciliation_checks": [],
            "safeguarding_attestations": [],
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
        "regulatory_client_asset_safeguarding_segregation_custody_assurance_layer_status": {
            "posture": latest.get("posture", "UNINITIALIZED"),
            "latest_score": latest.get("score"),
            "band": latest.get("band", "UNSET"),
            "run_count": len(s.get("runs") or []),
            "alert_count": len(s.get("alerts") or []),
            "segregation_snapshot_count": len(s.get("segregation_snapshots") or []),
            "custody_account_count": len(s.get("custody_accounts") or []),
            "reconciliation_check_count": len(s.get("reconciliation_checks") or []),
            "safeguarding_attestation_count": len(s.get("safeguarding_attestations") or []),
            "operator_review_required": bool(latest.get("operator_review_required", False)),
        },
        "latest_run": latest,
        "alerts": s.get("alerts") or [],
        "policy": s.get("policy") or dict(DEFAULT_POLICY),
        "last_context": s.get("last_context") or {},
        "segregation_snapshots": s.get("segregation_snapshots") or [],
        "custody_accounts": s.get("custody_accounts") or [],
        "reconciliation_checks": s.get("reconciliation_checks") or [],
        "safeguarding_attestations": s.get("safeguarding_attestations") or [],
    }


def _cross_system_context(email: str) -> dict:
    return {
        "captured_at": _now_iso(),
        "reporting": (_reporting()._summary_for_email(email).get("cross_market_transaction_reporting_regulatory_disclosure_layer_status") or {}),
        "records": (_records()._summary_for_email(email).get("regulatory_records_retention_legal_hold_supervisory_retrieval_command_layer_status") or {}),
        "provenance": (_provenance()._summary_for_email(email).get("regulatory_data_lineage_evidence_provenance_attestation_fabric_status") or {}),
        "breach": (_breach()._summary_for_email(email).get("regulatory_breach_escalation_remediation_command_layer_status") or {}),
    }


def _band(score: float) -> str:
    if score >= 98.0:
        return "CLIENT_ASSET_SAFEGUARDING_READY"
    if score >= 96.0:
        return "CUSTODY_ASSURANCE_CLEAR"
    if score >= 92.0:
        return "SAFEGUARDING_WATCH"
    return "CLIENT_ASSET_REMEDIATION_REQUIRED"


def _evaluate(email: str, payload: dict) -> dict:
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get("policy") or {})}
    ctx = _cross_system_context(email)

    asset_segregation_integrity = float(payload.get("asset_segregation_integrity", 0.0) or 0.0)
    reconciliation_coverage = float(payload.get("reconciliation_coverage", 0.0) or 0.0)
    custody_confirmation_quality = float(payload.get("custody_confirmation_quality", 0.0) or 0.0)
    client_asset_disclosure_readiness = float(payload.get("client_asset_disclosure_readiness", 0.0) or 0.0)
    unresolved_segregation_breaks = int(payload.get("unresolved_segregation_breaks", 0) or 0)
    unresolved_custody_exceptions = int(payload.get("unresolved_custody_exceptions", 0) or 0)

    score = 100.0
    reasons = []
    alerts = []

    if asset_segregation_integrity < float(policy.get("minimum_asset_segregation_integrity", 0.99)):
        score -= round((float(policy.get("minimum_asset_segregation_integrity", 0.99)) - asset_segregation_integrity) * 120.0, 2)
        reasons.append("asset segregation integrity is below safeguarding threshold")
        alerts.append("ASSET_SEGREGATION_WEAK")
    if reconciliation_coverage < float(policy.get("minimum_reconciliation_coverage", 0.98)):
        score -= round((float(policy.get("minimum_reconciliation_coverage", 0.98)) - reconciliation_coverage) * 100.0, 2)
        reasons.append("client asset reconciliation coverage is below policy")
        alerts.append("RECONCILIATION_COVERAGE_WEAK")
    if custody_confirmation_quality < float(policy.get("minimum_custody_confirmation_quality", 0.98)):
        score -= round((float(policy.get("minimum_custody_confirmation_quality", 0.98)) - custody_confirmation_quality) * 100.0, 2)
        reasons.append("custody confirmation quality is below assurance threshold")
        alerts.append("CUSTODY_CONFIRMATION_WEAK")
    if client_asset_disclosure_readiness < float(policy.get("minimum_client_asset_disclosure_readiness", 0.97)):
        score -= round((float(policy.get("minimum_client_asset_disclosure_readiness", 0.97)) - client_asset_disclosure_readiness) * 90.0, 2)
        reasons.append("client asset disclosure readiness is below regulatory threshold")
        alerts.append("CLIENT_ASSET_DISCLOSURE_WEAK")
    if unresolved_segregation_breaks > 0:
        score -= min(unresolved_segregation_breaks * 6.0, 24.0)
        reasons.append("segregation breaks remain unresolved")
        alerts.append("OPEN_SEGREGATION_BREAKS")
    if unresolved_custody_exceptions > 0:
        score -= min(unresolved_custody_exceptions * 5.0, 20.0)
        reasons.append("custody exceptions remain unresolved")
        alerts.append("OPEN_CUSTODY_EXCEPTIONS")

    reporting_posture = str(ctx.get("reporting", {}).get("posture", "UNINITIALIZED"))
    records_posture = str(ctx.get("records", {}).get("posture", "UNINITIALIZED"))
    provenance_posture = str(ctx.get("provenance", {}).get("posture", "UNINITIALIZED"))
    breach_posture = str(ctx.get("breach", {}).get("posture", "UNINITIALIZED"))

    if policy.get("require_reporting_clear", True) and reporting_posture not in {"REPORTING_AND_DISCLOSURE_CLEAR", "REPORTING_WATCH", "UNINITIALIZED"}:
        score -= 8.0; reasons.append("reporting posture is not custody-clear"); alerts.append("REPORTING_NOT_CLEAR")
    if policy.get("require_records_retrievable", True) and records_posture not in {"SUPERVISORY_RETRIEVAL_READY", "RECORD_RETRIEVAL_WATCH", "UNINITIALIZED"}:
        score -= 8.0; reasons.append("records posture is not retrieval-ready"); alerts.append("RECORDS_NOT_RETRIEVABLE")
    if policy.get("require_provenance_clear", True) and provenance_posture not in {"EVIDENCE_PROVENANCE_CLEAR", "HEIGHTENED_DATA_GOVERNANCE_WATCH", "UNINITIALIZED"}:
        score -= 8.0; reasons.append("provenance posture is not safeguarding-clear"); alerts.append("PROVENANCE_NOT_CLEAR")
    if breach_posture not in {"REMEDIATION_COMMAND_CLEAR", "REMEDIATION_WATCH", "UNINITIALIZED"}:
        score -= 7.0; reasons.append("breach posture is not custody-clear"); alerts.append("BREACH_NOT_CLEAR")

    score = max(round(score, 2), 0.0)
    band = _band(score)
    posture = "CUSTODY_ASSURANCE_CLEAR" if score >= float(policy.get("minimum_score", 96.0)) else ("SAFEGUARDING_WATCH" if score >= 92.0 else "CLIENT_ASSET_REMEDIATION_REQUIRED")
    operator_review_required = posture != "CUSTODY_ASSURANCE_CLEAR" or unresolved_segregation_breaks > 0 or unresolved_custody_exceptions > 0
    row = {
        "mission": "QNT30770",
        "evaluated_at": _now_iso(),
        "score": score,
        "band": band,
        "posture": posture,
        "operator_review_required": operator_review_required,
        "asset_segregation_integrity": asset_segregation_integrity,
        "reconciliation_coverage": reconciliation_coverage,
        "custody_confirmation_quality": custody_confirmation_quality,
        "client_asset_disclosure_readiness": client_asset_disclosure_readiness,
        "unresolved_segregation_breaks": unresolved_segregation_breaks,
        "unresolved_custody_exceptions": unresolved_custody_exceptions,
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


@router.post("/record-segregation-snapshot")
def record_segregation_snapshot(payload: dict = Body(...), user=Depends(_require_user)):
    email = user["email"]
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get("policy") or {})}
    row = {
        "recorded_at": _now_iso(),
        "snapshot_code": payload.get("snapshot_code", "CAS_2026_Q4_SEGREGATION_SNAPSHOT_001"),
        "ledger_scope": payload.get("ledger_scope", "CLIENT_MONEY_AND_CUSTODY_ASSETS"),
        "status": payload.get("status", "RECORDED"),
    }
    _append(store, "segregation_snapshots", row, policy.get("retain_cycles", 180))
    _save(email, store)
    return {"ok": True, "segregation_snapshot": row, "summary": _summary_for_email(email)}


@router.post("/register-custody-account")
def register_custody_account(payload: dict = Body(...), user=Depends(_require_user)):
    email = user["email"]
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get("policy") or {})}
    row = {
        "registered_at": _now_iso(),
        "account_code": payload.get("account_code", "CUSTODY_OMNIBUS_001"),
        "custodian_name": payload.get("custodian_name", "INSTITUTIONAL_GLOBAL_CUSTODIAN"),
        "status": payload.get("status", "ACTIVE"),
    }
    _append(store, "custody_accounts", row, policy.get("retain_cycles", 180))
    _save(email, store)
    return {"ok": True, "custody_account": row, "summary": _summary_for_email(email)}


@router.post("/record-reconciliation-check")
def record_reconciliation_check(payload: dict = Body(...), user=Depends(_require_user)):
    email = user["email"]
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get("policy") or {})}
    row = {
        "recorded_at": _now_iso(),
        "check_code": payload.get("check_code", "REC_2026_Q4_CLIENT_ASSET_RECON_001"),
        "coverage_scope": payload.get("coverage_scope", "LEDGER_CUSTODIAN_BANK_MATCH"),
        "status": payload.get("status", "MATCHED"),
    }
    _append(store, "reconciliation_checks", row, policy.get("retain_cycles", 180))
    _save(email, store)
    return {"ok": True, "reconciliation_check": row, "summary": _summary_for_email(email)}


@router.post("/issue-safeguarding-attestation")
def issue_safeguarding_attestation(payload: dict = Body(...), user=Depends(_require_user)):
    email = user["email"]
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get("policy") or {})}
    row = {
        "issued_at": _now_iso(),
        "attestation_code": payload.get("attestation_code", "ATT_2026_Q4_CLIENT_ASSET_SAFEGUARDING"),
        "scope": payload.get("scope", "SEGREGATION_CUSTODY_RECONCILIATION_DISCLOSURE"),
        "status": payload.get("status", "ISSUED"),
    }
    _append(store, "safeguarding_attestations", row, policy.get("retain_cycles", 180))
    _save(email, store)
    return {"ok": True, "safeguarding_attestation": row, "summary": _summary_for_email(email)}


@router.get("/policy")
def policy(user=Depends(_require_user)):
    return {"ok": True, "policy": _load(user["email"]).get("policy") or dict(DEFAULT_POLICY)}


@router.post("/bootstrap-demo")
def bootstrap_demo(user=Depends(_require_user)):
    email = user["email"]
    record_segregation_snapshot({}, user)
    register_custody_account({}, user)
    record_reconciliation_check({}, user)
    issue_safeguarding_attestation({}, user)
    run = _evaluate(email, {
        "asset_segregation_integrity": 0.995,
        "reconciliation_coverage": 0.99,
        "custody_confirmation_quality": 0.99,
        "client_asset_disclosure_readiness": 0.98,
        "unresolved_segregation_breaks": 0,
        "unresolved_custody_exceptions": 0,
    })
    return {"ok": True, "run": run, "summary": _summary_for_email(email)}
