from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict

STATE_PATH = Path(__file__).resolve().parents[1] / 'state' / 'autonomous_execution_state.json'


def default_state() -> Dict[str, Any]:
    return {
        'generated_by': 'QNT50006',
        'status': 'degraded',
        'policy': {
            'enabled': False,
            'auto_execute_paper': True,
            'auto_execute_live': False,
            'require_committee_ticket_for_live': True,
            'max_orders_per_cycle': 4,
            'max_cycle_notional': 250000.0,
            'minimum_sharpe_ratio': 0.25,
            'maximum_drawdown_pct': 0.12,
            'allow_regime_stress': False,
            'default_order_type': 'MARKET',
            'participation_rate': 1.0,
        },
        'price_map': {
            'BTCUSDT': 65000.0,
            'ETHUSDT': 3200.0,
            'USDTUSD': 1.0,
        },
        'release_queue_cache': [],
        'decision_queue': [],
        'last_plan': None,
        'last_cycle': None,
        'cycle_history': [],
        'escalations': [],
        'audit_log': [],
    }


def load_state() -> Dict[str, Any]:
    if not STATE_PATH.exists():
        return default_state()
    return json.loads(STATE_PATH.read_text(encoding='utf-8'))


def save_state(state: Dict[str, Any]) -> Dict[str, Any]:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=2), encoding='utf-8')
    return state


def append_audit(event_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    state = load_state()
    state.setdefault('audit_log', []).insert(0, {
        'event_id': f'autonomous_exec_audit_{time.time_ns()}',
        'event_type': event_type,
        'timestamp': int(time.time()),
        **payload,
    })
    state['audit_log'] = state['audit_log'][:500]
    return save_state(state)
