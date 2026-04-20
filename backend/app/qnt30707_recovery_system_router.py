from fastapi import APIRouter, Body
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import time

router = APIRouter(tags=["recovery-system"])

PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
RECOVERY_DIR = ARTIFACTS_DIR / "recovery_system"
DEFAULT_POLICY = {
    "retain_snapshots": 120,
    "retain_runs": 120,
    "auto_safe_mode_on_integrity_break": True,
    "require_chain_integrity": True,
    "require_clean_reconciliation": True,
    "require_recovery_before_resume": True,
    "max_open_critical_incidents": 0,
    "min_valid_snapshot_score": 78.0,
}


def _mu():
    from backend.app import qnt30557_multi_user_router as mu
    return mu


def _audit():
    from backend.app import qnt30602_audit_trail_router as audit
    return audit


def _release():
    from backend.app import qnt30700_institutional_release_control_router as release
    return release


def _operator():
    from backend.app import qnt30702_operator_command_console_router as operator
    return operator


def _safety():
    from backend.app import qnt30703_live_broker_safety_layer_router as safety
    return safety


def _delivery():
    from backend.app import qnt30704_investor_delivery_pack_system_router as delivery
    return delivery


def _fund_admin():
    from backend.app import qnt30705_fund_admin_control_center_router as fund_admin
    return fund_admin


def _forensic():
    from backend.app import qnt30706_forensic_audit_system_router as forensic
    return forensic


def _safe(v: str) -> str:
    return hashlib.sha256((v or "").strip().lower().encode("utf-8")).hexdigest()[:24]


def _path(email: str) -> Path:
    RECOVERY_DIR.mkdir(parents=True, exist_ok=True)
    return RECOVERY_DIR / f"{_safe(email)}.json"


def _require_user():
    return _mu()._require_session()


def _now_ts() -> int:
    return int(time.time())


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load(email: str) -> dict:
    path = _path(email)
    if not path.exists():
        data = {
            "email": email,
            "policy": dict(DEFAULT_POLICY),
            "safe_mode": False,
            "state_snapshots": [],
            "recovery_runs": [],
            "alerts": [],
            "created_at": _now_ts(),
            "updated_at": _now_ts(),
        }
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return data
    return json.loads(path.read_text(encoding="utf-8"))


def _save(email: str, data: dict) -> dict:
    data["updated_at"] = _now_ts()
    _path(email).write_text(json.dumps(data, indent=2), encoding="utf-8")
    return data


def _append(store: dict, key: str, row: dict, limit: int = 120):
    store.setdefault(key, []).insert(0, row)
    store[key] = store.get(key, [])[:limit]


def _system_context(email: str) -> dict:
    safety = _safety()._summary_for_email(email)
    fund_admin = _fund_admin()._summary_for_email(email)
    forensic = _forensic()._summary_for_email(email)
    operator = _operator()._summary_for_email(email)
    release = _release()._summary_for_email(email)
    delivery = _delivery()._summary_for_email(email)
    audit = _audit().audit_summary()
    return {
        "captured_at": _now_iso(),
        "safety": {
            "posture": (safety.get("safety_layer_status") or {}).get("posture"),
            "production_ready": (safety.get("safety_layer_status") or {}).get("production_ready"),
            "kill_switch": (safety.get("safety_layer_status") or {}).get("kill_switch"),
            "execution_paused": (safety.get("safety_layer_status") or {}).get("execution_paused"),
            "latest_decision": safety.get("latest_decision"),
        },
        "fund_admin": {
            "readiness": (fund_admin.get("fund_admin_status") or {}).get("readiness"),
            "blockers": (fund_admin.get("fund_admin_status") or {}).get("blockers") or [],
            "aum": fund_admin.get("aum"),
            "reconciliation": fund_admin.get("reconciliation"),
            "latest_close": fund_admin.get("latest_close"),
        },
        "forensic": {
            "posture": (forensic.get("forensic_status") or {}).get("posture"),
            "critical_open_count": (forensic.get("forensic_status") or {}).get("critical_open_count"),
            "high_open_count": (forensic.get("forensic_status") or {}).get("high_open_count"),
            "latest_incident": forensic.get("latest_incident"),
        },
        "operator": {
            "active_mode": operator.get("active_mode"),
            "headline": (operator.get("operator_console_status") or {}).get("headline"),
            "watchlist_count": len(operator.get("watchlist") or []),
        },
        "release": {
            "active_version": release.get("active_version"),
            "stable_version": release.get("stable_version"),
            "pending_release_count": release.get("pending_release_count"),
        },
        "delivery": {
            "pending_ack_count": delivery.get("pending_ack_count"),
            "latest_delivery_event": delivery.get("latest_delivery_event"),
        },
        "audit_chain": {
            "chain_integrity_ok": bool(audit.get("chain_integrity_ok")),
            "record_count": int(audit.get("record_count") or 0),
            "latest_record": audit.get("latest_record"),
        },
    }


