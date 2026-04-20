
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


def build_fill_position_package(
    fill_rows: Iterable[Dict],
    position_rows: Iterable[Dict],
    lifecycle_rows: Iterable[Dict],
    reconciliation_rows: Iterable[Dict],
) -> Dict:
    fill_rows = list(fill_rows or [])
    position_rows = list(position_rows or [])
    lifecycle_rows = list(lifecycle_rows or [])
    reconciliation_rows = list(reconciliation_rows or [])

    settled_fills = [x for x in fill_rows if (x.get("status") or "").lower() in {"filled", "settled", "confirmed"}]
    open_positions = [x for x in position_rows if (x.get("status") or "").lower() in {"open", "active", "live"}]
    completed_lifecycle = [x for x in lifecycle_rows if (x.get("status") or "").lower() in {"completed", "tracked", "closed"}]
    matched_recons = [x for x in reconciliation_rows if (x.get("status") or "").lower() in {"matched", "clean", "reconciled"}]

    fill_notional_total = sum(_as_float(x.get("fill_notional")) for x in fill_rows)
    position_notional_total = sum(_as_float(x.get("position_notional")) for x in position_rows)
    realized_pnl_total = sum(_as_float(x.get("realized_pnl")) for x in position_rows)

    fill_view: List[Dict] = []
    for row in fill_rows:
        fill_view.append({
            "fill_id": row.get("id"),
            "symbol": row.get("symbol") or "SPY",
            "fill_qty": _round(_as_float(row.get("fill_qty"))),
            "fill_price": _round(_as_float(row.get("fill_price"))),
            "fill_notional": _round(_as_float(row.get("fill_notional"))),
            "status": row.get("status") or "draft",
            "created_at": row.get("created_at"),
        })

    position_view: List[Dict] = []
    for row in position_rows:
        position_view.append({
            "position_id": row.get("id"),
            "symbol": row.get("symbol") or "SPY",
            "position_qty": _round(_as_float(row.get("position_qty"))),
            "position_notional": _round(_as_float(row.get("position_notional"))),
            "realized_pnl": _round(_as_float(row.get("realized_pnl"))),
            "status": row.get("status") or "draft",
            "created_at": row.get("created_at"),
        })

    lifecycle_view: List[Dict] = []
    for row in lifecycle_rows:
        lifecycle_view.append({
            "event_id": row.get("id"),
            "symbol": row.get("symbol") or "SPY",
            "event_name": row.get("event_name") or "fill_to_position",
            "status": row.get("status") or "draft",
            "created_at": row.get("created_at"),
        })

    recon_view: List[Dict] = []
    for row in reconciliation_rows:
        recon_view.append({
            "recon_id": row.get("id"),
            "recon_name": row.get("recon_name") or "Broker Reconciliation",
            "broker_value": _round(_as_float(row.get("broker_value"))),
            "internal_value": _round(_as_float(row.get("internal_value"))),
            "status": row.get("status") or "draft",
            "created_at": row.get("created_at"),
        })

    lifecycle_score = max(
        45,
        min(
            100,
            int(
                64
                + len(settled_fills) * 3
                + len(open_positions) * 3
                + len(completed_lifecycle) * 2
                + len(matched_recons) * 3
            )
        ),
    )

    lifecycle_state = "EMPTY"
    if settled_fills or open_positions:
        lifecycle_state = "TRACKING"
    if open_positions and matched_recons:
        lifecycle_state = "RECONCILED"

    return {
        "summary": {
            "fills_total": len(fill_rows),
            "fills_settled": len(settled_fills),
            "positions_total": len(position_rows),
            "positions_open": len(open_positions),
            "lifecycle_events_total": len(lifecycle_rows),
            "lifecycle_completed": len(completed_lifecycle),
            "reconciliations_total": len(reconciliation_rows),
            "reconciliations_matched": len(matched_recons),
            "fill_notional_total": _round(fill_notional_total),
            "position_notional_total": _round(position_notional_total),
            "realized_pnl_total": _round(realized_pnl_total),
            "lifecycle_score": lifecycle_score,
            "lifecycle_state": lifecycle_state,
        },
        "fills": fill_view,
        "positions": position_view,
        "lifecycle_events": lifecycle_view,
        "reconciliations": recon_view,
        "lifecycle_health": {
            "fill_registry_ready": bool(fill_rows),
            "position_registry_ready": bool(position_rows),
            "event_registry_ready": bool(lifecycle_rows),
            "reconciliation_registry_ready": bool(reconciliation_rows),
            "lifecycle_score": lifecycle_score,
            "lifecycle_state": lifecycle_state,
        },
    }
