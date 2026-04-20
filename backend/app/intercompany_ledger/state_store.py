from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict

STATE_PATH = Path(__file__).resolve().parents[1] / 'state' / 'intercompany_ledger_state.json'


def default_state() -> Dict[str, Any]:
    return {
        'generated_by': 'QNT50018',
        'status': 'degraded',
        'policy': {
            'base_currency': 'USD',
            'auto_sync_sources': True,
            'require_approval': True,
            'approval_threshold': 250000.0,
            'require_treasury_capacity': True,
            'require_disclosure_acknowledgement': False,
            'default_settlement_route': 'internal_treasury_route',
            'retention_days': 2555,
        },
        'last_sync': None,
        'sync_history': [],
        'flow_cases': [],
        'journal_entries': [],
        'settlements': [],
        'exceptions': [],
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
        'event_id': f'intercompany_ledger_audit_{time.time_ns()}',
        'event_type': event_type,
        'timestamp': int(time.time()),
        **payload,
    })
    state['audit_log'] = state['audit_log'][:500]
    return save_state(state)
