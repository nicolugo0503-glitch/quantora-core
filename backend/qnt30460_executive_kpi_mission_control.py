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


def build_executive_kpi_package(
    kpis: Iterable[Dict],
    scorecards: Iterable[Dict],
    executive_alerts: Iterable[Dict],
    strategic_initiatives: Iterable[Dict],
) -> Dict:
    kpis = list(kpis or [])
    scorecards = list(scorecards or [])
    executive_alerts = list(executive_alerts or [])
    strategic_initiatives = list(strategic_initiatives or [])

    healthy_kpis = [x for x in kpis if (x.get("status") or "").lower() in {"healthy", "on_track", "green"}]
    critical_alerts = [x for x in executive_alerts if (x.get("severity") or "").lower() in {"high", "critical"}]
    active_initiatives = [x for x in strategic_initiatives if (x.get("status") or "").lower() in {"active", "in_progress", "live"}]

    total_target_gap = sum(_as_float(x.get("target_value")) - _as_float(x.get("current_value")) for x in kpis)

    kpi_rows: List[Dict] = []
    for row in kpis:
        kpi_rows.append({
            "kpi_id": row.get("id"),
            "kpi_name": row.get("kpi_name") or "KPI",
            "category": row.get("category") or "company",
            "current_value": _round(_as_float(row.get("current_value"))),
            "target_value": _round(_as_float(row.get("target_value"))),
            "status": row.get("status") or "watch",
            "created_at": row.get("created_at"),
        })

    scorecard_rows: List[Dict] = []
    for row in scorecards:
        scorecard_rows.append({
            "scorecard_id": row.get("id"),
            "scorecard_name": row.get("scorecard_name") or "Executive Scorecard",
            "owner": row.get("owner") or "ceo",
            "score": _round(_as_float(row.get("score"))),
            "status": row.get("status") or "draft",
            "created_at": row.get("created_at"),
        })

    alert_rows: List[Dict] = []
    for row in executive_alerts:
        alert_rows.append({
            "alert_id": row.get("id"),
            "alert_name": row.get("alert_name") or "Executive Alert",
            "severity": row.get("severity") or "medium",
            "status": row.get("status") or "open",
            "target_ref": row.get("target_ref") or "-",
            "created_at": row.get("created_at"),
        })

    initiative_rows: List[Dict] = []
    for row in strategic_initiatives:
        initiative_rows.append({
            "initiative_id": row.get("id"),
            "initiative_name": row.get("initiative_name") or "Initiative",
            "owner": row.get("owner") or "operator",
            "status": row.get("status") or "draft",
            "progress_percent": round(_as_float(row.get("progress_percent")), 2),
            "created_at": row.get("created_at"),
        })

    mission_score = max(
        45,
        min(
            100,
            int(
                58
                + len(healthy_kpis) * 3
                + len(scorecards) * 2
                + len(active_initiatives) * 2
                - len(critical_alerts) * 4
            )
        ),
    )

    return {
        "summary": {
            "kpis_total": len(kpis),
            "kpis_healthy": len(healthy_kpis),
            "scorecards_total": len(scorecards),
            "critical_alerts": len(critical_alerts),
            "active_initiatives": len(active_initiatives),
            "target_gap_total": _round(total_target_gap),
            "mission_score": mission_score,
        },
        "kpis": kpi_rows,
        "scorecards": scorecard_rows,
        "executive_alerts": alert_rows,
        "strategic_initiatives": initiative_rows,
        "mission_health": {
            "kpi_registry_ready": bool(kpis),
            "scorecard_engine_ready": bool(scorecards),
            "executive_alerting_ready": bool(executive_alerts),
            "initiative_tracking_ready": bool(strategic_initiatives),
            "mission_score": mission_score,
        },
    }
