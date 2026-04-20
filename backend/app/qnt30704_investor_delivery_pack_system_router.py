from fastapi import APIRouter, Body, HTTPException
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import time

router = APIRouter(tags=["investor-delivery-pack-system"])

PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
DELIVERY_DIR = ARTIFACTS_DIR / "investor_delivery_pack_system"

DEFAULT_TEMPLATE = {
    "template_id": "tmpl_institutional_standard",
    "name": "institutional standard delivery pack",
    "sections": [
        "cover_letter",
        "performance_summary",
        "lp_statement",
        "nav_snapshot",
        "waterfall_summary",
        "risk_and_controls",
        "delivery_log",
    ],
    "channel": "portal_simulated",
    "requires_operator_note": True,
    "distribution_policy": "investor_safe",
}

DEFAULT_POLICY = {
    "default_channel": "portal_simulated",
    "require_acknowledgement": True,
    "max_pending_packs": 50,
    "block_if_safety_posture_blocked": True,
    "block_if_kill_switch": True,
}

DEMO_EMAIL = "operator@quantora.test"


def _mu():
    from backend.app import qnt30557_multi_user_router as mu
    return mu


def _statement_pack():
    from backend.app import qnt30588_statement_pack_router as packs
    return packs


def _delivery_log():
    from backend.app import qnt30589_report_delivery_log_router as log
    return log


def _calendar():
    from backend.app import qnt30590_reporting_calendar_router as cal
    return cal


def _safety():
    from backend.app import qnt30703_live_broker_safety_layer_router as safety
    return safety


def _release():
    from backend.app import qnt30700_institutional_release_control_router as rel
    return rel


def _operator():
    from backend.app import qnt30702_operator_command_console_router as op
    return op


def _safe(value: str) -> str:
    return hashlib.sha256((value or "").strip().lower().encode("utf-8")).hexdigest()[:24]


def _path(email: str) -> Path:
    DELIVERY_DIR.mkdir(parents=True, exist_ok=True)
    return DELIVERY_DIR / f"{_safe(email)}.json"


def _require_user():
    return _mu()._require_session()