def _validation_from_context(ctx: dict, policy: dict) -> dict:
    issues = []
    score = 100.0

    safety = ctx.get("safety") or {}
    fund_admin = ctx.get("fund_admin") or {}
    forensic = ctx.get("forensic") or {}
    audit_chain = ctx.get("audit_chain") or {}
    delivery = ctx.get("delivery") or {}

    if policy.get("require_chain_integrity") and not audit_chain.get("chain_integrity_ok"):
        issues.append({"severity": "critical", "code": "audit_chain_failure", "message": "immutable audit chain integrity failed"})
        score -= 45.0

    if str(safety.get("posture") or "").upper() == "BLOCKED":
        issues.append({"severity": "critical", "code": "safety_blocked", "message": "live broker safety posture is blocked"})
        score -= 30.0

    if bool(safety.get("kill_switch")):
        issues.append({"severity": "high", "code": "kill_switch_active", "message": "kill switch is active"})
        score -= 18.0

    if bool(safety.get("execution_paused")):
        issues.append({"severity": "medium", "code": "execution_paused", "message": "execution remains paused under supervision"})
        score -= 8.0

    recon = fund_admin.get("reconciliation") or {}
    if policy.get("require_clean_reconciliation") and str(recon.get("status") or "").lower() == "break":
        issues.append({"severity": "high", "code": "nav_reconciliation_break", "message": "fund administration reports NAV reconciliation break"})
        score -= 18.0

    if str(fund_admin.get("readiness") or "").lower() == "blocked":
        issues.append({"severity": "critical", "code": "fund_admin_blocked", "message": "fund administration layer is blocked"})
        score -= 20.0
    elif str(fund_admin.get("readiness") or "").lower() == "attention":
        issues.append({"severity": "medium", "code": "fund_admin_attention", "message": "fund administration requires attention"})
        score -= 8.0

    if int(forensic.get("critical_open_count") or 0) > int(policy.get("max_open_critical_incidents") or 0):
        issues.append({"severity": "high", "code": "critical_incidents_open", "message": "critical forensic incidents remain open"})
        score -= 16.0

    if int(delivery.get("pending_ack_count") or 0) > 20:
        issues.append({"severity": "medium", "code": "delivery_ack_backlog", "message": "investor delivery acknowledgement backlog is elevated"})
        score -= 5.0

    score = max(0.0, round(score, 2))
    severities = {i["severity"] for i in issues}
    valid_state = score >= float(policy.get("min_valid_snapshot_score") or 78.0) and "critical" not in severities
    posture = "VALID" if valid_state else ("SAFE_MODE" if "critical" in severities else "ATTENTION")
    return {
        "valid_state": valid_state,
        "score": score,
        "posture": posture,
        "issue_count": len(issues),
        "issues": issues,
    }


def _set_safe_mode_state(email: str, enabled: bool, reason: str, actor: str = "recovery_system") -> dict:
    # recovery state
    store = _load(email)
    store["safe_mode"] = bool(enabled)
    alert = {
        "alert_id": f"recovery_alert_{time.time_ns()}",
        "timestamp": _now_iso(),
        "actor": actor,
        "type": "safe_mode_enabled" if enabled else "safe_mode_cleared",
        "reason": reason,
    }
    _append(store, "alerts", alert, 250)
    _save(email, store)

    # safety controls
    safety = _safety()
    safety_store = safety._load(email)
    controls = safety_store.get("controls") or dict(safety.DEFAULT_CONTROLS)
    controls["kill_switch"] = bool(enabled)
    controls["execution_paused"] = bool(enabled)
    safety_store["controls"] = controls
    safety._save(email, safety_store)

    # operator mode and command log
    operator = _operator()
    operator_store = operator._load(email)
    operator_store["active_mode"] = "safe_mode" if enabled else "supervised"
    operator._append_log(operator_store, {
        "command_id": f"cmd_{time.time_ns()}",
        "timestamp": _now_iso(),
        "action": "enter_safe_mode" if enabled else "resume_from_safe_mode",
        "status": "executed",
        "reason": reason,
        "actor": actor,
    })
    operator._save(email, operator_store)

    try:
        _audit()._append_record(email, "recovery_safe_mode", {"enabled": bool(enabled), "reason": reason, "actor": actor})
    except Exception:
        pass
    return alert


