
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


def build_connectivity_mesh_package(
    broker_connections: Iterable[Dict],
    custodian_links: Iterable[Dict],
    prime_services: Iterable[Dict],
    connectivity_health_logs: Iterable[Dict],
) -> Dict:
    broker_connections = list(broker_connections or [])
    custodian_links = list(custodian_links or [])
    prime_services = list(prime_services or [])
    connectivity_health_logs = list(connectivity_health_logs or [])

    live_brokers = [x for x in broker_connections if (x.get("status") or "").lower() in {"live", "active", "connected"}]
    live_custodians = [x for x in custodian_links if (x.get("status") or "").lower() in {"live", "active", "connected"}]
    enabled_primes = [x for x in prime_services if (x.get("status") or "").lower() in {"live", "active", "enabled"}]
    healthy_logs = [x for x in connectivity_health_logs if (x.get("status") or "").lower() in {"healthy", "ok", "green"}]

    avg_uptime = round(
        sum(_as_float(x.get("uptime_percent")) for x in connectivity_health_logs) / len(connectivity_health_logs),
        2
    ) if connectivity_health_logs else 0.0

    broker_rows: List[Dict] = []
    for row in broker_connections:
        broker_rows.append({
            "broker_id": row.get("id"),
            "broker_name": row.get("broker_name") or "Broker",
            "connection_type": row.get("connection_type") or "execution",
            "status": row.get("status") or "draft",
            "created_at": row.get("created_at"),
        })

    custodian_rows: List[Dict] = []
    for row in custodian_links:
        custodian_rows.append({
            "custodian_id": row.get("id"),
            "custodian_name": row.get("custodian_name") or "Custodian",
            "asset_scope": row.get("asset_scope") or "multi_asset",
            "status": row.get("status") or "draft",
            "created_at": row.get("created_at"),
        })

    prime_rows: List[Dict] = []
    for row in prime_services:
        prime_rows.append({
            "prime_id": row.get("id"),
            "provider_name": row.get("provider_name") or "Prime Service",
            "service_type": row.get("service_type") or "financing",
            "status": row.get("status") or "draft",
            "created_at": row.get("created_at"),
        })

    log_rows: List[Dict] = []
    for row in connectivity_health_logs:
        log_rows.append({
            "log_id": row.get("id"),
            "system_name": row.get("system_name") or "System",
            "uptime_percent": _round(_as_float(row.get("uptime_percent"))),
            "latency_ms": _round(_as_float(row.get("latency_ms"))),
            "status": row.get("status") or "unknown",
            "created_at": row.get("created_at"),
        })

    mesh_score = max(
        45,
        min(
            100,
            int(
                60
                + len(live_brokers) * 3
                + len(live_custodians) * 3
                + len(enabled_primes) * 3
                + len(healthy_logs) * 2
                + (5 if avg_uptime >= 99 else 0)
            )
        ),
    )

    return {
        "summary": {
            "brokers_total": len(broker_connections),
            "brokers_live": len(live_brokers),
            "custodians_total": len(custodian_links),
            "custodians_live": len(live_custodians),
            "prime_services_total": len(prime_services),
            "prime_services_enabled": len(enabled_primes),
            "health_logs_total": len(connectivity_health_logs),
            "average_uptime_percent": avg_uptime,
            "mesh_score": mesh_score,
        },
        "broker_connections": broker_rows,
        "custodian_links": custodian_rows,
        "prime_services": prime_rows,
        "connectivity_health_logs": log_rows,
        "mesh_health": {
            "broker_registry_ready": bool(broker_connections),
            "custodian_registry_ready": bool(custodian_links),
            "prime_registry_ready": bool(prime_services),
            "health_log_ready": bool(connectivity_health_logs),
            "mesh_score": mesh_score,
        },
    }
