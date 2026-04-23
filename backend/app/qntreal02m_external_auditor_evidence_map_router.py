import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/external-auditor-evidence", tags=["external-auditor-evidence-map"])

ROOT = Path(__file__).resolve().parents[1]
STATE_DIR = ROOT / "app" / "state"
STATE_FILE = STATE_DIR / "external_auditor_evidence_map_state.json"

# Evidence source state files
_INTEGRITY_STATE = STATE_DIR / "supervisory_audit_trail_integrity_verification_state.json"
_ARCHIVE_STATE = STATE_DIR / "supervisory_archive_retrieval_index_state.json"
_CLOSURE_STATE = STATE_DIR / "supervisory_incident_closure_permanent_record_seal_state.json"
_BUNDLE_STATE = STATE_DIR / "supervisory_incident_packet_evidence_bundle_state.json"
_INQUIRY_STATE = STATE_DIR / "regulatory_inquiry_response_pack_state.json"
_EXCEPTION_QUEUE = STATE_DIR / "event_state_consistency_exception_queue.json"
_HOLD_STATE = STATE_DIR / "exception_escalation_trading_hold_state.json"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read(path: Path) -> Dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _write_state(data: Dict[str, Any]) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _load_state() -> Dict[str, Any]:
    return _read(STATE_FILE) or {
        "mission": "QNT-REAL02M",
        "audit_status": "idle",
        "hard_blocked": False,
    }


def _gather_evidence() -> Dict[str, Any]:
    integ = _read(_INTEGRITY_STATE)
    archive = _read(_ARCHIVE_STATE)
    closure = _read(_CLOSURE_STATE)
    bundle = _read(_BUNDLE_STATE)
    inquiry = _read(_INQUIRY_STATE)
    exc_q = _read(_EXCEPTION_QUEUE)
    hold = _read(_HOLD_STATE)
    return {
        "integrity_ok": bool(integ.get("integrity_ok")),
        "integrity_sealed": bool(integ.get("integrity_sealed")),
        "seal_id": integ.get("seal_id"),
        "seal_hash": integ.get("seal_hash"),
        "chain_head": integ.get("chain_head"),
        "chain_event_count": integ.get("chain_event_count", 0),
        "archive_retrieval_ready": bool(archive.get("retrieval_ready")),
        "archive_records": archive.get("records", []),
        "incident_closed": bool(closure.get("closed")),
        "record_sealed": bool(closure.get("record_sealed")),
        "permanent_record_ref": closure.get("permanent_record_ref"),
        "packet_built": bundle.get("packet_status") == "built",
        "last_packet_id": bundle.get("last_packet_id"),
        "inquiry_responded": inquiry.get("inquiry_status") == "responded",
        "inquiry_ref": inquiry.get("open_inquiry_ref"),
        "regulator": inquiry.get("regulator"),
        "last_dispatch_id": inquiry.get("last_dispatch_id"),
        "open_breaks": len(exc_q.get("open_breaks", [])),
        "hold_clear": hold.get("hold_status") == "clear",
    }


def _evaluate_blockers(ev: Dict[str, Any]) -> List[str]:
    blockers = []
    if not ev["integrity_ok"]:
        blockers.append("Audit trail integrity verification not passed")
    if not ev["integrity_sealed"]:
        blockers.append("Audit trail integrity seal not confirmed")
    if not ev["incident_closed"]:
        blockers.append("Incident closure record not sealed")
    if not ev["archive_retrieval_ready"]:
        blockers.append("Archive retrieval index not ready")
    if not ev["packet_built"]:
        blockers.append("Evidence packet bundle not built")
    if ev["open_breaks"] > 0:
        blockers.append(f"Open exception breaks: {ev['open_breaks']}")
    if not ev["hold_clear"]:
        blockers.append("Trading hold not cleared")
    return blockers


