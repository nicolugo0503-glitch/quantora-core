from fastapi import APIRouter, Body
from pathlib import Path
import json, time, hashlib, datetime

router = APIRouter(tags=["notification-campaign-engine"])

PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
CAMPAIGN_DIR = ARTIFACTS_DIR / "investor_notification_campaigns"

def _mu():
    from backend.app import qnt30557_multi_user_router as mu
    return mu

def _identity():
    from backend.app import qnt30617_identity_registry_router as identity
    return identity

def _routing():
    from backend.app import qnt30618_notice_routing_router as routing
    return routing

def _safe(v):
    return hashlib.sha256((v or "").strip().lower().encode()).hexdigest()[:24]

def _path(email):
    CAMPAIGN_DIR.mkdir(parents=True, exist_ok=True)
    return CAMPAIGN_DIR / f"{_safe(email)}.json"

def _require_user():
    return _mu()._require_session()

def _load(email):
    p = _path(email)
    if not p.exists():
        d = {
            "email": email,
            "campaigns": [],
            "batches": [],
            "created_at": int(time.time()),
            "updated_at": int(time.time())
        }
        p.write_text(json.dumps(d, indent=2), encoding="utf-8")
        return d
    return json.loads(p.read_text(encoding="utf-8"))

def _save(email, d):
    d["updated_at"] = int(time.time())
    _path(email).write_text(json.dumps(d, indent=2), encoding="utf-8")
    return d

def _utc_date():
    return datetime.datetime.utcnow().strftime("%Y-%m-%d")

def _active_profiles(email):
    data = _identity()._load(email)
    return [p for p in data.get("profiles", []) if p.get("status") == "active"]

def _resolve_route(email, investor_id, notice_type, urgency):
    data = _routing()._load(email)
    pref = next((p for p in data.get("preferences", []) if p.get("investor_id") == investor_id), None)
    preferences = (pref or {}).get("preferences", {})
    enabled_rules = [r for r in data.get("routing_rules", []) if r.get("enabled")]
    chosen_rule = next((r for r in enabled_rules if r.get("notice_type") in {notice_type, "general"}), None)
    if urgency == "urgent":
        channel = preferences.get("urgent_notice_channel") or "email_simulated"
    elif chosen_rule:
        channel = chosen_rule.get("channel")
    else:
        channels = preferences.get("preferred_channels") or ["portal"]
        channel = channels[0]
    return {
        "channel": channel,
        "language": preferences.get("language", "en"),
        "delivery_window": preferences.get("delivery_window", "business_hours"),
        "digest_mode": preferences.get("digest_mode", "daily"),
        "rule_id": chosen_rule.get("rule_id") if chosen_rule else None
    }

@router.get("/api/notification-campaigns")
def notification_campaigns():
    session = _require_user()
    return _load(session.get("email"))

@router.post("/api/notification-campaigns/create")
def create_campaign(payload: dict = Body(...)):
    session = _require_user()
    email = session.get("email")
    data = _load(email)
    item = {
        "campaign_id": f"camp_{int(time.time())}",
        "campaign_name": str(payload.get("campaign_name") or "Investor Notice Campaign"),
        "notice_type": str(payload.get("notice_type") or "general"),
        "urgency": str(payload.get("urgency") or "normal"),
        "subject": str(payload.get("subject") or "Investor Notice"),
        "message": str(payload.get("message") or ""),
        "target_scope": str(payload.get("target_scope") or "all_active_profiles"),
        "status": "draft",
        "created_at": int(time.time())
    }
    data.setdefault("campaigns", []).insert(0, item)
    data["campaigns"] = data.get("campaigns", [])[:500]
    _save(email, data)
    return {"status": "created", "campaign": item}

@router.post("/api/notification-campaigns/batch")
def generate_batch(payload: dict = Body(...)):
    session = _require_user()
    email = session.get("email")
    campaign_id = str(payload.get("campaign_id") or "")
    data = _load(email)
    campaign = next((c for c in data.get("campaigns", []) if c.get("campaign_id") == campaign_id), None)
    if not campaign:
        return {"status": "campaign_not_found"}

    profiles = _active_profiles(email)
    deliveries = []
    for profile in profiles:
        investor_id = str(profile.get("investor_id") or "")
        route = _resolve_route(email, investor_id, campaign.get("notice_type"), campaign.get("urgency"))
        deliveries.append({
            "investor_id": investor_id,
            "profile_id": profile.get("profile_id"),
            "profile_name": profile.get("profile_name"),
            "recipient_count": len(profile.get("recipients", [])),
            "channel": route.get("channel"),
            "language": route.get("language"),
            "delivery_window": route.get("delivery_window"),
            "digest_mode": route.get("digest_mode"),
            "rule_id": route.get("rule_id"),
            "status": "scheduled"
        })

    batch = {
        "batch_id": f"batch_{int(time.time())}",
        "campaign_id": campaign_id,
        "campaign_name": campaign.get("campaign_name"),
        "date": _utc_date(),
        "scheduled_for": str(payload.get("scheduled_for") or _utc_date()),
        "delivery_count": len(deliveries),
        "deliveries": deliveries[:500],
        "status": "scheduled",
        "created_at": int(time.time())
    }
    data.setdefault("batches", []).insert(0, batch)
    data["batches"] = data.get("batches", [])[:500]
    campaign["status"] = "scheduled"
    campaign["last_batch_id"] = batch["batch_id"]
    _save(email, data)
    return {"status": "scheduled", "batch": batch}

@router.post("/api/notification-campaigns/batch/send")
def send_batch(payload: dict = Body(...)):
    session = _require_user()
    email = session.get("email")
    batch_id = str(payload.get("batch_id") or "")
    data = _load(email)
    batch = next((b for b in data.get("batches", []) if b.get("batch_id") == batch_id), None)
    if not batch:
        return {"status": "batch_not_found"}
    batch["status"] = "sent"
    batch["sent_at"] = int(time.time())
    for d in batch.get("deliveries", []):
        d["status"] = "sent"
    _save(email, data)
    return {"status": "sent", "batch": batch}

@router.get("/api/notification-campaigns/summary")
def notification_campaigns_summary():
    session = _require_user()
    email = session.get("email")
    data = _load(email)
    campaigns = data.get("campaigns", [])
    batches = data.get("batches", [])
    scheduled = sum(1 for b in batches if b.get("status") == "scheduled")
    sent = sum(1 for b in batches if b.get("status") == "sent")
    latest_campaign = campaigns[0] if campaigns else None
    latest_batch = batches[0] if batches else None
    return {
        "email": email,
        "campaign_count": len(campaigns),
        "batch_count": len(batches),
        "scheduled_batch_count": scheduled,
        "sent_batch_count": sent,
        "latest_campaign": latest_campaign,
        "latest_batch": latest_batch,
        "campaigns": campaigns[:100],
        "batches": batches[:100]
    }
