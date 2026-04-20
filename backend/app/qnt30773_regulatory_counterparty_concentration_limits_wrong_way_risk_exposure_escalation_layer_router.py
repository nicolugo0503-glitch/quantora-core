from fastapi import APIRouter, Body, Depends
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json

router = APIRouter(prefix="/api/regulatory-counterparty-concentration-limits-wrong-way-risk-exposure-escalation-layer", tags=["regulatory-counterparty-concentration-limits-wrong-way-risk-exposure-escalation-layer"])
PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
ENGINE_DIR = ARTIFACTS_DIR / "regulatory_counterparty_concentration_limits_wrong_way_risk_exposure_escalation_layer"
DEFAULT_POLICY = {
    "retain_cycles": 180,
    "minimum_score": 96.0,
    "require_counterparty_protection_clear": True,
    "require_capital_clear": True,
    "require_liquidity_clear": True,
    "minimum_concentration_diversification": 0.97,
    "minimum_wrong_way_risk_control": 0.97,
    "minimum_exposure_headroom": 0.96,
    "minimum_collateral_resilience": 0.97,
}


def _mu():
    from backend.app import qnt30557_multi_user_router as mu
    return mu


def _counterparty_protection():
    from backend.app import qnt30772_regulatory_prime_broker_exposure_counterparty_safeguarding_collateral_protection_layer_router as module
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
            "counterparty_groups": [],
            "exposure_profiles": [],
            "wrong_way_risk_checks": [],
            "exposure_escalations": [],
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
        "regulatory_counterparty_concentration_limits_wrong_way_risk_exposure_escalation_layer_status": {
            "posture": latest.get("posture", "UNINITIALIZED"),
            "latest_score": latest.get("score"),
            "band": latest.get("band", "UNSET"),
            "run_count": len(s.get("runs") or []),
            "alert_count": len(s.get("alerts") or []),
            "counterparty_group_count": len(s.get("counterparty_groups") or []),
            "exposure_profile_count": len(s.get("exposure_profiles") or []),
            "wrong_way_risk_check_count": len(s.get("wrong_way_risk_checks") or []),
            "exposure_escalation_count": len(s.get("exposure_escalations") or []),
            "operator_review_required": bool(latest.get("operator_review_required", False)),
        },
        "latest_run": latest,
        "alerts": s.get("alerts") or [],
        "policy": s.get("policy") or dict(DEFAULT_POLICY),
        "last_context": s.get("last_context") or {},
        "counterparty_groups": s.get("counterparty_groups") or [],
        "exposure_profiles": s.get("exposure_profiles") or [],
        "wrong_way_risk_checks": s.get("wrong_way_risk_checks") or [],
        "exposure_escalations": s.get("exposure_escalations") or [],
    }


def _cross_system_context(email: str) -> dict:
    return {
        "captured_at": _now_iso(),
        "counterparty_protection": (_counterparty_protection()._summary_for_email(email).get("regulatory_prime_broker_exposure_counterparty_safeguarding_collateral_protection_layer_status") or {}),
        "capital": (_capital()._summary_for_email(email).get("regulatory_capital_adequacy_surveillance_early_warning_layer_status") or {}),
        "liquidity": (_liquidity()._summary_for_email(email).get("regulatory_liquidity_stress_command_recovery_layer_status") or {}),
    }


def _band(score: float) -> str:
    if score >= 98.0:
        return "EXPOSURE_GOVERNANCE_READY"
    if score >= 96.0:
        return "LIMIT_DISCIPLINE_CLEAR"
    if score >= 92.0:
        return "CONCENTRATION_WATCH"
    return "EXPOSURE_ESCALATION_REQUIRED"


