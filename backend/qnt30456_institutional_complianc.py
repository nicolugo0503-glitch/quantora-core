from __future__ import annotations

from typing import Dict, Iterable, List


def _as_float(value, default: float = 0.0) -> float:
    try:
        if value in (None, ""):
            return default
        return float(value)
    except Exception:
        return default


def build_compliance_vault_package(
    policies: Iterable[Dict],
    diligence_requests: Iterable[Dict],
    certifications: Iterable[Dict],
    disclosures: Iterable[Dict],
) -> Dict:
    policies = list(policies or [])
    diligence_requests = list(diligence_requests or [])
    certifications = list(certifications or [])
    disclosures = list(disclosures or [])

    active_policies = [p for p in policies if (p.get("status") or "").lower() in {"active", "approved", "published"}]
    open_requests = [r for r in diligence_requests if (r.get("status") or "").lower() in {"open", "pending", "in_review"}]
    completed_requests = [r for r in diligence_requests if (r.get("status") or "").lower() in {"completed", "fulfilled", "closed"}]
    valid_certs = [c for c in certifications if (c.get("status") or "").lower() in {"active", "valid", "approved"}]
    overdue_disclosures = [d for d in disclosures if (d.get("status") or "").lower() in {"overdue", "late"}]

    policy_rows: List[Dict] = []
    for row in policies:
        policy_rows.append({
            "policy_id": row.get("id"),
            "policy_name": row.get("policy_name") or "policy",
            "policy_type": row.get("policy_type") or "governance",
            "owner": row.get("owner") or "compliance",
            "status": row.get("status") or "draft",
            "created_at": row.get("created_at"),
        })

    request_rows: List[Dict] = []
    for row in diligence_requests:
        request_rows.append({
            "request_id": row.get("id"),
            "request_name": row.get("request_name") or "ddq_request",
            "requester": row.get("requester") or "allocator",
            "status": row.get("status") or "open",
            "priority": row.get("priority") or "medium",
            "created_at": row.get("created_at"),
        })

    cert_rows: List[Dict] = []
    for row in certifications:
        cert_rows.append({
            "certification_id": row.get("id"),
            "certification_name": row.get("certification_name") or "certification",
            "issuing_body": row.get("issuing_body") or "internal",
            "status": row.get("status") or "draft",
            "expires_at": row.get("expires_at"),
            "created_at": row.get("created_at"),
        })

    disclosure_rows: List[Dict] = []
    for row in disclosures:
        disclosure_rows.append({
            "disclosure_id": row.get("id"),
            "disclosure_name": row.get("disclosure_name") or "disclosure",
            "audience": row.get("audience") or "investors",
            "status": row.get("status") or "draft",
            "due_at": row.get("due_at"),
            "created_at": row.get("created_at"),
        })

    compliance_score = max(
        40,
        min(
            100,
            int(
                58
                + len(active_policies) * 3
                + len(completed_requests) * 2
                + len(valid_certs) * 3
                - len(open_requests) * 2
                - len(overdue_disclosures) * 5
            )
        ),
    )

    return {
        "summary": {
            "policies_total": len(policies),
            "policies_active": len(active_policies),
            "diligence_requests_open": len(open_requests),
            "diligence_requests_completed": len(completed_requests),
            "certifications_valid": len(valid_certs),
            "disclosures_overdue": len(overdue_disclosures),
            "compliance_score": compliance_score,
        },
        "policies": policy_rows,
        "diligence_requests": request_rows,
        "certifications": cert_rows,
        "disclosures": disclosure_rows,
        "compliance_health": {
            "policy_library_ready": bool(policies),
            "diligence_workflow_ready": bool(diligence_requests),
            "certification_registry_ready": bool(certifications),
            "disclosure_tracking_ready": bool(disclosures),
            "compliance_score": compliance_score,
        },
    }
