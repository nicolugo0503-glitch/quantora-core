from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict

STATE_PATH = Path(__file__).resolve().parents[1] / 'state' / 'institutional_breach_exception_resolution_state.json'


def default_state() -> Dict[str, Any]:
    return {
        'generated_by': 'QNT50026',
        'status': 'degraded',
        'policy': {
            'enabled': True,
            'auto_sync_sources': True,
            'require_risk_sync': True,
            'require_settlement_sync': True,
            'require_charter_directive_context': True,
            'require_supervisory_escalation_for_severe': True,
            'severe_alignment_threshold': 60.0,
            'default_resolution_sla_hours': 24,
            'max_cases_to_keep': 500,
            'max_resolutions_to_keep': 500,
            'max_escalations_to_keep': 500,
        },
        'last_sync': None,
        'sync_history': [],
        'breach_cases': [],
        'exception_resolutions': [],
        'escalation_log': [],
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
        'event_id': f'institutional_breach_exception_resolution_audit_{time.time_ns()}',
        'event_type': event_type,
        'timestamp': int(time.time()),
        **payload,
    })
    state['audit_log'] = state['audit_log'][:500]
    return save_state(state)
