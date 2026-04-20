
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


def build_portfolio_risk_package(
    exposure_rows: Iterable[Dict],
    factor_rows: Iterable[Dict],
    stress_rows: Iterable[Dict],
    concentration_rows: Iterable[Dict],
) -> Dict:
    exposure_rows = list(exposure_rows or [])
    factor_rows = list(factor_rows or [])
    stress_rows = list(stress_rows or [])
    concentration_rows = list(concentration_rows or [])

    total_gross = sum(abs(_as_float(x.get("gross_exposure"))) for x in exposure_rows)
    total_net = sum(_as_float(x.get("net_exposure")) for x in exposure_rows)
    high_risk_factors = [x for x in factor_rows if abs(_as_float(x.get("factor_score"))) >= 0.7]
    failed_stress = [x for x in stress_rows if (x.get("status") or "").lower() in {"breach", "failed", "warning"}]
    concentrated = [x for x in concentration_rows if _as_float(x.get("weight_percent")) >= 20]

    exposure_view: List[Dict] = []
    for row in exposure_rows:
        exposure_view.append({
            "exposure_id": row.get("id"),
            "bucket_name": row.get("bucket_name") or "Core Book",
            "asset_class": row.get("asset_class") or "equities",
            "gross_exposure": _round(_as_float(row.get("gross_exposure"))),
            "net_exposure": _round(_as_float(row.get("net_exposure"))),
            "status": row.get("status") or "active",
            "created_at": row.get("created_at"),
        })

    factor_view: List[Dict] = []
    for row in factor_rows:
        factor_view.append({
            "factor_id": row.get("id"),
            "factor_name": row.get("factor_name") or "Momentum",
            "factor_score": _round(_as_float(row.get("factor_score"))),
            "direction": row.get("direction") or "long",
            "status": row.get("status") or "active",
            "created_at": row.get("created_at"),
        })

    stress_view: List[Dict] = []
    for row in stress_rows:
        pnl_impact = _as_float(row.get("pnl_impact"))
        capital_impact = _as_float(row.get("capital_impact"))
        stress_view.append({
            "stress_id": row.get("id"),
            "scenario_name": row.get("scenario_name") or "Market Shock",
            "pnl_impact": _round(pnl_impact),
            "capital_impact": _round(capital_impact),
            "status": row.get("status") or "passed",
            "created_at": row.get("created_at"),
        })

    concentration_view: List[Dict] = []
    for row in concentration_rows:
        concentration_view.append({
            "concentration_id": row.get("id"),
            "position_name": row.get("position_name") or "Position",
            "weight_percent": _round(_as_float(row.get("weight_percent"))),
            "status": row.get("status") or "normal",
            "created_at": row.get("created_at"),
        })

    risk_score = max(
        45,
        min(
            100,
            int(
                72
                - len(failed_stress) * 4
                - len(concentrated) * 3
                - len(high_risk_factors) * 2
                + (4 if total_gross > 0 else -8)
            )
        ),
    )

    risk_state = "SAFE"
    if failed_stress or len(concentrated) >= 2:
        risk_state = "ELEVATED"
    if len(failed_stress) >= 2 or len(concentrated) >= 3:
        risk_state = "HIGH"

    return {
        "summary": {
            "gross_exposure_total": _round(total_gross),
            "net_exposure_total": _round(total_net),
            "factor_count": len(factor_rows),
            "high_risk_factors": len(high_risk_factors),
            "stress_tests_total": len(stress_rows),
            "stress_failures": len(failed_stress),
            "concentration_flags": len(concentrated),
            "risk_score": risk_score,
            "risk_state": risk_state,
        },
        "exposures": exposure_view,
        "factors": factor_view,
        "stress_tests": stress_view,
        "concentrations": concentration_view,
        "risk_health": {
            "exposure_registry_ready": bool(exposure_rows),
            "factor_registry_ready": bool(factor_rows),
            "stress_registry_ready": bool(stress_rows),
            "concentration_registry_ready": bool(concentration_rows),
            "risk_score": risk_score,
            "risk_state": risk_state,
        },
    }
