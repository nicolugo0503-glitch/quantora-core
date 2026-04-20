from fastapi import APIRouter, Body
from pathlib import Path
import json, time, hashlib

router = APIRouter(tags=["automated-break-alerts"])

PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
ALERT_DIR = ARTIFACTS_DIR / "automated_break_alerts"

def _mu():
    from backend.app import qnt30557_multi_user_router as mu
    return mu

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
    ALERT_DIR.mkdir(parents=True, exist_ok=True)
    return ALERT_DIR / f"{_safe(email)}.json"

def _require_user():
    return _mu()._require_session()

def _load(email: str) -> dict:
    path = _path(email)
    if not path.exists():
        data = {"email": email, "alerts": [], "runs": [], "created_at": int(time.time()), "updated_at": int(time.time())}
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return data
    return json.loads(path.read_text(encoding="utf-8"))

def _save(email: str, data: dict) -> dict:
    data["updated_at"] = int(time.time())
    _path(email).write_text(json.dumps(data, indent=2), encoding="utf-8")
    return data

def _make_alert(source: str, code: str, severity: str, message: str, metadata: dict):
    return {
        "alert_id": f"alert_{int(time.time())}_{abs(hash((source, code, message))) % 100000}",
        "source": source,
        "code": code,
        "severity": severity,
        "message": message,
        "metadata": metadata,
        "status": "open",
        "created_at": int(time.time()),
        "acknowledged_at": None,
        "resolved_at": None,
    }

def _collect_breaks(email: str):
    alerts = []

    threeway_data = _threeway()._load(email)
    threeway_runs = threeway_data.get("runs") or []
    if not threeway_runs:
        run = _threeway()._run_reconciliation(email)
        threeway_data.setdefault("runs", []).insert(0, run)
        _threeway()._save(email, threeway_data)
    latest_threeway = (threeway_data.get("runs") or [None])[0] or {}
    for b in latest_threeway.get("breaks", []):
        alerts.append(_make_alert(
            "threeway",
            b.get("code", "threeway_break"),
            b.get("severity", "high"),
            b.get("message", "Three-way reconciliation break detected"),
            {"difference": b.get("difference"), "symbol": b.get("symbol")}
        ))

    broker_data = _broker()._load(email)
    broker_runs = broker_data.get("runs") or []
    if not broker_runs:
        run = _broker()._run_match(email)
        broker_data.setdefault("runs", []).insert(0, run)
        _broker()._save(email, broker_data)
    latest_broker = (broker_data.get("runs") or [None])[0] or {}
    if latest_broker.get("missing_in_broker_count", 0) > 0:
        alerts.append(_make_alert(
            "broker_match",
            "missing_in_broker",
            "high",
            f"{latest_broker.get('missing_in_broker_count', 0)} internal trades are missing in broker records.",
            {"count": latest_broker.get("missing_in_broker_count", 0)}
        ))
    if latest_broker.get("unexpected_broker_count", 0) > 0:
        alerts.append(_make_alert(
            "broker_match",
            "unexpected_broker_trade",
            "high",
            f"{latest_broker.get('unexpected_broker_count', 0)} broker trades were not expected internally.",
            {"count": latest_broker.get("unexpected_broker_count", 0)}
        ))

    recon_data = _recon()._load(email)
    recon_runs = recon_data.get("runs") or []
    if not recon_runs:
        run = _recon()._run_checks(email)
        recon_data.setdefault("runs", []).insert(0, run)
        _recon()._save(email, recon_data)
    latest_recon = (recon_data.get("runs") or [None])[0] or {}
    for issue in latest_recon.get("issues", []):
        alerts.append(_make_alert(
            "full_reconciliation",
            issue.get("code", "reconciliation_issue"),
            issue.get("severity", "medium"),
            issue.get("message", "Reconciliation issue detected"),
            {"difference": issue.get("difference")}
        ))

    return alerts

@router.get("/api/break-alerts")
def break_alerts():
    session = _require_user()
    return _load(session.get("email"))

@router.post("/api/break-alerts/run")
def break_alerts_run(payload: dict = Body(None)):
    session = _require_user()
    email = session.get("email")
    data = _load(email)

    alerts = _collect_breaks(email)
    existing_keys = {(a.get("source"), a.get("code"), a.get("message"), a.get("status")) for a in data.get("alerts", [])}
    new_alerts = []
    for a in alerts:
        key = (a.get("source"), a.get("code"), a.get("message"), a.get("status"))
        if key not in existing_keys:
            data.setdefault("alerts", []).insert(0, a)
            new_alerts.append(a)

    run = {
        "run_id": f"alert_run_{int(time.time())}",
        "timestamp": int(time.time()),
        "new_alert_count": len(new_alerts),
        "total_open_alerts": sum(1 for a in data.get("alerts", []) if a.get("status") == "open"),
        "status": "alerts_detected" if new_alerts else "no_new_alerts",
    }
    if payload and payload.get("notes"):
        run["notes"] = str(payload.get("notes"))
    data.setdefault("runs", []).insert(0, run)
    data["runs"] = data["runs"][:200]
    data["alerts"] = data.get("alerts", [])[:1000]
    _save(email, data)
    return {"status": run["status"], "run": run, "new_alerts": new_alerts}

@router.post("/api/break-alerts/ack")
def break_alerts_ack(payload: dict = Body(...)):
    session = _require_user()
    email = session.get("email")
    alert_id = str(payload.get("alert_id") or "")
    data = _load(email)
    alert = next((a for a in data.get("alerts", []) if a.get("alert_id") == alert_id), None)
    if not alert:
        return {"status": "not_found"}
    alert["status"] = "acknowledged"
    alert["acknowledged_at"] = int(time.time())
    _save(email, data)
    return {"status": "acknowledged", "alert": alert}

@router.post("/api/break-alerts/resolve")
def break_alerts_resolve(payload: dict = Body(...)):
    session = _require_user()
    email = session.get("email")
    alert_id = str(payload.get("alert_id") or "")
    data = _load(email)
    alert = next((a for a in data.get("alerts", []) if a.get("alert_id") == alert_id), None)
    if not alert:
        return {"status": "not_found"}
    alert["status"] = "resolved"
    alert["resolved_at"] = int(time.time())
    _save(email, data)
    return {"status": "resolved", "alert": alert}

@router.get("/api/break-alerts/summary")
def break_alerts_summary():
    session = _require_user()
    email = session.get("email")
    data = _load(email)
    alerts = data.get("alerts", [])
    open_count = sum(1 for a in alerts if a.get("status") == "open")
    ack_count = sum(1 for a in alerts if a.get("status") == "acknowledged")
    resolved_count = sum(1 for a in alerts if a.get("status") == "resolved")
    high_count = sum(1 for a in alerts if a.get("severity") == "high")
    latest = alerts[0] if alerts else None
    return {
        "email": email,
        "alert_count": len(alerts),
        "open_count": open_count,
        "acknowledged_count": ack_count,
        "resolved_count": resolved_count,
        "high_severity_count": high_count,
        "latest_alert": latest,
        "alerts": alerts[:100],
        "runs": data.get("runs", [])[:50],
    }
