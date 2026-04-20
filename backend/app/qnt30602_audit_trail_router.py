from fastapi import APIRouter, Body
from pathlib import Path
import json, time, hashlib

router = APIRouter(tags=["immutable-audit-trail"])

PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
AUDIT_DIR = ARTIFACTS_DIR / "immutable_audit_trail"

def _mu():
    from backend.app import qnt30557_multi_user_router as mu
    return mu

def _recon():
    from backend.app import qnt30600_reconciliation_router as recon
    return recon

def _exc():
    from backend.app import qnt30601_exception_resolution_router as exc
    return exc

def _safe(value: str) -> str:
    return hashlib.sha256((value or "").strip().lower().encode("utf-8")).hexdigest()[:24]

def _hash_payload(payload: dict, previous_hash: str) -> str:
    canonical = json.dumps({"previous_hash": previous_hash, "payload": payload}, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

def _path(email: str) -> Path:
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    return AUDIT_DIR / f"{_safe(email)}.json"

def _require_user():
    return _mu()._require_session()

def _load(email: str) -> dict:
    path = _path(email)
    if not path.exists():
        data = {
            "email": email,
            "records": [],
            "created_at": int(time.time()),
            "updated_at": int(time.time()),
        }
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return data
    return json.loads(path.read_text(encoding="utf-8"))

def _save(email: str, data: dict) -> dict:
    data["updated_at"] = int(time.time())
    _path(email).write_text(json.dumps(data, indent=2), encoding="utf-8")
    return data

def _append_record(email: str, record_type: str, payload: dict):
    data = _load(email)
    previous_hash = data["records"][0]["record_hash"] if data.get("records") else "GENESIS"
    record = {
        "record_id": f"audit_{int(time.time())}_{len(data.get('records', []))+1}",
        "record_type": record_type,
        "timestamp": int(time.time()),
        "payload": payload,
        "previous_hash": previous_hash,
    }
    record["record_hash"] = _hash_payload({"record_type": record_type, "timestamp": record["timestamp"], "payload": payload}, previous_hash)
    data.setdefault("records", []).insert(0, record)
    data["records"] = data["records"][:1000]
    _save(email, data)
    return record

@router.get("/api/audit-trail")
def audit_trail():
    session = _require_user()
    return _load(session.get("email"))

@router.post("/api/audit-trail/capture-reconciliation")
def audit_capture_reconciliation(payload: dict = Body(None)):
    session = _require_user()
    email = session.get("email")
    recon_data = _recon()._load(email)
    latest = (recon_data.get("runs") or [None])[0]
    if latest is None:
        latest = _recon()._run_checks(email)
        recon_data.setdefault("runs", []).insert(0, latest)
        _recon()._save(email, recon_data)
    record = _append_record(email, "reconciliation_run", latest)
    return {"status": "captured", "record": record}

@router.post("/api/audit-trail/capture-exception-state")
def audit_capture_exception_state(payload: dict = Body(None)):
    session = _require_user()
    email = session.get("email")
    exc_data = _exc()._load(email)
    snapshot = {
        "exception_count": len(exc_data.get("exceptions", [])),
        "exceptions": exc_data.get("exceptions", [])[:50],
        "history": exc_data.get("history", [])[:50],
    }
    record = _append_record(email, "exception_state", snapshot)
    return {"status": "captured", "record": record}

@router.post("/api/audit-trail/evidence")
def audit_add_evidence(payload: dict = Body(...)):
    session = _require_user()
    email = session.get("email")
    evidence = {
        "title": str(payload.get("title") or "Control Evidence"),
        "description": str(payload.get("description") or ""),
        "evidence_type": str(payload.get("evidence_type") or "manual_note"),
        "reference_id": str(payload.get("reference_id") or ""),
    }
    record = _append_record(email, "control_evidence", evidence)
    return {"status": "captured", "record": record}

@router.get("/api/audit-trail/summary")
def audit_summary():
    session = _require_user()
    email = session.get("email")
    data = _load(email)
    records = data.get("records", [])
    reconciliation_records = sum(1 for r in records if r.get("record_type") == "reconciliation_run")
    exception_records = sum(1 for r in records if r.get("record_type") == "exception_state")
    evidence_records = sum(1 for r in records if r.get("record_type") == "control_evidence")
    latest = records[0] if records else None
    chain_ok = True
    prev = "GENESIS"
    for rec in reversed(records):
        expected_prev = prev
        if rec.get("previous_hash") != expected_prev:
            chain_ok = False
            break
        expected_hash = _hash_payload(
            {"record_type": rec.get("record_type"), "timestamp": rec.get("timestamp"), "payload": rec.get("payload")},
            rec.get("previous_hash")
        )
        if rec.get("record_hash") != expected_hash:
            chain_ok = False
            break
        prev = rec.get("record_hash")
    return {
        "email": email,
        "record_count": len(records),
        "reconciliation_record_count": reconciliation_records,
        "exception_record_count": exception_records,
        "evidence_record_count": evidence_records,
        "chain_integrity_ok": chain_ok,
        "latest_record": latest,
        "records": records[:100],
    }
