from fastapi import APIRouter, Body, HTTPException
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import time

router = APIRouter(tags=["operator-command-console"])

PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
CONSOLE_DIR = ARTIFACTS_DIR / "operator_command_console"
DEMO_EMAIL = "operator@quantora.test"

DEFAULT_PROFILE = {
    "operator_name": "Quantora Operator",
    "seat_mode": "supervised",
    "authority_tier": "institutional",
    "require_reason_for_resume": True,
    "default_watch_symbols": ["SPY", "QQQ", "AAPL"],
}


def _mu():
    from backend.app import qnt30557_multi_user_router as mu
    return mu


def _safety():
    from backend.app import qnt30703_live_broker_safety_layer_router as safety
    return safety


def _release():
    from backend.app import qnt30700_institutional_release_control_router as release
    return release


def _safe(v: str) -> str:
    return hashlib.sha256((v or "").strip().lower().encode("utf-8")).hexdigest()[:24]


def _path(email: str) -> Path:
    CONSOLE_DIR.mkdir(parents=True, exist_ok=True)
    return CONSOLE_DIR / f"{_safe(email)}.json"


def _require_user():
    return _mu()._require_session()


def _now_ts() -> int:
    return int(time.time())


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_json(path: Path, fallback):
    if not path.exists():
        return fallback
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return fallback


