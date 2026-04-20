from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Dict, List

MISSION = "QNT30421"


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')


def broker_env_summary() -> Dict[str, Any]:
    api_key = os.getenv("ALPACA_API_KEY") or os.getenv("APCA_API_KEY_ID")
    secret_key = os.getenv("ALPACA_SECRET_KEY") or os.getenv("APCA_API_SECRET_KEY")
    base_url = (os.getenv("ALPACA_BASE_URL") or os.getenv("APCA_API_BASE_URL") or "https://paper-api.alpaca.markets").rstrip('/')
    paper = str(os.getenv("ALPACA_PAPER", "true")).lower() == "true"
    return {
        "api_key_present": bool(api_key),
        "secret_key_present": bool(secret_key),
        "base_url": base_url,
        "paper": paper,
        "mode": "paper" if paper else "live",
        "credentials_ready": bool(api_key and secret_key),
    }


def canonical_live_requirements(user: Dict[str, Any], risk_view: Dict[str, Any], deployment: Dict[str, Any], env: Dict[str, Any], broker_view: Dict[str, Any]) -> Dict[str, Any]:
    billing = user.get("billing") or {}
    blockers: List[str] = []
    warnings: List[str] = []
    plan = billing.get("plan") or user.get("plan") or "free"
    subscription_status = billing.get("subscription_status") or user.get("subscription_status") or "free"
    if plan != "institutional":
        blockers.append("institutional_plan_required")
    if subscription_status not in {"active", "trialing", "free"}:
        blockers.append("subscription_not_active")
    if risk_view.get("status") in {"BREACH", "LOCKED"}:
        blockers.append("risk_engine_blocked")
    risk_cfg = risk_view.get("config") or {}
    if risk_cfg.get("kill_switch_active"):
        blockers.append("kill_switch_active")
    overall = str((deployment or {}).get("overall_status") or "unknown").lower()
    if overall == "blocked":
        blockers.append("deployment_blocked")
    elif overall == "degraded":
        warnings.append("deployment_degraded")
    if not broker_view.get("connected"):
        blockers.append("broker_not_connected")
    if not env.get("credentials_ready"):
        blockers.append("broker_credentials_missing")
    if env.get("paper", True):
        warnings.append("broker_running_in_paper_mode")
    if not str(env.get("base_url", "")).startswith("https://"):
        warnings.append("broker_base_url_not_https")
    ready = not blockers
    return {
        "mission": MISSION,
        "ready": ready,
        "blockers": blockers,
        "warnings": warnings,
        "required_plan": "institutional",
        "required_subscription_status": "active|trialing",
        "live_mode": "paper_bridge" if env.get("paper", True) else "canonical_live",
        "checked_at": now_iso(),
    }


def build_status_snapshot(operator: Dict[str, Any], billing: Dict[str, Any], deployment: Dict[str, Any], risk_view: Dict[str, Any], broker_view: Dict[str, Any], order_state: Dict[str, Any]) -> Dict[str, Any]:
    env = broker_env_summary()
    readiness = canonical_live_requirements({**operator, "billing": billing.get("billing", billing)}, risk_view, deployment, env, broker_view)
    orders = list((order_state or {}).get("orders") or [])
    live_orders = [o for o in orders if str(o.get("mode") or "").lower() == "alpaca"]
    return {
        "mission": MISSION,
        "operator": {
            "operator_id": operator.get("operator_id"),
            "email": operator.get("email"),
            "display_name": operator.get("display_name"),
        },
        "billing": billing,
        "deployment": {
            "overall_status": deployment.get("overall_status"),
            "readiness_score": deployment.get("readiness_score"),
            "safe_mode": deployment.get("safe_mode"),
            "environment": deployment.get("environment"),
        },
        "risk": {
            "status": risk_view.get("status"),
            "breaches": risk_view.get("breaches", []),
            "kill_switch_active": bool((risk_view.get("config") or {}).get("kill_switch_active")),
        },
        "broker": {
            "connected": broker_view.get("connected"),
            "base_url": broker_view.get("base_url"),
            "source": broker_view.get("source"),
            "paper": broker_view.get("paper"),
            "last_status": broker_view.get("last_status"),
        },
        "environment": env,
        "readiness": readiness,
        "execution": {
            "canonical_route": "/live-execution/submit",
            "status_route": "/live-execution/status",
            "orders_route": "/live-execution/orders",
            "audit_route": "/live-execution/audit",
            "orders_total": len(orders),
            "live_orders_total": len(live_orders),
            "last_live_order": live_orders[0] if live_orders else None,
        },
    }


def build_audit_event(actor: Dict[str, Any], action: str, details: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "mission": MISSION,
        "timestamp": now_iso(),
        "actor_email": actor.get("email"),
        "actor_operator_id": actor.get("operator_id"),
        "action": action,
        "details": details,
    }
