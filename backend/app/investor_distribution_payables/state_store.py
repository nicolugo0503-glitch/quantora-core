from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict

STATE_PATH = Path(__file__).resolve().parents[1] / 'state' / 'investor_distribution_payables_state.json'


def default_state() -> Dict[str, Any]:
    return {
        'generated_by': 'QNT50011',
        'status': 'degraded',
        'policy': {
            'base_currency': 'USD',
            'require_registered_investor': True,
            'require_statement_cycle': True,
            'require_dual_attestation': True,
            'require_treasury_capacity': True,
            'require_batch_authority': True,
            'require_transfer_approved': True,
            'require_positive_distributable_return': False,
            'max_unresolved_breaks': 0,
            'max_distribution_pct_of_equity': 0.25,
            'distribution_amount_tolerance': 1.0,
            'release_authority_ttl_seconds': 86400,
            'auto_sync_sources': True,
        },
        'distribution_batches': [],
        'attestations': [],
        'authorized_batches': [],
        'blocked_batches': [],
        'transfer_links': [],
        'authorized_payable_releases': [],
        'executed_payables': [],
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
        'event_id': f'investor_distribution_payables_audit_{time.time_ns()}',
        'event_type': event_type,
        'timestamp': int(time.time()),
        **payload,
    })
    state['audit_log'] = state['audit_log'][:500]
    return save_state(state)


def distribution_release_status(transfer_id: str) -> Dict[str, Any]:
    transfer_id = str(transfer_id or '').strip()
    if not transfer_id:
        return {'authorized': False, 'reason': 'transfer_id is required'}
    state = load_state()
    now = int(time.time())
    for item in state.get('authorized_payable_releases', []):
        if item.get('treasury_transfer_id') == transfer_id and item.get('status') == 'authorized':
            expires_at = int(item.get('expires_at') or 0)
            if expires_at and expires_at < now:
                return {
                    'authorized': False,
                    'reason': 'distribution payable authority expired',
                    'payable_release_id': item.get('payable_release_id'),
                }
            return {
                'authorized': True,
                'payable_release_id': item.get('payable_release_id'),
                'batch_id': item.get('batch_id'),
                'investor_id': item.get('investor_id'),
                'amount': item.get('amount'),
                'authorized_at': item.get('authorized_at'),
                'expires_at': item.get('expires_at'),
            }
    for item in state.get('transfer_links', []):
        if item.get('treasury_transfer_id') == transfer_id:
            return {
                'authorized': False,
                'reason': f"linked transfer status={item.get('status') or 'pending'}",
                'batch_id': item.get('batch_id'),
                'line_id': item.get('line_id'),
            }
    return {'authorized': False, 'reason': 'no distribution payable authority found'}
