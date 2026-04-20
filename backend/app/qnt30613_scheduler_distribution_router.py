from fastapi import APIRouter, Body
from pathlib import Path
import json, time, hashlib, datetime
router = APIRouter(tags=["automated-daily-scheduler-distribution-queue"])
PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
QUEUE_DIR = ARTIFACTS_DIR / "daily_scheduler_distribution_queue"
DEFAULT_SCHEDULE = {"enabled": True, "frequency": "daily", "hour_utc": 13, "minute_utc": 0, "report_title_template": "Quantora Daily Investor Report"}
def _mu():
    from backend.app import qnt30557_multi_user_router as mu
    return mu
def _packet():
    from backend.app import qnt30611_daily_packet_router as packet
    return packet
def _reports():
    from backend.app import qnt30612_pdf_report_router as reports
    return reports
def _safe(v): return hashlib.sha256((v or "").strip().lower().encode()).hexdigest()[:24]
def _path(email):
    QUEUE_DIR.mkdir(parents=True, exist_ok=True)
    return QUEUE_DIR / f"{_safe(email)}.json"
def _require_user():
    return _mu()._require_session()
def _load(email):
    p = _path(email)
    if not p.exists():
        d = {"email": email, "schedule": DEFAULT_SCHEDULE, "queue": [], "runs": [], "created_at": int(time.time()), "updated_at": int(time.time())}
        p.write_text(json.dumps(d, indent=2))
        return d
    return json.loads(p.read_text())
def _save(email, d):
    d["updated_at"] = int(time.time())
    _path(email).write_text(json.dumps(d, indent=2))
    return d
def _utc_date(): return datetime.datetime.utcnow().strftime("%Y-%m-%d")
def _ensure_daily_packet(email):
    pdata = _packet()._load(email)
    if pdata.get("packets"): return pdata["packets"][0]
    packet = _packet()._generate_packet(email)
    pdata.setdefault("packets", []).insert(0, packet)
    _packet()._save(email, pdata)
    return packet
def _ensure_report(email, title):
    rdata = _reports()._load(email)
    if rdata.get("reports"): return rdata["reports"][0]
    report = _reports()._build_report(email, title)
    rdata.setdefault("reports", []).insert(0, report)
    _reports()._save(email, rdata)
    return report
def _build_queue_item(email, title):
    packet = _ensure_daily_packet(email)
    report = _ensure_report(email, title)
    return {"queue_id": f"dist_{int(time.time())}", "date": _utc_date(), "packet_id": packet.get("packet_id"), "report_id": report.get("report_id"), "title": title, "status": "queued", "created_at": int(time.time()), "delivered_at": None, "notes": ""}
@router.get("/api/daily-scheduler")
def daily_scheduler():
    session = _require_user()
    return _load(session.get("email"))
@router.post("/api/daily-scheduler/configure")
def configure_daily_scheduler(payload: dict = Body(...)):
    session = _require_user()
    email = session.get("email")
    data = _load(email)
    schedule = data.get("schedule", DEFAULT_SCHEDULE.copy())
    for k in ["enabled","frequency","hour_utc","minute_utc","report_title_template"]:
        if k in payload: schedule[k] = payload.get(k)
    data["schedule"] = schedule
    _save(email, data)
    return {"status": "configured", "schedule": schedule}
@router.post("/api/daily-scheduler/run")
def run_daily_scheduler(payload: dict = Body(None)):
    session = _require_user()
    email = session.get("email")
    data = _load(email)
    schedule = data.get("schedule", DEFAULT_SCHEDULE.copy())
    title = ((payload or {}).get("title") or schedule.get("report_title_template") or "Quantora Daily Investor Report").strip()
    item = _build_queue_item(email, title)
    if payload and payload.get("notes"): item["notes"] = str(payload.get("notes"))
    data.setdefault("queue", []).insert(0, item)
    data["queue"] = data["queue"][:300]
    run = {"run_id": f"schedule_{int(time.time())}", "timestamp": int(time.time()), "status": "queued" if schedule.get("enabled", True) else "disabled_but_queued", "queue_id": item["queue_id"], "title": title}
    data.setdefault("runs", []).insert(0, run)
    data["runs"] = data["runs"][:200]
    _save(email, data)
    return {"status": run["status"], "run": run, "queue_item": item}
@router.post("/api/daily-scheduler/deliver")
def deliver_daily_scheduler(payload: dict = Body(...)):
    session = _require_user()
    email = session.get("email")
    queue_id = str(payload.get("queue_id") or "")
    data = _load(email)
    item = next((q for q in data.get("queue", []) if q.get("queue_id") == queue_id), None)
    if not item: return {"status": "not_found"}
    item["status"] = "delivered"
    item["delivered_at"] = int(time.time())
    if payload.get("notes"): item["notes"] = str(payload.get("notes"))
    _save(email, data)
    return {"status": "delivered", "queue_item": item}
@router.get("/api/daily-scheduler/summary")
def daily_scheduler_summary():
    session = _require_user()
    email = session.get("email")
    data = _load(email)
    queued = sum(1 for q in data.get("queue", []) if q.get("status") == "queued")
    delivered = sum(1 for q in data.get("queue", []) if q.get("status") == "delivered")
    latest = data.get("queue", [None])[0] if data.get("queue") else None
    return {"email": email, "schedule": data.get("schedule", DEFAULT_SCHEDULE), "queue_count": len(data.get("queue", [])), "queued_count": queued, "delivered_count": delivered, "latest_queue_item": latest, "queue": data.get("queue", [])[:100], "runs": data.get("runs", [])[:50]}
