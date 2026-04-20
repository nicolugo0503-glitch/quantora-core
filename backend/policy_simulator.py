import uuid
from datetime import datetime, timezone


def now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')


def default_policy_simulator_state():
    return {
        "version": "30360",
        "last_simulation_at": None,
        "last_compile_at": None,
        "simulations": [],
        "compiled_requests": [],
        "policies": {
            "live_notional_limit": 25000.0,
            "max_estimated_slippage_bps": 28.0,
            "max_strategy_rebalance_pct": 0.18,
            "max_net_exposure_usd": 150000.0,
            "approval_expiry_minutes": 20,
        },
    }


def policy_simulator_state_view(state):
    merged = default_policy_simulator_state()
    if isinstance(state, dict):
        for k, v in state.items():
            if k == 'policies' and isinstance(v, dict):
                merged['policies'].update(v)
            else:
                merged[k] = v
    merged.setdefault('simulations', [])
    merged.setdefault('compiled_requests', [])
    return merged


def policy_simulator_summary(state):
    state = policy_simulator_state_view(state)
    sims = state.get('simulations', [])
    compiled = state.get('compiled_requests', [])
    blocked = sum(1 for s in sims if s.get('verdict') == 'blocked')
    approval = sum(1 for s in sims if s.get('verdict') == 'approval_required')
    return {
        'simulation_count': len(sims),
        'compiled_count': len(compiled),
        'blocked_count': blocked,
        'approval_required_count': approval,
        'last_simulation_at': state.get('last_simulation_at'),
        'last_compile_at': state.get('last_compile_at'),
    }


def simulate_policy(state, *, action_type, market='equities', symbol=None, side='buy', qty=0.0, price=0.0, estimated_slippage_bps=0.0, net_exposure_usd=0.0, rebalance_pct=0.0, execution_mode='paper', autonomy_mode='supervised'):
    state = policy_simulator_state_view(state)
    policies = state['policies']
    qty = float(qty or 0.0)
    price = float(price or 0.0)
    notional = round(qty * price, 2)
    estimated_slippage_bps = float(estimated_slippage_bps or 0.0)
    net_exposure_usd = float(net_exposure_usd or 0.0)
    rebalance_pct = float(rebalance_pct or 0.0)
    triggers = []
    verdict = 'approved'

    if execution_mode == 'live' and notional > float(policies['live_notional_limit']):
        verdict = 'approval_required'
        triggers.append('live_notional_limit')
    if estimated_slippage_bps > float(policies['max_estimated_slippage_bps']):
        verdict = 'blocked'
        triggers.append('max_estimated_slippage_bps')
    if rebalance_pct > float(policies['max_strategy_rebalance_pct']):
        verdict = 'approval_required' if verdict != 'blocked' else verdict
        triggers.append('max_strategy_rebalance_pct')
    if abs(net_exposure_usd) > float(policies['max_net_exposure_usd']):
        verdict = 'blocked'
        triggers.append('max_net_exposure_usd')
    if autonomy_mode == 'delegated_autonomy' and execution_mode == 'live' and notional > float(policies['live_notional_limit']) * 0.5:
        verdict = 'approval_required' if verdict != 'blocked' else verdict
        triggers.append('delegated_live_escalation')

    simulation = {
        'simulation_id': f'sim_{uuid.uuid4().hex[:10]}',
        'timestamp': now_iso(),
        'action_type': action_type,
        'market': market,
        'symbol': symbol,
        'side': side,
        'qty': qty,
        'price': price,
        'notional': notional,
        'estimated_slippage_bps': round(estimated_slippage_bps, 2),
        'net_exposure_usd': round(net_exposure_usd, 2),
        'rebalance_pct': round(rebalance_pct, 4),
        'execution_mode': execution_mode,
        'autonomy_mode': autonomy_mode,
        'triggers': triggers,
        'verdict': verdict,
    }
    state['last_simulation_at'] = simulation['timestamp']
    state['simulations'].append(simulation)
    state['simulations'] = state['simulations'][-100:]
    return {'status': 'ok', 'simulation': simulation, 'summary': policy_simulator_summary(state)}


def compile_pretrade_approval(state, *, simulation, requested_by=None, operator_id=None, notes=None):
    state = policy_simulator_state_view(state)
    approval = {
        'request_id': f'appr_{uuid.uuid4().hex[:10]}',
        'created_at': now_iso(),
        'requested_by': requested_by,
        'operator_id': operator_id,
        'simulation_id': simulation.get('simulation_id'),
        'action_type': simulation.get('action_type'),
        'verdict': simulation.get('verdict'),
        'priority': 'high' if simulation.get('verdict') == 'blocked' else 'normal',
        'expires_in_minutes': int(state['policies'].get('approval_expiry_minutes', 20)),
        'payload': simulation,
        'notes': notes,
    }
    state['last_compile_at'] = approval['created_at']
    state['compiled_requests'].append(approval)
    state['compiled_requests'] = state['compiled_requests'][-100:]
    return {'status': 'ok', 'approval_request': approval, 'summary': policy_simulator_summary(state)}
