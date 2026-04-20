
from __future__ import annotations

from typing import Dict, Iterable, List


def _as_float(value, default: float = 0.0) -> float:
    try:
        if value in (None, ""):
            return default
        return float(value)
    except Exception:
        return default


def _round(value: float) -> float:
    return round(float(value), 2)


def build_governance_approval_package(
    committees: Iterable[Dict],
    approval_requests: Iterable[Dict],
    approval_votes: Iterable[Dict],
    governance_audit_logs: Iterable[Dict],
) -> Dict:
    committees = list(committees or [])
    approval_requests = list(approval_requests or [])
    approval_votes = list(approval_votes or [])
    governance_audit_logs = list(governance_audit_logs or [])

    active_committees = [x for x in committees if (x.get("status") or "").lower() in {"active", "live", "enabled"}]
    open_requests = [x for x in approval_requests if (x.get("status") or "").lower() in {"open", "pending", "submitted"}]
    approved_votes = [x for x in approval_votes if (x.get("vote_result") or "").lower() in {"approved", "yes", "passed"}]
    completed_audits = [x for x in governance_audit_logs if (x.get("status") or "").lower() in {"logged", "completed", "recorded"}]

    request_value_total = sum(_as_float(x.get("request_value")) for x in approval_requests)

    committee_rows: List[Dict] = []
    for row in committees:
        committee_rows.append({
            "committee_id": row.get("id"),
            "committee_name": row.get("committee_name") or "Committee",
            "committee_type": row.get("committee_type") or "investment",
            "status": row.get("status") or "draft",
            "created_at": row.get("created_at"),
        })

    request_rows: List[Dict] = []
    for row in approval_requests:
        request_rows.append({
            "request_id": row.get("id"),
            "request_name": row.get("request_name") or "Approval Request",
            "request_value": _round(_as_float(row.get("request_value"))),
            "request_type": row.get("request_type") or "investment",
            "status": row.get("status") or "draft",
            "created_at": row.get("created_at"),
        })

    vote_rows: List[Dict] = []
    for row in approval_votes:
        vote_rows.append({
            "vote_id": row.get("id"),
            "request_name": row.get("request_name") or "Approval Request",
            "member_name": row.get("member_name") or "Member",
            "vote_result": row.get("vote_result") or "pending",
            "created_at": row.get("created_at"),
        })

    audit_rows: List[Dict] = []
    for row in governance_audit_logs:
        audit_rows.append({
            "audit_id": row.get("id"),
            "event_name": row.get("event_name") or "Governance Event",
            "actor_name": row.get("actor_name") or "Operator",
            "status": row.get("status") or "logged",
            "created_at": row.get("created_at"),
        })

    governance_score = max(
        45,
        min(
            100,
            int(
                60
                + len(active_committees) * 3
                + len(open_requests) * 2
                + len(approved_votes) * 2
                + len(completed_audits) * 2
            )
        ),
    )

    return {
        "summary": {
            "committees_total": len(committees),
            "committees_active": len(active_committees),
            "requests_total": len(approval_requests),
            "requests_open": len(open_requests),
            "votes_total": len(approval_votes),
            "votes_approved": len(approved_votes),
            "audits_total": len(governance_audit_logs),
            "request_value_total": _round(request_value_total),
            "governance_score": governance_score,
        },
        "committees": committee_rows,
        "approval_requests": request_rows,
        "approval_votes": vote_rows,
        "governance_audit_logs": audit_rows,
        "governance_health": {
            "committee_registry_ready": bool(committees),
            "request_registry_ready": bool(approval_requests),
            "vote_registry_ready": bool(approval_votes),
            "audit_registry_ready": bool(governance_audit_logs),
            "governance_score": governance_score,
        },
    }
