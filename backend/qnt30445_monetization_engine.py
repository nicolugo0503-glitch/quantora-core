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


def build_monetization_package(
    subscriptions: Iterable[Dict],
    invoices: Iterable[Dict],
    fee_ledger: Iterable[Dict],
    licenses: Iterable[Dict],
) -> Dict:
    subscriptions = list(subscriptions or [])
    invoices = list(invoices or [])
    fee_ledger = list(fee_ledger or [])
    licenses = list(licenses or [])

    active_subs = [s for s in subscriptions if (s.get("status") or "").lower() in {"active", "trialing", "paid"}]
    mrr = sum(_as_float(s.get("monthly_amount")) for s in active_subs)
    arr = mrr * 12.0

    open_invoices = [i for i in invoices if (i.get("status") or "").lower() in {"open", "pending", "due"}]
    paid_invoices = [i for i in invoices if (i.get("status") or "").lower() in {"paid", "settled"}]
    invoice_open_value = sum(_as_float(i.get("amount")) for i in open_invoices)
    invoice_paid_value = sum(_as_float(i.get("amount")) for i in paid_invoices)

    perf_fees = [f for f in fee_ledger if (f.get("fee_type") or "").lower() == "performance_fee"]
    mgmt_fees = [f for f in fee_ledger if (f.get("fee_type") or "").lower() == "management_fee"]
    license_fees = [f for f in fee_ledger if (f.get("fee_type") or "").lower() == "license_fee"]

    realized_revenue = sum(_as_float(f.get("amount")) for f in fee_ledger if (f.get("status") or "").lower() in {"recognized", "paid", "settled"})
    projected_revenue = realized_revenue + mrr + invoice_open_value

    license_rows: List[Dict] = []
    for row in licenses:
        license_rows.append({
            "license_id": row.get("id"),
            "client_name": row.get("client_name") or "Unnamed Client",
            "plan_name": row.get("plan_name") or "institutional",
            "status": row.get("status") or "draft",
            "monthly_amount": _round(_as_float(row.get("monthly_amount"))),
            "seat_count": int(_as_float(row.get("seat_count"), 0)),
            "term_months": int(_as_float(row.get("term_months"), 0)),
            "created_at": row.get("created_at"),
        })

    revenue_mix = {
        "saas_mrr": _round(mrr),
        "management_fee_total": _round(sum(_as_float(f.get("amount")) for f in mgmt_fees)),
        "performance_fee_total": _round(sum(_as_float(f.get("amount")) for f in perf_fees)),
        "license_fee_total": _round(sum(_as_float(f.get("amount")) for f in license_fees)),
    }

    engine_health = {
        "subscriptions_ready": bool(subscriptions),
        "fee_ledger_ready": bool(fee_ledger),
        "licensing_ready": bool(licenses),
        "collections_backlog": len(open_invoices),
        "monetization_score": max(45, min(100, int(55 + len(active_subs) * 5 + len(licenses) * 3 + len(paid_invoices) * 2 - len(open_invoices) * 2))),
    }

    return {
        "summary": {
            "active_subscriptions": len(active_subs),
            "mrr": _round(mrr),
            "arr": _round(arr),
            "open_invoices": len(open_invoices),
            "open_invoice_value": _round(invoice_open_value),
            "paid_invoice_value": _round(invoice_paid_value),
            "realized_revenue": _round(realized_revenue),
            "projected_revenue": _round(projected_revenue),
            "monetization_score": engine_health["monetization_score"],
        },
        "subscriptions": list(subscriptions),
        "invoices": list(invoices),
        "fee_ledger": list(fee_ledger),
        "licenses": license_rows,
        "revenue_mix": revenue_mix,
        "engine_health": engine_health,
    }
