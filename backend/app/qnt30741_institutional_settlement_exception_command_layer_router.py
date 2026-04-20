from fastapi import APIRouter, Body, Depends
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json

router = APIRouter(prefix="/api/institutional-settlement-exception-command-layer", tags=["institutional-settlement-exception-command-layer"])
PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
ENGINE_DIR = ARTIFACTS_DIR / "institutional_settlement_exception_command_layer"
DEFAULT_POLICY = {
    "retain_cycles": 180,
    "minimum_score": 96.0,
    "require_operator_clear": True,
    "require_release_clear": True,
    "require_safety_clear": True,
    "require_recovery_clear": True,
    "require_settlement_integrity_clear": True,
    "max_open_exceptions": 2,
    "max_critical_exceptions": 0,
    "minimum_triage_score": 0.97,
    "minimum_counterparty_response_score": 0.96,
    "minimum_remediation_readiness_score": 0.965,
    "minimum_escalation_coverage_score": 0.97,
    "minimum_cash_resolution_score": 0.965,
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


def _settlement():
    from backend.app import qnt30740_institutional_settlement_integrity_command_layer_router as settlement
    return settlement


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
        "institutional_settlement_exception_command_layer_status": {
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
        "settlement": (_settlement()._summary_for_email(email).get("institutional_settlement_integrity_command_layer_status") or {}),
    }


def _band(score: float) -> str:
    if score >= 98:
        return "EXCEPTION_CLEARED"
    if score >= 96:
        return "CONTROLLED_EXCEPTION"
    if score >= 93:
        return "EXCEPTION_WATCH"
    return "ESCALATE_EXCEPTION"


def _evaluate(email: str, payload: dict) -> dict:
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get("policy") or {})}
    ctx = _cross_system_context(email)
    metrics = {k: float(payload.get(k, 0.0) or 0.0) for k in [
        "triage_score", "counterparty_response_score", "remediation_readiness_score",
        "escalation_coverage_score", "cash_resolution_score"
    ]}
    open_exceptions = int(payload.get("open_exceptions", 0) or 0)
    critical_exceptions = int(payload.get("critical_exceptions", 0) or 0)
    evidence_complete = bool(payload.get("evidence_complete", False))
    manual_override_used = bool(payload.get("manual_override_used", False))

    score = 100.0
    reasons = []
    alerts = []
    penalties = {
        "triage_score": 110.0,
        "counterparty_response_score": 95.0,
        "remediation_readiness_score": 105.0,
        "escalation_coverage_score": 110.0,
        "cash_resolution_score": 100.0,
    }
    reason_map = {
        "triage_score": "settlement exception triage is below institutional threshold",
        "counterparty_response_score": "counterparty response quality is below policy",
        "remediation_readiness_score": "settlement remediation readiness is below institutional threshold",
        "escalation_coverage_score": "settlement escalation coverage is incomplete",
        "cash_resolution_score": "cash exception resolution quality is below policy",
    }
    alert_map = {
        "triage_score": "TRIAGE_WEAK",
        "counterparty_response_score": "COUNTERPARTY_RESPONSE_WEAK",
        "remediation_readiness_score": "REMEDIATION_NOT_READY",
        "escalation_coverage_score": "ESCALATION_COVERAGE_WEAK",
        "cash_resolution_score": "CASH_RESOLUTION_WEAK",
    }
    threshold_map = {
        "triage_score": "minimum_triage_score",
        "counterparty_response_score": "minimum_counterparty_response_score",
        "remediation_readiness_score": "minimum_remediation_readiness_score",
        "escalation_coverage_score": "minimum_escalation_coverage_score",
        "cash_resolution_score": "minimum_cash_resolution_score",
    }
    for key, value in metrics.items():
        threshold = float(policy.get(threshold_map[key], 0.96))
        if value < threshold:
            score -= round((threshold - value) * penalties[key], 2)
            reasons.append(reason_map[key])
            alerts.append(alert_map[key])

    if open_exceptions > int(policy.get("max_open_exceptions", 2)):
        score -= min((open_exceptions - int(policy.get("max_open_exceptions", 2))) * 5.0, 20.0)
        reasons.append("open settlement exceptions exceed policy")
        alerts.append("OPEN_SETTLEMENT_EXCEPTIONS")
    if critical_exceptions > int(policy.get("max_critical_exceptions", 0)):
        score -= min(critical_exceptions * 9.0, 27.0)
        reasons.append("critical settlement exceptions remain unresolved")
        alerts.append("CRITICAL_SETTLEMENT_EXCEPTIONS")
    if not evidence_complete:
        score -= 7.0
        reasons.append("settlement exception evidence is incomplete")
        alerts.append("EVIDENCE_INCOMPLETE")
    if manual_override_used:
        score -= 4.0
        reasons.append("manual override was used in exception command flow")
        alerts.append("MANUAL_OVERRIDE_USED")

    if policy.get("require_operator_clear") and ctx["operator"].get("posture") in {"INCIDENT", "LOCKED", "STOPPED"}:
        score -= 10.0
        alerts.append("OPERATOR_NOT_CLEAR")
    if policy.get("require_release_clear") and ctx["release"].get("posture") in {"BLOCKED", "ROLLED_BACK", "PENDING"}:
        score -= 10.0
        alerts.append("RELEASE_NOT_CLEAR")
    if policy.get("require_safety_clear") and ctx["safety"].get("posture") in {"BLOCKED", "KILL_SWITCH", "PAUSED"}:
        score -= 12.0
        alerts.append("SAFETY_NOT_CLEAR")
    if policy.get("require_recovery_clear") and ctx["recovery"].get("posture") in {"SAFE_MODE", "FAILED", "RECOVERING"}:
        score -= 12.0
        alerts.append("RECOVERY_NOT_CLEAR")
    if policy.get("require_settlement_integrity_clear") and ctx["settlement"].get("posture") in {"BLOCKED", "WATCH", "DO_NOT_SCALE"}:
        score -= 11.0
        alerts.append("SETTLEMENT_INTEGRITY_NOT_CLEAR")

    score = max(round(score, 2), 0.0)
    posture = "APPROVED" if score >= float(policy.get("minimum_score", 96.0)) and not alerts else ("WATCH" if score >= float(policy.get("minimum_score", 96.0)) - 3 else "BLOCKED")
    band = _band(score)
    operator_review_required = bool(score < 98 or len(alerts) > 0)

    run = {
        "captured_at": _now_iso(),
        "title": payload.get("title", "institutional settlement exception review"),
        "summary": payload.get("summary", "Evaluate whether Quantora can govern settlement exceptions institutionally after settlement integrity review."),
        "score": score,
        "posture": posture,
        "band": band,
        "operator_review_required": operator_review_required,
        "metrics": metrics,
        "open_exceptions": open_exceptions,
        "critical_exceptions": critical_exceptions,
        "evidence_complete": evidence_complete,
        "manual_override_used": manual_override_used,
        "reasons": reasons,
        "alerts": alerts,
    }
    book_row = {
        "captured_at": run["captured_at"],
        "posture": posture,
        "band": band,
        "score": score,
        "summary": run["summary"],
        "title": run["title"],
    }
    store["latest_run"] = run
    store["last_context"] = ctx
    _append(store, "runs", run, int(policy.get("retain_cycles", 180)))
    if alerts:
        _append(store, "alerts", {
            "captured_at": run["captured_at"],
            "posture": posture,
            "alerts": alerts,
            "title": run["title"],
            "score": score,
        }, int(policy.get("retain_cycles", 180)))
    _append(store, "book", book_row, int(policy.get("retain_cycles", 180)))
    _save(email, store)
    return {"ok": True, "run": run, "context": ctx, "policy": policy}


