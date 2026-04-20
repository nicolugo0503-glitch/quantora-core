from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict

STATE_PATH = Path(__file__).resolve().parents[1] / 'state' / 'governance_binder_publication_state.json'


def default_state() -> Dict[str, Any]:
    return {
        'generated_by': 'QNT50014',
        'status': 'degraded',
        'policy': {
            'base_currency': 'USD',
            'require_official_books_release': True,
            'require_archive_certification': True,
            'require_retrieval_packet_assembly': True,
            'require_regulator_channel': True,
            'require_operations_attestation': True,
            'require_compliance_attestation': True,
            'retain_packet_days': 2555,
            'binder_channel': 'governance_binder',
            'regulator_channel': 'supervisory_retrieval_packet',
            'auto_sync_sources': True,
        },
        'last_sync': None,
        'sync_history': [],
        'publication_cases': [],
        'retrieval_packets': [],
        'published_binders': [],
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
        'event_id': f'governance_binder_publication_audit_{time.time_ns()}',
        'event_type': event_type,
        'timestamp': int(time.time()),
        **payload,
    })
    state['audit_log'] = state['audit_log'][:500]
    return save_state(state)
