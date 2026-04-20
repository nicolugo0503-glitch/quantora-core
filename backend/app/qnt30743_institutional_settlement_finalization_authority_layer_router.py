from fastapi import APIRouter, Body, Depends
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json

router = APIRouter(prefix="/api/institutional-settlement-finalization-authority-layer", tags=["institutional-settlement-finalization-authority-layer"])
PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
ENGINE_DIR = ARTIFACTS_DIR / "institutional_settlement_finalization_authority_layer"
DEFAULT_POLICY = {
    "retain_cycles": 180,
    "minimum_score": 97.0,
    "require_operator_clear": True,
    "require_release_clear": True,
    "require_safety_clear": True,
    "require_recovery_clear": True,
    "require_settlement_integrity_clear": True,
    "require_settlement_recovery_clear": True,
    "max_open_finalization_items": 1,
    "max_critical_finalization_items": 0,
    "minimum_final_match_score": 0.98,
    "minimum_authority_coverage_score": 0.98,
    "minimum_settlement_evidence_score": 0.975,
    "minimum_counterparty_signoff_score": 0.97,
    "minimum_final_control_score": 0.98,
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


def _settlement_integrity():
    from backend.app import qnt30740_institutional_settlement_integrity_command_layer_router as settlement_integrity
    return settlement_integrity


def _settlement_recovery():
    from backend.app import qnt30742_institutional_settlement_recovery_resolution_layer_router as settlement_recovery
    return settlement_recovery


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
        "institutional_settlement_finalization_authority_layer_status": {
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
        "settlement_integrity": (_settlement_integrity()._summary_for_email(email).get("institutional_settlement_integrity_command_layer_status") or {}),
        "settlement_recovery": (_settlement_recovery()._summary_for_email(email).get("institutional_settlement_recovery_resolution_layer_status") or {}),
    }


def _band(score: float) -> str:
    if score >= 98.5:
        return "FINALIZATION_AUTHORIZED"
    if score >= 97.0:
        return "FINALIZATION_CONTROLLED"
    if score >= 94.0:
        return "FINALIZATION_WATCH"
    return "FINALIZATION_BLOCKED"


def _evaluate(email: str, payload: dict) -> dict:
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get("policy") or {})}
    ctx = _cross_system_context(email)
    metrics = {k: float(payload.get(k, 0.0) or 0.0) for k in [
        "final_match_score", "authority_coverage_score", "settlement_evidence_score",
        "counterparty_signoff_score", "final_control_score"
    ]}
    open_finalization_items = int(payload.get("open_finalization_items", 0) or 0)
    critical_finalization_items = int(payload.get("critical_finalization_items", 0) or 0)
    evidence_complete = bool(payload.get("evidence_complete", False))
    capital_impact_confirmed = bool(payload.get("capital_impact_confirmed", False))
    manual_override_used = bool(payload.get("manual_override_used", False))

    score = 100.0
    reasons = []
    alerts = []
    penalties = {
        "final_match_score": 120.0,
        "authority_coverage_score": 110.0,
        "settlement_evidence_score": 95.0,
        "counterparty_signoff_score": 90.0,
        "final_control_score": 115.0,
    }
    reason_map = {
        "final_match_score": "final settlement match quality is below institutional threshold",
        "authority_coverage_score": "finalization authority coverage is incomplete",
        "settlement_evidence_score": "settlement evidence quality is below policy",
        "counterparty_signoff_score": "counterparty signoff quality is below policy",
        "final_control_score": "final control posture is incomplete",
    }
    alert_map = {
        "final_match_score": "FINAL_MATCH_WEAK",
        "authority_coverage_score": "AUTHORITY_COVERAGE_WEAK",
        "settlement_evidence_score": "SETTLEMENT_EVIDENCE_WEAK",
        "counterparty_signoff_score": "COUNTERPARTY_SIGNOFF_WEAK",
        "final_control_score": "FINAL_CONTROL_WEAK",
    }
    threshold_map = {
        "final_match_score": "minimum_final_match_score",
        "authority_coverage_score": "minimum_authority_coverage_score",
        "settlement_evidence_score": "minimum_settlement_evidence_score",
        "counterparty_signoff_score": "minimum_counterparty_signoff_score",
        "final_control_score": "minimum_final_control_score",
    }
    for key, value in metrics.items():
        threshold = float(policy.get(threshold_map[key], 0.97))
        if value < threshold:
            score -= round((threshold - value) * penalties[key], 2)
            reasons.append(reason_map[key])
            alerts.append(alert_map[key])

    if open_finalization_items > int(policy.get("max_open_finalization_items", 1)):
        score -= min((open_finalization_items - int(policy.get("max_open_finalization_items", 1))) * 5.0, 20.0)
        reasons.append("open finalization items exceed policy")
        alerts.append("OPEN_FINALIZATION_ITEMS")
    if critical_finalization_items > int(policy.get("max_critical_finalization_items", 0)):
        score -= min(critical_finalization_items * 10.0, 30.0)
        reasons.append("critical finalization items remain unresolved")
        alerts.append("CRITICAL_FINALIZATION_ITEMS")
    if not evidence_complete:
        score -= 7.0
        reasons.append("finalization evidence is incomplete")
        alerts.append("EVIDENCE_INCOMPLETE")
    if not capital_impact_confirmed:
        score -= 6.0
        reasons.append("capital impact is not fully confirmed")
        alerts.append("CAPITAL_IMPACT_UNCONFIRMED")
    if manual_override_used:
        score -= 4.0
        reasons.append("manual override was used in finalization flow")
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
    if policy.get("require_settlement_integrity_clear") and ctx["settlement_integrity"].get("posture") in {"ESCALATED", "BLOCKED", "UNINITIALIZED"}:
        score -= 14.0
        alerts.append("SETTLEMENT_INTEGRITY_NOT_CLEAR")
    if policy.get("require_settlement_recovery_clear") and ctx["settlement_recovery"].get("posture") in {"RECOVERY_ESCALATE", "UNINITIALIZED"}:
        score -= 14.0
        alerts.append("SETTLEMENT_RECOVERY_NOT_CLEAR")

    score = max(0.0, round(score, 2))
    band = _band(score)
    operator_review_required = band in {"FINALIZATION_WATCH", "FINALIZATION_BLOCKED"} or manual_override_used
    posture = "AUTHORIZED" if band == "FINALIZATION_AUTHORIZED" else ("CONTROLLED" if band == "FINALIZATION_CONTROLLED" else ("WATCH" if band == "FINALIZATION_WATCH" else "BLOCKED"))

    run = {
        "run_id": f"final_{int(datetime.now(timezone.utc).timestamp())}",
        "captured_at": _now_iso(),
        "score": score,
        "band": band,
        "posture": posture,
        "reasons": reasons,
        "alerts": alerts,
        "operator_review_required": operator_review_required,
        "metrics": metrics,
        "open_finalization_items": open_finalization_items,
        "critical_finalization_items": critical_finalization_items,
        "evidence_complete": evidence_complete,
        "capital_impact_confirmed": capital_impact_confirmed,
        "manual_override_used": manual_override_used,
    }
    _append(store, "runs", run, int(policy.get("retain_cycles", 180)))
    if alerts:
        _append(store, "alerts", {"captured_at": _now_iso(), "alerts": alerts, "score": score, "band": band}, int(policy.get("retain_cycles", 180)))
    _append(store, "book", {"captured_at": _now_iso(), "band": band, "posture": posture, "score": score}, int(policy.get("retain_cycles", 180)))
    store["latest_run"] = run
    store["last_context"] = ctx
    store["policy"] = policy
    _save(email, store)
    return {"ok": True, "run": run, "summary": _summary_for_email(email)}


@router.get('/summary')
def summary(user=Depends(_require_user)):
    return _summary_for_email(user['email'])


@router.post('/evaluate')
def evaluate(payload: dict = Body(default={}), user=Depends(_require_user)):
    return _evaluate(user['email'], payload or {})


@router.post('/policy')
def policy(payload: dict = Body(default={}), user=Depends(_require_user)):
    store = _load(user['email'])
    store['policy'] = {**dict(DEFAULT_POLICY), **(store.get('policy') or {}), **(payload or {})}
    _save(user['email'], store)
    return {"ok": True, "policy": store['policy']}


@router.post('/bootstrap-demo')
def bootstrap_demo(user=Depends(_require_user)):
    payload = {
        "final_match_score": 0.991,
        "authority_coverage_score": 0.989,
        "settlement_evidence_score": 0.982,
        "counterparty_signoff_score": 0.978,
        "final_control_score": 0.986,
        "open_finalization_items": 0,
        "critical_finalization_items": 0,
        "evidence_complete": True,
        "capital_impact_confirmed": True,
        "manual_override_used": False,
    }
    return _evaluate(user['email'], payload)
