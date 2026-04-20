from fastapi import APIRouter, Body, Depends
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json

router = APIRouter(prefix="/api/regulatory-prime-broker-exposure-counterparty-safeguarding-collateral-protection-layer", tags=["regulatory-prime-broker-exposure-counterparty-safeguarding-collateral-protection-layer"])
PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
ENGINE_DIR = ARTIFACTS_DIR / "regulatory_prime_broker_exposure_counterparty_safeguarding_collateral_protection_layer"
DEFAULT_POLICY = {
    "retain_cycles": 180,
    "minimum_score": 96.0,
    "require_custody_clear": True,
    "require_client_money_clear": True,
    "require_capital_clear": True,
    "require_liquidity_clear": True,
    "minimum_prime_broker_credit_quality": 0.98,
    "minimum_counterparty_exposure_coverage": 0.98,
    "minimum_collateral_protection_quality": 0.98,
    "minimum_margin_integrity": 0.97,
}


def _mu():
    from backend.app import qnt30557_multi_user_router as mu
    return mu


def _custody():
    from backend.app import qnt30770_regulatory_client_asset_safeguarding_segregation_custody_assurance_layer_router as module
    return module


def _client_money():
    from backend.app import qnt30771_regulatory_client_money_protection_reserve_formula_daily_safeguarding_control_layer_router as module
    return module


def _capital():
    from backend.app import qnt30759_regulatory_capital_adequacy_surveillance_early_warning_layer_router as module
    return module


def _liquidity():
    from backend.app import qnt30760_regulatory_liquidity_stress_command_recovery_layer_router as module
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
            "prime_brokers": [],
            "counterparty_exposures": [],
            "collateral_protection_checks": [],
            "protection_attestations": [],
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
        "regulatory_prime_broker_exposure_counterparty_safeguarding_collateral_protection_layer_status": {
            "posture": latest.get("posture", "UNINITIALIZED"),
            "latest_score": latest.get("score"),
            "band": latest.get("band", "UNSET"),
            "run_count": len(s.get("runs") or []),
            "alert_count": len(s.get("alerts") or []),
            "prime_broker_count": len(s.get("prime_brokers") or []),
            "counterparty_exposure_count": len(s.get("counterparty_exposures") or []),
            "collateral_protection_check_count": len(s.get("collateral_protection_checks") or []),
            "protection_attestation_count": len(s.get("protection_attestations") or []),
            "operator_review_required": bool(latest.get("operator_review_required", False)),
        },
        "latest_run": latest,
        "alerts": s.get("alerts") or [],
        "policy": s.get("policy") or dict(DEFAULT_POLICY),
        "last_context": s.get("last_context") or {},
        "prime_brokers": s.get("prime_brokers") or [],
        "counterparty_exposures": s.get("counterparty_exposures") or [],
        "collateral_protection_checks": s.get("collateral_protection_checks") or [],
        "protection_attestations": s.get("protection_attestations") or [],
    }


def _cross_system_context(email: str) -> dict:
    return {
        "captured_at": _now_iso(),
        "custody": (_custody()._summary_for_email(email).get("regulatory_client_asset_safeguarding_segregation_custody_assurance_layer_status") or {}),
        "client_money": (_client_money()._summary_for_email(email).get("regulatory_client_money_protection_reserve_formula_daily_safeguarding_control_layer_status") or {}),
        "capital": (_capital()._summary_for_email(email).get("regulatory_capital_adequacy_surveillance_early_warning_layer_status") or {}),
        "liquidity": (_liquidity()._summary_for_email(email).get("regulatory_liquidity_stress_command_recovery_layer_status") or {}),
    }


def _band(score: float) -> str:
    if score >= 98.0:
        return "COUNTERPARTY_PROTECTION_READY"
    if score >= 96.0:
        return "COLLATERAL_PROTECTION_CLEAR"
    if score >= 92.0:
        return "COUNTERPARTY_WATCH"
    return "COUNTERPARTY_REMEDIATION_REQUIRED"


