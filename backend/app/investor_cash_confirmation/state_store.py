from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict

STATE_PATH = Path(__file__).resolve().parents[1] / 'state' / 'investor_cash_confirmation_state.json'


def default_state() -> Dict[str, Any]:
    return {
        'generated_by': 'QNT50009',
        'status': 'degraded',
        'policy': {
            'base_currency': 'USD',
            'require_bank_instruction_verified': True,
            'require_statement_alignment': True,
            'require_transfer_approved': True,
            'require_treasury_capacity': True,
            'require_dual_ack': True,
            'release_authority_ttl_seconds': 86400,
            'max_unresolved_exceptions': 0,
            'auto_sync_treasury': True,
        },
        'investors': {},
        'pending_release_requests': [],
        'authorized_releases': [],
        'rejected_releases': [],
        'acknowledgements': [],
        'exceptions': [],
        'last_sync': None,
        'sync_history': [],
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
        'event_id': f'investor_cash_confirmation_audit_{time.time_ns()}',
        'event_type': event_type,
        'timestamp': int(time.time()),
        **payload,
    })
    state['audit_log'] = state['audit_log'][:500]
    return save_state(state)


def transfer_release_status(transfer_id: str) -> Dict[str, Any]:
    transfer_id = str(transfer_id or '').strip()
    if not transfer_id:
        return {'authorized': False, 'reason': 'transfer_id is required'}
    state = load_state()
    now = int(time.time())
    for item in state.get('authorized_releases', []):
        if item.get('treasury_transfer_id') == transfer_id and item.get('status') == 'authorized':
            expires_at = int(item.get('expires_at') or 0)
            if expires_at and expires_at < now:
                return {
                    'authorized': False,
                    'reason': 'release authority expired',
                    'release_authority_id': item.get('release_authority_id'),
                }
            return {
                'authorized': True,
                'release_authority_id': item.get('release_authority_id'),
                'investor_id': item.get('investor_id'),
                'amount': item.get('amount'),
                'authorized_at': item.get('authorized_at'),
                'expires_at': item.get('expires_at'),
            }
    for item in state.get('pending_release_requests', []):
        if item.get('treasury_transfer_id') == transfer_id:
            return {
                'authorized': False,
                'reason': f"release request status={item.get('status') or 'pending'}",
                'release_request_id': item.get('release_request_id'),
            }
    return {'authorized': False, 'reason': 'no release authority found'}
