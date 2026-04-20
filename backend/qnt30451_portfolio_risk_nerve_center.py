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


def build_portfolio_risk_package(
    exposures: Iterable[Dict],
    limits: Iterable[Dict],
    alerts: Iterable[Dict],
    stress_tests: Iterable[Dict],
) -> Dict:
    exposures = list(exposures or [])
    limits = list(limits or [])
    alerts = list(alerts or [])
    stress_tests = list(stress_tests or [])

    total_gross = sum(_as_float(x.get("gross_exposure")) for x in exposures)
    total_net = sum(_as_float(x.get("net_exposure")) for x in exposures)
    breached_limits = [l for l in limits if (l.get("status") or "").lower() in {"breached", "warning"}]
    live_alerts = [a for a in alerts if (a.get("status") or "").lower() in {"open", "active", "triggered"}]
    failing_stress = [s for s in stress_tests if (s.get("status") or "").lower() in {"failed", "breached"}]

    exposure_rows: List[Dict] = []
    for row in exposures:
        exposure_rows.append({
            "exposure_id": row.get("id"),
            "book_name": row.get("book_name") or "core",
            "asset_class": row.get("asset_class") or "multi_asset",
            "gross_exposure": _round(_as_float(row.get("gross_exposure"))),
            "net_exposure": _round(_as_float(row.get("net_exposure"))),
            "var_1d": _round(_as_float(row.get("var_1d"))),
            "created_at": row.get("created_at"),
        })

    limit_rows: List[Dict] = []
    for row in limits:
        limit_rows.append({
            "limit_id": row.get("id"),
            "limit_name": row.get("limit_name") or "risk_limit",
            "limit_type": row.get("limit_type") or "gross_exposure",
            "threshold_value": _round(_as_float(row.get("threshold_value"))),
            "current_value": _round(_as_float(row.get("current_value"))),
            "status": row.get("status") or "ok",
            "created_at": row.get("created_at"),
        })

    alert_rows: List[Dict] = []
    for row in alerts:
        alert_rows.append({
            "alert_id": row.get("id"),
            "alert_name": row.get("alert_name") or "risk_alert",
            "severity": row.get("severity") or "medium",
            "status": row.get("status") or "open",
            "target_ref": row.get("target_ref") or "-",
            "created_at": row.get("created_at"),
        })

    stress_rows: List[Dict] = []
    for row in stress_tests:
        stress_rows.append({
            "scenario_id": row.get("id"),
            "scenario_name": row.get("scenario_name") or "stress_scenario",
            "loss_estimate": _round(_as_float(row.get("loss_estimate"))),
            "capital_impact": _round(_as_float(row.get("capital_impact"))),
            "status": row.get("status") or "pass",
            "created_at": row.get("created_at"),
        })

    risk_score = max(
        35,
        min(
            100,
            int(
                82
                - len(breached_limits) * 6
                - len(live_alerts) * 4
                - len(failing_stress) * 5
                + max(0, len(exposures) // 2)
            ),
        ),
    )

    return {
        "summary": {
            "books_tracked": len(exposures),
            "gross_exposure": _round(total_gross),
            "net_exposure": _round(total_net),
            "limits_breached": len(breached_limits),
            "live_alerts": len(live_alerts),
            "stress_failures": len(failing_stress),
            "risk_score": risk_score,
        },
        "exposures": exposure_rows,
        "limits": limit_rows,
        "alerts": alert_rows,
        "stress_tests": stress_rows,
        "risk_health": {
            "exposure_registry_ready": bool(exposures),
            "limit_framework_ready": bool(limits),
            "alerting_ready": bool(alerts),
            "stress_engine_ready": bool(stress_tests),
            "risk_score": risk_score,
        },
    }
