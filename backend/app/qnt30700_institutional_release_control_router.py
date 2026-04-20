from fastapi import APIRouter, Body, HTTPException
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import time

router = APIRouter(tags=["institutional-release-control"])

PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
RELEASE_DIR = ARTIFACTS_DIR / "institutional_release_control"
SAFETY_DIR = ARTIFACTS_DIR / "live_broker_safety_layer"

DEFAULT_RULES = {
    "require_operator_approval": True,
    "min_safety_risk_score": 70.0,
    "max_pending_releases": 10,
    "block_when_kill_switch": True,
    "block_when_execution_paused": True,
    "require_simulation_pass": True,
}

DEMO_EMAIL = "operator@quantora.test"


def _mu():
    from backend.app import qnt30557_multi_user_router as mu
    return mu


def _safe(v: str) -> str:
    return hashlib.sha256((v or "").strip().lower().encode("utf-8")).hexdigest()[:24]


def _path(email: str) -> Path:
    RELEASE_DIR.mkdir(parents=True, exist_ok=True)
    return RELEASE_DIR / f"{_safe(email)}.json"


def _safety_path(email: str) -> Path:
    return SAFETY_DIR / f"{_safe(email)}.json"


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
            "rules": dict(DEFAULT_RULES),
            "active_version": "v3.07.03",
            "stable_version": "v3.07.03",
            "counter": 0,
            "release_history": [],
            "pending_releases": [],
            "approvals": [],
            "deployment_events": [],
            "rollback_events": [],
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


def _next_release_id(store: dict) -> str:
    counter = int(store.get("counter") or 0) + 1
    store["counter"] = counter
    return f"rel_{counter:04d}"


def _latest_safety_summary(email: str) -> dict:
    safety_store = _read_json(_safety_path(email), {})
    latest_run = (safety_store.get("runs") or [{}])[0] if (safety_store.get("runs") or []) else {}
    latest_trade = (safety_store.get("trade_checks") or [{}])[0] if (safety_store.get("trade_checks") or []) else {}
    posture = latest_run.get("posture") or latest_trade.get("posture") or "UNKNOWN"
    production_ready = latest_run.get("production_ready")
    if production_ready is None:
        production_ready = posture != "BLOCKED"
    risk_score = float(latest_run.get("risk_score") or latest_trade.get("risk_score") or 0.0)
    drawdown_pct = float(latest_run.get("daily_drawdown_pct") or latest_trade.get("daily_drawdown_pct") or 0.0)
    open_exposure_pct = float(latest_run.get("open_exposure_pct") or latest_trade.get("open_exposure_pct") or 0.0)
    kill_switch = bool(latest_run.get("kill_switch") or latest_trade.get("kill_switch") or False)
    execution_paused = bool(latest_run.get("execution_paused") or latest_trade.get("execution_paused") or False)
    return {
        "available": bool(safety_store),
        "posture": posture,
        "production_ready": bool(production_ready),
        "risk_score": round(risk_score, 4),
        "daily_drawdown_pct": round(drawdown_pct, 4),
        "open_exposure_pct": round(open_exposure_pct, 4),
        "kill_switch": kill_switch,
        "execution_paused": execution_paused,
        "latest_run": latest_run,
        "latest_trade_check": latest_trade,
    }