def _build_evidence_index(ev: Dict[str, Any]) -> List[Dict[str, Any]]:
    index = []
    if ev.get("seal_id"):
        index.append({
            "artifact_id": f"ART-INTEGRITY-{ev['seal_id']}",
            "artifact_type": "audit_trail_integrity_seal",
            "description": "SHA256 hash-chained integrity seal across all Quantora ledgers",
            "seal_id": ev["seal_id"],
            "seal_hash": ev["seal_hash"],
            "chain_head": ev["chain_head"],
            "event_count": ev["chain_event_count"],
            "status": "available",
        })
    for rec in ev.get("archive_records", []):
        index.append({
            "artifact_id": f"ART-ARCHIVE-{rec.get('record_ref', 'unknown')}",
            "artifact_type": "archive_retrieval_record",
            "description": "Supervisory archive retrieval record with packet linkage",
            "record_ref": rec.get("record_ref"),
            "packet_id": rec.get("packet_id"),
            "retrieval_key": rec.get("retrieval_key"),
            "status": "available",
        })
    if ev.get("last_packet_id"):
        index.append({
            "artifact_id": f"ART-PACKET-{ev['last_packet_id']}",
            "artifact_type": "incident_evidence_packet",
            "description": "Compiled incident evidence bundle with full chronology",
            "packet_id": ev["last_packet_id"],
            "status": "available",
        })
    if ev.get("permanent_record_ref"):
        index.append({
            "artifact_id": f"ART-CLOSURE-{ev['permanent_record_ref']}",
            "artifact_type": "incident_closure_record",
            "description": "Permanent incident closure and seal record",
            "record_ref": ev["permanent_record_ref"],
            "status": "available",
        })
    if ev.get("last_dispatch_id"):
        index.append({
            "artifact_id": f"ART-DISPATCH-{ev['last_dispatch_id']}",
            "artifact_type": "regulatory_response_dispatch",
            "description": "Regulatory inquiry response pack with certifications",
            "dispatch_id": ev["last_dispatch_id"],
            "inquiry_ref": ev.get("inquiry_ref"),
            "regulator": ev.get("regulator"),
            "status": "available",
        })
    return index


class InitiateRequest(BaseModel):
    auditor_firm: str
    auditor_ref: str
    audit_scope: Optional[str] = "full_supervisory_chain"
    actor: Optional[str] = "operator"


class MapRequest(BaseModel):
    engagement_id: str
    actor: Optional[str] = "operator"


class PackageRequest(BaseModel):
    engagement_id: str
    actor: Optional[str] = "operator"


class AcknowledgeRequest(BaseModel):
    engagement_id: str
    auditor_ack_ref: str
    actor: Optional[str] = "operator"


class CloseRequest(BaseModel):
    engagement_id: str
    actor: Optional[str] = "operator"


@router.get("/health")
def health():
    return {"mission": "QNT-REAL02M", "status": "ok", "component": "external-auditor-evidence-map"}


@router.get("/summary")
def summary():
    s = _load_state()
    ev = _gather_evidence()
    blockers = _evaluate_blockers(ev)
    s["evidence_summary"] = ev
    s["blockers"] = blockers
    s["hard_blocked"] = len(blockers) > 0
    return s


@router.post("/initiate")
def initiate(req: InitiateRequest):
    ev = _gather_evidence()
    blockers = _evaluate_blockers(ev)
    if blockers:
        return {"initiated": False, "status": "blocked", "blockers": blockers}

    engagement_id = f"AUDIT-ENG-{uuid.uuid4().hex[:10].upper()}"
    s = _load_state()
    s["mission"] = "QNT-REAL02M"
    s["audit_status"] = "initiated"
    s["engagement_id"] = engagement_id
    s["auditor_firm"] = req.auditor_firm
    s["auditor_ref"] = req.auditor_ref
    s["audit_scope"] = req.audit_scope
    s["initiated_at"] = _now()
    s["initiated_by"] = req.actor
    s["evidence_index"] = []
    s["package_id"] = None
    s["auditor_ack_ref"] = None
    s["closed"] = False
    _write_state(s)
    return {
        "initiated": True,
        "engagement_id": engagement_id,
        "auditor_firm": req.auditor_firm,
        "auditor_ref": req.auditor_ref,
        "audit_scope": req.audit_scope,
    }


