
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
    return round(float(value), 4)


def build_pnl_nav_package(
    pnl_rows: Iterable[Dict],
    nav_rows: Iterable[Dict],
    attribution_rows: Iterable[Dict],
    valuation_rows: Iterable[Dict],
) -> Dict:
    pnl_rows = list(pnl_rows or [])
    nav_rows = list(nav_rows or [])
    attribution_rows = list(attribution_rows or [])
    valuation_rows = list(valuation_rows or [])

    positive_pnl_rows = [x for x in pnl_rows if _as_float(x.get("pnl_value")) > 0]
    published_nav_rows = [x for x in nav_rows if (x.get("status") or "").lower() in {"published", "final", "locked"}]
    active_attr_rows = [x for x in attribution_rows if (x.get("status") or "").lower() in {"active", "tracked", "live"}]
    fresh_valuations = [x for x in valuation_rows if (x.get("status") or "").lower() in {"fresh", "validated", "live"}]

    pnl_total = sum(_as_float(x.get("pnl_value")) for x in pnl_rows)
    nav_total = sum(_as_float(x.get("nav_value")) for x in nav_rows)
    gross_market_value = sum(_as_float(x.get("market_value")) for x in valuation_rows)

    pnl_view: List[Dict] = []
    for row in pnl_rows:
        pnl_view.append({
            "pnl_id": row.get("id"),
            "book_name": row.get("book_name") or "Core Book",
            "pnl_value": _round(_as_float(row.get("pnl_value"))),
            "pnl_type": row.get("pnl_type") or "realized",
            "status": row.get("status") or "draft",
            "created_at": row.get("created_at"),
        })

    nav_view: List[Dict] = []
    for row in nav_rows:
        nav_view.append({
            "nav_id": row.get("id"),
            "vehicle_name": row.get("vehicle_name") or "Flagship Fund",
            "nav_value": _round(_as_float(row.get("nav_value"))),
            "share_count": _round(_as_float(row.get("share_count"))),
            "status": row.get("status") or "draft",
            "created_at": row.get("created_at"),
        })

    attribution_view: List[Dict] = []
    for row in attribution_rows:
        attribution_view.append({
            "attribution_id": row.get("id"),
            "source_name": row.get("source_name") or "Momentum Alpha",
            "contribution_value": _round(_as_float(row.get("contribution_value"))),
            "bucket_type": row.get("bucket_type") or "strategy",
            "status": row.get("status") or "draft",
            "created_at": row.get("created_at"),
        })

    valuation_view: List[Dict] = []
    for row in valuation_rows:
        valuation_view.append({
            "valuation_id": row.get("id"),
            "symbol": row.get("symbol") or "SPY",
            "market_value": _round(_as_float(row.get("market_value"))),
            "price_mark": _round(_as_float(row.get("price_mark"))),
            "status": row.get("status") or "draft",
            "created_at": row.get("created_at"),
        })

    engine_score = max(
        45,
        min(
            100,
            int(
                65
                + len(positive_pnl_rows) * 2
                + len(published_nav_rows) * 3
                + len(active_attr_rows) * 2
                + len(fresh_valuations) * 2
            )
        ),
    )

    engine_state = "COLD"
    if pnl_rows or nav_rows:
        engine_state = "TRACKING"
    if published_nav_rows and fresh_valuations:
        engine_state = "LIVE"

    return {
        "summary": {
            "pnl_rows_total": len(pnl_rows),
            "nav_rows_total": len(nav_rows),
            "attribution_rows_total": len(attribution_rows),
            "valuation_rows_total": len(valuation_rows),
            "positive_pnl_rows": len(positive_pnl_rows),
            "published_nav_rows": len(published_nav_rows),
            "gross_market_value": _round(gross_market_value),
            "pnl_total": _round(pnl_total),
            "nav_total": _round(nav_total),
            "engine_score": engine_score,
            "engine_state": engine_state,
        },
        "pnl_rows": pnl_view,
        "nav_rows": nav_view,
        "attribution_rows": attribution_view,
        "valuation_rows": valuation_view,
        "engine_health": {
            "pnl_registry_ready": bool(pnl_rows),
            "nav_registry_ready": bool(nav_rows),
            "attribution_registry_ready": bool(attribution_rows),
            "valuation_registry_ready": bool(valuation_rows),
            "engine_score": engine_score,
            "engine_state": engine_state,
        },
    }
