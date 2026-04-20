from fastapi import APIRouter, Body
from pathlib import Path
import json, time, hashlib, datetime, html
router = APIRouter(tags=["pdf-export-investor-report"])
PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
REPORT_DIR = ARTIFACTS_DIR / "investor_report_exports"
def _mu():
    from backend.app import qnt30557_multi_user_router as mu
    return mu
def _packet():
    from backend.app import qnt30611_daily_packet_router as packet
    return packet
def _safe(v): return hashlib.sha256((v or "").strip().lower().encode()).hexdigest()[:24]
def _path(email):
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    return REPORT_DIR / f"{_safe(email)}.json"
def _require_user():
    return _mu()._require_session()
def _load(email):
    p = _path(email)
    if not p.exists():
        d = {"email": email, "reports": [], "created_at": int(time.time()), "updated_at": int(time.time())}
        p.write_text(json.dumps(d, indent=2))
        return d
    return json.loads(p.read_text())
def _save(email, d):
    d["updated_at"] = int(time.time())
    _path(email).write_text(json.dumps(d, indent=2))
    return d
def _latest_packet(email):
    data = _packet()._load(email)
    packets = data.get("packets") or []
    if packets: return packets[0]
    packet = _packet()._generate_packet(email)
    data.setdefault("packets", []).insert(0, packet)
    _packet()._save(email, data)
    return packet
def _build_report(email, title):
    packet = _latest_packet(email)
    summary = packet.get("summary", {})
    report_id = f"invrep_{int(time.time())}"
    date_str = packet.get("date") or datetime.datetime.utcnow().strftime("%Y-%m-%d")
    html_body = f"<html><body><h1>{html.escape(title)}</h1><p>Quantora Investor Report · {html.escape(date_str)}</p><p>Three-way: {html.escape(str(summary.get('threeway_status','-')))}</p><p>Breaks: {summary.get('break_count',0)}</p><p>Open alerts: {summary.get('open_alerts',0)}</p><p>Open escalations: {summary.get('open_escalations',0)}</p></body></html>"
    return {"report_id": report_id, "title": title, "date": date_str, "created_at": int(time.time()), "packet_id": packet.get("packet_id"), "summary": summary, "html_report": html_body, "status": "generated"}
@router.get("/api/investor-reports")
def investor_reports():
    session = _require_user()
    return _load(session.get("email"))
@router.post("/api/investor-reports/generate")
def investor_reports_generate(payload: dict = Body(None)):
    session = _require_user()
    email = session.get("email")
    title = ((payload or {}).get("title") or "Quantora Daily Investor Report").strip()
    data = _load(email)
    item = _build_report(email, title)
    data.setdefault("reports", []).insert(0, item)
    data["reports"] = data["reports"][:100]
    _save(email, data)
    return {"status": "generated", "report": item, "total_reports": len(data["reports"])}
@router.post("/api/investor-reports/publish")
def investor_reports_publish(payload: dict = Body(...)):
    session = _require_user()
    email = session.get("email")
    report_id = str(payload.get("report_id") or "")
    data = _load(email)
    item = next((r for r in data.get("reports", []) if r.get("report_id") == report_id), None)
    if not item: return {"status": "not_found"}
    item["status"] = "published"
    item["published_at"] = int(time.time())
    _save(email, data)
    return {"status": "published", "report": item}
@router.get("/api/investor-reports/summary")
def investor_reports_summary():
    session = _require_user()
    email = session.get("email")
    data = _load(email)
    if not data.get("reports"):
        item = _build_report(email, "Quantora Daily Investor Report")
        data.setdefault("reports", []).insert(0, item)
        _save(email, data)
    latest = data["reports"][0]
    published = sum(1 for r in data.get("reports", []) if r.get("status") == "published")
    return {"email": email, "report_count": len(data.get("reports", [])), "published_count": published, "latest_report": latest, "reports": data.get("reports", [])[:50]}
