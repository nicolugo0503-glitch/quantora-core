from fastapi import APIRouter, Body, Depends
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json

router = APIRouter(prefix="/api/institutional-cash-reconciliation-closure-layer", tags=["institutional-cash-reconciliation-closure-layer"])
PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
ENGINE_DIR = ARTIFACTS_DIR / "institutional_cash_reconciliation_closure_layer"
DEFAULT_POLICY = {
    "retain_cycles": 180,
    "minimum_score": 96.0,
    "require_operator_clear": True,
    "require_release_clear": True,
    "require_safety_clear": True,
    "require_recovery_clear": True,
    "require_settlement_finalization_clear": True,
    "max_open_cash_breaks": 1,
    "max_critical_cash_breaks": 0,
    "minimum_cash_match_score": 0.985,
    "minimum_ledger_alignment_score": 0.98,
    "minimum_bank_confirmation_score": 0.975,
    "minimum_closure_evidence_score": 0.97,
    "minimum_control_attestation_score": 0.98,
}


def _mu():
    from backend.app import qnt30557_multi_user_router as mu
    return mu


def _operator():
    from backend.app import qnt30702_operator_command_console_router as operator
    return operator


def _release():
    from backend.app import qnt30700_institutional_release_control_router as release
    return release


def _safety():
    from backend.app import qnt30703_live_broker_safety_layer_router as safety
    return safety


def _recovery():
    from backend.app import qnt30707_recovery_system_router as recovery
    return recovery


def _settlement_finalization():
    from backend.app import qnt30743_institutional_settlement_finalization_authority_layer_router as settlement_finalization
    return settlement_finalization


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
            "book": [],
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
        "institutional_cash_reconciliation_closure_layer_status": {
            "posture": latest.get("posture", "UNINITIALIZED"),
            "latest_score": latest.get("score"),
            "band": latest.get("band", "UNSET"),
            "run_count": len(s.get("runs") or []),
            "alert_count": len(s.get("alerts") or []),
            "operator_review_required": bool(latest.get("operator_review_required", False)),
        },
        "latest_run": latest,
        "alerts": s.get("alerts") or [],
        "policy": s.get("policy") or dict(DEFAULT_POLICY),
        "last_context": s.get("last_context") or {},
    }


def _cross_system_context(email: str) -> dict:
    return {
        "captured_at": _now_iso(),
        "operator": (_operator()._summary_for_email(email).get("operator_console_status") or {}),
        "release": (_release()._summary_for_email(email).get("release_control_status") or {}),
        "safety": (_safety()._summary_for_email(email).get("safety_layer_status") or {}),
        "recovery": (_recovery()._summary_for_email(email).get("recovery_status") or {}),
        "settlement_finalization": (_settlement_finalization()._summary_for_email(email).get("institutional_settlement_finalization_authority_layer_status") or {}),
    }


def _band(score: float) -> str:
    if score >= 98.0:
        return "CASH_CLOSED"
    if score >= 96.0:
        return "CASH_CONTROLLED"
    if score >= 93.0:
        return "CASH_WATCH"
    return "CASH_BLOCKED"