def _validate_release(store: dict, release: dict, email: str) -> dict:
    rules = store.get("rules") or dict(DEFAULT_RULES)
    safety = _latest_safety_summary(email)
    violations = []
    warnings = []
    if not safety.get("available"):
        warnings.append("live broker safety layer data not found; validation running in degraded mode")
    if safety.get("available") and not safety.get("production_ready"):
        violations.append("safety posture is not production ready")
    if safety.get("available") and float(safety.get("risk_score") or 0.0) < float(rules.get("min_safety_risk_score") or 70.0):
        violations.append("safety risk score below release threshold")
    if bool(rules.get("block_when_kill_switch")) and safety.get("kill_switch"):
        violations.append("kill switch active")
    if bool(rules.get("block_when_execution_paused")) and safety.get("execution_paused"):
        violations.append("execution pause active")
    if bool(rules.get("require_operator_approval")) and not release.get("approved"):
        warnings.append("operator approval required before deployment")
    if not release.get("changes"):
        violations.append("release proposal missing change set")
    if not release.get("rationale"):
        warnings.append("release proposal missing rationale")
    if not release.get("affected_modules"):
        warnings.append("affected modules not specified")
    if len(store.get("pending_releases") or []) > int(rules.get("max_pending_releases") or 10):
        violations.append("pending release queue above governance limit")
    simulation_passed = len(violations) == 0
    return {
        "validated_at": _now_iso(),
        "simulation_passed": simulation_passed,
        "production_ready": bool(safety.get("production_ready")),
        "risk_score": safety.get("risk_score"),
        "posture": safety.get("posture"),
        "violations": violations,
        "warnings": warnings,
        "safety": safety,
    }


def _release_status(release: dict) -> str:
    if release.get("rolled_back"):
        return "rolled_back"
    if release.get("deployed"):
        return "deployed"
    if release.get("approved"):
        return "approved"
    return "pending"


def _summary_for_email(email: str) -> dict:
    store = _load(email)
    pending = store.get("pending_releases") or []
    history = store.get("release_history") or []
    safety = _latest_safety_summary(email)
    latest = history[0] if history else None
    deploys = [r for r in history if r.get("deployed")]
    rollbacks = [r for r in history if r.get("rolled_back")]
    return {
        "mission": "QNT30700",
        "generated_at": _now_iso(),
        "active_version": store.get("active_version"),
        "stable_version": store.get("stable_version"),
        "rules": store.get("rules") or dict(DEFAULT_RULES),
        "pending_release_count": len(pending),
        "deployment_count": len(deploys),
        "rollback_count": len(rollbacks),
        "latest_release": latest,
        "pending_releases": pending[:10],
        "recent_history": history[:15],
        "safety_gate": safety,
        "release_control_status": {
            "governed": True,
            "active_version": store.get("active_version"),
            "stable_version": store.get("stable_version"),
            "can_deploy": bool(safety.get("production_ready")) and not safety.get("kill_switch") and not safety.get("execution_paused"),
            "approval_backlog": len([r for r in pending if not r.get("approved")]),
        },
    }


def _insert_history(store: dict, release: dict):
    release = dict(release)
    release["status"] = _release_status(release)
    history = [r for r in (store.get("release_history") or []) if r.get("release_id") != release.get("release_id")]
    history.insert(0, release)
    store["release_history"] = history[:250]


def _find_pending(store: dict, release_id: str):
    for rel in store.get("pending_releases") or []:
        if rel.get("release_id") == release_id:
            return rel
    return None


def _remove_pending(store: dict, release_id: str):
    store["pending_releases"] = [r for r in (store.get("pending_releases") or []) if r.get("release_id") != release_id]


@router.get("/api/institutional-release-control/summary")
def institutional_release_control_summary():
    session = _require_user()
    return _summary_for_email(session.get("email"))


@router.post("/api/institutional-release-control/propose")
def institutional_release_control_propose(payload: dict = Body(...)):
    session = _require_user()
    email = session.get("email")
    store = _load(email)
    release = {
        "release_id": _next_release_id(store),
        "mission": "QNT30700",
        "version": payload.get("version") or f"v3.07.00-{int(time.time())}",
        "title": payload.get("title") or "institutional release proposal",
        "rationale": payload.get("rationale") or "",
        "changes": payload.get("changes") or [],
        "affected_modules": payload.get("affected_modules") or [],
        "risk_impact": payload.get("risk_impact") or "medium",
        "author": payload.get("author") or email,
        "approved": False,
        "approved_by": None,
        "approved_at": None,
        "deployed": False,
        "deployed_at": None,
        "rolled_back": False,
        "rolled_back_at": None,
        "rollback_reason": None,
        "created_at": _now_iso(),
        "status": "pending",
    }
    release["validation"] = _validate_release(store, release, email)
    store.setdefault("pending_releases", []).insert(0, release)
    _insert_history(store, release)
    _save(email, store)
    return {"status": "proposed", "release": release, "summary": _summary_for_email(email)}