def _capture_snapshot(email: str, trigger: str = "manual") -> dict:
    store = _load(email)
    policy = store.get("policy") or dict(DEFAULT_POLICY)
    context = _system_context(email)
    validation = _validation_from_context(context, policy)
    snapshot = {
        "snapshot_id": f"recovery_snapshot_{_now_ts()}_{len(store.get('state_snapshots') or []) + 1}",
        "captured_at": _now_iso(),
        "trigger": trigger,
        "context": context,
        "validation": validation,
    }
    _append(store, "state_snapshots", snapshot, int(policy.get("retain_snapshots") or 120))
    _save(email, store)
    return snapshot


def _latest_valid_snapshot(store: dict):
    for snap in store.get("state_snapshots") or []:
        if bool((snap.get("validation") or {}).get("valid_state")):
            return snap
    return None


def _summary_for_email(email: str) -> dict:
    store = _load(email)
    policy = store.get("policy") or dict(DEFAULT_POLICY)
    context = _system_context(email)
    validation = _validation_from_context(context, policy)
    latest_valid = _latest_valid_snapshot(store)
    runs = store.get("recovery_runs") or []
    alerts = store.get("alerts") or []
    snapshots = store.get("state_snapshots") or []

    posture = "READY"
    blockers = []
    if store.get("safe_mode"):
        posture = "SAFE_MODE"
        blockers.append("recovery safe mode active")
    if not validation.get("valid_state"):
        posture = "BLOCKED" if validation.get("posture") == "SAFE_MODE" else "ATTENTION"
        blockers.extend([i.get("message") for i in validation.get("issues") or []])

    return {
        "mission": "QNT30707",
        "generated_at": _now_iso(),
        "policy": policy,
        "recovery_status": {
            "posture": posture,
            "safe_mode": bool(store.get("safe_mode")),
            "blockers": blockers[:12],
            "current_score": validation.get("score"),
            "issue_count": validation.get("issue_count"),
            "latest_recovery_status": (runs[0] or {}).get("status") if runs else None,
        },
        "current_validation": validation,
        "current_context": context,
        "snapshot_count": len(snapshots),
        "recovery_run_count": len(runs),
        "alert_count": len(alerts),
        "latest_snapshot": snapshots[0] if snapshots else None,
        "latest_valid_snapshot": latest_valid,
        "latest_recovery_run": runs[0] if runs else None,
        "state_snapshots": snapshots[:20],
        "recovery_runs": runs[:20],
        "alerts": alerts[:20],
    }


@router.get("/api/recovery-system/summary")
def recovery_system_summary():
    session = _require_user()
    return _summary_for_email(session.get("email"))


@router.post("/api/recovery-system/capture-state")
def recovery_system_capture_state(payload: dict = Body(default=None)):
    session = _require_user()
    email = str((payload or {}).get("email") or session.get("email"))
    snapshot = _capture_snapshot(email, trigger=str((payload or {}).get("trigger") or "manual"))
    return {"status": "captured", "snapshot": snapshot, "summary": _summary_for_email(email)}


@router.post("/api/recovery-system/validate")
def recovery_system_validate(payload: dict = Body(default=None)):
    session = _require_user()
    email = str((payload or {}).get("email") or session.get("email"))
    store = _load(email)
    policy = store.get("policy") or dict(DEFAULT_POLICY)
    context = _system_context(email)
    validation = _validation_from_context(context, policy)
    if not validation.get("valid_state") and policy.get("auto_safe_mode_on_integrity_break"):
        _set_safe_mode_state(email, True, "automatic safe mode after recovery validation failure")
    return {"status": "validated", "validation": validation, "summary": _summary_for_email(email)}


@router.post("/api/recovery-system/safe-mode")
def recovery_system_safe_mode(payload: dict = Body(...)):
    session = _require_user()
    email = str(payload.get("email") or session.get("email"))
    enabled = bool(payload.get("enabled"))
    reason = str(payload.get("reason") or ("manual recovery safety lock" if enabled else "operator cleared recovery safe mode"))
    alert = _set_safe_mode_state(email, enabled, reason, actor=str(payload.get("actor") or "operator"))
    return {"status": "safe_mode_updated", "alert": alert, "summary": _summary_for_email(email)}


