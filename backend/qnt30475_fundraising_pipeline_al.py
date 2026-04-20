
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


def build_fundraising_pipeline_package(
    fundraising_targets: Iterable[Dict],
    allocation_offers: Iterable[Dict],
    commitment_events: Iterable[Dict],
    conversion_logs: Iterable[Dict],
) -> Dict:
    fundraising_targets = list(fundraising_targets or [])
    allocation_offers = list(allocation_offers or [])
    commitment_events = list(commitment_events or [])
    conversion_logs = list(conversion_logs or [])

    active_targets = [x for x in fundraising_targets if (x.get("status") or "").lower() in {"active", "live", "open"}]
    live_offers = [x for x in allocation_offers if (x.get("status") or "").lower() in {"active", "open", "sent"}]
    committed_events = [x for x in commitment_events if (x.get("status") or "").lower() in {"committed", "closed", "won"}]
    converted_logs = [x for x in conversion_logs if (x.get("status") or "").lower() in {"converted", "funded", "closed"}]

    target_total = sum(_as_float(x.get("target_amount")) for x in fundraising_targets)
    offer_total = sum(_as_float(x.get("offer_amount")) for x in allocation_offers)
    committed_total = sum(_as_float(x.get("commitment_amount")) for x in commitment_events)
    converted_total = sum(_as_float(x.get("converted_amount")) for x in conversion_logs)

    target_rows: List[Dict] = []
    for row in fundraising_targets:
        target_rows.append({
            "target_id": row.get("id"),
            "target_name": row.get("target_name") or "Fundraising Target",
            "channel_name": row.get("channel_name") or "allocator",
            "target_amount": _round(_as_float(row.get("target_amount"))),
            "status": row.get("status") or "draft",
            "created_at": row.get("created_at"),
        })

    offer_rows: List[Dict] = []
    for row in allocation_offers:
        offer_rows.append({
            "offer_id": row.get("id"),
            "investor_name": row.get("investor_name") or "Investor",
            "offer_amount": _round(_as_float(row.get("offer_amount"))),
            "vehicle_name": row.get("vehicle_name") or "Fund Vehicle",
            "status": row.get("status") or "draft",
            "created_at": row.get("created_at"),
        })

    commitment_rows: List[Dict] = []
    for row in commitment_events:
        commitment_rows.append({
            "commitment_id": row.get("id"),
            "investor_name": row.get("investor_name") or "Investor",
            "commitment_amount": _round(_as_float(row.get("commitment_amount"))),
            "status": row.get("status") or "open",
            "created_at": row.get("created_at"),
        })

    conversion_rows: List[Dict] = []
    for row in conversion_logs:
        conversion_rows.append({
            "conversion_id": row.get("id"),
            "investor_name": row.get("investor_name") or "Investor",
            "converted_amount": _round(_as_float(row.get("converted_amount"))),
            "status": row.get("status") or "pending",
            "created_at": row.get("created_at"),
        })

    pipeline_score = max(
        45,
        min(
            100,
            int(
                60
                + len(active_targets) * 2
                + len(live_offers) * 3
                + len(committed_events) * 3
                + len(converted_logs) * 2
                + (5 if converted_total >= 1000000 else 0)
            )
        ),
    )

    return {
        "summary": {
            "targets_total": len(fundraising_targets),
            "targets_active": len(active_targets),
            "offers_total": len(allocation_offers),
            "offers_live": len(live_offers),
            "commitments_total": len(commitment_events),
            "commitments_closed": len(committed_events),
            "conversions_total": len(converted_logs),
            "target_amount_total": _round(target_total),
            "offer_amount_total": _round(offer_total),
            "commitment_amount_total": _round(committed_total),
            "converted_amount_total": _round(converted_total),
            "pipeline_score": pipeline_score,
        },
        "fundraising_targets": target_rows,
        "allocation_offers": offer_rows,
        "commitment_events": commitment_rows,
        "conversion_logs": conversion_rows,
        "pipeline_health": {
            "target_registry_ready": bool(fundraising_targets),
            "offer_registry_ready": bool(allocation_offers),
            "commitment_registry_ready": bool(commitment_events),
            "conversion_registry_ready": bool(conversion_logs),
            "pipeline_score": pipeline_score,
        },
    }
