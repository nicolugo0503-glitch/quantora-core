from __future__ import annotations

from typing import Dict, Iterable, List


def _as_float(value, default: float = 0.0) -> float:
    try:
        if value in (None, ""):
            return default
        return float(value)
    except Exception:
        return default


def build_investor_portal_package(
    portal_users: Iterable[Dict],
    report_access: Iterable[Dict],
    portal_sessions: Iterable[Dict],
    delivery_logs: Iterable[Dict],
) -> Dict:
    portal_users = list(portal_users or [])
    report_access = list(report_access or [])
    portal_sessions = list(portal_sessions or [])
    delivery_logs = list(delivery_logs or [])

    active_users = [x for x in portal_users if (x.get("status") or "").lower() in {"active", "enabled", "live"}]
    enabled_access = [x for x in report_access if (x.get("status") or "").lower() in {"active", "enabled", "granted"}]
    active_sessions = [x for x in portal_sessions if (x.get("status") or "").lower() in {"active", "open"}]
    delivered_logs = [x for x in delivery_logs if (x.get("status") or "").lower() in {"delivered", "sent", "completed"}]

    user_rows: List[Dict] = []
    for row in portal_users:
        user_rows.append({
            "user_id": row.get("id"),
            "investor_name": row.get("investor_name") or "Investor",
            "access_tier": row.get("access_tier") or "standard",
            "status": row.get("status") or "draft",
            "created_at": row.get("created_at"),
        })

    access_rows: List[Dict] = []
    for row in report_access:
        access_rows.append({
            "access_id": row.get("id"),
            "investor_name": row.get("investor_name") or "Investor",
            "report_name": row.get("report_name") or "Report",
            "status": row.get("status") or "draft",
            "expires_at": row.get("expires_at"),
            "created_at": row.get("created_at"),
        })

    session_rows: List[Dict] = []
    for row in portal_sessions:
        session_rows.append({
            "session_id": row.get("id"),
            "investor_name": row.get("investor_name") or "Investor",
            "last_page": row.get("last_page") or "dashboard",
            "status": row.get("status") or "inactive",
            "created_at": row.get("created_at"),
        })

    delivery_rows: List[Dict] = []
    for row in delivery_logs:
        delivery_rows.append({
            "delivery_id": row.get("id"),
            "investor_name": row.get("investor_name") or "Investor",
            "report_name": row.get("report_name") or "Report",
            "channel": row.get("channel") or "portal",
            "status": row.get("status") or "queued",
            "created_at": row.get("created_at"),
        })

    portal_score = max(
        45,
        min(
            100,
            int(
                58
                + len(active_users) * 3
                + len(enabled_access) * 2
                + len(active_sessions) * 2
                + len(delivered_logs) * 2
            )
        ),
    )

    return {
        "summary": {
            "portal_users": len(portal_users),
            "active_users": len(active_users),
            "report_access_total": len(report_access),
            "report_access_enabled": len(enabled_access),
            "active_sessions": len(active_sessions),
            "deliveries_total": len(delivery_logs),
            "deliveries_completed": len(delivered_logs),
            "portal_score": portal_score,
        },
        "portal_users": user_rows,
        "report_access": access_rows,
        "portal_sessions": session_rows,
        "delivery_logs": delivery_rows,
        "portal_health": {
            "user_registry_ready": bool(portal_users),
            "report_access_ready": bool(report_access),
            "session_tracking_ready": bool(portal_sessions),
            "delivery_tracking_ready": bool(delivery_logs),
            "portal_score": portal_score,
        },
    }
