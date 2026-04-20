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


def build_distribution_growth_package(
    referral_programs: Iterable[Dict],
    referral_leads: Iterable[Dict],
    growth_loops: Iterable[Dict],
    acquisition_campaigns: Iterable[Dict],
) -> Dict:
    referral_programs = list(referral_programs or [])
    referral_leads = list(referral_leads or [])
    growth_loops = list(growth_loops or [])
    acquisition_campaigns = list(acquisition_campaigns or [])

    active_programs = [x for x in referral_programs if (x.get("status") or "").lower() in {"active", "live", "enabled"}]
    converted_leads = [x for x in referral_leads if (x.get("status") or "").lower() in {"converted", "won", "funded"}]
    active_loops = [x for x in growth_loops if (x.get("status") or "").lower() in {"active", "live", "running"}]
    profitable_campaigns = [x for x in acquisition_campaigns if _as_float(x.get("roi")) > 1.0]

    total_referral_value = sum(_as_float(x.get("estimated_value")) for x in referral_leads)
    total_campaign_spend = sum(_as_float(x.get("spend")) for x in acquisition_campaigns)

    program_rows: List[Dict] = []
    for row in referral_programs:
        program_rows.append({
            "program_id": row.get("id"),
            "program_name": row.get("program_name") or "Referral Program",
            "reward_type": row.get("reward_type") or "cash",
            "status": row.get("status") or "draft",
            "created_at": row.get("created_at"),
        })

    lead_rows: List[Dict] = []
    for row in referral_leads:
        lead_rows.append({
            "lead_id": row.get("id"),
            "referrer_name": row.get("referrer_name") or "Referrer",
            "lead_name": row.get("lead_name") or "Lead",
            "estimated_value": _round(_as_float(row.get("estimated_value"))),
            "status": row.get("status") or "new",
            "created_at": row.get("created_at"),
        })

    loop_rows: List[Dict] = []
    for row in growth_loops:
        loop_rows.append({
            "loop_id": row.get("id"),
            "loop_name": row.get("loop_name") or "Growth Loop",
            "channel": row.get("channel") or "referral",
            "status": row.get("status") or "draft",
            "created_at": row.get("created_at"),
        })

    campaign_rows: List[Dict] = []
    for row in acquisition_campaigns:
        campaign_rows.append({
            "campaign_id": row.get("id"),
            "campaign_name": row.get("campaign_name") or "Campaign",
            "channel": row.get("channel") or "social",
            "spend": _round(_as_float(row.get("spend"))),
            "roi": _round(_as_float(row.get("roi"))),
            "status": row.get("status") or "draft",
            "created_at": row.get("created_at"),
        })

    growth_score = max(
        45,
        min(
            100,
            int(
                58
                + len(active_programs) * 3
                + len(converted_leads) * 3
                + len(active_loops) * 2
                + len(profitable_campaigns) * 2
            )
        ),
    )

    return {
        "summary": {
            "programs_total": len(referral_programs),
            "programs_active": len(active_programs),
            "referral_leads_total": len(referral_leads),
            "referral_leads_converted": len(converted_leads),
            "growth_loops_total": len(growth_loops),
            "growth_loops_active": len(active_loops),
            "campaign_spend_total": _round(total_campaign_spend),
            "referral_value_total": _round(total_referral_value),
            "growth_score": growth_score,
        },
        "referral_programs": program_rows,
        "referral_leads": lead_rows,
        "growth_loops": loop_rows,
        "acquisition_campaigns": campaign_rows,
        "growth_health": {
            "program_registry_ready": bool(referral_programs),
            "lead_registry_ready": bool(referral_leads),
            "loop_registry_ready": bool(growth_loops),
            "campaign_registry_ready": bool(acquisition_campaigns),
            "growth_score": growth_score,
        },
    }
