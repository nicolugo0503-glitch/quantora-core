from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict

STATE_PATH = Path(__file__).resolve().parents[1] / 'state' / 'treasury_cash_mobility_state.json'


def default_state() -> Dict[str, Any]:
    return {
        'generated_by': 'QNT50008',
        'status': 'degraded',
        'policy': {
            'base_currency': 'USD',
            'reserve_floor': 25000.0,
            'reserve_buffer_pct': 0.15,
            'min_operating_cash': 10000.0,
            'max_single_transfer_pct_of_available': 0.40,
            'auto_sync_settlement': True,
            'settlement_haircut_pct': 0.02,
            'rebalance_tolerance_pct': 0.10,
        },
        'accounts': {
            'operating': {'currency': 'USD', 'balance': 0.0},
            'broker_buffer': {'currency': 'USD', 'balance': 0.0},
            'custody_reserve': {'currency': 'USD', 'balance': 0.0},
        },
        'external_destinations': {
            'prime_broker': 'IBKR',
            'crypto_venue': 'Binance',
            'administrator': 'Fund Administrator',
            'investor_settlement': 'Investor Settlement Bank',
        },
        'pending_transfers': [],
        'completed_transfers': [],
        'rejected_transfers': [],
        'liquidity_snapshots': [],
        'last_sync': None,
        'last_rebalance': None,
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
        'event_id': f'treasury_audit_{time.time_ns()}',
        'event_type': event_type,
        'timestamp': int(time.time()),
        **payload,
    })
    state['audit_log'] = state['audit_log'][:500]
    return save_state(state)
