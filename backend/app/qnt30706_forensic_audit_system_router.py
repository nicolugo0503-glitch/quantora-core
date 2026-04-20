from fastapi import APIRouter, Body, HTTPException
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import time

router = APIRouter(tags=["forensic-audit-system"])

PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
FORENSIC_DIR = ARTIFACTS_DIR / "forensic_audit_system"
DEFAULT_POLICY = {
    "retain_snapshots": 200,
    "retain_incidents": 120,
    "auto_capture_on_bootstrap": True,
    "require_chain_integrity": True,
    "critical_break_threshold": 1,
}


def _mu():
    from backend.app import qnt30557_multi_user_router as mu
    return mu


def _audit():
    from backend.app import qnt30602_audit_trail_router as audit
    return audit


def _release():
    from backend.app import qnt30700_institutional_release_control_router as release
    return release


def _operator():
    from backend.app import qnt30702_operator_command_console_router as op
    return op


def _safety():
    from backend.app import qnt30703_live_broker_safety_layer_router as safety
    return safety


def _delivery():
    from backend.app import qnt30704_investor_delivery_pack_system_router as delivery
    return delivery


def _fund_admin():
    from backend.app import qnt30705_fund_admin_control_center_router as facc
    return facc


def _safe(v: str) -> str:
    return hashlib.sha256((v or "").strip().lower().encode("utf-8")).hexdigest()[:24]


def _path(email: str) -> Path:
    FORENSIC_DIR.mkdir(parents=True, exist_ok=True)
    return FORENSIC_DIR / f"{_safe(email)}.json"


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
            "snapshots": [],
            "incidents": [],
            "acknowledgements": [],
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


def _append(store: dict, key: str, row: dict, limit: int):
    store.setdefault(key, []).insert(0, row)
    store[key] = store.get(key, [])[:limit]


def _chain_summary(email: str) -> dict:
    s = _audit().audit_summary()
    return {
        "chain_integrity_ok": bool(s.get("chain_integrity_ok")),
        "record_count": int(s.get("record_count") or 0),
        "evidence_record_count": int(s.get("evidence_record_count") or 0),
        "latest_record": s.get("latest_record"),
    }


def _cross_system_snapshot(email: str) -> dict:
    release = _release()._summary_for_email(email)
    operator = _operator()._summary_for_email(email)
    safety = _safety()._summary_for_email(email)
    delivery = _delivery()._summary_for_email(email)
    fund_admin = _fund_admin()._summary_for_email(email)
    chain = _chain_summary(email)
    return {
        "captured_at": _now_iso(),
        "release": {
            "active_version": release.get("active_version"),
            "pending_release_count": release.get("pending_release_count"),
            "latest_event": release.get("latest_event"),
        },
        "operator": {
            "active_mode": operator.get("active_mode"),
            "kill_switch": operator.get("kill_switch"),
            "watchlist_count": operator.get("watchlist_count"),
            "latest_command": operator.get("latest_command"),
        },
        "safety": {
            "posture": (safety.get("safety_layer_status") or {}).get("posture"),
            "production_ready": (safety.get("safety_layer_status") or {}).get("production_ready"),
            "kill_switch": (safety.get("safety_layer_status") or {}).get("kill_switch"),
            "blocked_trade_count": safety.get("blocked_trade_count"),
            "latest_decision": safety.get("latest_decision"),
        },
        "delivery": {
            "pending_ack_count": delivery.get("pending_ack_count"),
            "delivered_count": delivery.get("delivered_count"),
            "latest_delivery_event": delivery.get("latest_delivery_event"),
        },
        "fund_admin": {
            "readiness": (fund_admin.get("fund_admin_status") or {}).get("readiness"),
            "aum": fund_admin.get("aum"),
            "reconciliation": fund_admin.get("reconciliation"),
            "latest_close": (fund_admin.get("close_runs") or [None])[0],
        },
        "audit_chain": chain,
    }


