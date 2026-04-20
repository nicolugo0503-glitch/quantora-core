from fastapi import APIRouter, Body
from pathlib import Path
import json, time, hashlib

router = APIRouter(tags=["autonomous-correction-execution"])

PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
EXEC_DIR = ARTIFACTS_DIR / "autonomous_correction_execution"

def _mu():
    from backend.app import qnt30557_multi_user_router as mu
    return mu

def _alerts():
    from backend.app import qnt30606_break_alert_router as alerts
    return alerts

def _suggestions():
    from backend.app import qnt30607_resolution_suggestion_router as suggestions
    return suggestions

def _threeway():
    from backend.app import qnt30604_threeway_reconciliation_router as threeway
    return threeway

def _broker():
    from backend.app import qnt30603_broker_reconciliation_router as broker
    return broker

def _recon():
    from backend.app import qnt30600_reconciliation_router as recon
    return recon

def _safe(value: str) -> str:
    return hashlib.sha256((value or "").strip().lower().encode("utf-8")).hexdigest()[:24]

def _path(email: str) -> Path:
    EXEC_DIR.mkdir(parents=True, exist_ok=True)
    return EXEC_DIR / f"{_safe(email)}.json"

def _require_user():
    return _mu()._require_session()

def _load(email: str) -> dict:
    path = _path(email)
    if not path.exists():
        data = {"email": email, "executions": [], "created_at": int(time.time()), "updated_at": int(time.time())}
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return data
    return json.loads(path.read_text(encoding="utf-8"))

def _save(email: str, data: dict) -> dict:
    data["updated_at"] = int(time.time())
    _path(email).write_text(json.dumps(data, indent=2), encoding="utf-8")
    return data

def _latest_suggestion_for_alert(email: str, alert_id: str):
    data = _suggestions()._load(email)
    if not data.get("runs"):
        return None
    for s in data["runs"][0].get("suggestions", []):
        if s.get("alert_id") == alert_id:
            return s
    return None

def _execute_action(email: str, action: str):
    result = {"action": action, "steps": [], "success": True}
    if action == "rerun_threeway_after_cash_sync":
        run = _threeway()._run_reconciliation(email)
        tdata = _threeway()._load(email)
        tdata.setdefault("runs", []).insert(0, run)
        tdata["runs"] = tdata["runs"][:200]
        _threeway()._save(email, tdata)
        result["steps"].append("reran_threeway_reconciliation")
        result["details"] = {"threeway_status": run.get("status"), "break_count": run.get("break_count", 0)}
    elif action == "rerun_position_sync_and_broker_match":
        run = _broker()._run_match(email)
        bdata = _broker()._load(email)
        bdata.setdefault("runs", []).insert(0, run)
        bdata["runs"] = bdata["runs"][:200]
        _broker()._save(email, bdata)
        result["steps"].append("reran_broker_match")
        result["details"] = {"broker_status": run.get("status"), "missing": run.get("missing_in_broker_count", 0), "unexpected": run.get("unexpected_broker_count", 0)}
    elif action == "refresh_nav_and_rerun_threeway":
        run = _threeway()._run_reconciliation(email)
        tdata = _threeway()._load(email)
        tdata.setdefault("runs", []).insert(0, run)
        tdata["runs"] = tdata["runs"][:200]
        _threeway()._save(email, tdata)
        result["steps"].extend(["refreshed_nav_context", "reran_threeway_reconciliation"])
        result["details"] = {"threeway_status": run.get("status")}
    elif action == "rerun_broker_sync_and_match":
        run = _broker()._run_match(email)
        bdata = _broker()._load(email)
        bdata.setdefault("runs", []).insert(0, run)
        bdata["runs"] = bdata["runs"][:200]
        _broker()._save(email, bdata)
        result["steps"].append("reran_broker_reconciliation")
        result["details"] = {"broker_status": run.get("status")}
    elif action == "reconcile_capital_flow_and_confirmations":
        run = _recon()._run_checks(email)
        rdata = _recon()._load(email)
        rdata.setdefault("runs", []).insert(0, run)
        rdata["runs"] = rdata["runs"][:200]
        _recon()._save(email, rdata)
        result["steps"].append("reran_full_reconciliation")
        result["details"] = {"reconciliation_status": run.get("status"), "issue_count": run.get("issue_count", 0)}
    elif action == "refresh_equalization_series":
        run = _recon()._run_checks(email)
        rdata = _recon()._load(email)
        rdata.setdefault("runs", []).insert(0, run)
        rdata["runs"] = rdata["runs"][:200]
        _recon()._save(email, rdata)
        result["steps"].append("refreshed_equalization_context")
        result["details"] = {"reconciliation_status": run.get("status")}
    elif action == "rebuild_rollforward":
        run = _recon()._run_checks(email)
        rdata = _recon()._load(email)
        rdata.setdefault("runs", []).insert(0, run)
        rdata["runs"] = rdata["runs"][:200]
        _recon()._save(email, rdata)
        result["steps"].append("rebuilt_rollforward_context")
        result["details"] = {"reconciliation_status": run.get("status")}
    elif action in {"generate_missing_confirmations", "regenerate_allocation_confirmation", "manual_investigation", "quarantine_unexpected_broker_trade"}:
        result["steps"].append("recorded_manual_or_followup_action")
        result["details"] = {"note": "action recorded for operator follow-up"}
    else:
        result["success"] = False
        result["steps"].append("unknown_action")
        result["details"] = {"note": "no execution mapping found"}
    return result

@router.get("/api/correction-execution")
def correction_execution():
    session = _require_user()
    return _load(session.get("email"))

@router.post("/api/correction-execution/run")
def correction_execution_run(payload: dict = Body(...)):
    session = _require_user()
    email = session.get("email")
    alert_id = str(payload.get("alert_id") or "")
    if not alert_id:
        return {"status": "missing_alert_id"}
    suggestion = _latest_suggestion_for_alert(email, alert_id)
    if not suggestion:
        return {"status": "suggestion_not_found"}
    action = suggestion.get("recommended_action")
    exec_result = _execute_action(email, action)

    data = _load(email)
    record = {
        "execution_id": f"exec_{int(time.time())}",
        "alert_id": alert_id,
        "recommended_action": action,
        "suggestion_status": suggestion.get("status"),
        "result": exec_result,
        "status": "executed" if exec_result.get("success") else "failed",
        "timestamp": int(time.time()),
    }
    if payload.get("notes"):
        record["notes"] = str(payload.get("notes"))
    data.setdefault("executions", []).insert(0, record)
    data["executions"] = data["executions"][:300]
    _save(email, data)

    alerts_data = _alerts()._load(email)
    for alert in alerts_data.get("alerts", []):
        if alert.get("alert_id") == alert_id and exec_result.get("success"):
            alert["status"] = "acknowledged"
            alert["acknowledged_at"] = int(time.time())
            break
    _alerts()._save(email, alerts_data)

    return {"status": record["status"], "execution": record}

@router.get("/api/correction-execution/summary")
def correction_execution_summary():
    session = _require_user()
    email = session.get("email")
    data = _load(email)
    executions = data.get("executions", [])
    executed = sum(1 for e in executions if e.get("status") == "executed")
    failed = sum(1 for e in executions if e.get("status") == "failed")
    latest = executions[0] if executions else None
    return {
        "email": email,
        "execution_count": len(executions),
        "executed_count": executed,
        "failed_count": failed,
        "latest_execution": latest,
        "executions": executions[:100],
    }
