from fastapi import APIRouter, Body
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import time

router = APIRouter(tags=["institutional-compliance-layer"])

PROJECT_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_DIR / "backend" / "artifacts"
COMPLIANCE_DIR = ARTIFACTS_DIR / "institutional_compliance_layer"

DEFAULT_POLICY = {
    "min_required_documents": 4,
    "minimum_approved_documents": 3,
    "max_blocked_events": 0,
    "max_pending_approvals": 2,
    "max_critical_constraints": 0,
    "max_open_queue_cases": 1,
    "minimum_growth_capacity": 62.0,
    "minimum_confidence_score": 58.0,
    "require_audit_chain": True,
    "require_live_approval": True,
    "jurisdiction_mode": "US_FIRST",
    "approved_jurisdictions": ["US", "MX"],
}


def _mu():
    from backend.app import qnt30557_multi_user_router as mu
    return mu


def _vault():
    from backend.app import qnt30576_identity_vault_router as vault
    return vault


def _queue():
    from backend.app import qnt30577_compliance_queue_router as queue
    return queue


def _data_room():
    from backend.app import qnt30571_data_room_router as data_room
    return data_room


def _governance():
    from backend.app import qnt30633_governance_compliance_router as governance
    return governance


def _strategic():
    from backend.app import qnt30650_strategic_decision_router as strategic
    return strategic


def _growth():
    from backend.app import qnt30651_autonomous_growth_router as growth
    return growth


def _safe(v: str) -> str:
    return hashlib.sha256((v or "").strip().lower().encode("utf-8")).hexdigest()[:24]


def _path(email: str) -> Path:
    COMPLIANCE_DIR.mkdir(parents=True, exist_ok=True)
    return COMPLIANCE_DIR / f"{_safe(email)}.json"


def _require_user():
    return _mu()._require_session()


def _now_ts() -> int:
    return int(time.time())


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _round_pct(v) -> float:
    return round(float(v or 0.0), 4)


