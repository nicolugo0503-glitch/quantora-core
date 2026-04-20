
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


def build_multi_asset_package(
    asset_connectors: Iterable[Dict],
    market_universes: Iterable[Dict],
    execution_profiles: Iterable[Dict],
    asset_health_logs: Iterable[Dict],
) -> Dict:
    asset_connectors = list(asset_connectors or [])
    market_universes = list(market_universes or [])
    execution_profiles = list(execution_profiles or [])
    asset_health_logs = list(asset_health_logs or [])

    live_connectors = [x for x in asset_connectors if (x.get("status") or "").lower() in {"live", "active", "enabled"}]
    enabled_universes = [x for x in market_universes if (x.get("status") or "").lower() in {"live", "active", "enabled"}]
    ready_profiles = [x for x in execution_profiles if (x.get("status") or "").lower() in {"ready", "active", "enabled"}]
    healthy_logs = [x for x in asset_health_logs if (x.get("status") or "").lower() in {"healthy", "ok", "green"}]

    supported_notional = sum(_as_float(x.get("supported_notional")) for x in market_universes)

    connector_rows: List[Dict] = []
    for row in asset_connectors:
        connector_rows.append({
            "connector_id": row.get("id"),
            "asset_class": row.get("asset_class") or "futures",
            "provider_name": row.get("provider_name") or "Provider",
            "status": row.get("status") or "draft",
            "created_at": row.get("created_at"),
        })

    universe_rows: List[Dict] = []
    for row in market_universes:
        universe_rows.append({
            "universe_id": row.get("id"),
            "universe_name": row.get("universe_name") or "Universe",
            "asset_class": row.get("asset_class") or "futures",
            "supported_notional": _round(_as_float(row.get("supported_notional"))),
            "status": row.get("status") or "draft",
            "created_at": row.get("created_at"),
        })

    profile_rows: List[Dict] = []
    for row in execution_profiles:
        profile_rows.append({
            "profile_id": row.get("id"),
            "profile_name": row.get("profile_name") or "Execution Profile",
            "asset_class": row.get("asset_class") or "futures",
            "risk_mode": row.get("risk_mode") or "standard",
            "status": row.get("status") or "draft",
            "created_at": row.get("created_at"),
        })

    health_rows: List[Dict] = []
    for row in asset_health_logs:
        health_rows.append({
            "log_id": row.get("id"),
            "asset_class": row.get("asset_class") or "futures",
            "uptime_percent": _round(_as_float(row.get("uptime_percent"))),
            "latency_ms": _round(_as_float(row.get("latency_ms"))),
            "status": row.get("status") or "unknown",
            "created_at": row.get("created_at"),
        })

    expansion_score = max(
        45,
        min(
            100,
            int(
                60
                + len(live_connectors) * 3
                + len(enabled_universes) * 3
                + len(ready_profiles) * 3
                + len(healthy_logs) * 2
            )
        ),
    )

    return {
        "summary": {
            "connectors_total": len(asset_connectors),
            "connectors_live": len(live_connectors),
            "universes_total": len(market_universes),
            "universes_enabled": len(enabled_universes),
            "profiles_total": len(execution_profiles),
            "profiles_ready": len(ready_profiles),
            "health_logs_total": len(asset_health_logs),
            "supported_notional_total": _round(supported_notional),
            "expansion_score": expansion_score,
        },
        "asset_connectors": connector_rows,
        "market_universes": universe_rows,
        "execution_profiles": profile_rows,
        "asset_health_logs": health_rows,
        "expansion_health": {
            "connector_registry_ready": bool(asset_connectors),
            "universe_registry_ready": bool(market_universes),
            "profile_registry_ready": bool(execution_profiles),
            "health_registry_ready": bool(asset_health_logs),
            "expansion_score": expansion_score,
        },
    }
