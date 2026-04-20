from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict

STATE_PATH = Path(__file__).resolve().parents[1] / 'state' / 'autonomous_remediation_recovery_state.json'


def default_state() -> Dict[str, Any]:
    return {
        'generated_by': 'QNT50027',
        'status': 'degraded',
        'policy': {
            'enabled': True,
            'auto_sync_sources': True,
            'require_breach_sync': True,
            'require_risk_clearance_for_execute': True,
            'require_supervisory_resolution_for_severe_cases': True,
            'max_open_actions': 250,
            'max_recovery_cycles': 500,
            'max_audit_events': 500,
        },
        'last_sync': None,
        'sync_history': [],
        'remediation_actions': [],
        'recovery_cycles': [],
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
        'event_id': f'autonomous_remediation_recovery_audit_{time.time_ns()}',
        'event_type': event_type,
        'timestamp': int(time.time()),
        **payload,
    })
    state['audit_log'] = state['audit_log'][: int((state.get('policy') or {}).get('max_audit_events', 500))]
    return save_state(state)
