from fastapi import APIRouter, Body
from pathlib import Path
import json, time, hashlib
router = APIRouter(tags=["delivery-channel-router"])
PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
DELIVERY_DIR = ARTIFACTS_DIR / "delivery_channel_router"
DEFAULT_CHANNELS = {"portal": {"enabled": True}, "email_simulated": {"enabled": True}, "download_pack": {"enabled": True}}
def _mu():
    from backend.app import qnt30557_multi_user_router as mu
    return mu
def _scheduler():
    from backend.app import qnt30613_scheduler_distribution_router as scheduler
    return scheduler
def _safe(v): return hashlib.sha256((v or "").strip().lower().encode()).hexdigest()[:24]
def _path(email):
    DELIVERY_DIR.mkdir(parents=True, exist_ok=True)
    return DELIVERY_DIR / f"{_safe(email)}.json"
def _require_user():
    return _mu()._require_session()
def _load(email):
    p = _path(email)
    if not p.exists():
        d = {"email": email, "channels": DEFAULT_CHANNELS, "deliveries": [], "audit_log": [], "created_at": int(time.time()), "updated_at": int(time.time())}
        p.write_text(json.dumps(d, indent=2))
        return d
    return json.loads(p.read_text())
def _save(email, d):
    d["updated_at"] = int(time.time())
    _path(email).write_text(json.dumps(d, indent=2))
    return d
def _log_event(data, event_type, payload):
    data.setdefault("audit_log", []).insert(0, {"event_id": f"audit_{int(time.time())}_{len(data.get('audit_log', []))+1}", "event_type": event_type, "payload": payload, "timestamp": int(time.time())})
    data["audit_log"] = data["audit_log"][:1000]
@router.get("/api/delivery-router")
def delivery_router():
    session = _require_user()
    return _load(session.get("email"))
@router.post("/api/delivery-router/configure")
def delivery_router_configure(payload: dict = Body(...)):
    session = _require_user()
    email = session.get("email")
    data = _load(email)
    channels = data.get("channels", DEFAULT_CHANNELS.copy())
    for name, cfg in (payload.get("channels") or {}).items():
        channels[name] = {"enabled": bool(cfg.get("enabled", True))}
    data["channels"] = channels
    _log_event(data, "channels_configured", {"channels": channels})
    _save(email, data)
    return {"status": "configured", "channels": channels}
@router.post("/api/delivery-router/dispatch")
def delivery_router_dispatch(payload: dict = Body(...)):
    session = _require_user()
    email = session.get("email")
    queue_id = str(payload.get("queue_id") or "")
    channel = str(payload.get("channel") or "portal")
    data = _load(email)
    scheduler_data = _scheduler()._load(email)
    item = next((q for q in scheduler_data.get("queue", []) if q.get("queue_id") == queue_id), None)
    if not item: return {"status": "queue_item_not_found"}
    if not data.get("channels", {}).get(channel, {}).get("enabled", False): return {"status": "channel_disabled"}
    delivery = {"delivery_id": f"delivery_{int(time.time())}", "queue_id": queue_id, "channel": channel, "title": item.get("title"), "packet_id": item.get("packet_id"), "report_id": item.get("report_id"), "status": "delivered", "delivered_at": int(time.time()), "notes": str(payload.get("notes") or "")}
    data.setdefault("deliveries", []).insert(0, delivery)
    data["deliveries"] = data["deliveries"][:500]
    item["status"] = "delivered"
    item["delivered_at"] = int(time.time())
    _scheduler()._save(email, scheduler_data)
    _log_event(data, "dispatched", {"delivery_id": delivery["delivery_id"], "queue_id": queue_id, "channel": channel})
    _save(email, data)
    return {"status": "delivered", "delivery": delivery}
@router.get("/api/delivery-router/summary")
def delivery_router_summary():
    session = _require_user()
    email = session.get("email")
    data = _load(email)
    deliveries = data.get("deliveries", [])
    latest = deliveries[0] if deliveries else None
    by_channel = {}
    for d in deliveries:
        by_channel[d.get("channel")] = by_channel.get(d.get("channel"), 0) + 1
    return {"email": email, "channel_count": len(data.get("channels", {})), "delivery_count": len(deliveries), "latest_delivery": latest, "channels": data.get("channels", {}), "deliveries": deliveries[:100], "audit_log": data.get("audit_log", [])[:100], "deliveries_by_channel": by_channel}