@router.post("/map-evidence")
def map_evidence(req: MapRequest):
    s = _load_state()
    if s.get("engagement_id") != req.engagement_id:
        return {"mapped": False, "error": "engagement_id mismatch"}
    if s.get("audit_status") not in ("initiated", "mapped"):
        return {"mapped": False, "error": f"invalid state: {s.get('audit_status')}"}

    ev = _gather_evidence()
    blockers = _evaluate_blockers(ev)
    if blockers:
        return {"mapped": False, "status": "blocked", "blockers": blockers}

    index = _build_evidence_index(ev)
    s["audit_status"] = "mapped"
    s["evidence_index"] = index
    s["mapped_at"] = _now()
    s["mapped_by"] = req.actor
    _write_state(s)
    return {
        "mapped": True,
        "engagement_id": req.engagement_id,
        "artifact_count": len(index),
        "evidence_index": index,
    }


@router.post("/package")
def package(req: PackageRequest):
    s = _load_state()
    if s.get("engagement_id") != req.engagement_id:
        return {"packaged": False, "error": "engagement_id mismatch"}
    if s.get("audit_status") != "mapped":
        return {"packaged": False, "error": f"must be in mapped state, currently: {s.get('audit_status')}"}

    package_id = f"AUDPKG-{uuid.uuid4().hex[:12].upper()}"
    s["audit_status"] = "packaged"
    s["package_id"] = package_id
    s["packaged_at"] = _now()
    s["packaged_by"] = req.actor
    _write_state(s)
    return {
        "packaged": True,
        "engagement_id": req.engagement_id,
        "package_id": package_id,
        "artifact_count": len(s.get("evidence_index", [])),
        "packaged_at": s["packaged_at"],
    }


@router.post("/acknowledge")
def acknowledge(req: AcknowledgeRequest):
    s = _load_state()
    if s.get("engagement_id") != req.engagement_id:
        return {"acknowledged": False, "error": "engagement_id mismatch"}
    if s.get("audit_status") != "packaged":
        return {"acknowledged": False, "error": f"must be in packaged state, currently: {s.get('audit_status')}"}

    s["audit_status"] = "acknowledged"
    s["auditor_ack_ref"] = req.auditor_ack_ref
    s["acknowledged_at"] = _now()
    s["acknowledged_by"] = req.actor
    _write_state(s)
    return {
        "acknowledged": True,
        "engagement_id": req.engagement_id,
        "package_id": s.get("package_id"),
        "auditor_ack_ref": req.auditor_ack_ref,
    }


@router.post("/close")
def close(req: CloseRequest):
    s = _load_state()
    if s.get("engagement_id") != req.engagement_id:
        return {"closed": False, "error": "engagement_id mismatch"}
    if s.get("audit_status") != "acknowledged":
        return {"closed": False, "error": f"must be in acknowledged state, currently: {s.get('audit_status')}"}

    closure_ref = f"AUDCLOSE-{uuid.uuid4().hex[:10].upper()}"
    s["audit_status"] = "closed"
    s["closed"] = True
    s["closure_ref"] = closure_ref
    s["closed_at"] = _now()
    s["closed_by"] = req.actor
    _write_state(s)
    return {
        "closed": True,
        "engagement_id": req.engagement_id,
        "package_id": s.get("package_id"),
        "closure_ref": closure_ref,
        "closed_at": s["closed_at"],
    }


@router.post("/reset")
def reset():
    _write_state({"mission": "QNT-REAL02M", "audit_status": "idle", "hard_blocked": False})
    return {"reset": True}
