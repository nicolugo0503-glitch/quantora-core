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


def build_investor_operating_package(
    investors: Iterable[Dict],
    pools: Iterable[Dict],
    flows: Iterable[Dict],
    reports: Iterable[Dict],
) -> Dict:
    investors = list(investors or [])
    pools = list(pools or [])
    flows = list(flows or [])
    reports = list(reports or [])

    total_nav = sum(_as_float(p.get("capital_balance")) for p in pools)
    total_committed = sum(_as_float(i.get("committed_capital")) for i in investors)
    active_investors = [i for i in investors if (i.get("status") or "").lower() in {"active", "funded"}]
    pending_reports = [r for r in reports if (r.get("delivery_status") or "pending").lower() in {"pending", "queued", "draft"}]
    sent_reports = [r for r in reports if (r.get("delivery_status") or "").lower() in {"sent", "delivered"}]
    deposit_count = len([f for f in flows if (f.get("flow_type") or "").lower() in {"deposit", "subscription", "inflow"}])
    withdrawal_count = len([f for f in flows if (f.get("flow_type") or "").lower() in {"withdrawal", "redemption", "outflow"}])

    trust_score = 100
    if not active_investors:
        trust_score -= 15
    if pending_reports:
        trust_score -= min(25, len(pending_reports) * 5)
    if total_nav <= 0:
        trust_score -= 20
    trust_score = max(40, trust_score)

    latest_by_investor = {}
    for row in sorted(reports, key=lambda r: r.get("created_at") or ""):
        latest_by_investor[row.get("investor_id")] = row

    investor_rows: List[Dict] = []
    nav_base = total_nav or total_committed or 1.0
    for row in investors:
        committed = _as_float(row.get("committed_capital"))
        pnl = _as_float(row.get("distributed_pnl"))
        est_nav = committed + pnl
        latest = latest_by_investor.get(row.get("id"), {})
        investor_rows.append(
            {
                "investor_id": row.get("id"),
                "investor_name": row.get("investor_name") or "Unnamed Investor",
                "status": row.get("status") or "pending",
                "investor_type": row.get("investor_type") or "lp",
                "committed_capital": _round(committed),
                "distributed_pnl": _round(pnl),
                "estimated_nav": _round(est_nav),
                "ownership_percent": round((committed / nav_base) * 100.0, 2) if nav_base else 0.0,
                "last_report_type": latest.get("report_type"),
                "last_delivery_status": latest.get("delivery_status"),
                "last_report_at": latest.get("created_at"),
            }
        )

    report_rows = []
    for row in sorted(reports, key=lambda r: r.get("created_at") or "", reverse=True):
        report_rows.append(
            {
                "report_id": row.get("id"),
                "investor_id": row.get("investor_id"),
                "investor_name": row.get("investor_name") or "Investor",
                "report_type": row.get("report_type") or "capital_statement",
                "delivery_status": row.get("delivery_status") or "pending",
                "period_label": row.get("period_label") or "MTD",
                "generated_nav": _round(_as_float(row.get("generated_nav"))),
                "generated_pnl": _round(_as_float(row.get("generated_pnl"))),
                "created_at": row.get("created_at"),
            }
        )

    trust_center = {
        "investor_registry_ready": bool(investors),
        "capital_pools_ready": bool(pools),
        "reporting_queue_ready": True,
        "statement_coverage_percent": round((len(sent_reports) / max(1, len(investors))) * 100.0, 2),
        "dispatch_backlog": len(pending_reports),
        "trust_score": trust_score,
    }

    return {
        "summary": {
            "active_investors": len(active_investors),
            "total_investors": len(investors),
            "total_committed_capital": _round(total_committed),
            "estimated_fund_nav": _round(total_nav),
            "reports_sent": len(sent_reports),
            "reports_pending": len(pending_reports),
            "capital_inflows_recorded": deposit_count,
            "capital_outflows_recorded": withdrawal_count,
            "trust_score": trust_score,
        },
        "investors": investor_rows,
        "reports": report_rows,
        "trust_center": trust_center,
    }
