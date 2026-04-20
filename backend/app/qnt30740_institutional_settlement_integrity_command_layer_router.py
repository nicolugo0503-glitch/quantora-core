from fastapi import APIRouter, Body, Depends
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json

router = APIRouter(prefix="/api/institutional-settlement-integrity-command-layer", tags=["institutional-settlement-integrity-command-layer"])
PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
ENGINE_DIR = ARTIFACTS_DIR / "institutional_settlement_integrity_command_layer"
DEFAULT_POLICY = {
    "retain_cycles": 180,
    "minimum_score": 97.0,
    "require_operator_clear": True,
    "require_release_clear": True,
    "require_safety_clear": True,
    "require_recovery_clear": True,
    "require_fund_admin_clear": True,
    "require_post_trade_clear": True,
    "max_open_breaks": 0,
    "max_unsettled_trades": 1,
    "minimum_settlement_match_score": 0.985,
    "minimum_cash_match_score": 0.98,
    "minimum_counterparty_ack_score": 0.98,
    "minimum_timeliness_score": 0.975,
    "minimum_exception_readiness_score": 0.97,
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


def _post_trade():
    from backend.app import qnt30739_institutional_post_trade_control_assurance_layer_router as post_trade
    return post_trade


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
        "institutional_settlement_integrity_command_layer_status": {
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
        "post_trade": (_post_trade()._summary_for_email(email).get("institutional_post_trade_control_assurance_layer_status") or {}),
    }


def _band(score: float) -> str:
    if score >= 99:
        return "SETTLEMENT_CLEAR"
    if score >= 97:
        return "CONTROLLED_SETTLEMENT"
    if score >= 94:
        return "SETTLEMENT_WATCH"
    return "SETTLEMENT_HOLD"


def _evaluate(email: str, payload: dict) -> dict:
    store = _load(email)
    policy = {**dict(DEFAULT_POLICY), **(store.get("policy") or {})}
    ctx = _cross_system_context(email)
    metrics = {k: float(payload.get(k, 0.0) or 0.0) for k in [
        "settlement_match_score", "cash_match_score", "counterparty_ack_score",
        "timeliness_score", "exception_readiness_score"
    ]}
    open_breaks = int(payload.get("open_breaks", 0) or 0)
    unsettled_trades = int(payload.get("unsettled_trades", 0) or 0)
    failover_ready = bool(payload.get("failover_ready", False))
    evidence_published = bool(payload.get("evidence_published", False))

    score = 100.0
    reasons = []
    alerts = []
    penalties = {
        "settlement_match_score": 140.0,
        "cash_match_score": 120.0,
        "counterparty_ack_score": 110.0,
        "timeliness_score": 110.0,
        "exception_readiness_score": 95.0,
    }
    reason_map = {
        "settlement_match_score": "settlement matching is below institutional threshold",
        "cash_match_score": "cash matching is below institutional threshold",
        "counterparty_ack_score": "counterparty acknowledgement is below institutional threshold",
        "timeliness_score": "settlement timeliness is below policy",
        "exception_readiness_score": "settlement exception readiness is below institutional threshold",
    }
    alert_map = {
        "settlement_match_score": "SETTLEMENT_MATCH_WEAK",
        "cash_match_score": "CASH_MATCH_WEAK",
        "counterparty_ack_score": "COUNTERPARTY_ACK_WEAK",
        "timeliness_score": "SETTLEMENT_TIMELINESS_WEAK",
        "exception_readiness_score": "SETTLEMENT_EXCEPTION_READINESS_WEAK",
    }
    threshold_map = {
        "settlement_match_score": "minimum_settlement_match_score",
        "cash_match_score": "minimum_cash_match_score",
        "counterparty_ack_score": "minimum_counterparty_ack_score",
        "timeliness_score": "minimum_timeliness_score",
        "exception_readiness_score": "minimum_exception_readiness_score",
    }
    for key, value in metrics.items():
        threshold = float(policy.get(threshold_map[key], 0.97))
        if value < threshold:
            score -= round((threshold - value) * penalties[key], 2)
            reasons.append(reason_map[key])
            alerts.append(alert_map[key])

    if open_breaks > int(policy.get("max_open_breaks", 0)):
        score -= min(open_breaks * 7.0, 21.0)
        reasons.append("open settlement breaks remain before clearance")
        alerts.append("OPEN_SETTLEMENT_BREAKS")
    if unsettled_trades > int(policy.get("max_unsettled_trades", 1)):
        score -= min((unsettled_trades - int(policy.get("max_unsettled_trades", 1))) * 4.0, 16.0)
        reasons.append("unsettled trade count exceeds settlement policy")
        alerts.append("UNSETTLED_TRADE_PRESSURE")
    if not failover_ready:
        score -= 8.0
        reasons.append("settlement failover readiness is incomplete")
        alerts.append("FAILOVER_NOT_READY")
    if not evidence_published:
        score -= 6.0
        reasons.append("settlement evidence has not been published")
        alerts.append("SETTLEMENT_EVIDENCE_NOT_PUBLISHED")

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
    if policy.get("require_post_trade_clear") and ctx["post_trade"].get("posture") in {"BLOCKED", "WATCH", "DO_NOT_SCALE"}:
        score -= 10.0
        alerts.append("POST_TRADE_NOT_CLEAR")

    score = max(round(score, 2), 0.0)
    posture = "APPROVED" if score >= float(policy.get("minimum_score", 97.0)) and not alerts else ("WATCH" if score >= float(policy.get("minimum_score", 97.0)) - 3 else "BLOCKED")
    band = _band(score)
    operator_review_required = bool(score < 99 or len(alerts) > 0)
    run = {
        "captured_at": _now_iso(),
        "title": payload.get("title", "institutional settlement integrity review"),
        "summary": payload.get("summary", "Evaluate whether Quantora can clear institutional settlement integrity after post-trade assurance."),
        "score": score,
        "posture": posture,
        "band": band,
        "operator_review_required": operator_review_required,
        "metrics": metrics,
        "open_breaks": open_breaks,
        "unsettled_trades": unsettled_trades,
        "failover_ready": failover_ready,
        "evidence_published": evidence_published,
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
        "title": "institutional settlement integrity bootstrap",
        "summary": "Bootstrap a representative settlement integrity review after post-trade control assurance.",
        "settlement_match_score": 0.994,
        "cash_match_score": 0.992,
        "counterparty_ack_score": 0.991,
        "timeliness_score": 0.989,
        "exception_readiness_score": 0.986,
        "open_breaks": 0,
        "unsettled_trades": 1,
        "failover_ready": True,
        "evidence_published": True,
    }
    return _evaluate(session.get("email") or "demo@quantora.ai", payload)
