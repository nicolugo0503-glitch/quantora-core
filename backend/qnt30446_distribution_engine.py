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


def build_distribution_package(
    leads: Iterable[Dict],
    referrals: Iterable[Dict],
    campaigns: Iterable[Dict],
    onboarding_flows: Iterable[Dict],
) -> Dict:
    leads = list(leads or [])
    referrals = list(referrals or [])
    campaigns = list(campaigns or [])
    onboarding_flows = list(onboarding_flows or [])

    active_leads = [l for l in leads if (l.get("status") or "").lower() in {"new", "qualified", "active", "contacted"}]
    converted_leads = [l for l in leads if (l.get("status") or "").lower() in {"converted", "won", "activated"}]
    active_campaigns = [c for c in campaigns if (c.get("status") or "").lower() in {"active", "running", "live"}]
    active_flows = [f for f in onboarding_flows if (f.get("status") or "").lower() in {"active", "live"}]
    active_referrals = [r for r in referrals if (r.get("status") or "").lower() in {"pending", "active", "earned"}]

    total_pipeline_value = sum(_as_float(l.get("pipeline_value")) for l in leads)
    qualified_value = sum(_as_float(l.get("pipeline_value")) for l in leads if (l.get("status") or "").lower() in {"qualified", "converted", "won", "activated"})
    conversion_rate = round((len(converted_leads) / max(1, len(leads))) * 100.0, 2)

    loop_score = max(40, min(100, int(
        50
        + len(active_campaigns) * 5
        + len(active_flows) * 4
        + len(active_referrals) * 3
        + len(converted_leads) * 4
        - max(0, len(active_leads) - len(converted_leads)) // 3
    )))

    lead_rows: List[Dict] = []
    for row in leads:
        lead_rows.append({
            "lead_id": row.get("id"),
            "lead_name": row.get("lead_name") or "Unknown Lead",
            "channel": row.get("channel") or "direct",
            "status": row.get("status") or "new",
            "pipeline_value": _round(_as_float(row.get("pipeline_value"))),
            "owner": row.get("owner") or "operator",
            "created_at": row.get("created_at"),
        })

    campaign_rows: List[Dict] = []
    for row in campaigns:
        campaign_rows.append({
            "campaign_id": row.get("id"),
            "campaign_name": row.get("campaign_name") or "Campaign",
            "channel": row.get("channel") or "direct",
            "status": row.get("status") or "draft",
            "budget": _round(_as_float(row.get("budget"))),
            "leads_generated": int(_as_float(row.get("leads_generated"))),
            "created_at": row.get("created_at"),
        })

    referral_rows: List[Dict] = []
    for row in referrals:
        referral_rows.append({
            "referral_id": row.get("id"),
            "referrer_name": row.get("referrer_name") or "Referrer",
            "referred_name": row.get("referred_name") or "Prospect",
            "reward_amount": _round(_as_float(row.get("reward_amount"))),
            "status": row.get("status") or "pending",
            "created_at": row.get("created_at"),
        })

    onboarding_rows: List[Dict] = []
    for row in onboarding_flows:
        onboarding_rows.append({
            "flow_id": row.get("id"),
            "flow_name": row.get("flow_name") or "Onboarding Flow",
            "target_segment": row.get("target_segment") or "general",
            "status": row.get("status") or "draft",
            "completion_rate": round(_as_float(row.get("completion_rate")), 2),
            "created_at": row.get("created_at"),
        })

    growth_mix = {
        "pipeline_value": _round(total_pipeline_value),
        "qualified_pipeline_value": _round(qualified_value),
        "conversion_rate_percent": conversion_rate,
        "campaigns_live": len(active_campaigns),
        "referrals_active": len(active_referrals),
    }

    engine_health = {
        "lead_registry_ready": bool(leads),
        "campaigns_ready": bool(campaigns),
        "referral_engine_ready": bool(referrals),
        "onboarding_ready": bool(onboarding_flows),
        "distribution_score": loop_score,
    }

    return {
        "summary": {
            "total_leads": len(leads),
            "active_leads": len(active_leads),
            "converted_leads": len(converted_leads),
            "total_pipeline_value": _round(total_pipeline_value),
            "qualified_pipeline_value": _round(qualified_value),
            "conversion_rate_percent": conversion_rate,
            "active_campaigns": len(active_campaigns),
            "distribution_score": loop_score,
        },
        "leads": lead_rows,
        "campaigns": campaign_rows,
        "referrals": referral_rows,
        "onboarding_flows": onboarding_rows,
        "growth_mix": growth_mix,
        "engine_health": engine_health,
    }