def _evaluate(email: str, payload: dict) -> dict:
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get("policy") or {})}
    ctx = _cross_system_context(email)
    metrics = {k: float(payload.get(k, 0.0) or 0.0) for k in [
        "cash_match_score", "ledger_alignment_score", "bank_confirmation_score",
        "closure_evidence_score", "control_attestation_score"
    ]}
    open_cash_breaks = int(payload.get("open_cash_breaks", 0) or 0)
    critical_cash_breaks = int(payload.get("critical_cash_breaks", 0) or 0)
    evidence_complete = bool(payload.get("evidence_complete", False))
    cash_impact_confirmed = bool(payload.get("cash_impact_confirmed", False))
    manual_override_used = bool(payload.get("manual_override_used", False))

    score = 100.0
    reasons = []
    alerts = []
    penalties = {
        "cash_match_score": 120.0,
        "ledger_alignment_score": 105.0,
        "bank_confirmation_score": 90.0,
        "closure_evidence_score": 85.0,
        "control_attestation_score": 110.0,
    }
    reason_map = {
        "cash_match_score": "cash match quality is below institutional threshold",
        "ledger_alignment_score": "cash ledger alignment is below policy",
        "bank_confirmation_score": "bank confirmation quality is below policy",
        "closure_evidence_score": "cash closure evidence is incomplete",
        "control_attestation_score": "cash control attestation is below policy",
    }
    alert_map = {
        "cash_match_score": "CASH_MATCH_WEAK",
        "ledger_alignment_score": "LEDGER_ALIGNMENT_WEAK",
        "bank_confirmation_score": "BANK_CONFIRMATION_WEAK",
        "closure_evidence_score": "CLOSURE_EVIDENCE_WEAK",
        "control_attestation_score": "CONTROL_ATTESTATION_WEAK",
    }
    threshold_map = {
        "cash_match_score": "minimum_cash_match_score",
        "ledger_alignment_score": "minimum_ledger_alignment_score",
        "bank_confirmation_score": "minimum_bank_confirmation_score",
        "closure_evidence_score": "minimum_closure_evidence_score",
        "control_attestation_score": "minimum_control_attestation_score",
    }
    for key, value in metrics.items():
        threshold = float(policy.get(threshold_map[key], 0.97))
        if value < threshold:
            score -= round((threshold - value) * penalties[key], 2)
            reasons.append(reason_map[key])
            alerts.append(alert_map[key])

    if open_cash_breaks > int(policy.get("max_open_cash_breaks", 1)):
        score -= min((open_cash_breaks - int(policy.get("max_open_cash_breaks", 1))) * 5.0, 20.0)
        reasons.append("open cash breaks exceed policy")
        alerts.append("OPEN_CASH_BREAKS")
    if critical_cash_breaks > int(policy.get("max_critical_cash_breaks", 0)):
        score -= min(critical_cash_breaks * 10.0, 30.0)
        reasons.append("critical cash breaks remain unresolved")
        alerts.append("CRITICAL_CASH_BREAKS")
    if not evidence_complete:
        score -= 7.0
        reasons.append("cash closure evidence is incomplete")
        alerts.append("EVIDENCE_INCOMPLETE")
    if not cash_impact_confirmed:
        score -= 6.0
        reasons.append("cash impact is not fully confirmed")
        alerts.append("CASH_IMPACT_UNCONFIRMED")
    if manual_override_used:
        score -= 4.0
        reasons.append("manual override was used in cash closure flow")
        alerts.append("MANUAL_OVERRIDE_USED")

    operator_posture = str(ctx.get("operator", {}).get("posture", "UNINITIALIZED"))
    release_posture = str(ctx.get("release", {}).get("posture", "UNINITIALIZED"))
    safety_posture = str(ctx.get("safety", {}).get("posture", "UNINITIALIZED"))
    recovery_posture = str(ctx.get("recovery", {}).get("posture", "UNINITIALIZED"))
    settlement_finalization_posture = str(ctx.get("settlement_finalization", {}).get("posture", "UNINITIALIZED"))

    if policy.get("require_operator_clear", True) and operator_posture not in {"READY", "HEALTHY", "OPERATIONAL", "UNINITIALIZED"}:
        score -= 8.0
        reasons.append("operator posture is not clear")
        alerts.append("OPERATOR_NOT_CLEAR")
    if policy.get("require_release_clear", True) and release_posture not in {"DEPLOYED", "APPROVED", "UNINITIALIZED"}:
        score -= 8.0
        reasons.append("release posture is not clear")
        alerts.append("RELEASE_NOT_CLEAR")
    if policy.get("require_safety_clear", True) and safety_posture not in {"APPROVED", "READY", "UNINITIALIZED"}:
        score -= 10.0
        reasons.append("safety posture is not clear")
        alerts.append("SAFETY_NOT_CLEAR")
    if policy.get("require_recovery_clear", True) and recovery_posture not in {"RECOVERED", "READY", "UNINITIALIZED"}:
        score -= 10.0
        reasons.append("recovery posture is not clear")
        alerts.append("RECOVERY_NOT_CLEAR")
    if policy.get("require_settlement_finalization_clear", True) and settlement_finalization_posture not in {"CLEAR", "FINALIZATION_AUTHORIZED", "FINALIZATION_CONTROLLED", "UNINITIALIZED"}:
        score -= 12.0
        reasons.append("settlement finalization posture is not clear")
        alerts.append("SETTLEMENT_FINALIZATION_NOT_CLEAR")

    score = round(max(score, 0.0), 2)
    band = _band(score)
    posture = "CLEAR" if score >= float(policy.get("minimum_score", 96.0)) and not critical_cash_breaks else "REVIEW"
    operator_review_required = posture != "CLEAR" or manual_override_used or open_cash_breaks > 0
    run = {
        "run_id": f"cashclose-{int(datetime.now(timezone.utc).timestamp())}",
        "captured_at": _now_iso(),
        "score": score,
        "band": band,
        "posture": posture,
        "operator_review_required": operator_review_required,
        "metrics": metrics,
        "open_cash_breaks": open_cash_breaks,
        "critical_cash_breaks": critical_cash_breaks,
        "evidence_complete": evidence_complete,
        "cash_impact_confirmed": cash_impact_confirmed,
        "manual_override_used": manual_override_used,
        "reasons": reasons,
        "alerts": alerts,
    }
    _append(store, "runs", run, int(policy.get("retain_cycles", 180)))
    _append(store, "book", {
        "captured_at": run["captured_at"],
        "band": band,
        "score": score,
        "posture": posture,
    }, int(policy.get("retain_cycles", 180)))
    for alert in alerts:
        _append(store, "alerts", {"captured_at": run["captured_at"], "code": alert, "run_id": run["run_id"]}, int(policy.get("retain_cycles", 180)))
    store["latest_run"] = run
    store["last_context"] = ctx
    _save(email, store)
    return run


@router.get("/summary")
def summary(session=Depends(_require_user)):
    return _summary_for_email(session["email"])


@router.post("/evaluate")
def evaluate(payload: dict = Body(default={}), session=Depends(_require_user)):
    return {"ok": True, "run": _evaluate(session["email"], payload)}


@router.post("/policy")
def policy(payload: dict = Body(default={}), session=Depends(_require_user)):
    store = _load(session["email"])
    store["policy"] = {**dict(DEFAULT_POLICY), **(store.get("policy") or {}), **payload}
    _save(session["email"], store)
    return {"ok": True, "policy": store["policy"]}


@router.post("/bootstrap-demo")
def bootstrap_demo(session=Depends(_require_user)):
    payload = {
        "cash_match_score": 0.992,
        "ledger_alignment_score": 0.989,
        "bank_confirmation_score": 0.984,
        "closure_evidence_score": 0.981,
        "control_attestation_score": 0.987,
        "open_cash_breaks": 0,
        "critical_cash_breaks": 0,
        "evidence_complete": True,
        "cash_impact_confirmed": True,
        "manual_override_used": False,
    }
    return {"ok": True, "run": _evaluate(session["email"], payload)}