def _now_ts() -> int:
    return int(time.time())


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load(email: str) -> dict:
    path = _path(email)
    if not path.exists():
        data = {
            "email": email,
            "policy": dict(DEFAULT_POLICY),
            "templates": [dict(DEFAULT_TEMPLATE)],
            "recipient_registry": [],
            "packs": [],
            "delivery_events": [],
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


def _upsert_recipient(store: dict, recipient: dict) -> dict:
    email = (recipient.get("email") or "").strip().lower()
    if not email:
        raise HTTPException(status_code=400, detail="recipient email required")
    registry = store.setdefault("recipient_registry", [])
    existing = next((r for r in registry if (r.get("email") or "").strip().lower() == email), None)
    payload = {
        "email": email,
        "investor_name": recipient.get("investor_name") or recipient.get("name") or email.split("@")[0].replace(".", " ").title(),
        "entity": recipient.get("entity") or "LP",
        "channel": recipient.get("channel") or (store.get("policy") or {}).get("default_channel") or "portal_simulated",
        "status": recipient.get("status") or "active",
        "last_delivery_at": recipient.get("last_delivery_at"),
        "notes": recipient.get("notes") or "",
    }
    if existing:
        existing.update(payload)
        return existing
    registry.insert(0, payload)
    store["recipient_registry"] = registry[:500]
    return payload


def _latest_release(email: str) -> dict:
    try:
        return (_release()._summary_for_email(email) or {}).get("latest_release") or {}
    except Exception:
        return {}


def _safety_summary(email: str) -> dict:
    try:
        return _safety()._summary_for_email(email) or {}
    except Exception:
        return {}


def _operator_summary(email: str) -> dict:
    try:
        return _operator()._summary_for_email(email) or {}
    except Exception:
        return {}


def _base_pack(email: str) -> dict:
    packs = _statement_pack()
    base = packs._build_pack(email)
    pack_store = packs._load(email)
    if not any((p.get("pack_id") == base.get("pack_id")) for p in (pack_store.get("packs") or [])):
        pack_store.setdefault("packs", []).insert(0, base)
        packs._save(email, pack_store)
    return base


def _reporting_calendar_snapshot(email: str) -> dict:
    cal = _calendar()._load(email)
    events = cal.get("events") or []
    history = cal.get("history") or []
    return {
        "event_count": len(events),
        "scheduled_count": len([e for e in events if e.get("status") == "scheduled"]),
        "executed_count": len([e for e in events if e.get("status") == "executed"]),
        "latest_event": history[0] if history else None,
    }


def _delivery_log_snapshot(email: str) -> dict:
    log = _delivery_log()._load(email)
    events = log.get("events") or []
    return {
        "delivery_count": len(events),
        "acknowledged_count": len([e for e in events if e.get("ack_status") == "acknowledged"]),
        "pending_ack_count": len([e for e in events if e.get("ack_status") == "pending"]),
        "latest_event": events[0] if events else None,
    }


def _build_delivery_pack_for_email(email: str, payload: dict | None = None) -> dict:
    payload = payload or {}
    store = _load(email)
    policy = store.get("policy") or dict(DEFAULT_POLICY)
    safety = _safety_summary(email)
    posture = ((safety.get("safety_layer_status") or {}).get("posture") or safety.get("posture") or "UNKNOWN").upper()
    kill_switch = bool((safety.get("controls") or {}).get("kill_switch") or (safety.get("safety_layer_status") or {}).get("kill_switch") or False)
    if bool(policy.get("block_if_safety_posture_blocked")) and posture == "BLOCKED":
        raise HTTPException(status_code=409, detail="delivery blocked while safety posture is BLOCKED")
    if bool(policy.get("block_if_kill_switch")) and kill_switch:
        raise HTTPException(status_code=409, detail="delivery blocked while kill switch is active")
    if len(store.get("packs") or []) >= int(policy.get("max_pending_packs") or 50):
        raise HTTPException(status_code=409, detail="delivery pack queue above configured limit")

    template_id = payload.get("template_id") or DEFAULT_TEMPLATE["template_id"]
    template = next((t for t in (store.get("templates") or []) if t.get("template_id") == template_id), None)
    if not template:
        raise HTTPException(status_code=404, detail="template not found")

    recipients = payload.get("recipients") or store.get("recipient_registry") or []
    normalized_recipients = []
    for recipient in recipients[:250]:
        normalized_recipients.append(_upsert_recipient(store, recipient))

    base = _base_pack(email)
    release = _latest_release(email)
    operator = _operator_summary(email)
    calendar = _reporting_calendar_snapshot(email)
    log_summary = _delivery_log_snapshot(email)

    pack_id = f"idp_{_now_ts()}_{len(store.get('packs') or [])+1:03d}"
    channel = payload.get("channel") or template.get("channel") or policy.get("default_channel") or "portal_simulated"
    title = payload.get("title") or "Investor Delivery Pack"
    note = payload.get("operator_note") or payload.get("cover_message") or "Institutional delivery pack generated by Quantora."

    pack = {
        "pack_id": pack_id,
        "mission": "QNT30704",
        "generated_at": _now_iso(),
        "email": email,
        "title": title,
        "template_id": template_id,
        "template_name": template.get("name"),
        "channel": channel,
        "operator_note": note,
        "recipient_count": len(normalized_recipients),
        "recipient_preview": normalized_recipients[:10],
        "base_statement_pack": base,
        "reporting_calendar": calendar,
        "delivery_log": log_summary,
        "release_context": {
            "active_version": (_release()._summary_for_email(email) or {}).get("active_version"),
            "latest_release": release,
        },
        "operator_context": {
            "active_mode": operator.get("active_mode"),
            "status": operator.get("operator_console_status"),
        },
        "risk_and_controls": {
            "safety_posture": posture,
            "kill_switch": kill_switch,
            "production_ready": (safety.get("safety_layer_status") or {}).get("production_ready"),
        },
        "sections": [
            {"name": section, "status": "included"} for section in (template.get("sections") or [])
        ],
        "delivery_status": "generated",
        "ack_required": bool(policy.get("require_acknowledgement")),
        "delivered_at": None,
    }
    store.setdefault("packs", []).insert(0, pack)
    store["packs"] = store["packs"][:500]
    _save(email, store)
    return pack


def _deliver_pack_for_email(email: str, payload: dict) -> dict:
    store = _load(email)
    pack_id = (payload.get("pack_id") or "").strip()
    if not pack_id:
        raise HTTPException(status_code=400, detail="pack_id required")
    pack = next((p for p in (store.get("packs") or []) if p.get("pack_id") == pack_id), None)
    if not pack:
        raise HTTPException(status_code=404, detail="delivery pack not found")

    channel = (payload.get("channel") or pack.get("channel") or (store.get("policy") or {}).get("default_channel") or "portal_simulated").strip().lower()
    delivery_event = {
        "event_id": f"idp_evt_{_now_ts()}_{len(store.get('delivery_events') or [])+1:03d}",
        "pack_id": pack_id,
        "channel": channel,
        "recipient_count": int(pack.get("recipient_count") or 0),
        "status": "delivered",
        "ack_status": "pending" if pack.get("ack_required") else "not_required",
        "delivered_at": _now_iso(),
        "notes": payload.get("notes") or "",
    }
    pack["delivery_status"] = delivery_event["status"]
    pack["channel"] = channel
    pack["delivered_at"] = delivery_event["delivered_at"]

    for recipient in store.get("recipient_registry") or []:
        recipient["last_delivery_at"] = delivery_event["delivered_at"]

    store.setdefault("delivery_events", []).insert(0, delivery_event)
    store["delivery_events"] = store["delivery_events"][:500]
    _save(email, store)

    log = _delivery_log()._load(email)
    log_event = {
        "event_id": delivery_event["event_id"],
        "pack_id": pack_id,
        "channel": channel,
        "delivery_status": "delivered",
        "ack_status": delivery_event["ack_status"],
        "delivered_at": _now_ts(),
        "acknowledged_at": None,
        "notes": delivery_event["notes"],
    }
    log.setdefault("events", []).insert(0, log_event)
    log["events"] = log["events"][:500]
    _delivery_log()._save(email, log)

    return {
        "status": "delivered",
        "pack": pack,
        "delivery_event": delivery_event,
        "summary": _summary_for_email(email),
    }


def _summary_for_email(email: str) -> dict:
    store = _load(email)
    packs = store.get("packs") or []
    delivery_events = store.get("delivery_events") or []
    latest = packs[0] if packs else None
    delivered = [p for p in packs if p.get("delivery_status") == "delivered"]
    pending_ack = [e for e in delivery_events if e.get("ack_status") == "pending"]
    safety = _safety_summary(email)
    operator = _operator_summary(email)
    release = _latest_release(email)
    return {
        "mission": "QNT30704",
        "generated_at": _now_iso(),
        "policy": store.get("policy") or dict(DEFAULT_POLICY),
        "template_count": len(store.get("templates") or []),
        "recipient_count": len(store.get("recipient_registry") or []),
        "pack_count": len(packs),
        "delivered_count": len(delivered),
        "pending_ack_count": len(pending_ack),
        "latest_pack": latest,
        "packs": packs[:20],
        "delivery_events": delivery_events[:20],
        "recipient_registry": (store.get("recipient_registry") or [])[:50],
        "calendar": _reporting_calendar_snapshot(email),
        "linked_statement_pack_summary": {
            "pack_count": len((_statement_pack()._load(email).get("packs") or [])),
        },
        "institutional_context": {
            "safety_posture": ((safety.get("safety_layer_status") or {}).get("posture") or safety.get("posture") or "UNKNOWN"),
            "operator_mode": operator.get("active_mode"),
            "active_release_version": (_release()._summary_for_email(email) or {}).get("active_version"),
            "latest_release": release,
        },
        "delivery_pack_status": {
            "standardized_output": True,
            "investor_ready": bool(latest),
            "blocked": ((safety.get("safety_layer_status") or {}).get("posture") or "").upper() == "BLOCKED",
            "default_channel": (store.get("policy") or {}).get("default_channel"),
        },
    }


def _bootstrap_demo_for_email(email: str) -> dict:
    _safety()._bootstrap_demo_for_email(email)
    store = _load(email)
    if not store.get("recipient_registry"):
        for recipient in [
            {"email": "allocator.alpha@example.com", "investor_name": "Allocator Alpha", "entity": "Family Office", "channel": "portal_simulated"},
            {"email": "capital.beta@example.com", "investor_name": "Capital Beta", "entity": "RIA", "channel": "secure_email_simulated"},
        ]:
            _upsert_recipient(store, recipient)
        _save(email, store)
    if not (_calendar()._load(email).get("events") or []):
        _calendar()._load(email)
    if not store.get("packs"):
        _build_delivery_pack_for_email(email, {"title": "Institutional Monthly Delivery Pack"})
    return _summary_for_email(email)


@router.get("/api/investor-delivery-pack-system/summary")
def investor_delivery_pack_system_summary():
    session = _require_user()
    return _summary_for_email(session.get("email"))


@router.post("/api/investor-delivery-pack-system/build")
def investor_delivery_pack_system_build(payload: dict = Body(None)):
    session = _require_user()
    email = session.get("email")
    pack = _build_delivery_pack_for_email(email, payload or {})
    return {"status": "generated", "pack": pack, "summary": _summary_for_email(email)}


@router.post("/api/investor-delivery-pack-system/deliver")
def investor_delivery_pack_system_deliver(payload: dict = Body(...)):
    session = _require_user()
    return _deliver_pack_for_email(session.get("email"), payload)


@router.post("/api/investor-delivery-pack-system/template")
def investor_delivery_pack_system_template(payload: dict = Body(...)):
    session = _require_user()
    email = session.get("email")
    store = _load(email)
    template_id = payload.get("template_id") or f"tmpl_{_now_ts()}"
    template = {
        "template_id": template_id,
        "name": payload.get("name") or "custom investor delivery pack",
        "sections": payload.get("sections") or list(DEFAULT_TEMPLATE["sections"]),
        "channel": payload.get("channel") or (store.get("policy") or {}).get("default_channel") or "portal_simulated",
        "requires_operator_note": bool(payload.get("requires_operator_note", True)),
        "distribution_policy": payload.get("distribution_policy") or "investor_safe",
    }
    templates = [t for t in (store.get("templates") or []) if t.get("template_id") != template_id]
    templates.insert(0, template)
    store["templates"] = templates[:100]
    for recipient in payload.get("recipients") or []:
        _upsert_recipient(store, recipient)
    if payload.get("policy"):
        store["policy"] = {**dict(DEFAULT_POLICY), **(store.get("policy") or {}), **dict(payload.get("policy") or {})}
    _save(email, store)
    return {"status": "configured", "template": template, "summary": _summary_for_email(email)}


@router.post("/api/investor-delivery-pack-system/bootstrap-demo")
def investor_delivery_pack_system_bootstrap_demo(payload: dict = Body(None)):
    email = ((payload or {}).get("email") or DEMO_EMAIL).strip().lower()
    return {"status": "bootstrapped", "summary": _bootstrap_demo_for_email(email)}