@router.post("/api/institutional-release-control/validate")
def institutional_release_control_validate(payload: dict = Body(...)):
    session = _require_user()
    email = session.get("email")
    release_id = payload.get("release_id")
    if not release_id:
        raise HTTPException(status_code=400, detail="release_id is required")
    store = _load(email)
    release = _find_pending(store, release_id)
    if not release:
        raise HTTPException(status_code=404, detail="release not found in pending queue")
    release["validation"] = _validate_release(store, release, email)
    _insert_history(store, release)
    _save(email, store)
    return {"status": "validated", "release": release, "summary": _summary_for_email(email)}


@router.post("/api/institutional-release-control/approve")
def institutional_release_control_approve(payload: dict = Body(...)):
    session = _require_user()
    email = session.get("email")
    release_id = payload.get("release_id")
    if not release_id:
        raise HTTPException(status_code=400, detail="release_id is required")
    store = _load(email)
    release = _find_pending(store, release_id)
    if not release:
        raise HTTPException(status_code=404, detail="release not found in pending queue")
    release["validation"] = _validate_release(store, release, email)
    release["approved"] = True
    release["approved_by"] = payload.get("approved_by") or email
    release["approved_at"] = _now_iso()
    release["status"] = _release_status(release)
    store.setdefault("approvals", []).insert(0, {
        "release_id": release_id,
        "approved_by": release["approved_by"],
        "approved_at": release["approved_at"],
        "note": payload.get("note") or "operator approval",
    })
    _insert_history(store, release)
    _save(email, store)
    return {"status": "approved", "release": release, "summary": _summary_for_email(email)}


@router.post("/api/institutional-release-control/deploy")
def institutional_release_control_deploy(payload: dict = Body(...)):
    session = _require_user()
    email = session.get("email")
    release_id = payload.get("release_id")
    if not release_id:
        raise HTTPException(status_code=400, detail="release_id is required")
    store = _load(email)
    release = _find_pending(store, release_id)
    if not release:
        raise HTTPException(status_code=404, detail="release not found in pending queue")
    release["validation"] = _validate_release(store, release, email)
    rules = store.get("rules") or dict(DEFAULT_RULES)
    if bool(rules.get("require_operator_approval")) and not release.get("approved"):
        raise HTTPException(status_code=409, detail="release requires operator approval before deployment")
    if bool(rules.get("require_simulation_pass")) and not release.get("validation", {}).get("simulation_passed"):
        raise HTTPException(status_code=409, detail="release validation failed; deployment blocked")
    previous_active = store.get("active_version")
    release["deployed"] = True
    release["deployed_at"] = _now_iso()
    release["status"] = _release_status(release)
    release["previous_active_version"] = previous_active
    store["active_version"] = release.get("version")
    store["stable_version"] = release.get("version")
    _remove_pending(store, release_id)
    store.setdefault("deployment_events", []).insert(0, {
        "release_id": release_id,
        "version": release.get("version"),
        "deployed_at": release.get("deployed_at"),
        "previous_active_version": previous_active,
        "deployed_by": payload.get("deployed_by") or email,
    })
    _insert_history(store, release)
    _save(email, store)
    return {"status": "deployed", "release": release, "summary": _summary_for_email(email)}


