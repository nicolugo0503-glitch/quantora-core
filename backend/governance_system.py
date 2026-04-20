
from datetime import datetime, timezone

def now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def default_governance_controls():
    return {
        "enabled": True,
        "last_evaluated_at": None,
        "last_simulation_at": None,
        "last_operator_id": None,
        "policy_breach_count": 0,
        "approval_backlog_warn": 5,
        "approval_sla_hours": 24,
        "ledger_retention_events": 2000,
        "enforcement": {
            "block_live_orders_on_pending_approval": True,
            "block_orders_on_risk_breach": True,
            "require_manual_review_on_large_rebalance": True,
        },
        "telemetry": [],
    }


def governance_controls_state(state):
    data = state.setdefault("governance_system", {})
    defaults = default_governance_controls()
    for key, value in defaults.items():
        if key not in data:
            data[key] = value
    data.setdefault("enforcement", {})
    for key, value in defaults["enforcement"].items():
        data["enforcement"].setdefault(key, value)
    data.setdefault("telemetry", [])
    return data


def _policy_map(policies):
    return {p.get("policy_type"): p for p in policies if p.get("enabled")}


def governance_policy_simulation(controls, policies, payload):
    pmap = _policy_map(policies)
    event_type = (payload.get("event_type") or "").lower()
    amount = float(payload.get("amount") or 0.0)
    interval_seconds = int(payload.get("interval_seconds") or 0)
    qty = float(payload.get("qty") or 0.0)
    estimated_slippage_bps = float(payload.get("estimated_slippage_bps") or 0.0)
    execution_mode = (payload.get("execution_mode") or "internal").lower()
    max_active_strategies = int(payload.get("max_active_strategies") or 0)
    breaches = []

    if event_type == "capital_change":
        policy = pmap.get("capital_change")
        if policy and abs(amount) >= float(policy.get("threshold", 0)):
            breaches.append({
                "policy_id": policy.get("policy_id"),
                "policy_type": policy.get("policy_type"),
                "decision": "approval_required",
                "reason": f"capital change {round(amount, 2)} exceeds threshold {policy.get('threshold')}",
            })

    if event_type == "loop_start":
        policy = pmap.get("loop_start")
        if policy and interval_seconds and interval_seconds < int(policy.get("threshold", 0)):
            breaches.append({
                "policy_id": policy.get("policy_id"),
                "policy_type": policy.get("policy_type"),
                "decision": "approval_required",
                "reason": f"interval {interval_seconds}s is below threshold {policy.get('threshold')}s",
            })

    if event_type == "live_order":
        policy = pmap.get("live_order_notional")
        notional = abs(amount)
        if policy and execution_mode == "live" and notional >= float(policy.get("threshold", 0)):
            breaches.append({
                "policy_id": policy.get("policy_id"),
                "policy_type": policy.get("policy_type"),
                "decision": "escalate",
                "reason": f"live order notional {round(notional, 2)} exceeds threshold {policy.get('threshold')}",
            })
        slip_policy = pmap.get("execution_slippage")
        if slip_policy and estimated_slippage_bps > float(slip_policy.get("threshold", 0)):
            breaches.append({
                "policy_id": slip_policy.get("policy_id"),
                "policy_type": slip_policy.get("policy_type"),
                "decision": "hold",
                "reason": f"estimated slippage {round(estimated_slippage_bps,2)} bps exceeds threshold {slip_policy.get('threshold')}",
            })

    if event_type == "strategy_rebalance":
        policy = pmap.get("strategy_rebalance")
        if policy and max_active_strategies >= int(policy.get("threshold", 0)):
            breaches.append({
                "policy_id": policy.get("policy_id"),
                "policy_type": policy.get("policy_type"),
                "decision": "manual_review",
                "reason": f"max active strategies {max_active_strategies} reaches oversight threshold {policy.get('threshold')}",
            })

    controls["last_simulation_at"] = now_iso()
    if breaches:
        controls["policy_breach_count"] = int(controls.get("policy_breach_count") or 0) + len(breaches)
    controls.setdefault("telemetry", []).insert(0, {
        "timestamp": now_iso(),
        "event_type": event_type,
        "breaches": len(breaches),
    })
    controls["telemetry"] = controls["telemetry"][:100]
    return {
        "status": "ok",
        "event_type": event_type,
        "approved_to_proceed": len(breaches) == 0,
        "breaches": breaches,
        "summary": {
            "breach_count": len(breaches),
            "decision": "allow" if not breaches else breaches[0]["decision"],
        },
    }


