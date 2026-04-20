
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
    investor_profiles: Iterable[Dict],
    relationship_stages: Iterable[Dict],
    touchpoints: Iterable[Dict],
    intelligence_notes: Iterable[Dict],
) -> Dict:
    investor_profiles = list(investor_profiles or [])
    relationship_stages = list(relationship_stages or [])
    touchpoints = list(touchpoints or [])
    intelligence_notes = list(intelligence_notes or [])

    active_profiles = [x for x in investor_profiles if (x.get("status") or "").lower() in {"active", "engaged", "live"}]
    advanced_stages = [x for x in relationship_stages if (x.get("stage_name") or "").lower() in {"qualified", "diligence", "allocation_committee", "soft_committed"}]
    completed_touchpoints = [x for x in touchpoints if (x.get("status") or "").lower() in {"completed", "held", "sent"}]
    high_signal_notes = [x for x in intelligence_notes if (x.get("signal_level") or "").lower() in {"high", "strong", "priority"}]

    potential_aum = sum(_as_float(x.get("potential_aum")) for x in investor_profiles)
    engaged_aum = sum(_as_float(x.get("potential_aum")) for x in active_profiles)

    profile_rows: List[Dict] = []
    for row in investor_profiles:
        profile_rows.append({
            "profile_id": row.get("id"),
            "investor_name": row.get("investor_name") or "Investor",
            "investor_type": row.get("investor_type") or "family_office",
            "potential_aum": _round(_as_float(row.get("potential_aum"))),
            "status": row.get("status") or "draft",
            "created_at": row.get("created_at"),
        })

    stage_rows: List[Dict] = []
    for row in relationship_stages:
        stage_rows.append({
            "stage_id": row.get("id"),
            "investor_name": row.get("investor_name") or "Investor",
            "stage_name": row.get("stage_name") or "sourced",
            "conviction_score": _round(_as_float(row.get("conviction_score"))),
            "status": row.get("status") or "open",
            "created_at": row.get("created_at"),
        })

    touchpoint_rows: List[Dict] = []
    for row in touchpoints:
        touchpoint_rows.append({
            "touchpoint_id": row.get("id"),
            "investor_name": row.get("investor_name") or "Investor",
            "touchpoint_type": row.get("touchpoint_type") or "meeting",
            "status": row.get("status") or "planned",
            "created_at": row.get("created_at"),
        })

    note_rows: List[Dict] = []
    for row in intelligence_notes:
        note_rows.append({
            "note_id": row.get("id"),
            "investor_name": row.get("investor_name") or "Investor",
            "signal_level": row.get("signal_level") or "medium",
            "summary": row.get("summary") or "Relationship note",
            "created_at": row.get("created_at"),
        })

    crm_score = max(
        45,
        min(
            100,
            int(
                60
                + len(active_profiles) * 2
                + len(advanced_stages) * 3
                + len(completed_touchpoints) * 2
                + len(high_signal_notes) * 2
                + (5 if engaged_aum >= 1000000 else 0)
            )
        ),
    )

    return {
        "summary": {
            "profiles_total": len(investor_profiles),
            "profiles_active": len(active_profiles),
            "stages_total": len(relationship_stages),
            "advanced_stages": len(advanced_stages),
            "touchpoints_total": len(touchpoints),
            "touchpoints_completed": len(completed_touchpoints),
            "notes_total": len(intelligence_notes),
            "high_signal_notes": len(high_signal_notes),
            "potential_aum_total": _round(potential_aum),
            "engaged_aum_total": _round(engaged_aum),
            "crm_score": crm_score,
        },
        "investor_profiles": profile_rows,
        "relationship_stages": stage_rows,
        "touchpoints": touchpoint_rows,
        "intelligence_notes": note_rows,
        "crm_health": {
            "profile_registry_ready": bool(investor_profiles),
            "stage_registry_ready": bool(relationship_stages),
            "touchpoint_registry_ready": bool(touchpoints),
            "intelligence_registry_ready": bool(intelligence_notes),
            "crm_score": crm_score,
        },
    }
