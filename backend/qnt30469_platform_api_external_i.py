from __future__ import annotations

from typing import Dict, Iterable, List


def _as_float(value, default: float = 0.0) -> float:
    try:
        if value in (None, ""):
            return default
        return float(value)
    except Exception:
        return default


def build_platform_api_package(
    api_clients: Iterable[Dict],
    integration_endpoints: Iterable[Dict],
    webhook_events: Iterable[Dict],
    api_usage_logs: Iterable[Dict],
) -> Dict:
    api_clients = list(api_clients or [])
    integration_endpoints = list(integration_endpoints or [])
    webhook_events = list(webhook_events or [])
    api_usage_logs = list(api_usage_logs or [])

    active_clients = [x for x in api_clients if (x.get("status") or "").lower() in {"active", "enabled", "live"}]
    live_endpoints = [x for x in integration_endpoints if (x.get("status") or "").lower() in {"active", "live", "enabled"}]
    delivered_webhooks = [x for x in webhook_events if (x.get("status") or "").lower() in {"delivered", "sent", "completed"}]
    healthy_calls = [x for x in api_usage_logs if (x.get("status") or "").lower() in {"success", "ok", "200"}]

    total_calls = len(api_usage_logs)
    success_rate = round((len(healthy_calls) / total_calls) * 100, 2) if total_calls else 0.0

    client_rows: List[Dict] = []
    for row in api_clients:
        client_rows.append({
            "client_id": row.get("id"),
            "client_name": row.get("client_name") or "Client",
            "scope": row.get("scope") or "read_only",
            "status": row.get("status") or "draft",
            "created_at": row.get("created_at"),
        })

    endpoint_rows: List[Dict] = []
    for row in integration_endpoints:
        endpoint_rows.append({
            "endpoint_id": row.get("id"),
            "endpoint_name": row.get("endpoint_name") or "Endpoint",
            "provider_name": row.get("provider_name") or "External System",
            "status": row.get("status") or "draft",
            "created_at": row.get("created_at"),
        })

    webhook_rows: List[Dict] = []
    for row in webhook_events:
        webhook_rows.append({
            "webhook_id": row.get("id"),
            "event_name": row.get("event_name") or "Webhook Event",
            "target_url": row.get("target_url") or "-",
            "status": row.get("status") or "queued",
            "created_at": row.get("created_at"),
        })

    usage_rows: List[Dict] = []
    for row in api_usage_logs:
        usage_rows.append({
            "usage_id": row.get("id"),
            "client_name": row.get("client_name") or "Client",
            "route_name": row.get("route_name") or "/",
            "status": row.get("status") or "success",
            "latency_ms": round(_as_float(row.get("latency_ms")), 2),
            "created_at": row.get("created_at"),
        })

    gateway_score = max(
        45,
        min(
            100,
            int(
                58
                + len(active_clients) * 3
                + len(live_endpoints) * 3
                + len(delivered_webhooks) * 2
                + (5 if success_rate >= 95 else 0)
            )
        ),
    )

    return {
        "summary": {
            "api_clients_total": len(api_clients),
            "api_clients_active": len(active_clients),
            "integration_endpoints_total": len(integration_endpoints),
            "integration_endpoints_live": len(live_endpoints),
            "webhook_events_total": len(webhook_events),
            "webhook_events_delivered": len(delivered_webhooks),
            "api_calls_total": total_calls,
            "api_success_rate": success_rate,
            "gateway_score": gateway_score,
        },
        "api_clients": client_rows,
        "integration_endpoints": endpoint_rows,
        "webhook_events": webhook_rows,
        "api_usage_logs": usage_rows,
        "gateway_health": {
            "client_registry_ready": bool(api_clients),
            "endpoint_registry_ready": bool(integration_endpoints),
            "webhook_engine_ready": bool(webhook_events),
            "usage_tracking_ready": bool(api_usage_logs),
            "gateway_score": gateway_score,
        },
    }