def _load(email: str) -> dict:
    path = _path(email)
    if not path.exists():
        data = {
            "email": email,
            "operator_profile": dict(DEFAULT_PROFILE),
            "watchlist": list(DEFAULT_PROFILE["default_watch_symbols"]),
            "active_mode": "supervised",
            "command_log": [],
            "incidents": [],
            "notes": [],
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


def _append_log(store: dict, row: dict, key: str = "command_log", limit: int = 250):
    store.setdefault(key, []).insert(0, row)
    store[key] = store.get(key, [])[:limit]


def _safety_summary(email: str) -> dict:
    try:
        return _safety()._summary_for_email(email)
    except Exception:
        return {
            "mission": "QNT30703",
            "generated_at": _now_iso(),
            "safety_layer_status": {
                "posture": "UNKNOWN",
                "production_ready": False,
                "kill_switch": False,
                "execution_paused": False,
                "operator_override_required": False,
                "risk_score": 0.0,
                "open_exposure_pct": 0.0,
                "daily_drawdown_pct": 0.0,
            },
            "controls": {},
            "policy": {},
        }


def _release_summary(email: str) -> dict:
    try:
        return _release()._summary_for_email(email)
    except Exception:
        return {
            "mission": "QNT30700",
            "generated_at": _now_iso(),
            "active_version": None,
            "stable_version": None,
            "pending_release_count": 0,
            "pending_releases": [],
            "recent_history": [],
            "release_control_status": {
                "governed": False,
                "can_deploy": False,
                "approval_backlog": 0,
            },
        }


def _status_from_inputs(safety_summary: dict, release_summary: dict) -> dict:
    posture = (safety_summary.get("safety_layer_status") or {}).get("posture") or "UNKNOWN"
    production_ready = bool((safety_summary.get("safety_layer_status") or {}).get("production_ready"))
    kill_switch = bool((safety_summary.get("safety_layer_status") or {}).get("kill_switch"))
    execution_paused = bool((safety_summary.get("safety_layer_status") or {}).get("execution_paused"))
    backlog = int(release_summary.get("release_control_status", {}).get("approval_backlog") or 0)
    pending = int(release_summary.get("pending_release_count") or 0)
    if kill_switch:
        color = "RED"
        headline = "emergency control active"
    elif execution_paused:
        color = "AMBER"
        headline = "execution paused under operator supervision"
    elif not production_ready:
        color = "RED"
        headline = "capital system not cleared for live execution"
    elif backlog > 0 or pending > 0:
        color = "AMBER"
        headline = "governance queue requires operator action"
    else:
        color = "GREEN"
        headline = "operator console clear for supervised capital flow"
    return {
        "color": color,
        "headline": headline,
        "posture": posture,
        "production_ready": production_ready,
        "kill_switch": kill_switch,
        "execution_paused": execution_paused,
        "approval_backlog": backlog,
        "pending_release_count": pending,
    }


def _summary_for_email(email: str) -> dict:
    store = _load(email)
    safety_summary = _safety_summary(email)
    release_summary = _release_summary(email)
    status = _status_from_inputs(safety_summary, release_summary)
    commands = store.get("command_log") or []
    incidents = store.get("incidents") or []
    return {
        "mission": "QNT30702",
        "generated_at": _now_iso(),
        "operator_profile": store.get("operator_profile") or dict(DEFAULT_PROFILE),
        "active_mode": store.get("active_mode") or "supervised",
        "watchlist": store.get("watchlist") or [],
        "operator_console_status": status,
        "safety": safety_summary,
        "release_control": release_summary,
        "recent_commands": commands[:20],
        "recent_incidents": incidents[:10],
        "command_metrics": {
            "total_commands": len(commands),
            "emergency_actions": len([c for c in commands if c.get("action") in {"emergency_stop", "rollback_release"}]),
            "release_actions": len([c for c in commands if c.get("action") in {"approve_release", "deploy_release", "rollback_release"}]),
        },
    }


def _set_safety_controls(email: str, **changes) -> dict:
    safety = _safety()
    store = safety._load(email)
    controls = store.get("controls") or dict(safety.DEFAULT_CONTROLS)
    for key, value in changes.items():
        if key in safety.DEFAULT_CONTROLS:
            controls[key] = bool(value)
    store["controls"] = controls
    safety._save(email, store)
    return controls


def _approve_release(email: str, release_id: str, operator: str, note: str = "operator command console approval") -> dict:
    rel = _release()
    store = rel._load(email)
    release = rel._find_pending(store, release_id)
    if not release:
        raise HTTPException(status_code=404, detail="release not found in pending queue")
    release["validation"] = rel._validate_release(store, release, email)
    release["approved"] = True
    release["approved_by"] = operator
    release["approved_at"] = rel._now_iso()
    release["status"] = rel._release_status(release)
    store.setdefault("approvals", []).insert(0, {
        "release_id": release_id,
        "approved_by": operator,
        "approved_at": release["approved_at"],
        "note": note,
    })
    rel._insert_history(store, release)
    rel._save(email, store)
    return release


def _deploy_release(email: str, release_id: str, operator: str) -> dict:
    rel = _release()
    store = rel._load(email)
    release = rel._find_pending(store, release_id)
    if not release:
        raise HTTPException(status_code=404, detail="release not found in pending queue")
    release["validation"] = rel._validate_release(store, release, email)
    rules = store.get("rules") or dict(rel.DEFAULT_RULES)
    if bool(rules.get("require_operator_approval")) and not release.get("approved"):
        raise HTTPException(status_code=409, detail="release requires operator approval before deployment")
    if bool(rules.get("require_simulation_pass")) and not release.get("validation", {}).get("simulation_passed"):
        raise HTTPException(status_code=409, detail="release validation failed; deployment blocked")
    previous_active = store.get("active_version")
    release["deployed"] = True
    release["deployed_at"] = rel._now_iso()
    release["status"] = rel._release_status(release)
    release["previous_active_version"] = previous_active
    store["active_version"] = release.get("version")
    store["stable_version"] = release.get("version")
    rel._remove_pending(store, release_id)
    store.setdefault("deployment_events", []).insert(0, {
        "release_id": release_id,
        "version": release.get("version"),
        "deployed_at": release.get("deployed_at"),
        "previous_active_version": previous_active,
        "deployed_by": operator,
    })
    rel._insert_history(store, release)
    rel._save(email, store)
    return release


def _rollback_release(email: str, operator: str, reason: str, target_version: str = None) -> dict:
    rel = _release()
    store = rel._load(email)
    history = store.get("release_history") or []
    candidates = [r for r in history if r.get("deployed")]
    target = None
    if target_version:
        for row in candidates:
            if row.get("version") == target_version:
                target = row
                break
        if not target:
            raise HTTPException(status_code=404, detail="target_version not found in deployment history")
    else:
        if len(candidates) < 2:
            raise HTTPException(status_code=409, detail="no prior stable deployment available for rollback")
        target = candidates[1]
    current_version = store.get("active_version")
    store["active_version"] = target.get("version")
    store["stable_version"] = target.get("version")
    rollback_event = {
        "rollback_id": f"rbk_{time.time_ns()}",
        "rolled_back_from": current_version,
        "rolled_back_to": target.get("version"),
        "reason": reason,
        "timestamp": rel._now_iso(),
        "operator": operator,
    }
    store.setdefault("rollback_events", []).insert(0, rollback_event)
    for row in history:
        if row.get("version") == current_version and row.get("deployed") and not row.get("rolled_back"):
            row["rolled_back"] = True
            row["rolled_back_at"] = rollback_event["timestamp"]
            row["rollback_reason"] = reason
            row["status"] = rel._release_status(row)
            break
    rel._save(email, store)
    return rollback_event


def _bootstrap_demo_for_email(email: str) -> dict:
    _safety()._bootstrap_demo_for_email(email)
    _release().institutional_release_control_bootstrap_demo({"email": email})
    store = _load(email)
    if not store.get("command_log"):
        _append_log(store, {
            "command_id": f"cmd_{time.time_ns()}",
            "action": "bootstrap_console",
            "status": "executed",
            "operator": email,
            "reason": "seed operator console baseline",
            "timestamp": _now_iso(),
        })
    _save(email, store)
    return _summary_for_email(email)


@router.get("/api/operator-command-console/summary")
def operator_command_console_summary():
    session = _require_user()
    return _summary_for_email(session.get("email"))


@router.post("/api/operator-command-console/operator-profile")
def operator_command_console_profile(payload: dict = Body(...)):
    session = _require_user()
    email = session.get("email")
    store = _load(email)
    profile = store.get("operator_profile") or dict(DEFAULT_PROFILE)
    for key, value in payload.items():
        if key in DEFAULT_PROFILE:
            profile[key] = value
    store["operator_profile"] = profile
    if payload.get("seat_mode"):
        store["active_mode"] = payload.get("seat_mode")
    _append_log(store, {
        "command_id": f"cmd_{time.time_ns()}",
        "action": "update_operator_profile",
        "status": "executed",
        "operator": email,
        "reason": payload.get("reason") or "profile update",
        "timestamp": _now_iso(),
    })
    _save(email, store)
    return {"status": "updated", "summary": _summary_for_email(email)}


@router.post("/api/operator-command-console/watchlist")
def operator_command_console_watchlist(payload: dict = Body(...)):
    session = _require_user()
    email = session.get("email")
    store = _load(email)
    watchlist = list(store.get("watchlist") or [])
    for symbol in payload.get("add", []) or []:
        s = str(symbol).upper().strip()
        if s and s not in watchlist:
            watchlist.append(s)
    for symbol in payload.get("remove", []) or []:
        s = str(symbol).upper().strip()
        if s in watchlist:
            watchlist.remove(s)
    store["watchlist"] = watchlist[:50]
    _append_log(store, {
        "command_id": f"cmd_{time.time_ns()}",
        "action": "update_watchlist",
        "status": "executed",
        "operator": email,
        "reason": payload.get("reason") or "watchlist update",
        "timestamp": _now_iso(),
    })
    _save(email, store)
    return {"status": "updated", "watchlist": store["watchlist"], "summary": _summary_for_email(email)}


@router.post("/api/operator-command-console/command")
def operator_command_console_command(payload: dict = Body(...)):
    session = _require_user()
    email = session.get("email")
    store = _load(email)
    action = (payload.get("action") or "").strip().lower()
    if not action:
        raise HTTPException(status_code=400, detail="action is required")
    operator = payload.get("operator") or email
    reason = payload.get("reason") or "operator command"
    status = "executed"
    details = {}
    if action == "emergency_stop":
        controls = _set_safety_controls(email, kill_switch=True, execution_paused=True)
        incident = {
            "incident_id": f"inc_{time.time_ns()}",
            "severity": "critical",
            "type": "capital_protection_lock",
            "reason": reason,
            "operator": operator,
            "timestamp": _now_iso(),
        }
        _append_log(store, incident, key="incidents", limit=100)
        details = {"controls": controls, "incident": incident}
    elif action == "pause_execution":
        controls = _set_safety_controls(email, execution_paused=True)
        details = {"controls": controls}
    elif action == "resume_execution":
        profile = store.get("operator_profile") or dict(DEFAULT_PROFILE)
        if profile.get("require_reason_for_resume") and not (payload.get("reason") or "").strip():
            raise HTTPException(status_code=400, detail="reason is required to resume execution")
        controls = _set_safety_controls(email, kill_switch=False, execution_paused=False)
        details = {"controls": controls}
    elif action == "require_operator_override":
        controls = _set_safety_controls(email, operator_override_required=True)
        details = {"controls": controls}
    elif action == "clear_operator_override":
        controls = _set_safety_controls(email, operator_override_required=False)
        details = {"controls": controls}
    elif action == "approve_release":
        release_id = payload.get("release_id")
        if not release_id:
            raise HTTPException(status_code=400, detail="release_id is required for approve_release")
        release = _approve_release(email, release_id, operator, note=reason)
        details = {"release": release}
    elif action == "deploy_release":
        release_id = payload.get("release_id")
        if not release_id:
            raise HTTPException(status_code=400, detail="release_id is required for deploy_release")
        release = _deploy_release(email, release_id, operator)
        details = {"release": release}
    elif action == "rollback_release":
        rollback = _rollback_release(email, operator, reason, payload.get("target_version"))
        controls = _set_safety_controls(email, execution_paused=True)
        details = {"rollback": rollback, "controls": controls}
    elif action == "note":
        note = {
            "note_id": f"note_{time.time_ns()}",
            "operator": operator,
            "text": payload.get("text") or reason,
            "timestamp": _now_iso(),
        }
        _append_log(store, note, key="notes", limit=200)
        details = {"note": note}
    else:
        raise HTTPException(status_code=400, detail=f"unsupported action: {action}")

    log_row = {
        "command_id": f"cmd_{time.time_ns()}",
        "action": action,
        "status": status,
        "operator": operator,
        "reason": reason,
        "details": details,
        "timestamp": _now_iso(),
    }
    _append_log(store, log_row)
    _save(email, store)
    return {"status": status, "command": log_row, "summary": _summary_for_email(email)}


@router.post("/api/operator-command-console/bootstrap-demo")
def operator_command_console_bootstrap_demo(payload: dict = Body(default=None)):
    session_email = None
    try:
        session_email = _require_user().get("email")
    except HTTPException:
        pass
    email = (payload or {}).get("email") or session_email or DEMO_EMAIL
    return {"status": "bootstrapped", "summary": _bootstrap_demo_for_email(email)}
