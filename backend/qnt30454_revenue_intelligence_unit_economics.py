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


def build_revenue_intelligence_package(
    customer_segments: Iterable[Dict],
    revenue_events: Iterable[Dict],
    cost_centers: Iterable[Dict],
    unit_economics_snapshots: Iterable[Dict],
) -> Dict:
    customer_segments = list(customer_segments or [])
    revenue_events = list(revenue_events or [])
    cost_centers = list(cost_centers or [])
    unit_economics_snapshots = list(unit_economics_snapshots or [])

    recurring_revenue = sum(_as_float(r.get("amount")) for r in revenue_events if (r.get("revenue_type") or "").lower() in {"subscription", "mrr", "recurring"})
    transactional_revenue = sum(_as_float(r.get("amount")) for r in revenue_events if (r.get("revenue_type") or "").lower() in {"performance_fee", "management_fee", "license_fee", "transactional"})
    total_cost = sum(_as_float(c.get("monthly_cost")) for c in cost_centers)
    gross_revenue = recurring_revenue + transactional_revenue
    contribution_margin = gross_revenue - total_cost

    latest_snapshot = unit_economics_snapshots[0] if unit_economics_snapshots else {}
    ltv = _as_float(latest_snapshot.get("ltv"))
    cac = _as_float(latest_snapshot.get("cac"))
    payback_months = _as_float(latest_snapshot.get("payback_months"))
    ltv_cac_ratio = round((ltv / cac), 2) if cac > 0 else 0.0

    segment_rows: List[Dict] = []
    for row in customer_segments:
        segment_rows.append({
            "segment_id": row.get("id"),
            "segment_name": row.get("segment_name") or "Segment",
            "customers": int(_as_float(row.get("customers"))),
            "mrr": _round(_as_float(row.get("mrr"))),
            "churn_percent": round(_as_float(row.get("churn_percent")), 2),
            "created_at": row.get("created_at"),
        })

    revenue_rows: List[Dict] = []
    for row in revenue_events:
        revenue_rows.append({
            "event_id": row.get("id"),
            "revenue_name": row.get("revenue_name") or "Revenue Event",
            "revenue_type": row.get("revenue_type") or "subscription",
            "amount": _round(_as_float(row.get("amount"))),
            "status": row.get("status") or "recognized",
            "created_at": row.get("created_at"),
        })

    cost_rows: List[Dict] = []
    for row in cost_centers:
        cost_rows.append({
            "cost_id": row.get("id"),
            "cost_name": row.get("cost_name") or "Cost Center",
            "category": row.get("category") or "operations",
            "monthly_cost": _round(_as_float(row.get("monthly_cost"))),
            "status": row.get("status") or "active",
            "created_at": row.get("created_at"),
        })

    snapshot_rows: List[Dict] = []
    for row in unit_economics_snapshots:
        snapshot_rows.append({
            "snapshot_id": row.get("id"),
            "period_label": row.get("period_label") or "MTD",
            "ltv": _round(_as_float(row.get("ltv"))),
            "cac": _round(_as_float(row.get("cac"))),
            "payback_months": round(_as_float(row.get("payback_months")), 2),
            "gross_margin_percent": round(_as_float(row.get("gross_margin_percent")), 2),
            "created_at": row.get("created_at"),
        })

    economics_score = max(
        40,
        min(
            100,
            int(
                55
                + len(customer_segments) * 3
                + len(revenue_events) * 2
                + (5 if contribution_margin > 0 else -5)
                + (5 if ltv_cac_ratio >= 3 else 0)
                - (5 if payback_months > 12 and payback_months > 0 else 0)
            )
        ),
    )

    return {
        "summary": {
            "segments_tracked": len(customer_segments),
            "gross_revenue": _round(gross_revenue),
            "recurring_revenue": _round(recurring_revenue),
            "transactional_revenue": _round(transactional_revenue),
            "total_cost": _round(total_cost),
            "contribution_margin": _round(contribution_margin),
            "ltv_cac_ratio": ltv_cac_ratio,
            "economics_score": economics_score,
        },
        "customer_segments": segment_rows,
        "revenue_events": revenue_rows,
        "cost_centers": cost_rows,
        "unit_economics_snapshots": snapshot_rows,
        "economics_health": {
            "segment_tracking_ready": bool(customer_segments),
            "revenue_tracking_ready": bool(revenue_events),
            "cost_tracking_ready": bool(cost_centers),
            "snapshot_engine_ready": bool(unit_economics_snapshots),
            "economics_score": economics_score,
        },
    }
