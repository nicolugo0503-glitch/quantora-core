import datetime
from typing import Any, Dict, List


def _now() -> str:
    return datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def build_unified_dashboard_summary(*, operator: Dict[str, Any], billing: Dict[str, Any], deployment: Dict[str, Any], attribution: Dict[str, Any], strategies: Dict[str, Any], orders: List[Dict[str, Any]], runtime_modules: List[Dict[str, Any]]) -> Dict[str, Any]:
    perf = attribution.get("portfolio_attribution") or {}
    strat = attribution.get("strategy_attribution") or []
    exe = attribution.get("execution_attribution") or []
    top_strategy = sorted(strat, key=lambda row: (row.get("realized_pnl", 0.0), row.get("orders_count", 0)), reverse=True)[0] if strat else None
    top_venue = sorted(exe, key=lambda row: (row.get("avg_execution_quality", 0.0), row.get("orders_count", 0)), reverse=True)[0] if exe else None
    active_strategies = [s for s in (strategies.get("strategies") or []) if s.get("enabled") and str(s.get("status","")).lower() == "running"]
    recent_orders = list(sorted([o for o in orders if isinstance(o, dict)], key=lambda o: str(o.get("timestamp") or o.get("submitted_at") or o.get("created_at") or ""), reverse=True))[:8]
    readiness = deployment.get("readiness_score", 0)
    environment = deployment.get("environment", "unknown")
    summary = {
        "mission": "QNT30419",
        "generated_at": _now(),
        "operator": {
            "operator_id": operator.get("operator_id"),
            "email": operator.get("email"),
            "display_name": operator.get("display_name") or operator.get("email") or "Operator",
        },
        "headline": {
            "environment": environment,
            "readiness_score": readiness,
            "overall_status": deployment.get("overall_status", "unknown"),
            "billing_mode": billing.get("billing_mode", "simulation"),
            "plan": billing.get("billing", {}).get("plan", "free"),
            "subscription_status": billing.get("billing", {}).get("subscription_status", "inactive"),
            "allocated_capital": perf.get("allocated_capital", 0.0),
            "used_capital": perf.get("used_capital", 0.0),
            "remaining_capital": perf.get("remaining_capital", 0.0),
            "daily_realized_pnl": perf.get("daily_realized_pnl", 0.0),
            "drawdown_pct": perf.get("drawdown_pct", 0.0),
            "orders_count": len(orders),
            "active_strategy_count": len(active_strategies),
            "runtime_module_count": len(runtime_modules),
        },
        "top_strategy": top_strategy,
        "top_execution_venue": top_venue,
        "active_strategies": active_strategies[:10],
        "recent_orders": recent_orders,
        "runtime_modules": runtime_modules,
        "recommendations": _recommendations(deployment, billing, perf, top_strategy),
    }
    return summary


def _recommendations(deployment: Dict[str, Any], billing: Dict[str, Any], perf: Dict[str, Any], top_strategy: Dict[str, Any] | None) -> List[str]:
    recs: List[str] = []
    if deployment.get("overall_status") != "ready":
        recs.append("Resolve deployment warnings before enabling more aggressive execution paths.")
    if billing.get("billing", {}).get("subscription_status") not in {"active", "trialing"}:
        recs.append("Restore an active subscription state before relying on paid execution surfaces.")
    if float(perf.get("drawdown_pct") or 0.0) >= 5.0:
        recs.append("Current drawdown is elevated; route decisions through governance and reduce deployment velocity.")
    if top_strategy and float(top_strategy.get("realized_pnl") or 0.0) > 0:
        recs.append(f"Top contributor is {top_strategy.get('strategy_name')}; review whether it merits capital promotion.")
    if not recs:
        recs.append("System posture is stable; proceed with measured expansion and operator review cadence.")
    return recs[:4]


def build_operator_brief(summary: Dict[str, Any]) -> Dict[str, Any]:
    headline = summary.get("headline") or {}
    return {
        "mission": "QNT30419",
        "generated_at": summary.get("generated_at"),
        "title": "Canonical Unified Dashboard Runtime Brief",
        "narrative": f"{summary.get('operator',{}).get('display_name','Operator')} is running Quantora in {headline.get('environment','unknown')} with a readiness score of {headline.get('readiness_score',0)}. Billing is {headline.get('billing_mode','simulation')} on the {headline.get('plan','free')} plan. Daily realized PnL is {headline.get('daily_realized_pnl',0)} with {headline.get('active_strategy_count',0)} active strategies across {headline.get('runtime_module_count',0)} runtime modules.",
        "recommendations": summary.get("recommendations") or [],
    }


def build_activity_feed(summary: Dict[str, Any]) -> List[Dict[str, Any]]:
    feed: List[Dict[str, Any]] = []
    for order in summary.get("recent_orders") or []:
        feed.append({
            "type": "order",
            "timestamp": order.get("timestamp") or order.get("submitted_at") or order.get("created_at"),
            "title": f"{str(order.get('side','buy')).upper()} {order.get('symbol','UNKNOWN')}",
            "detail": f"qty={order.get('qty','?')} mode={order.get('mode') or order.get('broker') or 'internal'} status={order.get('status','unknown')}",
        })
    for rec in summary.get("recommendations") or []:
        feed.append({"type": "recommendation", "timestamp": summary.get("generated_at"), "title": "Operator Recommendation", "detail": rec})
    return feed[:12]