def _evaluate(email: str, payload: dict) -> dict:
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get("policy") or {})}
    ctx = _cross_system_context(email)

    concentration_diversification = float(payload.get("concentration_diversification", 0.0) or 0.0)
    wrong_way_risk_control = float(payload.get("wrong_way_risk_control", 0.0) or 0.0)
    exposure_headroom = float(payload.get("exposure_headroom", 0.0) or 0.0)
    collateral_resilience = float(payload.get("collateral_resilience", 0.0) or 0.0)
    unresolved_limit_breaches = int(payload.get("unresolved_limit_breaches", 0) or 0)
    unresolved_wrong_way_flags = int(payload.get("unresolved_wrong_way_flags", 0) or 0)

    score = 100.0
    reasons = []
    alerts = []

    if concentration_diversification < float(policy.get("minimum_concentration_diversification", 0.97)):
        score -= round((float(policy.get("minimum_concentration_diversification", 0.97)) - concentration_diversification) * 120.0, 2)
        reasons.append("counterparty concentration diversification is below policy")
        alerts.append("COUNTERPARTY_CONCENTRATION_WEAK")
    if wrong_way_risk_control < float(policy.get("minimum_wrong_way_risk_control", 0.97)):
        score -= round((float(policy.get("minimum_wrong_way_risk_control", 0.97)) - wrong_way_risk_control) * 120.0, 2)
        reasons.append("wrong-way risk control is below policy")
        alerts.append("WRONG_WAY_RISK_CONTROL_WEAK")
    if exposure_headroom < float(policy.get("minimum_exposure_headroom", 0.96)):
        score -= round((float(policy.get("minimum_exposure_headroom", 0.96)) - exposure_headroom) * 110.0, 2)
        reasons.append("exposure headroom is below threshold")
        alerts.append("EXPOSURE_HEADROOM_THIN")
    if collateral_resilience < float(policy.get("minimum_collateral_resilience", 0.97)):
        score -= round((float(policy.get("minimum_collateral_resilience", 0.97)) - collateral_resilience) * 100.0, 2)
        reasons.append("collateral resilience is below escalation threshold")
        alerts.append("COLLATERAL_RESILIENCE_WEAK")
    if unresolved_limit_breaches > 0:
        score -= min(unresolved_limit_breaches * 7.0, 28.0)
        reasons.append("counterparty concentration limit breaches remain unresolved")
        alerts.append("OPEN_LIMIT_BREACHES")
    if unresolved_wrong_way_flags > 0:
        score -= min(unresolved_wrong_way_flags * 6.0, 24.0)
        reasons.append("wrong-way risk flags remain unresolved")
        alerts.append("OPEN_WRONG_WAY_FLAGS")

    counterparty_posture = str(ctx.get("counterparty_protection", {}).get("posture", "UNINITIALIZED"))
    capital_posture = str(ctx.get("capital", {}).get("posture", "UNINITIALIZED"))
    liquidity_posture = str(ctx.get("liquidity", {}).get("posture", "UNINITIALIZED"))

    if policy.get("require_counterparty_protection_clear", True) and counterparty_posture not in {"COLLATERAL_PROTECTION_CLEAR", "COUNTERPARTY_WATCH", "UNINITIALIZED"}:
        score -= 8.0; reasons.append("counterparty protection posture is not escalation-clear"); alerts.append("COUNTERPARTY_PROTECTION_NOT_CLEAR")
    if policy.get("require_capital_clear", True) and capital_posture not in {"CAPITAL_ADEQUACY_CLEAR", "CAPITAL_BUFFER_WATCH", "UNINITIALIZED"}:
        score -= 8.0; reasons.append("capital posture is not escalation-clear"); alerts.append("CAPITAL_NOT_CLEAR")
    if policy.get("require_liquidity_clear", True) and liquidity_posture not in {"LIQUIDITY_COMMAND_CLEAR", "LIQUIDITY_STRESS_WATCH", "UNINITIALIZED"}:
        score -= 8.0; reasons.append("liquidity posture is not escalation-clear"); alerts.append("LIQUIDITY_NOT_CLEAR")

    score = max(round(score, 2), 0.0)
    band = _band(score)
    posture = "LIMIT_DISCIPLINE_CLEAR" if score >= float(policy.get("minimum_score", 96.0)) else ("CONCENTRATION_WATCH" if score >= 92.0 else "EXPOSURE_ESCALATION_REQUIRED")
    operator_review_required = posture != "LIMIT_DISCIPLINE_CLEAR" or unresolved_limit_breaches > 0 or unresolved_wrong_way_flags > 0
    row = {
        "mission": "QNT30773",
        "evaluated_at": _now_iso(),
        "score": score,
        "band": band,
        "posture": posture,
        "operator_review_required": operator_review_required,
        "concentration_diversification": concentration_diversification,
        "wrong_way_risk_control": wrong_way_risk_control,
        "exposure_headroom": exposure_headroom,
        "collateral_resilience": collateral_resilience,
        "unresolved_limit_breaches": unresolved_limit_breaches,
        "unresolved_wrong_way_flags": unresolved_wrong_way_flags,
        "reasons": reasons,
        "alerts": alerts,
        "context": ctx,
    }
    _append(store, "runs", row, policy.get("retain_cycles", 180))
    for code in alerts:
        _append(store, "alerts", {"code": code, "at": row["evaluated_at"]}, policy.get("retain_cycles", 180))
    store["latest_run"] = row
    store["last_context"] = ctx
    _save(email, store)
    return row


@router.get("/summary")
def summary(user=Depends(_require_user)):
    return _summary_for_email(user["email"])


@router.post("/evaluate")
def evaluate(payload: dict = Body(...), user=Depends(_require_user)):
    return {"ok": True, "result": _evaluate(user["email"], payload)}


