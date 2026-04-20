
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


def build_revenue_ops_package(
    billing_accounts: Iterable[Dict],
    invoices: Iterable[Dict],
    subscriptions: Iterable[Dict],
    collections_logs: Iterable[Dict],
) -> Dict:
    billing_accounts = list(billing_accounts or [])
    invoices = list(invoices or [])
    subscriptions = list(subscriptions or [])
    collections_logs = list(collections_logs or [])

    active_accounts = [x for x in billing_accounts if (x.get("status") or "").lower() in {"active", "live", "paying"}]
    paid_invoices = [x for x in invoices if (x.get("status") or "").lower() in {"paid", "settled", "completed"}]
    active_subscriptions = [x for x in subscriptions if (x.get("status") or "").lower() in {"active", "live", "renewing"}]
    collected_logs = [x for x in collections_logs if (x.get("status") or "").lower() in {"collected", "completed", "settled"}]

    mrr_total = sum(_as_float(x.get("mrr_amount")) for x in subscriptions)
    invoice_total = sum(_as_float(x.get("invoice_amount")) for x in invoices)
    collected_total = sum(_as_float(x.get("amount_collected")) for x in collections_logs)

    account_rows: List[Dict] = []
    for row in billing_accounts:
        account_rows.append({
            "account_id": row.get("id"),
            "account_name": row.get("account_name") or "Billing Account",
            "account_type": row.get("account_type") or "subscription",
            "status": row.get("status") or "draft",
            "created_at": row.get("created_at"),
        })

    invoice_rows: List[Dict] = []
    for row in invoices:
        invoice_rows.append({
            "invoice_id": row.get("id"),
            "invoice_name": row.get("invoice_name") or "Invoice",
            "invoice_amount": _round(_as_float(row.get("invoice_amount"))),
            "status": row.get("status") or "draft",
            "created_at": row.get("created_at"),
        })

    subscription_rows: List[Dict] = []
    for row in subscriptions:
        subscription_rows.append({
            "subscription_id": row.get("id"),
            "subscription_name": row.get("subscription_name") or "Subscription",
            "plan_name": row.get("plan_name") or "Plan",
            "mrr_amount": _round(_as_float(row.get("mrr_amount"))),
            "status": row.get("status") or "draft",
            "created_at": row.get("created_at"),
        })

    collections_rows: List[Dict] = []
    for row in collections_logs:
        collections_rows.append({
            "collection_id": row.get("id"),
            "account_name": row.get("account_name") or "Account",
            "amount_collected": _round(_as_float(row.get("amount_collected"))),
            "status": row.get("status") or "pending",
            "created_at": row.get("created_at"),
        })

    revenue_score = max(
        45,
        min(
            100,
            int(
                60
                + len(active_accounts) * 2
                + len(paid_invoices) * 2
                + len(active_subscriptions) * 3
                + len(collected_logs) * 2
                + (5 if mrr_total >= 1000 else 0)
            )
        ),
    )

    return {
        "summary": {
            "accounts_total": len(billing_accounts),
            "accounts_active": len(active_accounts),
            "invoices_total": len(invoices),
            "invoices_paid": len(paid_invoices),
            "subscriptions_total": len(subscriptions),
            "subscriptions_active": len(active_subscriptions),
            "mrr_total": _round(mrr_total),
            "invoice_total": _round(invoice_total),
            "collected_total": _round(collected_total),
            "revenue_score": revenue_score,
        },
        "billing_accounts": account_rows,
        "invoices": invoice_rows,
        "subscriptions": subscription_rows,
        "collections_logs": collections_rows,
        "revenue_health": {
            "account_registry_ready": bool(billing_accounts),
            "invoice_registry_ready": bool(invoices),
            "subscription_registry_ready": bool(subscriptions),
            "collections_registry_ready": bool(collections_logs),
            "revenue_score": revenue_score,
        },
    }