def governance_aging_report(approvals):
    pending = [a for a in approvals if (a.get("status") or "").upper() == "PENDING"]
    now = datetime.now(timezone.utc)
    aged = []
    for req in pending:
        created = req.get("created_at")
        try:
            dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
            age_hours = round((now - dt).total_seconds() / 3600.0, 2)
        except Exception:
            age_hours = None
        aged.append({
            "request_id": req.get("request_id"),
            "request_type": req.get("request_type"),
            "target": req.get("target"),
            "created_by_email": req.get("created_by_email"),
            "age_hours": age_hours,
            "reason": req.get("reason"),
        })
    aged.sort(key=lambda x: (x["age_hours"] is None, -(x["age_hours"] or 0)))
    return {
        "pending_count": len(pending),
        "oldest_pending_hours": aged[0]["age_hours"] if aged else 0,
        "pending_requests": aged[:50],
    }


def governance_summary(controls, approvals, ledger):
    aging = governance_aging_report(approvals)
    policy_updates = len([e for e in ledger if e.get("action") == "policy.update"])
    approval_events = len([e for e in ledger if str(e.get("category")).lower() == "approval"])
    rejected = len([a for a in approvals if (a.get("status") or "").upper() == "REJECTED"])
    approved = len([a for a in approvals if (a.get("status") or "").upper() == "APPROVED"])
    return {
        "enabled": bool(controls.get("enabled")),
        "policy_breach_count": int(controls.get("policy_breach_count") or 0),
        "approval_pending_count": aging.get("pending_count", 0),
        "oldest_pending_hours": aging.get("oldest_pending_hours", 0),
        "approved_requests": approved,
        "rejected_requests": rejected,
        "policy_update_events": policy_updates,
        "approval_events": approval_events,
        "last_evaluated_at": controls.get("last_evaluated_at"),
    }


def governance_enforcement_snapshot(state, controls, approvals, ledger, include_orders=True, include_approvals=True, include_risk=True):
    operator_id = state.get("operator_id")
    pending = [a for a in approvals if (a.get("status") or "").upper() == "PENDING" and a.get("target") in (operator_id, "fleet")]
    risk_engine = state.get("risk_engine", {}) or {}
    risk_breached = bool(risk_engine.get("breached")) or bool(risk_engine.get("kill_switch_active"))
    recent_orders = list(reversed((state.get("orders", {}) or {}).get("orders", [])))[:25]

    holds = []
    if include_approvals and controls.get("enforcement", {}).get("block_live_orders_on_pending_approval") and pending:
        holds.append("pending approvals present")
    if include_risk and controls.get("enforcement", {}).get("block_orders_on_risk_breach") and risk_breached:
        holds.append("risk breach active")

    controls["last_evaluated_at"] = now_iso()
    controls["last_operator_id"] = operator_id
    decision = "clear" if not holds else "hold"
    return {
        "status": "ok",
        "operator_id": operator_id,
        "summary": {
            "decision": decision,
            "hold_reasons": holds,
            "pending_approvals": len(pending),
            "risk_breached": risk_breached,
            "recent_order_count": len(recent_orders),
            "ledger_events": len(ledger),
        },
        "pending_approvals": pending[:25] if include_approvals else [],
        "risk": {
            "breached": risk_breached,
            "kill_switch_active": bool(risk_engine.get("kill_switch_active")),
            "last_breach_reason": risk_engine.get("last_breach_reason"),
            "current_drawdown_pct": risk_engine.get("current_drawdown_pct"),
            "current_total_exposure": risk_engine.get("current_total_exposure"),
        } if include_risk else {},
        "recent_orders": recent_orders if include_orders else [],
    }
