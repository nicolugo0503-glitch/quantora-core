from fastapi import APIRouter, Body
from pathlib import Path
import json, time, hashlib
router = APIRouter(tags=["governance-attestation"])
PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
GOV_DIR = ARTIFACTS_DIR / "governance_attestation"
def _mu():
    from backend.app import qnt30557_multi_user_router as mu
    return mu
def _supervisory():
    from backend.app import qnt30609_supervisory_control_router as sup
    return sup
def _alerts():
    from backend.app import qnt30606_break_alert_router as alerts
    return alerts
def _safe(value: str) -> str:
    return hashlib.sha256((value or "").strip().lower().encode("utf-8")).hexdigest()[:24]
def _path(email: str) -> Path:
    GOV_DIR.mkdir(parents=True, exist_ok=True)
    return GOV_DIR / f"{_safe(email)}.json"
def _require_user():
    return _mu()._require_session()
def _load(email: str) -> dict:
    path = _path(email)
    if not path.exists():
        data = {"email": email, "attestations": [], "breach_snapshots": [], "created_at": int(time.time()), "updated_at": int(time.time())}
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return data
    return json.loads(path.read_text(encoding="utf-8"))
def _save(email: str, data: dict) -> dict:
    data["updated_at"] = int(time.time())
    _path(email).write_text(json.dumps(data, indent=2), encoding="utf-8")
    return data
def _build_breach_snapshot(email: str):
    sup_data = _supervisory()._load(email)
    escalations = sup_data.get("escalations", [])
    alerts_data = _alerts()._load(email)
    alerts = alerts_data.get("alerts", [])
    open_escalations = [e for e in escalations if e.get("status") in {"open", "acknowledged"}]
    high_open = [e for e in open_escalations if e.get("severity") == "high"]
    open_alerts = [a for a in alerts if a.get("status") in {"open", "acknowledged"}]
    high_alerts = [a for a in open_alerts if a.get("severity") == "high"]
    breach_status = "breach_detected" if high_open or high_alerts else ("warning" if open_escalations or open_alerts else "clear")
    return {"snapshot_id": f"breach_{int(time.time())}", "timestamp": int(time.time()), "status": breach_status, "open_escalation_count": len(open_escalations), "high_open_escalation_count": len(high_open), "open_alert_count": len(open_alerts), "high_open_alert_count": len(high_alerts), "open_escalations": open_escalations[:50], "open_alerts": open_alerts[:50]}
@router.get("/api/governance")
def governance():
    session = _require_user()
    return _load(session.get("email"))
@router.post("/api/governance/capture-breach-dashboard")
def governance_capture_breach_dashboard(payload: dict = Body(None)):
    session = _require_user()
    email = session.get("email")
    data = _load(email)
    snap = _build_breach_snapshot(email)
    if payload and payload.get("notes"):
        snap["notes"] = str(payload.get("notes"))
    data.setdefault("breach_snapshots", []).insert(0, snap)
    data["breach_snapshots"] = data["breach_snapshots"][:200]
    _save(email, data)
    return {"status": snap["status"], "snapshot": snap}
@router.post("/api/governance/attest")
def governance_attest(payload: dict = Body(...)):
    session = _require_user()
    email = session.get("email")
    attestor = str(payload.get("attestor") or "Operator")
    statement = str(payload.get("statement") or "Governance review completed.")
    data = _load(email)
    if not data.get("breach_snapshots"):
        snap = _build_breach_snapshot(email)
        data.setdefault("breach_snapshots", []).insert(0, snap)
    latest_snap = data["breach_snapshots"][0]
    attestation = {"attestation_id": f"att_{int(time.time())}", "attestor": attestor, "statement": statement, "related_snapshot_id": latest_snap.get("snapshot_id"), "snapshot_status": latest_snap.get("status"), "timestamp": int(time.time()), "status": "recorded"}
    data.setdefault("attestations", []).insert(0, attestation)
    data["attestations"] = data["attestations"][:200]
    _save(email, data)
    return {"status": "recorded", "attestation": attestation}
@router.get("/api/governance/summary")
def governance_summary():
    session = _require_user()
    email = session.get("email")
    data = _load(email)
    if not data.get("breach_snapshots"):
        snap = _build_breach_snapshot(email)
        data.setdefault("breach_snapshots", []).insert(0, snap)
        _save(email, data)
    latest_snap = data["breach_snapshots"][0]
    attestations = data.get("attestations", [])
    return {"email": email, "breach_snapshot_count": len(data.get("breach_snapshots", [])), "attestation_count": len(attestations), "latest_snapshot": latest_snap, "latest_attestation": attestations[0] if attestations else None, "breach_snapshots": data.get("breach_snapshots", [])[:50], "attestations": attestations[:50]}
