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


def build_global_capital_network_package(
    funds: Iterable[Dict],
    capital_transfers: Iterable[Dict],
    allocation_links: Iterable[Dict],
    orchestration_cycles: Iterable[Dict],
) -> Dict:
    funds = list(funds or [])
    capital_transfers = list(capital_transfers or [])
    allocation_links = list(allocation_links or [])
    orchestration_cycles = list(orchestration_cycles or [])

    active_funds = [x for x in funds if (x.get("status") or "").lower() in {"active", "live", "deployed"}]
    completed_transfers = [x for x in capital_transfers if (x.get("status") or "").lower() in {"completed", "settled", "applied"}]
    active_links = [x for x in allocation_links if (x.get("status") or "").lower() in {"active", "live", "enabled"}]
    completed_cycles = [x for x in orchestration_cycles if (x.get("status") or "").lower() in {"completed", "closed", "executed"}]

    total_capital = sum(_as_float(x.get("capital_base")) for x in funds)
    transfer_volume = sum(_as_float(x.get("amount")) for x in capital_transfers)
    linked_weight = sum(_as_float(x.get("allocation_weight")) for x in allocation_links)

    fund_rows: List[Dict] = []
    for row in funds:
        fund_rows.append({
            "fund_id": row.get("id"),
            "fund_name": row.get("fund_name") or "Fund",
            "jurisdiction": row.get("jurisdiction") or "US",
            "capital_base": _round(_as_float(row.get("capital_base"))),
            "status": row.get("status") or "draft",
            "created_at": row.get("created_at"),
        })

    transfer_rows: List[Dict] = []
    for row in capital_transfers:
        transfer_rows.append({
            "transfer_id": row.get("id"),
            "from_fund": row.get("from_fund") or "Fund A",
            "to_fund": row.get("to_fund") or "Fund B",
            "amount": _round(_as_float(row.get("amount"))),
            "status": row.get("status") or "pending",
            "created_at": row.get("created_at"),
        })

    link_rows: List[Dict] = []
    for row in allocation_links:
        link_rows.append({
            "link_id": row.get("id"),
            "source_fund": row.get("source_fund") or "Fund A",
            "target_strategy": row.get("target_strategy") or "Strategy",
            "allocation_weight": _round(_as_float(row.get("allocation_weight"))),
            "status": row.get("status") or "draft",
            "created_at": row.get("created_at"),
        })

    cycle_rows: List[Dict] = []
    for row in orchestration_cycles:
        cycle_rows.append({
            "cycle_id": row.get("id"),
            "cycle_name": row.get("cycle_name") or "Orchestration Cycle",
            "status": row.get("status") or "draft",
            "actions_count": int(_as_float(row.get("actions_count"))),
            "created_at": row.get("created_at"),
        })

    network_score = max(
        45,
        min(
            100,
            int(
                60
                + len(active_funds) * 4
                + len(completed_transfers) * 2
                + len(active_links) * 3
                + len(completed_cycles) * 3
            )
        ),
    )

    return {
        "summary": {
            "funds_total": len(funds),
            "funds_active": len(active_funds),
            "network_capital": _round(total_capital),
            "transfer_volume": _round(transfer_volume),
            "allocation_links": len(allocation_links),
            "linked_weight_total": _round(linked_weight),
            "cycles_completed": len(completed_cycles),
            "network_score": network_score,
        },
        "funds": fund_rows,
        "capital_transfers": transfer_rows,
        "allocation_links": link_rows,
        "orchestration_cycles": cycle_rows,
        "network_health": {
            "fund_registry_ready": bool(funds),
            "transfer_rail_ready": bool(capital_transfers),
            "allocation_link_ready": bool(allocation_links),
            "cycle_engine_ready": bool(orchestration_cycles),
            "network_score": network_score,
        },
    }
