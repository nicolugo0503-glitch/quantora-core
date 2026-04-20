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


def build_investor_crm_package(
    prospects: Iterable[Dict],
    meetings: Iterable[Dict],
    raise_rounds: Iterable[Dict],
    outreach_events: Iterable[Dict],
) -> Dict:
    prospects = list(prospects or [])
    meetings = list(meetings or [])
    raise_rounds = list(raise_rounds or [])
    outreach_events = list(outreach_events or [])

    active_prospects = [p for p in prospects if (p.get("stage") or "").lower() in {"new", "contacted", "qualified", "dd", "soft_commit"}]
    soft_commit_prospects = [p for p in prospects if (p.get("stage") or "").lower() in {"soft_commit", "verbal_commit"}]
    closed_prospects = [p for p in prospects if (p.get("stage") or "").lower() in {"won", "funded", "closed"}]
    live_rounds = [r for r in raise_rounds if (r.get("status") or "").lower() in {"active", "open", "raising"}]
    completed_meetings = [m for m in meetings if (m.get("status") or "").lower() in {"held", "completed"}]

    total_pipeline = sum(_as_float(p.get("target_commitment")) for p in prospects)
    soft_commit_value = sum(_as_float(p.get("target_commitment")) for p in soft_commit_prospects)
    funded_value = sum(_as_float(p.get("target_commitment")) for p in closed_prospects)

    prospect_rows: List[Dict] = []
    for row in prospects:
        prospect_rows.append({
            "prospect_id": row.get("id"),
            "prospect_name": row.get("prospect_name") or "Prospect",
            "investor_type": row.get("investor_type") or "family_office",
            "stage": row.get("stage") or "new",
            "target_commitment": _round(_as_float(row.get("target_commitment"))),
            "owner": row.get("owner") or "operator",
            "created_at": row.get("created_at"),
        })

    meeting_rows: List[Dict] = []
    for row in meetings:
        meeting_rows.append({
            "meeting_id": row.get("id"),
            "prospect_name": row.get("prospect_name") or "Prospect",
            "meeting_type": row.get("meeting_type") or "intro_call",
            "status": row.get("status") or "scheduled",
            "scheduled_at": row.get("scheduled_at"),
            "created_at": row.get("created_at"),
        })

    round_rows: List[Dict] = []
    for row in raise_rounds:
        round_rows.append({
            "round_id": row.get("id"),
            "round_name": row.get("round_name") or "Capital Raise",
            "target_amount": _round(_as_float(row.get("target_amount"))),
            "soft_commit_amount": _round(_as_float(row.get("soft_commit_amount"))),
            "funded_amount": _round(_as_float(row.get("funded_amount"))),
            "status": row.get("status") or "draft",
            "created_at": row.get("created_at"),
        })

    outreach_rows: List[Dict] = []
    for row in outreach_events:
        outreach_rows.append({
            "event_id": row.get("id"),
            "prospect_name": row.get("prospect_name") or "Prospect",
            "channel": row.get("channel") or "email",
            "outreach_type": row.get("outreach_type") or "follow_up",
            "status": row.get("status") or "sent",
            "created_at": row.get("created_at"),
        })

    crm_score = max(
        45,
        min(
            100,
            int(
                55
                + len(active_prospects) * 2
                + len(completed_meetings) * 2
                + len(live_rounds) * 4
                + len(soft_commit_prospects) * 3
            ),
        ),
    )

    return {
        "summary": {
            "prospects_total": len(prospects),
            "active_prospects": len(active_prospects),
            "meetings_total": len(meetings),
            "live_rounds": len(live_rounds),
            "pipeline_value": _round(total_pipeline),
            "soft_commit_value": _round(soft_commit_value),
            "funded_value": _round(funded_value),
            "crm_score": crm_score,
        },
        "prospects": prospect_rows,
        "meetings": meeting_rows,
        "raise_rounds": round_rows,
        "outreach_events": outreach_rows,
        "crm_health": {
            "prospect_registry_ready": bool(prospects),
            "meeting_pipeline_ready": bool(meetings),
            "raise_rounds_ready": bool(raise_rounds),
            "outreach_tracking_ready": bool(outreach_events),
            "crm_score": crm_score,
        },
    }
