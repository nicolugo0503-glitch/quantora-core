from __future__ import annotations

import time
import uuid
from typing import Any, Dict, Optional

from backend.app.investor_cash_confirmation.state_store import append_audit, load_state, save_state
from backend.app.treasury_cash_mobility.engine import TreasuryCashMobilityEngine
from backend.app.treasury_cash_mobility.state_store import load_state as load_treasury_state


class InvestorCashConfirmationEngine:
    def __init__(self):
        self.state = load_state()
        self.treasury = TreasuryCashMobilityEngine()

    def _refresh(self) -> Dict[str, Any]:
        self.state = load_state()
        return self.state

    @staticmethod
    def _round(value: Any, digits: int = 2) -> float:
        return round(float(value or 0.0), digits)

    def _policy(self, state: Dict[str, Any]) -> Dict[str, Any]:
        return dict(state.get('policy') or {})

    def _treasury_context(self) -> Dict[str, Any]:
        treasury_state = load_treasury_state()
        summary = self.treasury.summary()
        investor_pending = [
            t for t in treasury_state.get('pending_transfers', [])
            if self._transfer_requires_release(t)
        ]
        investor_completed = [
            t for t in treasury_state.get('completed_transfers', [])
            if self._transfer_requires_release(t)
        ]
        return {
            'summary': summary,
            'pending_investor_transfers': investor_pending,
            'completed_investor_transfers': investor_completed,
        }

    @staticmethod
    def _transfer_requires_release(transfer: Optional[Dict[str, Any]]) -> bool:
        transfer = transfer or {}
        transfer_type = str(transfer.get('transfer_type') or '').lower()
        destination = str(transfer.get('destination') or '').lower()
        return transfer_type in {'investor_redemption', 'investor_distribution', 'capital_return'} or destination in {
            'investor_settlement', 'investor settlement bank', 'investor_settlement_bank'
        }

    def sync_treasury_context(self, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        payload = payload or {}
        state = self._refresh()
        ctx = self._treasury_context()
        snapshot = {
            'synced_at': int(time.time()),
            'source': str(payload.get('source') or 'manual'),
            'available_to_move': self._round((ctx.get('summary') or {}).get('available_to_move'), 2),
            'cash_balance': self._round((ctx.get('summary') or {}).get('cash_balance'), 2),
            'break_count': int((ctx.get('summary') or {}).get('break_count') or 0),
            'settlement_status': (ctx.get('summary') or {}).get('settlement_status'),
            'pending_investor_transfer_count': len(ctx.get('pending_investor_transfers') or []),
            'completed_investor_transfer_count': len(ctx.get('completed_investor_transfers') or []),
        }
        state['last_sync'] = snapshot
        state.setdefault('sync_history', []).insert(0, snapshot)
        state['sync_history'] = state['sync_history'][:500]
        save_state(state)
        append_audit('treasury_context_synced', snapshot)
        return {'mission': 'QNT50009', 'status': 'synced', 'snapshot': snapshot}

    def _ensure_synced(self, state: Dict[str, Any]) -> Dict[str, Any]:
        if self._policy(state).get('auto_sync_treasury', True) and not state.get('last_sync'):
            self.sync_treasury_context({'source': 'auto'})
            state = self._refresh()
        return state

    def register_investor(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        state = self._refresh()
        investor_id = str(payload.get('investor_id') or '').strip()
        if not investor_id:
            raise ValueError('investor_id is required')
        investor = {
            'investor_id': investor_id,
            'investor_name': str(payload.get('investor_name') or investor_id),
            'bank_instruction_verified': bool(payload.get('bank_instruction_verified', False)),
            'statement_alignment_status': str(payload.get('statement_alignment_status') or 'pending').lower(),
            'preferred_currency': str(payload.get('preferred_currency') or self._policy(state).get('base_currency') or 'USD').upper(),
            'cash_confirmation_contact': str(payload.get('cash_confirmation_contact') or ''),
            'status': str(payload.get('status') or 'active').lower(),
            'last_updated_at': int(time.time()),
        }
        state.setdefault('investors', {})[investor_id] = investor
        save_state(state)
        append_audit('investor_registered', {'investor_id': investor_id, 'investor_name': investor['investor_name']})
        return {'mission': 'QNT50009', 'status': 'registered', 'investor': investor, 'summary': self.summary()}

    def _find_transfer(self, transfer_id: str) -> Dict[str, Any]:
        transfer_id = str(transfer_id or '').strip()
        treasury_state = load_treasury_state()
        for bucket in ['pending_transfers', 'completed_transfers']:
            for item in treasury_state.get(bucket, []):
                if item.get('transfer_id') == transfer_id:
                    return item
        raise ValueError('treasury transfer_id not found')

    def _find_request(self, state: Dict[str, Any], release_request_id: str) -> Dict[str, Any]:
        for item in state.get('pending_release_requests', []):
            if item.get('release_request_id') == release_request_id:
                return item
        raise ValueError('release_request_id not found')

    def request_release(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        state = self._ensure_synced(self._refresh())
        operator = str(payload.get('operator') or '').strip()
        if not operator:
            raise ValueError('operator is required')
        transfer = self._find_transfer(payload.get('transfer_id'))
        if not self._transfer_requires_release(transfer):
            raise ValueError('transfer does not require investor cash confirmation authority')
        investor_id = str(payload.get('investor_id') or transfer.get('investor_id') or '').strip()
        if not investor_id:
            raise ValueError('investor_id is required')
        investors = state.get('investors') or {}
        investor = investors.get(investor_id)
        if not investor:
            raise ValueError('investor_id is not registered')
        amount = self._round(payload.get('amount') if payload.get('amount') is not None else transfer.get('amount'), 2)
        if amount <= 0:
            raise ValueError('amount must be positive')
        request = {
            'release_request_id': f'irr_{uuid.uuid4().hex[:12]}',
            'created_at': int(time.time()),
            'operator': operator,
            'investor_id': investor_id,
            'investor_name': investor.get('investor_name'),
            'treasury_transfer_id': transfer.get('transfer_id'),
            'amount': amount,
            'currency': str(transfer.get('currency') or investor.get('preferred_currency') or 'USD').upper(),
            'transfer_type': transfer.get('transfer_type') or 'investor_distribution',
            'dealing_reference': str(payload.get('dealing_reference') or transfer.get('capital_activity_id') or transfer.get('decision_id') or ''),
            'statement_cycle_id': str(payload.get('statement_cycle_id') or transfer.get('statement_cycle_id') or ''),
            'status': 'pending_confirmation',
            'confirmation_received': False,
            'ops_acknowledged': False,
            'investor_acknowledged': False,
            'bank_instruction_verified': bool(investor.get('bank_instruction_verified', False)),
            'statement_aligned': str(investor.get('statement_alignment_status') or 'pending').lower() in {'aligned', 'confirmed', 'complete'},
            'notes': str(payload.get('notes') or ''),
        }
        state.setdefault('pending_release_requests', []).insert(0, request)
        state['pending_release_requests'] = state['pending_release_requests'][:500]
        save_state(state)
        append_audit('release_requested', {
            'release_request_id': request['release_request_id'],
            'investor_id': investor_id,
            'treasury_transfer_id': request['treasury_transfer_id'],
            'amount': amount,
        })
        return {'mission': 'QNT50009', 'status': request['status'], 'release_request': request, 'summary': self.summary()}

    def acknowledge(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        state = self._refresh()
        actor = str(payload.get('actor') or '').strip()
        if not actor:
            raise ValueError('actor is required')
        request = self._find_request(state, str(payload.get('release_request_id') or '').strip())
        ack_type = str(payload.get('ack_type') or 'ops').strip().lower()
        if ack_type not in {'ops', 'investor', 'bank', 'statement'}:
            raise ValueError('ack_type must be one of ops, investor, bank, statement')
        request['status'] = 'ready_for_authority'
        if ack_type == 'ops':
            request['ops_acknowledged'] = True
        elif ack_type == 'investor':
            request['investor_acknowledged'] = True
            request['confirmation_received'] = True
        elif ack_type == 'bank':
            request['bank_instruction_verified'] = True
        elif ack_type == 'statement':
            request['statement_aligned'] = True
        ack = {
            'ack_id': f'ack_{uuid.uuid4().hex[:12]}',
            'release_request_id': request['release_request_id'],
            'treasury_transfer_id': request['treasury_transfer_id'],
            'investor_id': request['investor_id'],
            'ack_type': ack_type,
            'actor': actor,
            'note': str(payload.get('note') or ''),
            'acknowledged_at': int(time.time()),
        }
        state.setdefault('acknowledgements', []).insert(0, ack)
        state['acknowledgements'] = state['acknowledgements'][:500]
        save_state(state)
        append_audit('release_acknowledged', ack)
        return {'mission': 'QNT50009', 'status': request['status'], 'acknowledgement': ack, 'release_request': request, 'summary': self.summary()}

    def authorize_release(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        state = self._ensure_synced(self._refresh())
        approver = str(payload.get('approver') or '').strip()
        if not approver:
            raise ValueError('approver is required')
        request = self._find_request(state, str(payload.get('release_request_id') or '').strip())
        transfer = self._find_transfer(request.get('treasury_transfer_id'))
        policy = self._policy(state)
        ctx = self._treasury_context()
        summary = ctx.get('summary') or {}
        reasons = []
        if policy.get('require_transfer_approved', True) and str(transfer.get('status') or '').lower() != 'approved':
            reasons.append('treasury transfer is not approved')
        if policy.get('require_bank_instruction_verified', True) and not bool(request.get('bank_instruction_verified')):
            reasons.append('bank instructions are not verified')
        if policy.get('require_statement_alignment', True) and not bool(request.get('statement_aligned')):
            reasons.append('statement alignment is incomplete')
        if policy.get('require_dual_ack', True) and not (bool(request.get('ops_acknowledged')) and bool(request.get('investor_acknowledged'))):
            reasons.append('dual acknowledgement is incomplete')
        if policy.get('require_treasury_capacity', True) and self._round(summary.get('available_to_move'), 2) < self._round(request.get('amount'), 2):
            reasons.append('treasury mobility capacity is insufficient for requested release')
        if int(summary.get('break_count') or 0) > int(policy.get('max_unresolved_exceptions') or 0):
            reasons.append('unresolved reconciliation breaks block investor cash release')
        expires_at = int(time.time()) + int(policy.get('release_authority_ttl_seconds') or 86400)
        if reasons:
            request['status'] = 'blocked'
            request['blocked_reasons'] = reasons
            rejected = {
                'release_request_id': request['release_request_id'],
                'treasury_transfer_id': request['treasury_transfer_id'],
                'investor_id': request['investor_id'],
                'amount': request['amount'],
                'currency': request['currency'],
                'rejected_at': int(time.time()),
                'rejected_by': approver,
                'reasons': reasons,
                'status': 'blocked',
            }
            state.setdefault('rejected_releases', []).insert(0, rejected)
            state['rejected_releases'] = state['rejected_releases'][:500]
            save_state(state)
            append_audit('release_blocked', rejected)
            return {'mission': 'QNT50009', 'status': 'blocked', 'release_request': request, 'reasons': reasons, 'summary': self.summary()}
        authority = {
            'release_authority_id': f'ira_{uuid.uuid4().hex[:12]}',
            'release_request_id': request['release_request_id'],
            'treasury_transfer_id': request['treasury_transfer_id'],
            'investor_id': request['investor_id'],
            'investor_name': request['investor_name'],
            'amount': request['amount'],
            'currency': request['currency'],
            'authorized_at': int(time.time()),
            'authorized_by': approver,
            'expires_at': expires_at,
            'status': 'authorized',
            'dealing_reference': request.get('dealing_reference'),
            'statement_cycle_id': request.get('statement_cycle_id'),
        }
        request['status'] = 'authorized'
        request['release_authority_id'] = authority['release_authority_id']
        state.setdefault('authorized_releases', []).insert(0, authority)
        state['authorized_releases'] = state['authorized_releases'][:500]
        save_state(state)
        append_audit('release_authorized', authority)
        return {'mission': 'QNT50009', 'status': 'authorized', 'authority': authority, 'release_request': request, 'summary': self.summary()}

    def configure(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        state = self._refresh()
        policy = self._policy(state)
        for key in [
            'base_currency', 'require_bank_instruction_verified', 'require_statement_alignment',
            'require_transfer_approved', 'require_treasury_capacity', 'require_dual_ack',
            'release_authority_ttl_seconds', 'max_unresolved_exceptions', 'auto_sync_treasury'
        ]:
            if payload.get(key) is not None:
                policy[key] = payload[key]
        state['policy'] = policy
        save_state(state)
        append_audit('investor_confirmation_policy_configured', {'policy': policy})
        if payload.get('sync_after_configure', True):
            self.sync_treasury_context({'source': 'configure'})
        return self.summary()

    def summary(self) -> Dict[str, Any]:
        state = self._ensure_synced(self._refresh())
        ctx = self._treasury_context()
        summary = ctx.get('summary') or {}
        pending = state.get('pending_release_requests', [])
        authorized = [r for r in state.get('authorized_releases', []) if r.get('status') == 'authorized']
        blocked = [r for r in state.get('rejected_releases', []) if r.get('status') == 'blocked']
        posture = 'ready'
        if blocked:
            posture = 'constrained'
        if (summary.get('break_count') or 0) > 0:
            posture = 'blocked'
        if pending and not authorized:
            posture = 'awaiting_confirmation'
        return {
            'mission': 'QNT50009',
            'status': 'ok',
            'posture': posture,
            'investor_count': len(state.get('investors', {})),
            'pending_release_count': len(pending),
            'authorized_release_count': len(authorized),
            'blocked_release_count': len(blocked),
            'acknowledgement_count': len(state.get('acknowledgements', [])),
            'treasury_available_to_move': self._round(summary.get('available_to_move'), 2),
            'treasury_break_count': int(summary.get('break_count') or 0),
            'pending_investor_transfer_count': len(ctx.get('pending_investor_transfers') or []),
            'completed_investor_transfer_count': len(ctx.get('completed_investor_transfers') or []),
            'last_sync': state.get('last_sync'),
        }

    def reset(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        operator = str(payload.get('operator') or '').strip()
        if not operator:
            raise ValueError('operator is required')
        clear_audit = bool(payload.get('clear_audit', False))
        current = load_state()
        fresh = {
            **current,
            'pending_release_requests': [],
            'authorized_releases': [],
            'rejected_releases': [],
            'acknowledgements': [],
            'exceptions': [],
            'last_sync': None,
            'sync_history': [],
        }
        if clear_audit:
            fresh['audit_log'] = []
        save_state(fresh)
        append_audit('investor_cash_confirmation_reset', {
            'operator': operator,
            'reason': str(payload.get('reason') or 'manual reset'),
            'clear_audit': clear_audit,
        })
        return self.sync_treasury_context({'source': 'reset'})