@router.get("/summary")
def summary(session=Depends(_require_user)):
    return _summary_for_email(session.get("email") or "demo@quantora.ai")


@router.post("/evaluate")
def evaluate(payload: dict = Body(default={}), session=Depends(_require_user)):
    return _evaluate(session.get("email") or "demo@quantora.ai", payload or {})


@router.post("/policy")
def update_policy(payload: dict = Body(default={}), session=Depends(_require_user)):
    email = session.get("email") or "demo@quantora.ai"
    store = _load(email)
    store["policy"] = {**dict(DEFAULT_POLICY), **(store.get("policy") or {}), **(payload or {})}
    _save(email, store)
    return {"ok": True, "policy": store["policy"]}


@router.post("/bootstrap-demo")
def bootstrap_demo(session=Depends(_require_user)):
    payload = {
        "title": "institutional settlement exception bootstrap",
        "summary": "Bootstrap a representative settlement exception command review after settlement integrity clearance.",
        "triage_score": 0.989,
        "counterparty_response_score": 0.982,
        "remediation_readiness_score": 0.984,
        "escalation_coverage_score": 0.986,
        "cash_resolution_score": 0.983,
        "open_exceptions": 1,
        "critical_exceptions": 0,
        "evidence_complete": True,
        "manual_override_used": False,
    }
    return _evaluate(session.get("email") or "demo@quantora.ai", payload)