@router.post("/api/institutional-release-control/rollback")
def institutional_release_control_rollback(payload: dict = Body(...)):
    session = _require_user()
    email = session.get("email")
    target_version = payload.get("target_version")
    reason = payload.get("reason") or "operator rollback"
    store = _load(email)
    history = store.get("release_history") or []
    candidates = [r for r in history if r.get("deployed")]
    target = None
    if target_version:
        for rel in candidates:
            if rel.get("version") == target_version:
                target = rel
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
        "timestamp": _now_iso(),
        "operator": payload.get("operator") or email,
    }
    store.setdefault("rollback_events", []).insert(0, rollback_event)
    for rel in history:
        if rel.get("version") == current_version and rel.get("deployed") and not rel.get("rolled_back"):
            rel["rolled_back"] = True
            rel["rolled_back_at"] = rollback_event["timestamp"]
            rel["rollback_reason"] = reason
            rel["status"] = _release_status(rel)
            break
    _save(email, store)
    return {"status": "rolled_back", "rollback": rollback_event, "summary": _summary_for_email(email)}


@router.post("/api/institutional-release-control/rules")
def institutional_release_control_rules(payload: dict = Body(...)):
    session = _require_user()
    email = session.get("email")
    store = _load(email)
    rules = store.get("rules") or dict(DEFAULT_RULES)
    for key, value in payload.items():
        if key in DEFAULT_RULES:
            rules[key] = value
    store["rules"] = rules
    _save(email, store)
    return {"status": "updated", "rules": rules, "summary": _summary_for_email(email)}


@router.post("/api/institutional-release-control/bootstrap-demo")
def institutional_release_control_bootstrap_demo(payload: dict = Body(default=None)):
    session_email = None
    try:
        session_email = _require_user().get("email")
    except HTTPException:
        pass
    email = (payload or {}).get("email") or session_email or DEMO_EMAIL
    store = _load(email)
    if not store.get("release_history"):
        seed_release = {
            "release_id": _next_release_id(store),
            "mission": "QNT30700",
            "version": "v3.07.03",
            "title": "baseline governed deployment",
            "rationale": "establish stable governed baseline before release control activation",
            "changes": ["baseline live broker safety layer active"],
            "affected_modules": ["qnt30703_live_broker_safety_layer_router.py"],
            "risk_impact": "low",
            "author": email,
            "approved": True,
            "approved_by": email,
            "approved_at": _now_iso(),
            "deployed": True,
            "deployed_at": _now_iso(),
            "rolled_back": False,
            "created_at": _now_iso(),
        }
        seed_release["validation"] = _validate_release(store, seed_release, email)
        _insert_history(store, seed_release)
        store["active_version"] = seed_release["version"]
        store["stable_version"] = seed_release["version"]
    if not store.get("pending_releases"):
        proposal = {
            "version": "v3.07.00-rc1",
            "title": "institutional release control activation",
            "rationale": "govern live system changes through proposals approvals deployments and rollbacks",
            "changes": [
                "add release registry",
                "add approval engine",
                "add deployment controller",
                "add rollback command",
            ],
            "affected_modules": [
                "backend/app/qnt30700_institutional_release_control_router.py",
                "frontend/mission_qnt30700_institutional_release_control.html",
                "backend/app/main.py",
                "frontend/mission_registry.json",
            ],
            "risk_impact": "medium",
            "author": email,
        }
        release = {
            "release_id": _next_release_id(store),
            "mission": "QNT30700",
            "version": proposal["version"],
            "title": proposal["title"],
            "rationale": proposal["rationale"],
            "changes": proposal["changes"],
            "affected_modules": proposal["affected_modules"],
            "risk_impact": proposal["risk_impact"],
            "author": proposal["author"],
            "approved": False,
            "approved_by": None,
            "approved_at": None,
            "deployed": False,
            "deployed_at": None,
            "rolled_back": False,
            "rolled_back_at": None,
            "rollback_reason": None,
            "created_at": _now_iso(),
            "status": "pending",
        }
        release["validation"] = _validate_release(store, release, email)
        store.setdefault("pending_releases", []).insert(0, release)
        _insert_history(store, release)
    _save(email, store)
    return {"status": "bootstrapped", "summary": _summary_for_email(email)}
