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


def build_treasury_liquidity_package(
    cash_accounts: Iterable[Dict],
    liquidity_buckets: Iterable[Dict],
    treasury_flows: Iterable[Dict],
    funding_forecasts: Iterable[Dict],
) -> Dict:
    cash_accounts = list(cash_accounts or [])
    liquidity_buckets = list(liquidity_buckets or [])
    treasury_flows = list(treasury_flows or [])
    funding_forecasts = list(funding_forecasts or [])

    total_cash = sum(_as_float(x.get("cash_balance")) for x in cash_accounts)
    total_available = sum(_as_float(x.get("available_cash")) for x in cash_accounts)
    total_restricted = sum(_as_float(x.get("restricted_cash")) for x in cash_accounts)
    near_term_liquidity = sum(_as_float(x.get("bucket_amount")) for x in liquidity_buckets if (x.get("bucket_name") or "").lower() in {"t0", "t1", "same_day", "next_day"})
    inflows = [f for f in treasury_flows if (f.get("flow_direction") or "").lower() in {"in", "inflow", "deposit"}]
    outflows = [f for f in treasury_flows if (f.get("flow_direction") or "").lower() in {"out", "outflow", "withdrawal"}]
    stressed_forecasts = [f for f in funding_forecasts if (f.get("status") or "").lower() in {"warning", "breach", "stressed"}]

    account_rows: List[Dict] = []
    for row in cash_accounts:
        account_rows.append({
            "account_id": row.get("id"),
            "account_name": row.get("account_name") or "Treasury Account",
            "institution_name": row.get("institution_name") or "Bank",
            "cash_balance": _round(_as_float(row.get("cash_balance"))),
            "available_cash": _round(_as_float(row.get("available_cash"))),
            "restricted_cash": _round(_as_float(row.get("restricted_cash"))),
            "status": row.get("status") or "active",
            "created_at": row.get("created_at"),
        })

    bucket_rows: List[Dict] = []
    for row in liquidity_buckets:
        bucket_rows.append({
            "bucket_id": row.get("id"),
            "bucket_name": row.get("bucket_name") or "T0",
            "bucket_amount": _round(_as_float(row.get("bucket_amount"))),
            "target_amount": _round(_as_float(row.get("target_amount"))),
            "status": row.get("status") or "ok",
            "created_at": row.get("created_at"),
        })

    flow_rows: List[Dict] = []
    for row in treasury_flows:
        flow_rows.append({
            "flow_id": row.get("id"),
            "flow_name": row.get("flow_name") or "Treasury Flow",
            "flow_direction": row.get("flow_direction") or "inflow",
            "amount": _round(_as_float(row.get("amount"))),
            "source_ref": row.get("source_ref") or "-",
            "status": row.get("status") or "scheduled",
            "created_at": row.get("created_at"),
        })

    forecast_rows: List[Dict] = []
    for row in funding_forecasts:
        forecast_rows.append({
            "forecast_id": row.get("id"),
            "forecast_name": row.get("forecast_name") or "Liquidity Forecast",
            "projected_cash": _round(_as_float(row.get("projected_cash"))),
            "minimum_required": _round(_as_float(row.get("minimum_required"))),
            "status": row.get("status") or "ok",
            "created_at": row.get("created_at"),
        })

    treasury_score = max(
        40,
        min(
            100,
            int(
                60
                + len(cash_accounts) * 4
                + len(liquidity_buckets) * 3
                + len(inflows)
                - len(outflows)
                - len(stressed_forecasts) * 5
            )
        ),
    )

    return {
        "summary": {
            "accounts_tracked": len(cash_accounts),
            "total_cash": _round(total_cash),
            "available_cash": _round(total_available),
            "restricted_cash": _round(total_restricted),
            "near_term_liquidity": _round(near_term_liquidity),
            "funding_forecasts": len(funding_forecasts),
            "treasury_score": treasury_score,
        },
        "cash_accounts": account_rows,
        "liquidity_buckets": bucket_rows,
        "treasury_flows": flow_rows,
        "funding_forecasts": forecast_rows,
        "treasury_health": {
            "cash_registry_ready": bool(cash_accounts),
            "liquidity_ladder_ready": bool(liquidity_buckets),
            "flow_monitoring_ready": bool(treasury_flows),
            "forecasting_ready": bool(funding_forecasts),
            "treasury_score": treasury_score,
        },
    }
