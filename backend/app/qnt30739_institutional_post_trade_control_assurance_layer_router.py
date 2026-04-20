from fastapi import APIRouter, Body, Depends
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json

router = APIRouter(prefix="/api/institutional-post-trade-control-assurance-layer", tags=["institutional-post-trade-control-assurance-layer"])
PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
ENGINE_DIR = ARTIFACTS_DIR / "institutional_post_trade_control_assurance_layer"
DEFAULT_POLICY = {
    "retain_cycles": 180,
    "minimum_score": 97.0,
    "require_operator_clear": True,
    "require_release_clear": True,
    "require_safety_clear": True,
    "require_recovery_clear": True,
    "require_fund_admin_clear": True,
    "require_execution_quality_clear": True,
    "max_open_exceptions": 0,
    "max_reconciliation_breaks": 0,
    "minimum_trade_capture_score": 0.98,
    "minimum_allocation_match_score": 0.97,
    "minimum_control_evidence_score": 0.97,
    "minimum_post_trade_timeliness_score": 0.97,
    "minimum_exception_readiness_score": 0.96,
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


def _fund_admin():
    from backend.app import qnt30705_fund_admin_control_center_router as fund_admin
    return fund_admin


def _execution_quality():
    from backend.app import qnt30738_institutional_execution_quality_assurance_layer_router as execution_quality
    return execution_quality


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
        "institutional_post_trade_control_assurance_layer_status": {
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
        "fund_admin": (_fund_admin()._summary_for_email(email).get("fund_admin_control_center_status") or {}),
        "execution_quality": (_execution_quality()._summary_for_email(email).get("institutional_execution_quality_assurance_layer_status") or {}),
    }


def _band(score: float) -> str:
    if score >= 99:
        return "POST_TRADE_CLEAR"
    if score >= 97:
        return "CONTROLLED_ASSURANCE"
    if score >= 94:
        return "LIMITED_ASSURANCE"
    return "DO_NOT_SCALE"


def _evaluate(email: str, payload: dict) -> dict:
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get("policy") or {})}
    ctx = _cross_system_context(email)
    metrics = {k: float(payload.get(k, 0.0) or 0.0) for k in [
        "trade_capture_score", "allocation_match_score", "control_evidence_score",
        "post_trade_timeliness_score", "exception_readiness_score"
    ]}
    reconciliation_breaks = int(payload.get("reconciliation_breaks", 0) or 0)
    open_exceptions = int(payload.get("open_exceptions", 0) or 0)
    controls_attested = bool(payload.get("controls_attested", False))
    evidence_published = bool(payload.get("evidence_published", False))

    score = 100.0
    reasons = []
    alerts = []
    penalties = {
        "trade_capture_score": 120.0,
        "allocation_match_score": 115.0,
        "control_evidence_score": 115.0,
        "post_trade_timeliness_score": 110.0,
        "exception_readiness_score": 95.0,
    }
    reason_map = {
        "trade_capture_score": "trade capture is below institutional threshold",
        "allocation_match_score": "allocation matching is below institutional threshold",
        "control_evidence_score": "control evidence is below institutional threshold",
        "post_trade_timeliness_score": "post-trade timeliness is below policy",
        "exception_readiness_score": "exception readiness is below institutional threshold",
    }
    alert_map = {
        "trade_capture_score": "TRADE_CAPTURE_WEAK",
        "allocation_match_score": "ALLOCATION_MATCH_WEAK",
        "control_evidence_score": "CONTROL_EVIDENCE_WEAK",
        "post_trade_timeliness_score": "POST_TRADE_TIMELINESS_WEAK",
        "exception_readiness_score": "EXCEPTION_READINESS_WEAK",
    }
    for key, value in metrics.items():
        threshold = float(policy.get('minimum_' + key, 0.97))
        if value < threshold:
            score -= round((threshold - value) * penalties[key], 2)
            reasons.append(reason_map[key])
            alerts.append(alert_map[key])

    if reconciliation_breaks > int(policy.get("max_reconciliation_breaks", 0)):
        score -= min(reconciliation_breaks * 7.0, 21.0)
        reasons.append("reconciliation breaks remain before clearance")
        alerts.append("RECONCILIATION_BREAKS_REMAIN")
    if open_exceptions > int(policy.get("max_open_exceptions", 0)):
        score -= min(open_exceptions * 6.0, 18.0)
        reasons.append("open post-trade exceptions remain")
        alerts.append("OPEN_POST_TRADE_EXCEPTIONS")
    if not controls_attested:
        score -= 10.0
        reasons.append("control attestation not complete")
        alerts.append("CONTROLS_NOT_ATTESTED")
    if not evidence_published:
        score -= 8.0
        reasons.append("post-trade evidence has not been published")
        alerts.append("EVIDENCE_NOT_PUBLISHED")

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
    if policy.get("require_fund_admin_clear") and ctx["fund_admin"].get("posture") in {"BLOCKED", "REVIEW", "RECONCILE"}:
        score -= 10.0
        alerts.append("FUND_ADMIN_NOT_CLEAR")
    if policy.get("require_execution_quality_clear") and ctx["execution_quality"].get("posture") in {"BLOCKED", "WATCH", "DO_NOT_EXECUTE"}:
        score -= 10.0
        alerts.append("EXECUTION_QUALITY_NOT_CLEAR")

    score = max(round(score, 2), 0.0)
    posture = "APPROVED" if score >= float(policy.get("minimum_score", 97.0)) and not alerts else ("WATCH" if score >= float(policy.get("minimum_score", 97.0)) - 3 else "BLOCKED")
    band = _band(score)
    operator_review_required = bool(score < 99 or len(alerts) > 0)
    run = {
        "captured_at": _now_iso(),
        "title": payload.get("title", "institutional post-trade control assurance review"),
        "summary": payload.get("summary", "Evaluate whether Quantora can clear institutional post-trade controls after execution quality assurance."),
        "score": score,
        "posture": posture,
        "band": band,
        "operator_review_required": operator_review_required,
        "metrics": metrics,
        "reconciliation_breaks": reconciliation_breaks,
        "open_exceptions": open_exceptions,
        "controls_attested": controls_attested,
        "evidence_published": evidence_published,
        "reasons": reasons,
        "alerts": alerts,
        "context_snapshot": ctx,
    }
    _append(store, "runs", run, int(policy.get("retain_cycles", 180) or 180))
    _append(store, "book", {
        "captured_at": run["captured_at"], "band": band, "score": score, "posture": posture
    }, int(policy.get("retain_cycles", 180) or 180))
    if alerts:
        _append(store, "alerts", {
            "captured_at": run["captured_at"], "alerts": alerts, "posture": posture
        }, int(policy.get("retain_cycles", 180) or 180))
    store["latest_run"] = run
    store["last_context"] = ctx
    store["policy"] = policy
    _save(email, store)
    return run


@router.get("/summary")
def summary(user=Depends(_require_user)):
    return _summary_for_email(user["email"])


@router.post("/evaluate")
def evaluate(payload: dict = Body(default={}), user=Depends(_require_user)):
    return _evaluate(user["email"], payload)


@router.post("/policy")
def policy(payload: dict = Body(default={}), user=Depends(_require_user)):
    store = _load(user["email"])
    store["policy"] = {**dict(DEFAULT_POLICY), **(store.get("policy") or {}), **(payload or {})}
    _save(user["email"], store)
    return {"ok": True, "policy": store["policy"]}


@router.post("/bootstrap-demo")
def bootstrap_demo(user=Depends(_require_user)):
    return _evaluate(user["email"], {
        "title": "institutional post-trade control assurance review",
        "summary": "Evaluate whether Quantora can clear institutional post-trade controls after execution quality assurance.",
        "trade_capture_score": 0.989,
        "allocation_match_score": 0.981,
        "control_evidence_score": 0.979,
        "post_trade_timeliness_score": 0.978,
        "exception_readiness_score": 0.972,
        "reconciliation_breaks": 0,
        "open_exceptions": 0,
        "controls_attested": True,
        "evidence_published": True,
    })
