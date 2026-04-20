from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict

STATE_PATH = Path(__file__).resolve().parents[1] / 'state' / 'investor_exit_finalization_state.json'


def default_state() -> Dict[str, Any]:
    return {
        'generated_by': 'QNT50010',
        'status': 'degraded',
        'policy': {
            'base_currency': 'USD',
            'require_executed_transfer': True,
            'require_release_authority': True,
            'require_dual_attestation': True,
            'require_reconciliation_clear': True,
            'require_cash_paid_match': True,
            'allow_in_kind_component': True,
            'amount_tolerance': 1.0,
            'max_unresolved_settlement_breaks': 0,
            'exit_authority_ttl_seconds': 172800,
            'auto_sync_sources': True,
        },
        'registered_cases': [],
        'attestations': [],
        'authorized_exit_finalizations': [],
        'blocked_cases': [],
        'finalized_exits': [],
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
        'event_id': f'investor_exit_finalization_audit_{time.time_ns()}',
        'event_type': event_type,
        'timestamp': int(time.time()),
        **payload,
    })
    state['audit_log'] = state['audit_log'][:500]
    return save_state(state)


def exit_finalization_status(case_id: str) -> Dict[str, Any]:
    case_id = str(case_id or '').strip()
    if not case_id:
        return {'authorized': False, 'reason': 'case_id is required'}
    state = load_state()
    now = int(time.time())
    for item in state.get('authorized_exit_finalizations', []):
        if item.get('case_id') == case_id and item.get('status') == 'authorized':
            expires_at = int(item.get('expires_at') or 0)
            if expires_at and expires_at < now:
                return {
                    'authorized': False,
                    'reason': 'exit finalization authority expired',
                    'exit_authority_id': item.get('exit_authority_id'),
                }
            return {
                'authorized': True,
                'exit_authority_id': item.get('exit_authority_id'),
                'authorized_at': item.get('authorized_at'),
                'expires_at': item.get('expires_at'),
                'transfer_id': item.get('treasury_transfer_id'),
                'investor_id': item.get('investor_id'),
            }
    for item in state.get('registered_cases', []):
        if item.get('case_id') == case_id:
            return {
                'authorized': False,
                'reason': f"case status={item.get('status') or 'pending'}",
                'case_id': item.get('case_id'),
            }
    return {'authorized': False, 'reason': 'no exit finalization authority found'}
