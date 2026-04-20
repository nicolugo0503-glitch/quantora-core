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


def build_execution_governance_package(
    rules: Iterable[Dict],
    approvals: Iterable[Dict],
    audit_events: Iterable[Dict],
    execution_failures: Iterable[Dict],
) -> Dict:
    rules = list(rules or [])
    approvals = list(approvals or [])
    audit_events = list(audit_events or [])
    execution_failures = list(execution_failures or [])

    active_rules = [r for r in rules if (r.get("status") or "").lower() in {"active", "enforced", "live"}]
    approved_actions = [a for a in approvals if (a.get("decision") or "").lower() in {"approved", "accepted"}]
    rejected_actions = [a for a in approvals if (a.get("decision") or "").lower() in {"rejected", "denied"}]
    severe_failures = [f for f in execution_failures if (f.get("severity") or "").lower() in {"high", "critical"}]
    unresolved_failures = [f for f in execution_failures if (f.get("status") or "").lower() not in {"resolved", "closed"}]

    audit_rows: List[Dict] = []
    for row in audit_events:
        audit_rows.append({
            "event_id": row.get("id"),
            "event_type": row.get("event_type") or "execution_event",
            "actor": row.get("actor") or "system",
            "target_ref": row.get("target_ref") or "-",
            "status": row.get("status") or "logged",
            "created_at": row.get("created_at"),
        })

    rule_rows: List[Dict] = []
    for row in rules:
        rule_rows.append({
            "rule_id": row.get("id"),
            "rule_name": row.get("rule_name") or "rule",
            "rule_type": row.get("rule_type") or "risk_limit",
            "threshold_value": _round(_as_float(row.get("threshold_value"))),
            "status": row.get("status") or "draft",
            "created_at": row.get("created_at"),
        })

    approval_rows: List[Dict] = []
    for row in approvals:
        approval_rows.append({
            "approval_id": row.get("id"),
            "plan_id": row.get("plan_id"),
            "plan_name": row.get("plan_name") or "-",
            "decision": row.get("decision") or "pending",
            "reviewer": row.get("reviewer") or "operator",
            "reason": row.get("reason") or "",
            "created_at": row.get("created_at"),
        })

    failure_rows: List[Dict] = []
    for row in execution_failures:
        failure_rows.append({
            "failure_id": row.get("id"),
            "execution_id": row.get("execution_id"),
            "failure_type": row.get("failure_type") or "execution_error",
            "severity": row.get("severity") or "medium",
            "status": row.get("status") or "open",
            "created_at": row.get("created_at"),
        })

    governance_score = max(
        40,
        min(
            100,
            int(
                55
                + len(active_rules) * 4
                + len(approved_actions) * 2
                + len(audit_events)
                - len(unresolved_failures) * 5
                - len(severe_failures) * 4
            ),
        ),
    )

    return {
        "summary": {
            "active_rules": len(active_rules),
            "approvals_logged": len(approvals),
            "approved_actions": len(approved_actions),
            "rejected_actions": len(rejected_actions),
            "audit_events": len(audit_events),
            "open_failures": len(unresolved_failures),
            "governance_score": governance_score,
        },
        "rules": rule_rows,
        "approvals": approval_rows,
        "audit_events": audit_rows,
        "execution_failures": failure_rows,
        "governance_health": {
            "rules_ready": bool(rules),
            "approval_log_ready": bool(approvals),
            "audit_trail_ready": bool(audit_events),
            "failure_registry_ready": True,
            "governance_score": governance_score,
        },
    }