def _evaluate(email: str, payload: dict) -> dict:
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get("policy") or {})}
    ctx = _cross_system_context(email)

    prime_broker_credit_quality = float(payload.get("prime_broker_credit_quality", 0.0) or 0.0)
    counterparty_exposure_coverage = float(payload.get("counterparty_exposure_coverage", 0.0) or 0.0)
    collateral_protection_quality = float(payload.get("collateral_protection_quality", 0.0) or 0.0)
    margin_integrity = float(payload.get("margin_integrity", 0.0) or 0.0)
    unresolved_counterparty_breaks = int(payload.get("unresolved_counterparty_breaks", 0) or 0)
    unresolved_collateral_exceptions = int(payload.get("unresolved_collateral_exceptions", 0) or 0)

    score = 100.0
    reasons = []
    alerts = []

    if prime_broker_credit_quality < float(policy.get("minimum_prime_broker_credit_quality", 0.98)):
        score -= round((float(policy.get("minimum_prime_broker_credit_quality", 0.98)) - prime_broker_credit_quality) * 120.0, 2)
        reasons.append("prime broker credit quality is below safeguarding threshold")
        alerts.append("PRIME_BROKER_CREDIT_WEAK")
    if counterparty_exposure_coverage < float(policy.get("minimum_counterparty_exposure_coverage", 0.98)):
        score -= round((float(policy.get("minimum_counterparty_exposure_coverage", 0.98)) - counterparty_exposure_coverage) * 110.0, 2)
        reasons.append("counterparty exposure coverage is below policy")
        alerts.append("COUNTERPARTY_EXPOSURE_COVERAGE_WEAK")
    if collateral_protection_quality < float(policy.get("minimum_collateral_protection_quality", 0.98)):
        score -= round((float(policy.get("minimum_collateral_protection_quality", 0.98)) - collateral_protection_quality) * 110.0, 2)
        reasons.append("collateral protection quality is below safeguarding threshold")
        alerts.append("COLLATERAL_PROTECTION_WEAK")
    if margin_integrity < float(policy.get("minimum_margin_integrity", 0.97)):
        score -= round((float(policy.get("minimum_margin_integrity", 0.97)) - margin_integrity) * 100.0, 2)
        reasons.append("margin integrity is below counterparty protection threshold")
        alerts.append("MARGIN_INTEGRITY_WEAK")
    if unresolved_counterparty_breaks > 0:
        score -= min(unresolved_counterparty_breaks * 6.0, 24.0)
        reasons.append("counterparty breaks remain unresolved")
        alerts.append("OPEN_COUNTERPARTY_BREAKS")
    if unresolved_collateral_exceptions > 0:
        score -= min(unresolved_collateral_exceptions * 5.0, 20.0)
        reasons.append("collateral exceptions remain unresolved")
        alerts.append("OPEN_COLLATERAL_EXCEPTIONS")

    custody_posture = str(ctx.get("custody", {}).get("posture", "UNINITIALIZED"))
    client_money_posture = str(ctx.get("client_money", {}).get("posture", "UNINITIALIZED"))
    capital_posture = str(ctx.get("capital", {}).get("posture", "UNINITIALIZED"))
    liquidity_posture = str(ctx.get("liquidity", {}).get("posture", "UNINITIALIZED"))

    if policy.get("require_custody_clear", True) and custody_posture not in {"CUSTODY_ASSURANCE_CLEAR", "SAFEGUARDING_WATCH", "UNINITIALIZED"}:
        score -= 8.0; reasons.append("custody posture is not counterparty-clear"); alerts.append("CUSTODY_NOT_CLEAR")
    if policy.get("require_client_money_clear", True) and client_money_posture not in {"DAILY_SAFEKEEPING_CLEAR", "SAFEGUARDING_WATCH", "UNINITIALIZED"}:
        score -= 8.0; reasons.append("client money posture is not counterparty-clear"); alerts.append("CLIENT_MONEY_NOT_CLEAR")
    if policy.get("require_capital_clear", True) and capital_posture not in {"CAPITAL_ADEQUACY_CLEAR", "CAPITAL_BUFFER_WATCH", "UNINITIALIZED"}:
        score -= 8.0; reasons.append("capital posture is not counterparty-clear"); alerts.append("CAPITAL_NOT_CLEAR")
    if policy.get("require_liquidity_clear", True) and liquidity_posture not in {"LIQUIDITY_COMMAND_CLEAR", "LIQUIDITY_STRESS_WATCH", "UNINITIALIZED"}:
        score -= 8.0; reasons.append("liquidity posture is not counterparty-clear"); alerts.append("LIQUIDITY_NOT_CLEAR")

    score = max(round(score, 2), 0.0)
    band = _band(score)
    posture = "COLLATERAL_PROTECTION_CLEAR" if score >= float(policy.get("minimum_score", 96.0)) else ("COUNTERPARTY_WATCH" if score >= 92.0 else "COUNTERPARTY_REMEDIATION_REQUIRED")
    operator_review_required = posture != "COLLATERAL_PROTECTION_CLEAR" or unresolved_counterparty_breaks > 0 or unresolved_collateral_exceptions > 0
    row = {
        "mission": "QNT30772",
        "evaluated_at": _now_iso(),
        "score": score,
        "band": band,
        "posture": posture,
        "operator_review_required": operator_review_required,
        "prime_broker_credit_quality": prime_broker_credit_quality,
        "counterparty_exposure_coverage": counterparty_exposure_coverage,
        "collateral_protection_quality": collateral_protection_quality,
        "margin_integrity": margin_integrity,
        "unresolved_counterparty_breaks": unresolved_counterparty_breaks,
        "unresolved_collateral_exceptions": unresolved_collateral_exceptions,
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


@router.post("/register-prime-broker")
def register_prime_broker(payload: dict = Body(...), user=Depends(_require_user)):
    email = user["email"]
    store = _load(email)
    row = {
        "prime_broker_id": payload.get("prime_broker_id") or f"pb-{len(store.get('prime_brokers') or []) + 1}",
        "name": payload.get("name", "Prime Broker"),
        "jurisdiction": payload.get("jurisdiction", "US"),
        "credit_quality": float(payload.get("credit_quality", 0.99) or 0.99),
        "funding_diversification": float(payload.get("funding_diversification", 0.98) or 0.98),
        "created_at": _now_iso(),
    }
    _append(store, "prime_brokers", row, (store.get("policy") or {}).get("retain_cycles", 180))
    _save(email, store)
    return {"ok": True, "prime_broker": row, "summary": _summary_for_email(email)}


@router.post("/record-counterparty-exposure")
def record_counterparty_exposure(payload: dict = Body(...), user=Depends(_require_user)):
    email = user["email"]
    store = _load(email)
    row = {
        "counterparty_id": payload.get("counterparty_id") or f"cp-{len(store.get('counterparty_exposures') or []) + 1}",
        "exposure_value": float(payload.get("exposure_value", 0.0) or 0.0),
        "coverage_ratio": float(payload.get("coverage_ratio", 0.99) or 0.99),
        "concentration_ratio": float(payload.get("concentration_ratio", 0.12) or 0.12),
        "captured_at": _now_iso(),
    }
    _append(store, "counterparty_exposures", row, (store.get("policy") or {}).get("retain_cycles", 180))
    _save(email, store)
    return {"ok": True, "counterparty_exposure": row, "summary": _summary_for_email(email)}


@router.post("/record-collateral-protection-check")
def record_collateral_protection_check(payload: dict = Body(...), user=Depends(_require_user)):
    email = user["email"]
    store = _load(email)
    row = {
        "check_id": payload.get("check_id") or f"collateral-check-{len(store.get('collateral_protection_checks') or []) + 1}",
        "collateral_quality": float(payload.get("collateral_quality", 0.99) or 0.99),
        "haircut_integrity": float(payload.get("haircut_integrity", 0.98) or 0.98),
        "segregation_quality": float(payload.get("segregation_quality", 0.98) or 0.98),
        "checked_at": _now_iso(),
    }
    _append(store, "collateral_protection_checks", row, (store.get("policy") or {}).get("retain_cycles", 180))
    _save(email, store)
    return {"ok": True, "collateral_protection_check": row, "summary": _summary_for_email(email)}


@router.post("/issue-protection-attestation")
def issue_protection_attestation(payload: dict = Body(...), user=Depends(_require_user)):
    email = user["email"]
    store = _load(email)
    row = {
        "attestation_id": payload.get("attestation_id") or f"attest-{len(store.get('protection_attestations') or []) + 1}",
        "scope": payload.get("scope", "prime-broker-counterparty-collateral"),
        "status": payload.get("status", "ISSUED"),
        "issued_by": payload.get("issued_by", "quantora-operator"),
        "issued_at": _now_iso(),
    }
    _append(store, "protection_attestations", row, (store.get("policy") or {}).get("retain_cycles", 180))
    _save(email, store)
    return {"ok": True, "protection_attestation": row, "summary": _summary_for_email(email)}


@router.get("/policy")
def policy(user=Depends(_require_user)):
    return _summary_for_email(user["email"])["policy"]


@router.post("/bootstrap-demo")
def bootstrap_demo(user=Depends(_require_user)):
    email = user["email"]
    register_prime_broker({
        "prime_broker_id": "pb-core",
        "name": "Quantora Prime Core",
        "jurisdiction": "US",
        "credit_quality": 0.992,
        "funding_diversification": 0.985,
    }, user)
    record_counterparty_exposure({
        "counterparty_id": "cp-alpha",
        "exposure_value": 1250000,
        "coverage_ratio": 0.989,
        "concentration_ratio": 0.11,
    }, user)
    record_collateral_protection_check({
        "check_id": "check-core",
        "collateral_quality": 0.991,
        "haircut_integrity": 0.985,
        "segregation_quality": 0.984,
    }, user)
    issue_protection_attestation({
        "attestation_id": "attest-core",
        "scope": "prime-broker-counterparty-collateral",
        "status": "ISSUED",
        "issued_by": "quantora-operator",
    }, user)
    run = _evaluate(email, {
        "prime_broker_credit_quality": 0.992,
        "counterparty_exposure_coverage": 0.989,
        "collateral_protection_quality": 0.988,
        "margin_integrity": 0.982,
        "unresolved_counterparty_breaks": 0,
        "unresolved_collateral_exceptions": 0,
    })
    return {"ok": True, "run": run, "summary": _summary_for_email(email)}
