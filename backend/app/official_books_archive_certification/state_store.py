from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict

STATE_PATH = Path(__file__).resolve().parents[1] / 'state' / 'official_books_archive_certification_state.json'


def default_state() -> Dict[str, Any]:
    return {
        'generated_by': 'QNT50013',
        'status': 'degraded',
        'policy': {
            'base_currency': 'USD',
            'require_closed_period': True,
            'require_notice_finalization': True,
            'require_archive_certification': True,
            'require_zero_open_breaks': True,
            'require_controller_signoff': True,
            'require_operations_signoff': True,
            'retain_release_payload_days': 2555,
            'archive_channel': 'governance_binder',
            'auto_sync_sources': True,
        },
        'last_sync': None,
        'sync_history': [],
        'books_releases': [],
        'archive_certifications': [],
        'official_releases': [],
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
        'event_id': f'official_books_archive_certification_audit_{time.time_ns()}',
        'event_type': event_type,
        'timestamp': int(time.time()),
        **payload,
    })
    state['audit_log'] = state['audit_log'][:500]
    return save_state(state)
