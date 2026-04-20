from fastapi import APIRouter, Body
from pathlib import Path
import json, time, hashlib

router = APIRouter(tags=["communication-preferences-notice-routing"])

PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
PREF_DIR = ARTIFACTS_DIR / "investor_communication_preferences"

DEFAULT_PREFERENCES = {
    "delivery_window": "business_hours",
    "language": "en",
    "preferred_channels": ["portal"],
    "urgent_notice_channel": "email_simulated",
    "digest_mode": "daily"
}

def _mu():
    from backend.app import qnt30557_multi_user_router as mu
    return mu

def _identity():
    from backend.app import qnt30617_identity_registry_router as identity
    return identity

def _safe(v):
    return hashlib.sha256((v or "").strip().lower().encode()).hexdigest()[:24]

def _path(email):
    PREF_DIR.mkdir(parents=True, exist_ok=True)
    return PREF_DIR / f"{_safe(email)}.json"

def _require_user():
    return _mu()._require_session()

def _load(email):
    p = _path(email)
    if not p.exists():
        d = {
            "email": email,
            "preferences": [],
            "routing_rules": [],
            "event_log": [],
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

def _find_pref(data, investor_id):
    return next((p for p in data.get("preferences", []) if p.get("investor_id") == investor_id), None)

def _find_rule(data, rule_id):
    return next((r for r in data.get("routing_rules", []) if r.get("rule_id") == rule_id), None)

def _log(data, event_type, payload):
    data.setdefault("event_log", []).insert(0, {
        "event_id": f"pref_{int(time.time())}_{len(data.get('event_log', []))+1}",
        "event_type": event_type,
        "payload": payload,
        "timestamp": int(time.time())
    })
    data["event_log"] = data.get("event_log", [])[:1000]

@router.get("/api/notice-routing")
def notice_routing():
    session = _require_user()
    return _load(session.get("email"))

@router.post("/api/notice-routing/preferences")
def set_preferences(payload: dict = Body(...)):
    session = _require_user()
    email = session.get("email")
    investor_id = str(payload.get("investor_id") or "")
    data = _load(email)
    pref = _find_pref(data, investor_id)
    prefs = DEFAULT_PREFERENCES.copy()
    prefs.update(payload.get("preferences") or {})
    if pref:
        pref["preferences"] = prefs
        pref["updated_at"] = int(time.time())
        item = pref
        status = "updated"
    else:
        item = {
            "preference_id": f"cp_{int(time.time())}",
            "investor_id": investor_id,
            "preferences": prefs,
            "created_at": int(time.time()),
            "updated_at": int(time.time())
        }
        data.setdefault("preferences", []).insert(0, item)
        status = "created"
    _log(data, "preferences_saved", {"investor_id": investor_id, "preferences": prefs})
    data["preferences"] = data.get("preferences", [])[:500]
    _save(email, data)
    return {"status": status, "preference": item}

@router.post("/api/notice-routing/rule")
def add_rule(payload: dict = Body(...)):
    session = _require_user()
    email = session.get("email")
    data = _load(email)
    item = {
        "rule_id": f"rule_{int(time.time())}",
        "rule_name": str(payload.get("rule_name") or "Default Notice Rule"),
        "notice_type": str(payload.get("notice_type") or "general"),
        "channel": str(payload.get("channel") or "portal"),
        "priority": str(payload.get("priority") or "normal"),
        "scope": str(payload.get("scope") or "all_investors"),
        "enabled": bool(payload.get("enabled", True)),
        "created_at": int(time.time())
    }
    data.setdefault("routing_rules", []).insert(0, item)
    data["routing_rules"] = data.get("routing_rules", [])[:500]
    _log(data, "routing_rule_created", item)
    _save(email, data)
    return {"status": "created", "rule": item}

@router.post("/api/notice-routing/rule/toggle")
def toggle_rule(payload: dict = Body(...)):
    session = _require_user()
    email = session.get("email")
    rule_id = str(payload.get("rule_id") or "")
    enabled = bool(payload.get("enabled", True))
    data = _load(email)
    rule = _find_rule(data, rule_id)
    if not rule:
        return {"status": "not_found"}
    rule["enabled"] = enabled
    rule["updated_at"] = int(time.time())
    _log(data, "routing_rule_toggled", {"rule_id": rule_id, "enabled": enabled})
    _save(email, data)
    return {"status": "updated", "rule": rule}

@router.post("/api/notice-routing/resolve")
def resolve_notice_route(payload: dict = Body(...)):
    session = _require_user()
    email = session.get("email")
    investor_id = str(payload.get("investor_id") or "")
    notice_type = str(payload.get("notice_type") or "general")
    urgency = str(payload.get("urgency") or "normal")
    data = _load(email)

    pref = _find_pref(data, investor_id)
    preferences = (pref or {}).get("preferences", DEFAULT_PREFERENCES.copy())
    enabled_rules = [r for r in data.get("routing_rules", []) if r.get("enabled")]

    chosen_rule = next((r for r in enabled_rules if r.get("notice_type") in {notice_type, "general"}), None)
    chosen_channel = None
    if urgency == "urgent":
        chosen_channel = preferences.get("urgent_notice_channel") or "email_simulated"
    elif chosen_rule:
        chosen_channel = chosen_rule.get("channel")
    else:
        pref_channels = preferences.get("preferred_channels") or ["portal"]
        chosen_channel = pref_channels[0]

    result = {
        "investor_id": investor_id,
        "notice_type": notice_type,
        "urgency": urgency,
        "resolved_channel": chosen_channel,
        "delivery_window": preferences.get("delivery_window"),
        "language": preferences.get("language"),
        "digest_mode": preferences.get("digest_mode"),
        "rule_id": chosen_rule.get("rule_id") if chosen_rule else None
    }
    _log(data, "notice_route_resolved", result)
    _save(email, data)
    return {"status": "resolved", "route": result}

@router.get("/api/notice-routing/summary")
def notice_routing_summary():
    session = _require_user()
    email = session.get("email")
    data = _load(email)
    preferences = data.get("preferences", [])
    rules = data.get("routing_rules", [])
    enabled_rules = sum(1 for r in rules if r.get("enabled"))
    latest_rule = rules[0] if rules else None
    latest_pref = preferences[0] if preferences else None
    return {
        "email": email,
        "preference_count": len(preferences),
        "rule_count": len(rules),
        "enabled_rule_count": enabled_rules,
        "latest_preference": latest_pref,
        "latest_rule": latest_rule,
        "preferences": preferences[:100],
        "routing_rules": rules[:100],
        "event_log": data.get("event_log", [])[:100]
    }
