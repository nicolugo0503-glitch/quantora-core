from __future__ import annotations

import time
import uuid
from typing import Any, Dict, Optional

from backend.app.investor_cash_confirmation.state_store import transfer_release_status
from backend.app.investor_exit_finalization.state_store import append_audit, default_state, load_state, save_state
from backend.app.settlement_reconciliation.engine import SettlementReconciliationEngine
from backend.app.settlement_reconciliation.state_store import load_state as load_settlement_state
from backend.app.treasury_cash_mobility.state_store import load_state as load_treasury_state


class InvestorExitFinalizationEngine:
    def __init__(self):
        self.state = load_state()
        self.settlement = SettlementReconciliationEngine()

    def _refresh(self) -> Dict[str, Any]:
        self.state = load_state()
        return self.state

    @staticmethod
    def _round(value: Any, digits: int = 2) -> float:
        return round(float(value or 0.0), digits)

    def _policy(self, state: Dict[str, Any]) -> Dict[str, Any]:
        return dict(state.get('policy') or {})

    @staticmethod
    def _requires_exit_control(transfer: Optional[Dict[str, Any]]) -> bool:
        transfer = transfer or {}
        transfer_type = str(transfer.get('transfer_type') or '').lower()
        destination = str(transfer.get('destination') or '').lower()
        return transfer_type in {'investor_redemption', 'capital_return'} or destination in {
            'investor_settlement', 'investor settlement bank', 'investor_settlement_bank'
        }

    def _source_context(self) -> Dict[str, Any]:
        treasury_state = load_treasury_state()
        settlement_state = load_settlement_state()
        treasury_completed = [
            t for t in treasury_state.get('completed_transfers', [])
            if self._requires_exit_control(t)
        ]
        return {
            'treasury_completed_exits': treasury_completed,
            'treasury_pending_exits': [
                t for t in treasury_state.get('pending_transfers', [])
                if self._requires_exit_control(t)
            ],
            'treasury_cash_balance': self._round(sum(float((row or {}).get('balance') or 0.0) for row in (treasury_state.get('accounts') or {}).values()), 2),
            'settlement_break_count': len(settlement_state.get('reconciliation_breaks') or []),
            'settlement_status': (settlement_state.get('last_reconciliation') or {}).get('status') or 'unreconciled',
            'settled_trade_count': len(settlement_state.get('settled_settlements', [])),
        }

    def sync_context(self, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        payload = payload or {}
        state = self._refresh()
        ctx = self._source_context()
        snapshot = {
            'synced_at': int(time.time()),
            'source': str(payload.get('source') or 'manual'),
            'treasury_completed_exit_count': len(ctx.get('treasury_completed_exits') or []),
            'treasury_pending_exit_count': len(ctx.get('treasury_pending_exits') or []),
            'treasury_cash_balance': ctx.get('treasury_cash_balance'),
            'settlement_break_count': ctx.get('settlement_break_count'),
            'settlement_status': ctx.get('settlement_status'),
            'settled_trade_count': ctx.get('settled_trade_count'),
        }
        state['last_sync'] = snapshot
        state.setdefault('sync_history', []).insert(0, snapshot)
        state['sync_history'] = state['sync_history'][:500]
        save_state(state)
        append_audit('exit_context_synced', snapshot)
        return {'mission': 'QNT50010', 'status': 'synced', 'snapshot': snapshot}

    def _ensure_synced(self, state: Dict[str, Any]) -> Dict[str, Any]:
        if self._policy(state).get('auto_sync_sources', True) and not state.get('last_sync'):
            self.sync_context({'source': 'auto'})
            state = self._refresh()
        return state

    def _find_completed_transfer(self, transfer_id: str) -> Dict[str, Any]:
        transfer_id = str(transfer_id or '').strip()
        treasury_state = load_treasury_state()
        for item in treasury_state.get('completed_transfers', []):
            if item.get('transfer_id') == transfer_id:
                return item
        raise ValueError('executed treasury transfer not found')

    def _find_case(self, state: Dict[str, Any], case_id: str) -> Dict[str, Any]:
        for item in state.get('registered_cases', []):
            if item.get('case_id') == case_id:
                return item
        raise ValueError('case_id not found')

    def register_case(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        state = self._ensure_synced(self._refresh())
        operator = str(payload.get('operator') or '').strip()
        if not operator:
            raise ValueError('operator is required')
        transfer = self._find_completed_transfer(payload.get('transfer_id'))
        if not self._requires_exit_control(transfer):
            raise ValueError('transfer is not an investor exit transfer')
        policy = self._policy(state)
        release = transfer_release_status(str(transfer.get('transfer_id') or ''))
        if policy.get('require_release_authority', True) and not release.get('authorized'):
            raise ValueError(f"investor release authority is required: {release.get('reason')}")
        investor_id = str(payload.get('investor_id') or transfer.get('investor_id') or release.get('investor_id') or '').strip()
        if not investor_id:
            raise ValueError('investor_id is required')
        cash_paid_amount = self._round(payload.get('cash_paid_amount') if payload.get('cash_paid_amount') is not None else transfer.get('amount'), 2)
        gross_redemption_amount = self._round(payload.get('gross_redemption_amount') if payload.get('gross_redemption_amount') is not None else transfer.get('amount'), 2)
        in_kind_amount = self._round(payload.get('in_kind_amount'), 2)
        if gross_redemption_amount <= 0:
            raise ValueError('gross_redemption_amount must be positive')
        if cash_paid_amount < 0 or in_kind_amount < 0:
            raise ValueError('cash_paid_amount and in_kind_amount cannot be negative')
        case = {
            'case_id': f'iex_{uuid.uuid4().hex[:12]}',
            'created_at': int(time.time()),
            'created_by': operator,
            'treasury_transfer_id': transfer.get('transfer_id'),
            'release_authority_id': release.get('release_authority_id'),
            'investor_id': investor_id,
            'investor_name': str(payload.get('investor_name') or investor_id),
            'capital_activity_id': str(payload.get('capital_activity_id') or transfer.get('capital_activity_id') or ''),
            'statement_cycle_id': str(payload.get('statement_cycle_id') or transfer.get('statement_cycle_id') or ''),
            'dealing_reference': str(payload.get('dealing_reference') or transfer.get('capital_activity_id') or transfer.get('decision_id') or ''),
            'currency': str(payload.get('currency') or transfer.get('currency') or policy.get('base_currency') or 'USD').upper(),
            'gross_redemption_amount': gross_redemption_amount,
            'cash_paid_amount': cash_paid_amount,
            'in_kind_amount': in_kind_amount,
            'expected_total_amount': self._round(cash_paid_amount + in_kind_amount, 2),
            'transfer_amount': self._round(transfer.get('amount'), 2),
            'transfer_executed_at': transfer.get('executed_at'),
            'transfer_destination': transfer.get('destination'),
            'status': 'pending_attestation',
            'ops_attested': False,
            'investor_attested': False,
            'reconciliation_cleared': False,
            'legal_docs_finalized': False,
            'notes': str(payload.get('notes') or ''),
        }
        state.setdefault('registered_cases', []).insert(0, case)
        state['registered_cases'] = state['registered_cases'][:500]
        save_state(state)
        append_audit('exit_case_registered', {
            'case_id': case['case_id'],
            'treasury_transfer_id': case['treasury_transfer_id'],
            'investor_id': investor_id,
            'gross_redemption_amount': gross_redemption_amount,
        })
        return {'mission': 'QNT50010', 'status': case['status'], 'case': case, 'summary': self.summary()}

    def attest(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        state = self._refresh()
        actor = str(payload.get('actor') or '').strip()
        if not actor:
            raise ValueError('actor is required')
        case = self._find_case(state, str(payload.get('case_id') or '').strip())
        attestation_type = str(payload.get('attestation_type') or 'ops').strip().lower()
        if attestation_type not in {'ops', 'investor', 'reconciliation', 'legal'}:
            raise ValueError('attestation_type must be one of ops, investor, reconciliation, legal')
        if attestation_type == 'ops':
            case['ops_attested'] = True
        elif attestation_type == 'investor':
            case['investor_attested'] = True
        elif attestation_type == 'reconciliation':
            case['reconciliation_cleared'] = True
        elif attestation_type == 'legal':
            case['legal_docs_finalized'] = True
        case['status'] = 'ready_for_authority'
        attestation = {
            'attestation_id': f'att_{uuid.uuid4().hex[:12]}',
            'case_id': case['case_id'],
            'treasury_transfer_id': case['treasury_transfer_id'],
            'investor_id': case['investor_id'],
            'attestation_type': attestation_type,
            'actor': actor,
            'note': str(payload.get('note') or ''),
            'attested_at': int(time.time()),
        }
        state.setdefault('attestations', []).insert(0, attestation)
        state['attestations'] = state['attestations'][:500]
        save_state(state)
        append_audit('exit_attested', attestation)
        return {'mission': 'QNT50010', 'status': case['status'], 'attestation': attestation, 'case': case, 'summary': self.summary()}

    def authorize_finalization(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        state = self._ensure_synced(self._refresh())
        approver = str(payload.get('approver') or '').strip()
        if not approver:
            raise ValueError('approver is required')
        case = self._find_case(state, str(payload.get('case_id') or '').strip())
        transfer = self._find_completed_transfer(case.get('treasury_transfer_id'))
        policy = self._policy(state)
        ctx = self._source_context()
        reasons = []
        if policy.get('require_executed_transfer', True) and not transfer.get('executed_at'):
            reasons.append('treasury transfer is not executed')
        if policy.get('require_release_authority', True) and not case.get('release_authority_id'):
            reasons.append('investor cash release authority is missing from exit case')
        if policy.get('require_dual_attestation', True) and not (bool(case.get('ops_attested')) and bool(case.get('investor_attested'))):
            reasons.append('operations and investor attestation are required')
        if policy.get('require_reconciliation_clear', True) and not bool(case.get('reconciliation_cleared')):
            reasons.append('reconciliation clearance attestation is required')
        if int(ctx.get('settlement_break_count') or 0) > int(policy.get('max_unresolved_settlement_breaks') or 0):
            reasons.append('unresolved settlement breaks block exit finalization authority')
        tolerance = self._round(policy.get('amount_tolerance'), 2)
        if policy.get('require_cash_paid_match', True) and abs(self._round(case.get('gross_redemption_amount') - case.get('expected_total_amount'), 2)) > tolerance:
            reasons.append('cash plus in-kind amount does not match gross redemption amount within tolerance')
        if not policy.get('allow_in_kind_component', True) and self._round(case.get('in_kind_amount'), 2) > 0:
            reasons.append('in-kind redemption component is disabled by policy')
        if case.get('in_kind_amount', 0.0) > 0 and not bool(case.get('legal_docs_finalized')):
            reasons.append('legal attestation is required for in-kind redemption delivery')
        expires_at = int(time.time()) + int(policy.get('exit_authority_ttl_seconds') or 172800)
        if reasons:
            case['status'] = 'blocked'
            case['blocked_reasons'] = reasons
            blocked = {
                'case_id': case['case_id'],
                'treasury_transfer_id': case['treasury_transfer_id'],
                'investor_id': case['investor_id'],
                'gross_redemption_amount': case['gross_redemption_amount'],
                'blocked_at': int(time.time()),
                'blocked_by': approver,
                'reasons': reasons,
                'status': 'blocked',
            }
            state.setdefault('blocked_cases', []).insert(0, blocked)
            state['blocked_cases'] = state['blocked_cases'][:500]
            save_state(state)
            append_audit('exit_authority_blocked', blocked)
            return {'mission': 'QNT50010', 'status': 'blocked', 'case': case, 'reasons': reasons, 'summary': self.summary()}
        authority = {
            'exit_authority_id': f'iea_{uuid.uuid4().hex[:12]}',
            'case_id': case['case_id'],
            'treasury_transfer_id': case['treasury_transfer_id'],
            'investor_id': case['investor_id'],
            'investor_name': case['investor_name'],
            'gross_redemption_amount': case['gross_redemption_amount'],
            'cash_paid_amount': case['cash_paid_amount'],
            'in_kind_amount': case['in_kind_amount'],
            'currency': case['currency'],
            'authorized_at': int(time.time()),
            'authorized_by': approver,
            'expires_at': expires_at,
            'status': 'authorized',
            'statement_cycle_id': case.get('statement_cycle_id'),
            'capital_activity_id': case.get('capital_activity_id'),
        }
        case['status'] = 'authorized'
        case['exit_authority_id'] = authority['exit_authority_id']
        state.setdefault('authorized_exit_finalizations', []).insert(0, authority)
        state['authorized_exit_finalizations'] = state['authorized_exit_finalizations'][:500]
        save_state(state)
        append_audit('exit_authorized', authority)
        return {'mission': 'QNT50010', 'status': 'authorized', 'authority': authority, 'case': case, 'summary': self.summary()}

    def finalize(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        state = self._refresh()
        operator = str(payload.get('operator') or '').strip()
        if not operator:
            raise ValueError('operator is required')
        case = self._find_case(state, str(payload.get('case_id') or '').strip())
        authority = None
        now = int(time.time())
        for item in state.get('authorized_exit_finalizations', []):
            if item.get('case_id') == case.get('case_id') and item.get('status') == 'authorized':
                authority = item
                break
        if not authority:
            raise ValueError('exit finalization authority is required')
        if int(authority.get('expires_at') or 0) and int(authority.get('expires_at') or 0) < now:
            raise ValueError('exit finalization authority has expired')
        case['status'] = 'finalized'
        case['finalized_at'] = now
        case['finalized_by'] = operator
        finalization = {
            'exit_finalization_id': f'exf_{uuid.uuid4().hex[:12]}',
            'case_id': case['case_id'],
            'exit_authority_id': authority.get('exit_authority_id'),
            'treasury_transfer_id': case['treasury_transfer_id'],
            'investor_id': case['investor_id'],
            'gross_redemption_amount': case['gross_redemption_amount'],
            'cash_paid_amount': case['cash_paid_amount'],
            'in_kind_amount': case['in_kind_amount'],
            'currency': case['currency'],
            'finalized_at': now,
            'finalized_by': operator,
            'posture': 'closed',
            'notes': str(payload.get('notes') or ''),
        }
        state.setdefault('finalized_exits', []).insert(0, finalization)
        state['finalized_exits'] = state['finalized_exits'][:500]
        save_state(state)
        append_audit('exit_finalized', finalization)
        return {'mission': 'QNT50010', 'status': 'finalized', 'finalization': finalization, 'case': case, 'summary': self.summary()}

    def configure(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        state = self._refresh()
        policy = self._policy(state)
        for key in [
            'base_currency', 'require_executed_transfer', 'require_release_authority', 'require_dual_attestation',
            'require_reconciliation_clear', 'require_cash_paid_match', 'allow_in_kind_component', 'amount_tolerance',
            'max_unresolved_settlement_breaks', 'exit_authority_ttl_seconds', 'auto_sync_sources'
        ]:
            if payload.get(key) is not None:
                policy[key] = payload[key]
        state['policy'] = policy
        save_state(state)
        append_audit('exit_finalization_policy_configured', {'policy': policy})
        if payload.get('sync_after_configure', True):
            self.sync_context({'source': 'configure'})
        return self.summary()

    def summary(self) -> Dict[str, Any]:
        state = self._ensure_synced(self._refresh())
        ctx = self._source_context()
        registered = state.get('registered_cases', [])
        authorized = [item for item in state.get('authorized_exit_finalizations', []) if item.get('status') == 'authorized']
        blocked = [item for item in state.get('blocked_cases', []) if item.get('status') == 'blocked']
        finalized = state.get('finalized_exits', [])
        posture = 'ready'
        if blocked:
            posture = 'constrained'
        if (ctx.get('settlement_break_count') or 0) > 0:
            posture = 'blocked'
        elif registered and not finalized:
            posture = 'awaiting_exit_close'
        return {
            'mission': 'QNT50010',
            'status': 'ok',
            'posture': posture,
            'registered_case_count': len(registered),
            'authorized_case_count': len(authorized),
            'blocked_case_count': len(blocked),
            'finalized_exit_count': len(finalized),
            'attestation_count': len(state.get('attestations', [])),
            'treasury_completed_exit_count': len(ctx.get('treasury_completed_exits') or []),
            'treasury_pending_exit_count': len(ctx.get('treasury_pending_exits') or []),
            'settlement_break_count': int(ctx.get('settlement_break_count') or 0),
            'settlement_status': ctx.get('settlement_status'),
            'last_sync': state.get('last_sync'),
        }

    def reset(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        operator = str(payload.get('operator') or '').strip()
        if not operator:
            raise ValueError('operator is required')
        clear_audit = bool(payload.get('clear_audit', False))
        current = load_state()
        fresh = default_state()
        if not clear_audit:
            fresh['audit_log'] = current.get('audit_log', [])[:200]
        save_state(fresh)
        append_audit('exit_finalization_reset', {
            'operator': operator,
            'reason': str(payload.get('reason') or 'manual reset'),
            'clear_audit': clear_audit,
        })
        return self.summary()