def _severity(snapshot: dict) -> str:
    safety = snapshot.get("safety") or {}
    fund_admin = snapshot.get("fund_admin") or {}
    audit_chain = snapshot.get("audit_chain") or {}
    delivery = snapshot.get("delivery") or {}
    if not audit_chain.get("chain_integrity_ok"):
        return "critical"
    if str(safety.get("posture") or "").upper() == "BLOCKED":
        return "critical"
    recon = (fund_admin.get("reconciliation") or {})
    if str((fund_admin.get("readiness") or "")).lower() == "blocked":
        return "critical"
    if str(recon.get("status") or "").lower() == "break":
        return "high"
    if int(delivery.get("pending_ack_count") or 0) > 10:
        return "high"
    if str((fund_admin.get("readiness") or "")).lower() == "attention":
        return "medium"
    return "normal"


def _summary_for_email(email: str) -> dict:
    store = _load(email)
    policy = store.get("policy") or dict(DEFAULT_POLICY)
    snapshots = store.get("snapshots") or []
    incidents = store.get("incidents") or []
    acks = store.get("acknowledgements") or []
    current = _cross_system_snapshot(email)
    critical_open = [i for i in incidents if i.get("status") != "closed" and i.get("severity") == "critical"]
    high_open = [i for i in incidents if i.get("status") != "closed" and i.get("severity") == "high"]
    posture = "ready"
    blockers = []
    if policy.get("require_chain_integrity") and not bool((current.get("audit_chain") or {}).get("chain_integrity_ok")):
        posture = "blocked"
        blockers.append("audit chain integrity failure")
    if int(len(critical_open)) >= int(policy.get("critical_break_threshold") or 1):
        posture = "blocked"
        blockers.append("critical forensic incidents open")
    elif high_open and posture != "blocked":
        posture = "attention"
        blockers.append("high severity forensic incidents open")
    return {
        "mission": "QNT30706",
        "generated_at": _now_iso(),
        "policy": policy,
        "forensic_status": {
            "posture": posture,
            "blockers": blockers,
            "critical_open_count": len(critical_open),
            "high_open_count": len(high_open),
            "ack_count": len(acks),
        },
        "current_snapshot": current,
        "snapshot_count": len(snapshots),
        "incident_count": len(incidents),
        "latest_snapshot": snapshots[0] if snapshots else None,
        "latest_incident": incidents[0] if incidents else None,
        "snapshots": snapshots[:20],
        "incidents": incidents[:20],
        "acknowledgements": acks[:20],
    }


@router.get("/api/forensic-audit-system/summary")
def forensic_audit_system_summary():
    session = _require_user()
    return _summary_for_email(session.get("email"))


@router.post("/api/forensic-audit-system/capture-snapshot")
def forensic_audit_system_capture_snapshot(payload: dict = Body(default=None)):
    session = _require_user()
    email = str((payload or {}).get("email") or session.get("email"))
    store = _load(email)
    policy = store.get("policy") or dict(DEFAULT_POLICY)
    snapshot = _cross_system_snapshot(email)
    snapshot["snapshot_id"] = f"forensic_snapshot_{_now_ts()}_{len(store.get('snapshots') or []) + 1}"
    snapshot["severity"] = _severity(snapshot)
    _append(store, "snapshots", snapshot, int(policy.get("retain_snapshots") or 200))
    _save(email, store)
    return {"status": "captured", "snapshot": snapshot, "summary": _summary_for_email(email)}


