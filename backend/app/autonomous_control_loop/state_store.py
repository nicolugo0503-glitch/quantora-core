
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict

STATE_PATH = Path(__file__).resolve().parents[1] / 'state' / 'autonomous_control_loop_state.json'


def default_state() -> Dict[str, Any]:
    return {
        'generated_by': 'QNT50022',
        'status': 'degraded',
        'policy': {
            'enabled': True,
            'auto_sync_sources': True,
            'auto_ingest_release_queue': True,
            'require_risk_clearance': True,
            'require_liquidity_capacity': True,
            'require_intercompany_clear': False,
            'require_positive_performance_bias': False,
            'minimum_available_liquidity': 100000.0,
            'minimum_cumulative_return_pct': -0.25,
            'max_cycles_to_keep': 200,
        },
        'last_sync': None,
        'sync_history': [],
        'control_plans': [],
        'control_cycles': [],
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
        'event_id': f'autonomous_control_loop_audit_{time.time_ns()}',
        'event_type': event_type,
        'timestamp': int(time.time()),
        **payload,
    })
    state['audit_log'] = state['audit_log'][:500]
    return save_state(state)