@router.post("/register-counterparty-group")
def register_counterparty_group(payload: dict = Body(...), user=Depends(_require_user)):
    store = _load(user["email"])
    row = {
        "registered_at": _now_iso(),
        "group_name": payload.get("group_name", "Global Counterparty Group"),
        "jurisdiction": payload.get("jurisdiction", "multi-jurisdiction"),
        "group_limit": float(payload.get("group_limit", 0.18) or 0.18),
        "watch_limit": float(payload.get("watch_limit", 0.14) or 0.14),
    }
    _append(store, "counterparty_groups", row, (store.get("policy") or {}).get("retain_cycles", 180))
    _save(user["email"], store)
    return {"ok": True, "counterparty_group": row}


@router.post("/record-exposure-profile")
def record_exposure_profile(payload: dict = Body(...), user=Depends(_require_user)):
    store = _load(user["email"])
    row = {
        "recorded_at": _now_iso(),
        "counterparty": payload.get("counterparty", "Prime-Clearing Complex A"),
        "gross_exposure": float(payload.get("gross_exposure", 0.12) or 0.12),
        "net_exposure": float(payload.get("net_exposure", 0.08) or 0.08),
        "collateralized_ratio": float(payload.get("collateralized_ratio", 0.99) or 0.99),
        "stress_addon": float(payload.get("stress_addon", 0.03) or 0.03),
    }
    _append(store, "exposure_profiles", row, (store.get("policy") or {}).get("retain_cycles", 180))
    _save(user["email"], store)
    return {"ok": True, "exposure_profile": row}


@router.post("/record-wrong-way-risk-check")
def record_wrong_way_risk_check(payload: dict = Body(...), user=Depends(_require_user)):
    store = _load(user["email"])
    row = {
        "checked_at": _now_iso(),
        "counterparty": payload.get("counterparty", "Prime-Clearing Complex A"),
        "scenario": payload.get("scenario", "stressed sovereign spread widening"),
        "wrong_way_score": float(payload.get("wrong_way_score", 0.98) or 0.98),
        "hedge_effectiveness": float(payload.get("hedge_effectiveness", 0.97) or 0.97),
        "status": payload.get("status", "CLEAR"),
    }
    _append(store, "wrong_way_risk_checks", row, (store.get("policy") or {}).get("retain_cycles", 180))
    _save(user["email"], store)
    return {"ok": True, "wrong_way_risk_check": row}


@router.post("/escalate-exposure-breach")
def escalate_exposure_breach(payload: dict = Body(...), user=Depends(_require_user)):
    store = _load(user["email"])
    row = {
        "escalated_at": _now_iso(),
        "counterparty": payload.get("counterparty", "Prime-Clearing Complex A"),
        "breach_type": payload.get("breach_type", "CONCENTRATION_LIMIT"),
        "severity": payload.get("severity", "HIGH"),
        "owner": payload.get("owner", "capital_committee"),
        "required_action": payload.get("required_action", "reduce exposure and increase collateral")
    }
    _append(store, "exposure_escalations", row, (store.get("policy") or {}).get("retain_cycles", 180))
    _append(store, "alerts", {"code": "EXPOSURE_ESCALATED", "at": row["escalated_at"]}, (store.get("policy") or {}).get("retain_cycles", 180))
    _save(user["email"], store)
    return {"ok": True, "exposure_escalation": row}


@router.get("/policy")
def policy(user=Depends(_require_user)):
    return {"ok": True, "policy": _load(user["email"]).get("policy") or dict(DEFAULT_POLICY)}


@router.post("/bootstrap-demo")
def bootstrap_demo(user=Depends(_require_user)):
    register_counterparty_group({
        "group_name": "Global Prime and OTC Network",
        "jurisdiction": "us-eu-uk",
        "group_limit": 0.18,
        "watch_limit": 0.14,
    }, user)
    record_exposure_profile({
        "counterparty": "Prime-Clearing Complex A",
        "gross_exposure": 0.11,
        "net_exposure": 0.07,
        "collateralized_ratio": 0.99,
        "stress_addon": 0.03,
    }, user)
    record_wrong_way_risk_check({
        "counterparty": "Prime-Clearing Complex A",
        "scenario": "credit-spread widening with collateral drag",
        "wrong_way_score": 0.98,
        "hedge_effectiveness": 0.97,
        "status": "CLEAR",
    }, user)
    result = _evaluate(user["email"], {
        "concentration_diversification": 0.98,
        "wrong_way_risk_control": 0.98,
        "exposure_headroom": 0.97,
        "collateral_resilience": 0.98,
        "unresolved_limit_breaches": 0,
        "unresolved_wrong_way_flags": 0,
    })
    return {"ok": True, "result": result, "summary": _summary_for_email(user["email"])}
