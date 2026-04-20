from fastapi import APIRouter, Body
from pathlib import Path
import json, time, hashlib

router = APIRouter(tags=["supervisory-control-center"])

PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
SUP_DIR = ARTIFACTS_DIR / "supervisory_control_center"

DEFAULT_ESCALATION_MATRIX = {
    "high": {"level": "L1", "owner_role": "Risk Lead", "target_minutes": 15},
    "medium": {"level": "L2", "owner_role": "Operations Lead", "target_minutes": 60},
    "low": {"level": "L3", "owner_role": "Analyst", "target_minutes": 240},
}

def _mu():
    from backend.app import qnt30557_multi_user_router as mu
    return mu

def _alerts():
    from backend.app import qnt30606_break_alert_router as alerts
    return alerts

def _execution():
    from backend.app import qnt30608_correction_execution_router as execution
    return execution

def _safe(value: str) -> str:
    return hashlib.sha256((value or "").strip().lower().encode("utf-8")).hexdigest()[:24]

def _path(email: str) -> Path:
    SUP_DIR.mkdir(parents=True, exist_ok=True)
    return SUP_DIR / f"{_safe(email)}.json"

def _require_user():
    return _mu()._require_session()

def _load(email: str) -> dict:
    path = _path(email)
    if not path.exists():
        data = {
            "email": email,
            "escalation_matrix": DEFAULT_ESCALATION_MATRIX,
            "supervisory_runs": [],
            "escalations": [],
            "created_at": int(time.time()),
            "updated_at": int(time.time()),
        }
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return data
    return json.loads(path.read_text(encoding="utf-8"))

def _save(email: str, data: dict) -> dict:
    data["updated_at"] = int(time.time())
    _path(email).write_text(json.dumps(data, indent=2), encoding="utf-8")
    return data

def _build_escalation(alert: dict, matrix: dict):
    sev = str(alert.get("severity") or "medium")
    rule = matrix.get(sev, matrix.get("medium", {}))
    return {
        "escalation_id": f"esc_{int(time.time())}_{abs(hash(alert.get('alert_id'))) % 100000}",
        "alert_id": alert.get("alert_id"),
        "source": alert.get("source"),
        "code": alert.get("code"),
        "severity": sev,
        "message": alert.get("message"),
        "level": rule.get("level", "L2"),
        "owner_role": rule.get("owner_role", "Operations Lead"),
        "target_minutes": rule.get("target_minutes", 60),
        "status": "open",
        "created_at": int(time.time()),
        "acknowledged_at": None,
        "closed_at": None,
    }

def _run_supervision(email: str):
    data = _load(email)
    matrix = data.get("escalation_matrix", DEFAULT_ESCALATION_MATRIX)

    alerts_data = _alerts()._load(email)
    open_alerts = [a for a in alerts_data.get("alerts", []) if a.get("status") in {"open", "acknowledged"}]

    execution_data = _execution()._load(email)
    executions = execution_data.get("executions", [])
    latest_exec = executions[0] if executions else None

    new_escalations = []
    existing_keys = {(e.get("alert_id"), e.get("status")) for e in data.get("escalations", []) if e.get("status") != "closed"}
    for alert in open_alerts:
        key = (alert.get("alert_id"), "open")
        if key not in existing_keys:
            esc = _build_escalation(alert, matrix)
            data.setdefault("escalations", []).insert(0, esc)
            new_escalations.append(esc)

    run = {
        "run_id": f"sup_{int(time.time())}",
        "timestamp": int(time.time()),
        "open_alert_count": len(open_alerts),
        "new_escalation_count": len(new_escalations),
        "latest_execution_status": latest_exec.get("status") if latest_exec else None,
        "status": "escalations_open" if open_alerts else "clear",
    }
    data.setdefault("supervisory_runs", []).insert(0, run)
    data["supervisory_runs"] = data["supervisory_runs"][:200]
    data["escalations"] = data.get("escalations", [])[:1000]
    _save(email, data)
    return run, new_escalations

@router.get("/api/supervisory-control")
def supervisory_control():
    session = _require_user()
    return _load(session.get("email"))

@router.post("/api/supervisory-control/run")
def supervisory_control_run(payload: dict = Body(None)):
    session = _require_user()
    email = session.get("email")
    run, escalations = _run_supervision(email)
    if payload and payload.get("notes"):
        run["notes"] = str(payload.get("notes"))
        data = _load(email)
        if data.get("supervisory_runs"):
            data["supervisory_runs"][0]["notes"] = run["notes"]
            _save(email, data)
    return {"status": run["status"], "run": run, "new_escalations": escalations}

@router.post("/api/supervisory-control/ack")
def supervisory_control_ack(payload: dict = Body(...)):
    session = _require_user()
    email = session.get("email")
    escalation_id = str(payload.get("escalation_id") or "")
    data = _load(email)
    esc = next((e for e in data.get("escalations", []) if e.get("escalation_id") == escalation_id), None)
    if not esc:
        return {"status": "not_found"}
    esc["status"] = "acknowledged"
    esc["acknowledged_at"] = int(time.time())
    _save(email, data)
    return {"status": "acknowledged", "escalation": esc}

@router.post("/api/supervisory-control/close")
def supervisory_control_close(payload: dict = Body(...)):
    session = _require_user()
    email = session.get("email")
    escalation_id = str(payload.get("escalation_id") or "")
    data = _load(email)
    esc = next((e for e in data.get("escalations", []) if e.get("escalation_id") == escalation_id), None)
    if not esc:
        return {"status": "not_found"}
    esc["status"] = "closed"
    esc["closed_at"] = int(time.time())
    _save(email, data)
    return {"status": "closed", "escalation": esc}

@router.get("/api/supervisory-control/summary")
def supervisory_control_summary():
    session = _require_user()
    email = session.get("email")
    data = _load(email)
    if not data.get("supervisory_runs"):
        _run_supervision(email)
        data = _load(email)
    escalations = data.get("escalations", [])
    open_count = sum(1 for e in escalations if e.get("status") == "open")
    ack_count = sum(1 for e in escalations if e.get("status") == "acknowledged")
    closed_count = sum(1 for e in escalations if e.get("status") == "closed")
    high_count = sum(1 for e in escalations if e.get("severity") == "high" and e.get("status") != "closed")
    latest = escalations[0] if escalations else None
    return {
        "email": email,
        "run_count": len(data.get("supervisory_runs", [])),
        "escalation_count": len(escalations),
        "open_count": open_count,
        "acknowledged_count": ack_count,
        "closed_count": closed_count,
        "high_open_count": high_count,
        "latest_escalation": latest,
        "escalation_matrix": data.get("escalation_matrix", DEFAULT_ESCALATION_MATRIX),
        "escalations": escalations[:100],
        "runs": data.get("supervisory_runs", [])[:50],
    }
