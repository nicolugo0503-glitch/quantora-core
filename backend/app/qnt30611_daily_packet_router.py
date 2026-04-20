from fastapi import APIRouter
from pathlib import Path
import json, time, hashlib, datetime
router = APIRouter(tags=["daily-control-packet"])
PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
PACKET_DIR = ARTIFACTS_DIR / "daily_control_packets"
def _mu():
    from backend.app import qnt30557_multi_user_router as mu
    return mu
def _threeway():
    from backend.app import qnt30604_threeway_reconciliation_router as t
    return t
def _alerts():
    from backend.app import qnt30606_break_alert_router as a
    return a
def _sup():
    from backend.app import qnt30609_supervisory_control_router as s
    return s
def _gov():
    from backend.app import qnt30610_governance_router as g
    return g
def _safe(v): return hashlib.sha256((v or "").encode()).hexdigest()[:24]
def _path(email):
    PACKET_DIR.mkdir(parents=True, exist_ok=True)
    return PACKET_DIR / f"{_safe(email)}.json"
def _require_user():
    return _mu()._require_session()
def _load(email):
    p = _path(email)
    if not p.exists():
        d = {"email": email, "packets": []}
        p.write_text(json.dumps(d, indent=2))
        return d
    return json.loads(p.read_text())
def _save(email, d):
    _path(email).write_text(json.dumps(d, indent=2))
    return d
def _generate_packet(email):
    date = datetime.datetime.utcnow().strftime("%Y-%m-%d")
    threeway = (_threeway()._load(email).get("runs") or [{}])[0]
    alerts = _alerts()._load(email)
    sup = _sup()._load(email)
    gov = _gov()._load(email)
    return {
        "packet_id": f"packet_{int(time.time())}",
        "date": date,
        "summary": {
            "threeway_status": threeway.get("status"),
            "break_count": threeway.get("break_count", 0),
            "open_alerts": sum(1 for a in alerts.get("alerts", []) if a.get("status")=="open"),
            "open_escalations": sum(1 for e in sup.get("escalations", []) if e.get("status")=="open"),
        },
        "threeway": threeway,
        "alerts": alerts.get("alerts", [])[:50],
        "escalations": sup.get("escalations", [])[:50],
        "governance": gov.get("attestations", [])[:5],
        "created_at": int(time.time())
    }
@router.post("/api/daily-packet/run")
def run_packet():
    session = _require_user()
    email = session.get("email")
    data = _load(email)
    packet = _generate_packet(email)
    data.setdefault("packets", []).insert(0, packet)
    data["packets"] = data["packets"][:200]
    _save(email, data)
    return {"status":"generated","packet":packet}
@router.get("/api/daily-packet/summary")
def summary():
    session = _require_user()
    email = session.get("email")
    data = _load(email)
    latest = data["packets"][0] if data.get("packets") else None
    return {"packet_count": len(data.get("packets",[])), "latest_packet": latest, "packets": data.get("packets",[])[:20]}
