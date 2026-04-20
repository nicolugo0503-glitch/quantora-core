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


def build_sales_partnership_package(
    enterprise_leads: Iterable[Dict],
    opportunities: Iterable[Dict],
    partnerships: Iterable[Dict],
    partner_activities: Iterable[Dict],
) -> Dict:
    enterprise_leads = list(enterprise_leads or [])
    opportunities = list(opportunities or [])
    partnerships = list(partnerships or [])
    partner_activities = list(partner_activities or [])

    active_leads = [x for x in enterprise_leads if (x.get("status") or "").lower() in {"new", "qualified", "active", "contacted"}]
    active_opps = [x for x in opportunities if (x.get("stage") or "").lower() in {"qualified", "proposal", "negotiation", "pilot"}]
    closed_won = [x for x in opportunities if (x.get("stage") or "").lower() in {"closed_won", "won"}]
    active_partnerships = [x for x in partnerships if (x.get("status") or "").lower() in {"active", "signed", "live"}]

    pipeline_value = sum(_as_float(x.get("pipeline_value")) for x in opportunities)
    won_value = sum(_as_float(x.get("pipeline_value")) for x in closed_won)

    lead_rows: List[Dict] = []
    for row in enterprise_leads:
        lead_rows.append({
            "lead_id": row.get("id"),
            "account_name": row.get("account_name") or "Account",
            "segment": row.get("segment") or "institutional",
            "status": row.get("status") or "new",
            "owner": row.get("owner") or "operator",
            "created_at": row.get("created_at"),
        })

    opp_rows: List[Dict] = []
    for row in opportunities:
        opp_rows.append({
            "opportunity_id": row.get("id"),
            "opportunity_name": row.get("opportunity_name") or "Opportunity",
            "account_name": row.get("account_name") or "Account",
            "stage": row.get("stage") or "qualified",
            "pipeline_value": _round(_as_float(row.get("pipeline_value"))),
            "created_at": row.get("created_at"),
        })

    partnership_rows: List[Dict] = []
    for row in partnerships:
        partnership_rows.append({
            "partnership_id": row.get("id"),
            "partner_name": row.get("partner_name") or "Partner",
            "partnership_type": row.get("partnership_type") or "distribution",
            "status": row.get("status") or "draft",
            "estimated_value": _round(_as_float(row.get("estimated_value"))),
            "created_at": row.get("created_at"),
        })

    activity_rows: List[Dict] = []
    for row in partner_activities:
        activity_rows.append({
            "activity_id": row.get("id"),
            "partner_name": row.get("partner_name") or "Partner",
            "activity_name": row.get("activity_name") or "Activity",
            "status": row.get("status") or "planned",
            "created_at": row.get("created_at"),
        })

    engine_score = max(
        45,
        min(
            100,
            int(
                55
                + len(active_leads) * 2
                + len(active_opps) * 3
                + len(active_partnerships) * 4
                + len(closed_won) * 3
            )
        ),
    )

    return {
        "summary": {
            "enterprise_leads": len(enterprise_leads),
            "active_leads": len(active_leads),
            "opportunities": len(opportunities),
            "active_opportunities": len(active_opps),
            "partnerships": len(partnerships),
            "active_partnerships": len(active_partnerships),
            "pipeline_value": _round(pipeline_value),
            "won_value": _round(won_value),
            "engine_score": engine_score,
        },
        "enterprise_leads": lead_rows,
        "opportunities": opp_rows,
        "partnerships": partnership_rows,
        "partner_activities": activity_rows,
        "engine_health": {
            "lead_registry_ready": bool(enterprise_leads),
            "opportunity_pipeline_ready": bool(opportunities),
            "partnership_registry_ready": bool(partnerships),
            "partner_activity_ready": bool(partner_activities),
            "engine_score": engine_score,
        },
    }