def _load(email: str) -> dict:
    path = _path(email)
    if not path.exists():
        data = {
            "email": email,
            "policy": dict(DEFAULT_POLICY),
            "runs": [],
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


def _document_snapshot(email: str):
    vault = _vault()._load(email)
    docs = vault.get("documents", []) or []
    total = len(docs)
    uploaded = sum(1 for d in docs if str(d.get("status")) != "missing")
    approved = sum(1 for d in docs if str(d.get("review_status")) == "approved")
    pending = sum(1 for d in docs if str(d.get("review_status")) == "pending_review")
    rejected = sum(1 for d in docs if str(d.get("review_status")) == "rejected")
    return {
        "total_documents": total,
        "uploaded_documents": uploaded,
        "approved_documents": approved,
        "pending_review_documents": pending,
        "rejected_documents": rejected,
        "documents": docs,
    }


def _queue_snapshot(email: str):
    case = _queue()._build_case(email)
    queue_data = _queue()._load()
    activity = [a for a in (queue_data.get("activity") or []) if a.get("email") == email][:10]
    return {
        "case": case,
        "recent_activity": activity,
        "status": case.get("status") or "unknown",
        "needs_attention": case.get("status") not in {"verified"},
    }


def _data_room_snapshot(email: str):
    room = _data_room()._load_room()
    access = _data_room()._load_access(email)
    grants = [g for g in (access.get("grants") or []) if g.get("status") == "active"]
    requests = access.get("requests") or []
    granted_ids = {g.get("doc_id") for g in grants}
    available_docs = room.get("documents", []) or []
    granted_docs = [d for d in available_docs if d.get("doc_id") in granted_ids]
    return {
        "available_document_count": len(available_docs),
        "granted_document_count": len(granted_docs),
        "request_count": len(requests),
        "grant_count": len(grants),
        "granted_documents": granted_docs,
        "open_requests": [r for r in requests if r.get("status") == "pending"],
    }


def _jurisdiction_snapshot(policy: dict):
    approved = policy.get("approved_jurisdictions") or []
    mode = policy.get("jurisdiction_mode") or "US_FIRST"
    cross_border_enabled = len(approved) > 1
    return {
        "mode": mode,
        "approved_jurisdictions": approved,
        "cross_border_ready": cross_border_enabled and mode in {"US_FIRST", "GLOBAL_STAGED", "GLOBAL_ACTIVE"},
    }


def _control_matrix(policy: dict, governance: dict, strategic: dict, growth: dict, docs: dict, queue_snap: dict, data_room: dict):
    latest_snapshot = governance.get("latest_snapshot") or {}
    audit_ok = bool((governance.get("audit_summary") or {}).get("chain_integrity_ok"))
    blocked_events = int(governance.get("blocked_event_count") or 0)
    open_approvals = int(governance.get("open_approval_count") or 0)
    critical_constraints = sum(1 for c in (growth.get("constraints") or []) if str(c.get("severity") or "").lower() == "critical")
    growth_capacity = float(growth.get("growth_capacity_score") or 0.0)
    confidence = float(strategic.get("confidence_score") or 0.0)
    total_docs = int(docs.get("total_documents") or 0)
    approved_docs = int(docs.get("approved_documents") or 0)
    data_room_docs = int(data_room.get("granted_document_count") or 0)

    controls = [
        {
            "control": "Identity & KYC Coverage",
            "status": "pass" if total_docs >= int(policy.get("min_required_documents") or 0) and approved_docs >= int(policy.get("minimum_approved_documents") or 0) else "fail",
            "metric": f"{approved_docs}/{total_docs} approved",
            "threshold": f">= {policy.get('minimum_approved_documents')} approvals",
        },
        {
            "control": "Audit Chain Integrity",
            "status": "pass" if (not bool(policy.get("require_audit_chain")) or audit_ok) else "fail",
            "metric": "intact" if audit_ok else "broken",
            "threshold": "chain intact",
        },
        {
            "control": "Governance Event Pressure",
            "status": "pass" if blocked_events <= int(policy.get("max_blocked_events") or 0) and open_approvals <= int(policy.get("max_pending_approvals") or 0) else "watch",
            "metric": f"{blocked_events} blocked / {open_approvals} approvals",
            "threshold": "within policy",
        },
        {
            "control": "Growth Release Eligibility",
            "status": "pass" if growth_capacity >= float(policy.get("minimum_growth_capacity") or 0.0) and critical_constraints <= int(policy.get("max_critical_constraints") or 0) and confidence >= float(policy.get("minimum_confidence_score") or 0.0) else "watch",
            "metric": f"capacity {growth_capacity:.2f} / confidence {confidence:.2f}",
            "threshold": "capacity + confidence cleared",
        },
        {
            "control": "Allocator Transparency Readiness",
            "status": "pass" if data_room_docs >= min(int(policy.get("minimum_approved_documents") or 0), 3) else "watch",
            "metric": f"{data_room_docs} granted docs",
            "threshold": "core packet available",
        },
        {
            "control": "Compliance Queue State",
            "status": "pass" if not queue_snap.get("needs_attention") else "watch",
            "metric": queue_snap.get("status") or "unknown",
            "threshold": "verified",
        },
        {
            "control": "Live Mode Approval Gate",
            "status": "pass" if (not bool(policy.get("require_live_approval"))) or open_approvals == 0 or str(latest_snapshot.get("autonomous_mode") or "").lower() != "live" else "watch",
            "metric": f"mode {latest_snapshot.get('autonomous_mode') or 'unknown'}",
            "threshold": "approved for live",
        },
    ]
    return controls


def _obligations(policy: dict, governance: dict, strategic: dict, growth: dict, docs: dict, queue_snap: dict, data_room: dict, jurisdiction: dict):
    items = []
    if int(docs.get("approved_documents") or 0) < int(policy.get("minimum_approved_documents") or 0):
        items.append({"severity": "critical", "type": "kyc", "message": "Insufficient approved identity documents for institutional onboarding."})
    if bool(policy.get("require_audit_chain")) and not bool((governance.get("audit_summary") or {}).get("chain_integrity_ok")):
        items.append({"severity": "critical", "type": "audit", "message": "Audit chain integrity must be restored before autonomous release."})
    if int(governance.get("blocked_event_count") or 0) > int(policy.get("max_blocked_events") or 0):
        items.append({"severity": "critical", "type": "governance", "message": "Blocked governance events exceed institutional tolerance."})
    if int(governance.get("open_approval_count") or 0) > int(policy.get("max_pending_approvals") or 0):
        items.append({"severity": "warning", "type": "approval", "message": "Approval queue backlog is above the release threshold."})
    if sum(1 for c in (growth.get("constraints") or []) if str(c.get("severity") or "").lower() == "critical") > int(policy.get("max_critical_constraints") or 0):
        items.append({"severity": "critical", "type": "growth_constraint", "message": "Critical growth constraints block full autonomy."})
    if float(growth.get("growth_capacity_score") or 0.0) < float(policy.get("minimum_growth_capacity") or 0.0):
        items.append({"severity": "warning", "type": "capacity", "message": "Growth capacity is below compliance release floor."})
    if float(strategic.get("confidence_score") or 0.0) < float(policy.get("minimum_confidence_score") or 0.0):
        items.append({"severity": "warning", "type": "confidence", "message": "Strategic confidence has not cleared institutional policy."})
    if int(data_room.get("granted_document_count") or 0) < min(int(policy.get("minimum_approved_documents") or 0), 3):
        items.append({"severity": "warning", "type": "transparency", "message": "Allocator transparency packet is incomplete for institutional diligence."})
    if queue_snap.get("needs_attention"):
        items.append({"severity": "warning", "type": "queue", "message": f"Compliance queue status is {queue_snap.get('status')}; supervisory review remains open."})
    if not jurisdiction.get("cross_border_ready"):
        items.append({"severity": "watch", "type": "jurisdiction", "message": "Cross-border release is staged; expand jurisdiction controls before global deployment."})
    return items


def _release_status(controls: list, obligations: list, jurisdiction: dict):
    control_fail = any(c.get("status") == "fail" for c in controls)
    critical = any(o.get("severity") == "critical" for o in obligations)
    warnings = sum(1 for o in obligations if o.get("severity") == "warning")
    if control_fail or critical:
        return "blocked"
    if warnings > 0:
        return "governed-release"
    if jurisdiction.get("cross_border_ready"):
        return "institutional-ready"
    return "domestic-ready"


def _build_summary(email: str):
    store = _load(email)
    policy = store.get("policy") or {}
    governance = _governance()._summary(email)
    strategic = _strategic()._build_summary(email)
    growth = _growth()._build_summary(email)
    docs = _document_snapshot(email)
    queue_snap = _queue_snapshot(email)
    data_room = _data_room_snapshot(email)
    jurisdiction = _jurisdiction_snapshot(policy)
    controls = _control_matrix(policy, governance, strategic, growth, docs, queue_snap, data_room)
    obligations = _obligations(policy, governance, strategic, growth, docs, queue_snap, data_room, jurisdiction)
    release_status = _release_status(controls, obligations, jurisdiction)
    pass_count = sum(1 for c in controls if c.get("status") == "pass")
    readiness_score = _round_pct((pass_count / max(len(controls), 1)) * 100.0)
    return {
        "mission": "QNT30652",
        "generated_at": _now_iso(),
        "release_status": release_status,
        "readiness_score": readiness_score,
        "control_matrix": controls,
        "obligations": obligations,
        "policy": policy,
        "identity_snapshot": {
            "total_documents": docs.get("total_documents"),
            "approved_documents": docs.get("approved_documents"),
            "pending_review_documents": docs.get("pending_review_documents"),
            "rejected_documents": docs.get("rejected_documents"),
        },
        "governance_snapshot": {
            "blocked_event_count": governance.get("blocked_event_count") or 0,
            "open_approval_count": governance.get("open_approval_count") or 0,
            "override_count": governance.get("override_count") or 0,
            "latest_snapshot": governance.get("latest_snapshot") or {},
            "audit_chain_ok": bool((governance.get("audit_summary") or {}).get("chain_integrity_ok")),
        },
        "autonomy_snapshot": {
            "operating_posture": strategic.get("operating_posture"),
            "confidence_score": strategic.get("confidence_score"),
            "growth_capacity_score": growth.get("growth_capacity_score"),
            "autonomy_posture": growth.get("autonomy_posture"),
            "critical_constraints": sum(1 for c in (growth.get("constraints") or []) if str(c.get("severity") or "").lower() == "critical"),
        },
        "transparency_snapshot": {
            "available_document_count": data_room.get("available_document_count"),
            "granted_document_count": data_room.get("granted_document_count"),
            "open_request_count": len(data_room.get("open_requests") or []),
        },
        "queue_snapshot": queue_snap,
        "jurisdiction_snapshot": jurisdiction,
    }


@router.get("/api/institutional-compliance-layer/summary")
def institutional_compliance_summary():
    session = _require_user()
    return _build_summary(session.get("email"))


@router.post("/api/institutional-compliance-layer/run")
def institutional_compliance_run(payload: dict = Body(default=None)):
    session = _require_user()
    email = session.get("email")
    store = _load(email)
    summary = _build_summary(email)
    run = {
        "run_id": f"icl_{time.time_ns()}",
        "mission": "QNT30652",
        "trigger": (payload or {}).get("trigger") or "manual",
        "timestamp": _now_ts(),
        "generated_at": summary.get("generated_at"),
        "release_status": summary.get("release_status"),
        "readiness_score": summary.get("readiness_score"),
        "critical_obligation_count": sum(1 for o in (summary.get("obligations") or []) if o.get("severity") == "critical"),
        "warning_obligation_count": sum(1 for o in (summary.get("obligations") or []) if o.get("severity") == "warning"),
        "control_matrix": summary.get("control_matrix"),
        "obligations": summary.get("obligations"),
    }
    store.setdefault("runs", []).insert(0, run)
    store["runs"] = store.get("runs", [])[:120]
    _save(email, store)
    return {"status": "ok", "summary": summary, "run": run}


@router.get("/api/institutional-compliance-layer/audit")
def institutional_compliance_audit():
    session = _require_user()
    email = session.get("email")
    store = _load(email)
    runs = store.get("runs") or []
    return {
        "mission": "QNT30652",
        "run_count": len(runs),
        "latest_run": runs[0] if runs else None,
        "runs": runs[:20],
    }


@router.post("/api/institutional-compliance-layer/policy")
def institutional_compliance_policy(payload: dict = Body(...)):
    session = _require_user()
    email = session.get("email")
    store = _load(email)
    policy = store.get("policy") or dict(DEFAULT_POLICY)
    allowed = set(DEFAULT_POLICY.keys())
    for key, value in payload.items():
        if key in allowed:
            policy[key] = value
    store["policy"] = policy
    _save(email, store)
    return {"status": "updated", "policy": policy, "summary": _build_summary(email)}
