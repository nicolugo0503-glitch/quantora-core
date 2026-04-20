from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict

STATE_PATH = Path(__file__).resolve().parents[1] / 'state' / 'execution_state.json'


def load_state() -> Dict[str, Any]:
    if not STATE_PATH.exists():
        return {
            'locked': False,
            'generated_by': 'QNT50001',
            'mode': 'paper',
            'safe_mode': True,
            'active_broker': 'paper',
            'decision_memory': [],
            'orders': [],
            'fills': [],
            'audit_log': [],
        }
    return json.loads(STATE_PATH.read_text(encoding='utf-8'))


def save_state(state: Dict[str, Any]) -> Dict[str, Any]:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=2), encoding='utf-8')
    return state


def append_audit(event_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    state = load_state()
    state.setdefault('audit_log', []).insert(0, {
        'event_id': f'audit_{time.time_ns()}',
        'event_type': event_type,
        'timestamp': int(time.time()),
        **payload,
    })
    state['audit_log'] = state['audit_log'][:500]
    return save_state(state)


def record_order(envelope: Dict[str, Any], response: Dict[str, Any]) -> Dict[str, Any]:
    state = load_state()
    state.setdefault('orders', []).insert(0, {
        'submitted_at': int(time.time()),
        'envelope': envelope,
        'response': response,
    })
    state['orders'] = state['orders'][:500]
    if float(response.get('filled_qty') or 0.0) > 0:
        state.setdefault('fills', []).insert(0, {
            'recorded_at': int(time.time()),
            'strategy_id': envelope.get('strategy_id'),
            'allocation_id': envelope.get('allocation_id'),
            'decision_id': envelope.get('decision_id'),
            'risk_tag': envelope.get('risk_tag'),
            'broker': response.get('broker'),
            'order_id': response.get('order_id'),
            'symbol': response.get('symbol'),
            'side': response.get('side'),
            'filled_qty': response.get('filled_qty'),
            'fill_price': response.get('fill_price'),
            'status': response.get('status'),
            'executed_at': response.get('executed_at'),
        })
        state['fills'] = state['fills'][:500]
    state.setdefault('decision_memory', []).insert(0, {
        'decision_id': envelope.get('decision_id'),
        'allocation_id': envelope.get('allocation_id'),
        'strategy_id': envelope.get('strategy_id'),
        'risk_tag': envelope.get('risk_tag'),
        'timestamp': int(time.time()),
    })
    state['decision_memory'] = state['decision_memory'][:500]
    return save_state(state)
