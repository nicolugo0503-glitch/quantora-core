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


def build_fund_admin_package(
    nav_entries: Iterable[Dict],
    reconciliation_breaks: Iterable[Dict],
    subscriptions_redemptions: Iterable[Dict],
    admin_closes: Iterable[Dict],
) -> Dict:
    nav_entries = list(nav_entries or [])
    reconciliation_breaks = list(reconciliation_breaks or [])
    subscriptions_redemptions = list(subscriptions_redemptions or [])
    admin_closes = list(admin_closes or [])

    latest_nav = nav_entries[0] if nav_entries else {}
    current_nav = _as_float(latest_nav.get("fund_nav"))
    unresolved_breaks = [b for b in reconciliation_breaks if (b.get("status") or "").lower() in {"open", "pending", "investigating"}]
    resolved_breaks = [b for b in reconciliation_breaks if (b.get("status") or "").lower() in {"resolved", "closed"}]
    subscriptions = [f for f in subscriptions_redemptions if (f.get("flow_type") or "").lower() in {"subscription", "inflow"}]
    redemptions = [f for f in subscriptions_redemptions if (f.get("flow_type") or "").lower() in {"redemption", "outflow"}]
    completed_closes = [c for c in admin_closes if (c.get("status") or "").lower() in {"completed", "closed"}]

    gross_subscriptions = sum(_as_float(x.get("amount")) for x in subscriptions)
    gross_redemptions = sum(_as_float(x.get("amount")) for x in redemptions)

    nav_rows: List[Dict] = []
    for row in nav_entries:
        nav_rows.append({
            "nav_id": row.get("id"),
            "as_of_date": row.get("as_of_date"),
            "fund_nav": _round(_as_float(row.get("fund_nav"))),
            "nav_per_unit": _round(_as_float(row.get("nav_per_unit"))),
            "status": row.get("status") or "draft",
            "created_at": row.get("created_at"),
        })

    break_rows: List[Dict] = []
    for row in reconciliation_breaks:
        break_rows.append({
            "break_id": row.get("id"),
            "break_name": row.get("break_name") or "reconciliation_break",
            "break_type": row.get("break_type") or "nav_break",
            "variance_amount": _round(_as_float(row.get("variance_amount"))),
            "status": row.get("status") or "open",
            "created_at": row.get("created_at"),
        })

    flow_rows: List[Dict] = []
    for row in subscriptions_redemptions:
        flow_rows.append({
            "flow_id": row.get("id"),
            "investor_name": row.get("investor_name") or "Investor",
            "flow_type": row.get("flow_type") or "subscription",
            "amount": _round(_as_float(row.get("amount"))),
            "status": row.get("status") or "pending",
            "created_at": row.get("created_at"),
        })

    close_rows: List[Dict] = []
    for row in admin_closes:
        close_rows.append({
            "close_id": row.get("id"),
            "close_name": row.get("close_name") or "monthly_close",
            "period_label": row.get("period_label") or "MTD",
            "status": row.get("status") or "draft",
            "completed_steps": int(_as_float(row.get("completed_steps"))),
            "total_steps": int(_as_float(row.get("total_steps"))),
            "created_at": row.get("created_at"),
        })

    admin_score = max(
        40,
        min(
            100,
            int(
                58
                + len(nav_entries) * 3
                + len(resolved_breaks) * 2
                + len(completed_closes) * 4
                - len(unresolved_breaks) * 5
            )
        ),
    )

    return {
        "summary": {
            "nav_entries": len(nav_entries),
            "current_fund_nav": _round(current_nav),
            "reconciliation_breaks_open": len(unresolved_breaks),
            "reconciliation_breaks_resolved": len(resolved_breaks),
            "gross_subscriptions": _round(gross_subscriptions),
            "gross_redemptions": _round(gross_redemptions),
            "admin_closes_completed": len(completed_closes),
            "admin_score": admin_score,
        },
        "nav_entries": nav_rows,
        "reconciliation_breaks": break_rows,
        "subscriptions_redemptions": flow_rows,
        "admin_closes": close_rows,
        "admin_health": {
            "nav_registry_ready": bool(nav_entries),
            "reconciliation_ready": bool(reconciliation_breaks),
            "flow_registry_ready": bool(subscriptions_redemptions),
            "close_process_ready": bool(admin_closes),
            "admin_score": admin_score,
        },
    }
