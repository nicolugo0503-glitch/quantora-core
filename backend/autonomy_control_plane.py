
from datetime import datetime, timezone


def now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')


def autonomy_state_defaults():
    return {
        "enabled": True,
        "current_mode": "supervised",
        "last_recommended_mode": "supervised",
        "last_transition_at": None,
        "last_transition_reason": None,
        "last_evaluated_at": None,
        "last_cycle_at": None,
        "last_cycle_status": "idle",
        "cycle_count": 0,
        "promotion_score_threshold": 75.0,
        "demotion_score_threshold": 45.0,
        "min_approval_clearance": "manager",
        "delegations": {},
        "telemetry": [],
    }


def autonomy_state_view(data):
    merged = autonomy_state_defaults()
    merged.update(data or {})
    merged.setdefault("delegations", {})
    merged.setdefault("telemetry", [])
    return merged


def _equity_score(performance):
    score = (performance or {}).get("scorecard", {}) or {}
    summary = (performance or {}).get("summary", {}) or {}
    win_rate = float(score.get("win_rate_pct", 0) or 0)
    pnl = float(summary.get("realized_pnl", 0) or 0) + float(summary.get("unrealized_pnl", 0) or 0)
    trades = float(summary.get("trade_count", 0) or 0)
    trade_score = min(trades * 2.5, 20)
    pnl_score = 20 if pnl > 0 else 10 if pnl == 0 else 0
    win_score = min(max(win_rate, 0), 100) * 0.4
    return round(trade_score + pnl_score + win_score, 2)


def autonomy_transition_decision(autonomy, *, state, performance, risk, governance_snapshot, execution_mode='paper', market_bias='neutral', target_mode=None, reason=None):
    autonomy = autonomy_state_view(autonomy)
    operator_id = state.get('operator_id')
    pending_approvals = int((governance_snapshot or {}).get('summary', {}).get('pending_approvals', 0) or 0)
    risk_breached = bool((governance_snapshot or {}).get('summary', {}).get('risk_breached')) or bool((risk or {}).get('status') not in ('SAFE', 'UNKNOWN'))
    hold_reasons = list((governance_snapshot or {}).get('summary', {}).get('hold_reasons', []))
    score = _equity_score(performance)
    recommended_mode = 'supervised'
    decision_reason = 'stable but human-led'
    if risk_breached or hold_reasons:
        recommended_mode = 'locked'
        decision_reason = ', '.join(hold_reasons) if hold_reasons else 'risk or governance breach active'
    elif pending_approvals:
        recommended_mode = 'supervised'
        decision_reason = 'pending approvals require supervised control'
    elif score >= float(autonomy.get('promotion_score_threshold', 75)):
        recommended_mode = 'constrained_autonomy' if execution_mode != 'live' else 'delegated_autonomy'
        decision_reason = 'performance, risk, and governance gates are clear'
    elif score <= float(autonomy.get('demotion_score_threshold', 45)):
        recommended_mode = 'supervised'
        decision_reason = 'performance below autonomy threshold'
    allowed = True
    target = target_mode or recommended_mode
    if target == 'delegated_autonomy':
        delegation = autonomy.get('delegations', {}).get(operator_id, {})
        if execution_mode == 'live' and not delegation.get('allow_live_orders'):
            allowed = False
            decision_reason = 'delegation tier does not allow live orders'
    if target == 'locked' and not target_mode:
        allowed = True
    if target_mode:
        if target_mode == 'full_autonomy':
            allowed = False
            decision_reason = 'full autonomy is not enabled; use delegated_autonomy as the highest governed state'
        elif target_mode == 'delegated_autonomy' and (risk_breached or pending_approvals):
            allowed = False
            decision_reason = 'delegated autonomy blocked by risk or pending approvals'
        elif target_mode == 'constrained_autonomy' and risk_breached:
            allowed = False
            decision_reason = 'constrained autonomy blocked by active risk breach'
    if allowed and target_mode:
        autonomy['current_mode'] = target_mode
        autonomy['last_transition_at'] = now_iso()
        autonomy['last_transition_reason'] = reason or decision_reason
    autonomy['last_recommended_mode'] = recommended_mode
    autonomy['last_evaluated_at'] = now_iso()
    autonomy.setdefault('telemetry', []).insert(0, {
        'timestamp': now_iso(),
        'operator_id': operator_id,
        'score': score,
        'recommended_mode': recommended_mode,
        'requested_mode': target_mode,
        'execution_mode': execution_mode,
        'market_bias': market_bias,
        'allowed': allowed,
    })
    autonomy['telemetry'] = autonomy.get('telemetry', [])[:100]
    return {
        'status': 'ok',
        'allowed': allowed,
        'summary': {
            'operator_id': operator_id,
            'current_mode': autonomy.get('current_mode'),
            'recommended_mode': recommended_mode,
            'decision_reason': decision_reason,
            'score': score,
            'pending_approvals': pending_approvals,
            'risk_breached': risk_breached,
        },
        'autonomy': autonomy,
    }


def autonomy_delegation_update(autonomy, *, tier, max_live_notional, allow_live_orders, allow_strategy_mutations, operator_id, actor_email=None):
    autonomy = autonomy_state_view(autonomy)
    autonomy.setdefault('delegations', {})[operator_id] = {
        'operator_id': operator_id,
        'tier': tier,
        'max_live_notional': float(max_live_notional or 0),
        'allow_live_orders': bool(allow_live_orders),
        'allow_strategy_mutations': bool(allow_strategy_mutations),
        'updated_at': now_iso(),
        'updated_by': actor_email,
    }
    return {'status': 'updated', 'delegation': autonomy['delegations'][operator_id], 'autonomy': autonomy}


def autonomy_summary(autonomy, state, approvals, ledger):
    autonomy = autonomy_state_view(autonomy)
    operator_id = state.get('operator_id')
    operator_delegation = autonomy.get('delegations', {}).get(operator_id)
    recent = autonomy.get('telemetry', [])[:25]
    pending = [a for a in approvals if (a.get('status') or '').upper() == 'PENDING']
    autonomy_events = [e for e in ledger if str(e.get('category')).lower() == 'autonomy']
    return {
        'current_mode': autonomy.get('current_mode'),
        'last_recommended_mode': autonomy.get('last_recommended_mode'),
        'cycle_count': int(autonomy.get('cycle_count') or 0),
        'pending_approval_count': len(pending),
        'autonomy_event_count': len(autonomy_events),
        'delegation': operator_delegation,
        'recent_telemetry': recent,
    }
