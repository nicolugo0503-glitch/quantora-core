from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict

STATE_PATH = Path(__file__).resolve().parents[1] / 'state' / 'settlement_reconciliation_state.json'


def default_state() -> Dict[str, Any]:
    return {
        'generated_by': 'QNT50007',
        'status': 'degraded',
        'control': {
            'auto_ingest_fills': True,
            'auto_reconcile_after_confirm': True,
            'position_tolerance_qty': 0.000001,
            'cash_tolerance': 1.0,
            'notional_tolerance': 1.0,
            'base_currency': 'USD',
        },
        'processed_order_ids': [],
        'pending_settlements': [],
        'settled_settlements': [],
        'cash_ledger': [],
        'position_ledger': [],
        'positions': {},
        'cash_balance': 0.0,
        'last_broker_snapshot': {'positions': {}, 'cash_balance': 0.0},
        'last_reconciliation': None,
        'reconciliation_breaks': [],
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
        'event_id': f'settlement_audit_{time.time_ns()}',
        'event_type': event_type,
        'timestamp': int(time.time()),
        **payload,
    })
    state['audit_log'] = state['audit_log'][:500]
    return save_state(state)
