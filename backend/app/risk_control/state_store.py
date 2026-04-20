from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict

STATE_PATH = Path(__file__).resolve().parents[1] / 'state' / 'risk_kill_switch_state.json'


def default_state() -> Dict[str, Any]:
    return {
        'generated_by': 'QNT50004',
        'status': 'degraded',
        'armed': True,
        'safe_mode_on_trigger': True,
        'kill_switch_triggered': False,
        'kill_switch_level': 'normal',
        'trigger_reason': None,
        'triggered_at': None,
        'reset_at': None,
        'thresholds': {
            'portfolio_drawdown_limit_pct': 0.12,
            'strategy_drawdown_limit_pct': 0.08,
            'daily_loss_limit_pct': 0.04,
            'max_single_order_notional': 250000.0,
            'max_live_notional': 1500000.0,
            'max_position_concentration_pct': 0.35,
            'max_margin_usage_pct': 0.55,
            'max_latency_ms': 1500,
        },
        'metrics': {
            'equity': 1000000.0,
            'peak_equity': 1000000.0,
            'portfolio_drawdown_pct': 0.0,
            'strategy_drawdown_pct': 0.0,
            'daily_loss_pct': 0.0,
            'open_notional': 0.0,
            'largest_position_pct': 0.0,
            'margin_usage_pct': 0.0,
            'latency_ms': 35,
            'venue_connectivity_ok': True,
            'breach_count': 0,
        },
        'active_breaches': [],
        'evaluation_log': [],
        'trigger_log': [],
        'override_log': [],
        'blocked_orders': [],
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
        'event_id': f'risk_audit_{time.time_ns()}',
        'event_type': event_type,
        'timestamp': int(time.time()),
        **payload,
    })
    state['audit_log'] = state['audit_log'][:500]
    return save_state(state)