@router.post("/api/forensic-audit-system/reconstruct-incident")
def forensic_audit_system_reconstruct_incident(payload: dict = Body(...)):
    session = _require_user()
    email = str(payload.get("email") or session.get("email"))
    store = _load(email)
    policy = store.get("policy") or dict(DEFAULT_POLICY)
    title = str(payload.get("title") or "Forensic incident")
    trigger = str(payload.get("trigger") or "manual reconstruction")
    snapshot = _cross_system_snapshot(email)
    severity = str(payload.get("severity") or _severity(snapshot))
    incident = {
        "incident_id": f"incident_{_now_ts()}_{len(store.get('incidents') or []) + 1}",
        "title": title,
        "trigger": trigger,
        "severity": severity,
        "status": str(payload.get("status") or ("closed" if severity == "normal" else "open")),
        "operator_note": str(payload.get("operator_note") or ""),
        "reconstructed_at": _now_iso(),
        "timeline": [
            {"step": "release context", "data": snapshot.get("release")},
            {"step": "operator context", "data": snapshot.get("operator")},
            {"step": "safety context", "data": snapshot.get("safety")},
            {"step": "delivery context", "data": snapshot.get("delivery")},
            {"step": "fund admin context", "data": snapshot.get("fund_admin")},
            {"step": "audit chain", "data": snapshot.get("audit_chain")},
        ],
        "snapshot": snapshot,
    }
    _append(store, "incidents", incident, int(policy.get("retain_incidents") or 120))
    _save(email, store)
    return {"status": "reconstructed", "incident": incident, "summary": _summary_for_email(email)}


@router.post("/api/forensic-audit-system/acknowledge")
def forensic_audit_system_acknowledge(payload: dict = Body(...)):
    session = _require_user()
    email = str(payload.get("email") or session.get("email"))
    store = _load(email)
    ack = {
        "ack_id": f"ack_{_now_ts()}_{len(store.get('acknowledgements') or []) + 1}",
        "incident_id": str(payload.get("incident_id") or ""),
        "status": str(payload.get("status") or "reviewed"),
        "owner": str(payload.get("owner") or email),
        "note": str(payload.get("note") or ""),
        "acknowledged_at": _now_iso(),
    }
    target_id = ack.get("incident_id")
    for item in store.get("incidents") or []:
        if item.get("incident_id") == target_id:
            item["status"] = "closed" if ack["status"] in {"closed", "resolved"} else item.get("status")
            item["resolution_note"] = ack["note"]
            item["owner"] = ack["owner"]
            item["resolved_at"] = ack["acknowledged_at"] if item.get("status") == "closed" else item.get("resolved_at")
            break
    _append(store, "acknowledgements", ack, 200)
    _save(email, store)
    return {"status": "acknowledged", "acknowledgement": ack, "summary": _summary_for_email(email)}


@router.post("/api/forensic-audit-system/policy")
def forensic_audit_system_policy(payload: dict = Body(...)):
    session = _require_user()
    email = str(payload.get("email") or session.get("email"))
    store = _load(email)
    policy = dict(DEFAULT_POLICY)
    policy.update(store.get("policy") or {})
    incoming = payload.get("policy") if isinstance(payload.get("policy"), dict) else payload
    policy.update({k: v for k, v in incoming.items() if k in DEFAULT_POLICY})
    store["policy"] = policy
    _save(email, store)
    return {"status": "configured", "policy": policy, "summary": _summary_for_email(email)}


@router.post("/api/forensic-audit-system/bootstrap-demo")
def forensic_audit_system_bootstrap_demo(payload: dict = Body(default=None)):
    session = _require_user()
    email = str((payload or {}).get("email") or session.get("email"))
    _audit().audit_add_evidence({
        "title": "bootstrap evidence",
        "description": "forensic audit bootstrap control evidence",
        "evidence_type": "bootstrap",
        "reference_id": "QNT30706",
    })
    store = _load(email)
    if (payload or {}).get("policy"):
        store["policy"] = {**dict(DEFAULT_POLICY), **dict((payload or {}).get("policy") or {})}
    _save(email, store)
    snap = forensic_audit_system_capture_snapshot({"email": email})
    incident = forensic_audit_system_reconstruct_incident({
        "email": email,
        "title": "bootstrap forensic walkthrough",
        "trigger": "institutional bootstrap",
        "severity": "medium",
        "status": "open",
        "operator_note": str((payload or {}).get("notes") or "forensic baseline established"),
    })
    return {
        "status": "bootstrapped",
        "snapshot": snap.get("snapshot"),
        "incident": incident.get("incident"),
        "summary": _summary_for_email(email),
    }
