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


def build_lp_reporting_package(
    statements: Iterable[Dict],
    nav_snapshots: Iterable[Dict],
    distributions: Iterable[Dict],
    reporting_cycles: Iterable[Dict],
) -> Dict:
    statements = list(statements or [])
    nav_snapshots = list(nav_snapshots or [])
    distributions = list(distributions or [])
    reporting_cycles = list(reporting_cycles or [])

    delivered_statements = [s for s in statements if (s.get("delivery_status") or "").lower() in {"sent", "delivered", "published"}]
    pending_statements = [s for s in statements if (s.get("delivery_status") or "").lower() in {"queued", "pending", "draft"}]
    completed_cycles = [c for c in reporting_cycles if (c.get("status") or "").lower() in {"closed", "completed", "published"}]
    active_cycles = [c for c in reporting_cycles if (c.get("status") or "").lower() in {"active", "open", "running"}]

    latest_nav = nav_snapshots[0] if nav_snapshots else {}
    current_nav = _as_float(latest_nav.get("fund_nav"))
    current_gross_pnl = _as_float(latest_nav.get("gross_pnl"))
    total_distributions = sum(_as_float(d.get("amount")) for d in distributions)

    statement_rows: List[Dict] = []
    for row in statements:
        statement_rows.append({
            "statement_id": row.get("id"),
            "investor_name": row.get("investor_name") or "Investor",
            "statement_type": row.get("statement_type") or "lp_statement",
            "period_label": row.get("period_label") or "MTD",
            "nav_amount": _round(_as_float(row.get("nav_amount"))),
            "pnl_amount": _round(_as_float(row.get("pnl_amount"))),
            "delivery_status": row.get("delivery_status") or "draft",
            "created_at": row.get("created_at"),
        })

    nav_rows: List[Dict] = []
    for row in nav_snapshots:
        nav_rows.append({
            "snapshot_id": row.get("id"),
            "as_of_date": row.get("as_of_date"),
            "fund_nav": _round(_as_float(row.get("fund_nav"))),
            "gross_pnl": _round(_as_float(row.get("gross_pnl"))),
            "net_pnl": _round(_as_float(row.get("net_pnl"))),
            "created_at": row.get("created_at"),
        })

    distribution_rows: List[Dict] = []
    for row in distributions:
        distribution_rows.append({
            "distribution_id": row.get("id"),
            "investor_name": row.get("investor_name") or "Investor",
            "distribution_type": row.get("distribution_type") or "cash_distribution",
            "amount": _round(_as_float(row.get("amount"))),
            "status": row.get("status") or "scheduled",
            "created_at": row.get("created_at"),
        })

    cycle_rows: List[Dict] = []
    for row in reporting_cycles:
        cycle_rows.append({
            "cycle_id": row.get("id"),
            "cycle_name": row.get("cycle_name") or "Monthly Cycle",
            "period_label": row.get("period_label") or "MTD",
            "status": row.get("status") or "draft",
            "statements_expected": int(_as_float(row.get("statements_expected"))),
            "statements_completed": int(_as_float(row.get("statements_completed"))),
            "created_at": row.get("created_at"),
        })

    coverage_percent = round((len(delivered_statements) / max(1, len(statements))) * 100.0, 2) if statements else 0.0
    reporting_score = max(
        45,
        min(
            100,
            int(
                55
                + len(delivered_statements) * 2
                + len(completed_cycles) * 4
                + len(nav_snapshots) * 2
                - len(pending_statements) * 2
            ),
        ),
    )

    return {
        "summary": {
            "statements_total": len(statements),
            "statements_delivered": len(delivered_statements),
            "statements_pending": len(pending_statements),
            "current_fund_nav": _round(current_nav),
            "current_gross_pnl": _round(current_gross_pnl),
            "total_distributions": _round(total_distributions),
            "active_cycles": len(active_cycles),
            "reporting_score": reporting_score,
        },
        "statements": statement_rows,
        "nav_snapshots": nav_rows,
        "distributions": distribution_rows,
        "reporting_cycles": cycle_rows,
        "reporting_health": {
            "nav_ready": bool(nav_snapshots),
            "statement_engine_ready": bool(statements),
            "distribution_registry_ready": bool(distributions),
            "cycle_management_ready": bool(reporting_cycles),
            "coverage_percent": coverage_percent,
            "reporting_score": reporting_score,
        },
    }