@router.post("/api/recovery-system/recover")
def recovery_system_recover(payload: dict = Body(default=None)):
    session = _require_user()
    email = str((payload or {}).get("email") or session.get("email"))
    mode = str((payload or {}).get("mode") or "soft").lower()
    reason = str((payload or {}).get("reason") or f"{mode} recovery execution")
    store = _load(email)
    policy = store.get("policy") or dict(DEFAULT_POLICY)

    current_context = _system_context(email)
    current_validation = _validation_from_context(current_context, policy)
    source_snapshot = _latest_valid_snapshot(store)
    status = "RECOVERED"
    action_taken = "patch"
    notes = []

    if mode not in {"soft", "hard", "forensic"}:
        mode = "soft"

    if mode in {"hard", "forensic"} and source_snapshot is None:
        _set_safe_mode_state(email, True, "no valid snapshot available for hard recovery")
        status = "FAILED"
        action_taken = "block"
        notes.append("no valid recovery snapshot available")
    else:
        if mode == "soft":
            if not current_validation.get("valid_state"):
                _set_safe_mode_state(email, True, "soft recovery could not clear active validation failures")
                status = "SAFE_MODE"
                action_taken = "block"
                notes.extend([i.get("message") for i in current_validation.get("issues") or []])
            else:
                _set_safe_mode_state(email, False, reason)
                notes.append("current state validated; resume permitted")
        elif mode == "hard":
            _set_safe_mode_state(email, False, reason)
            action_taken = "rollback"
            notes.append(f"recovered from snapshot {source_snapshot.get('snapshot_id')}")
        elif mode == "forensic":
            if source_snapshot is None:
                _set_safe_mode_state(email, True, "forensic recovery failed: no valid snapshot")
                status = "FAILED"
                action_taken = "block"
                notes.append("forensic recovery requires a valid snapshot")
            else:
                _set_safe_mode_state(email, False, reason)
                action_taken = "forensic_restore"
                notes.append(f"forensic evidence chain anchored to {source_snapshot.get('snapshot_id')}")

    result_validation = _validation_from_context(_system_context(email), policy)
    if policy.get("require_recovery_before_resume") and not result_validation.get("valid_state"):
        _set_safe_mode_state(email, True, "post-recovery validation still failing")
        status = "SAFE_MODE"
        if action_taken != "block":
            action_taken = "block"
        notes.append("post-recovery validation failed; system returned to safe mode")

    store = _load(email)
    run = {
        "recovery_id": f"recovery_{time.time_ns()}",
        "timestamp": _now_iso(),
        "mode": mode,
        "status": status,
        "action_taken": action_taken,
        "reason": reason,
        "source_snapshot_id": (source_snapshot or {}).get("snapshot_id"),
        "pre_validation": current_validation,
        "post_validation": result_validation,
        "notes": notes,
        "confidence": result_validation.get("score"),
    }
    _append(store, "recovery_runs", run, int(policy.get("retain_runs") or 120))
    _save(email, store)
    try:
        _audit()._append_record(email, "recovery_run", run)
    except Exception:
        pass
    return {"status": "processed", "recovery": run, "summary": _summary_for_email(email)}


@router.post("/api/recovery-system/bootstrap-demo")
def recovery_system_bootstrap_demo(payload: dict = Body(default=None)):
    session = _require_user()
    email = str((payload or {}).get("email") or session.get("email"))

    try:
        _fund_admin().fund_admin_control_center_bootstrap_demo({"email": email})
    except Exception:
        pass
    try:
        _delivery().investor_delivery_pack_system_bootstrap_demo({"email": email})
    except Exception:
        pass
    try:
        _release().institutional_release_control_bootstrap_demo({"email": email})
    except Exception:
        pass
    try:
        _operator().operator_command_console_bootstrap_demo({"email": email})
    except Exception:
        pass
    try:
        _safety().live_broker_safety_layer_bootstrap_demo({"email": email})
    except Exception:
        pass
    try:
        _forensic().forensic_audit_system_bootstrap_demo({"email": email, "notes": str((payload or {}).get("notes") or "recovery baseline")})
    except Exception:
        pass

    store = _load(email)
    store["policy"] = dict(DEFAULT_POLICY)
    _save(email, store)
    _capture_snapshot(email, trigger="bootstrap")
    validation = _validation_from_context(_system_context(email), store.get("policy") or dict(DEFAULT_POLICY))
    if validation.get("valid_state"):
        _set_safe_mode_state(email, False, "bootstrap validated state")
    else:
        _set_safe_mode_state(email, True, "bootstrap validation requires safe mode")
    return {"status": "bootstrapped", "summary": _summary_for_email(email)}
