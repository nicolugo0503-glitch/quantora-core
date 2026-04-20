from __future__ import annotations

import time
import uuid
from typing import Any, Dict, Optional

from backend.app.regulatory_disclosure_delivery.state_store import load_state as load_disclosure_state
from backend.app.settlement_reconciliation.state_store import load_state as load_settlement_state
from backend.app.treasury_cash_mobility.state_store import load_state as load_treasury_state
from backend.app.intercompany_ledger.state_store import append_audit, load_state, save_state


class IntercompanyLedgerEngine:
    def __init__(self):
        self.state = load_state()

    def _refresh(self) -> Dict[str, Any]:
        self.state = load_state()
        return self.state

    @staticmethod
    def _round(value: Any, digits: int = 2) -> float:
        return round(float(value or 0.0), digits)

    def _policy(self, state: Dict[str, Any]) -> Dict[str, Any]:
        return dict(state.get('policy') or {})

    def _source_context(self) -> Dict[str, Any]:
        treasury = load_treasury_state()
        settlement = load_settlement_state()
        disclosure = load_disclosure_state()
        latest_transfer = (treasury.get('completed_transfers') or treasury.get('pending_transfers') or [{}])[0]
        latest_settlement = (settlement.get('settled_settlements') or settlement.get('pending_settlements') or [{}])[0]
        latest_ack = (disclosure.get('supervisory_acknowledgements') or [{}])[0]
        return {
            'treasury_available_to_move': self._round((treasury.get('last_sync') or {}).get('available_to_move', 0.0), 2),
            'treasury_cash_balance': self._round((treasury.get('last_sync') or {}).get('cash_balance', 0.0), 2),
            'treasury_transfer_count': len(treasury.get('completed_transfers') or []) + len(treasury.get('pending_transfers') or []),
            'latest_treasury_transfer_id': latest_transfer.get('transfer_id') or '',
            'latest_treasury_status': latest_transfer.get('status') or '',
            'settlement_pending_count': len(settlement.get('pending_settlements') or []),
            'settlement_break_count': len(settlement.get('reconciliation_breaks') or []),
            'latest_settlement_id': latest_settlement.get('settlement_id') or '',
            'latest_settlement_status': latest_settlement.get('status') or '',
            'supervisory_acknowledgement_count': len(disclosure.get('supervisory_acknowledgements') or []),
            'latest_acknowledgement_id': latest_ack.get('acknowledgement_id') or '',
            'latest_acknowledgement_outcome': latest_ack.get('outcome') or '',
        }

    def sync_context(self, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        payload = payload or {}
        state = self._refresh()
        snapshot = {
            'synced_at': int(time.time()),
            'source': str(payload.get('source') or 'manual'),
            **self._source_context(),
        }
        state['last_sync'] = snapshot
        state.setdefault('sync_history', []).insert(0, snapshot)
        state['sync_history'] = state['sync_history'][:500]
        save_state(state)
        append_audit('intercompany_context_synced', snapshot)
        return {'mission': 'QNT50018', 'status': 'synced', 'snapshot': snapshot}

    def _ensure_synced(self, state: Dict[str, Any]) -> Dict[str, Any]:
        if self._policy(state).get('auto_sync_sources', True) and not state.get('last_sync'):
            self.sync_context({'source': 'auto'})
            state = self._refresh()
        return state

    def summary(self) -> Dict[str, Any]:
        state = self._ensure_synced(self._refresh())
        flow_cases = state.get('flow_cases') or []
        posted = [r for r in flow_cases if r.get('status') in {'posted', 'settled'}]
        open_items = [r for r in flow_cases if r.get('status') not in {'settled', 'rejected'}]
        posture = 'ready'
        if any(r.get('status') == 'exception' for r in flow_cases):
            posture = 'exception'
        elif not flow_cases:
            posture = 'degraded'
        state['status'] = posture
        save_state(state)
        return {
            'mission': 'QNT50018',
            'posture': posture,
            'flow_case_count': len(flow_cases),
            'posted_case_count': len(posted),
            'settled_case_count': len([r for r in flow_cases if r.get('status') == 'settled']),
            'open_case_count': len(open_items),
            'journal_entry_count': len(state.get('journal_entries') or []),
            'settlement_count': len(state.get('settlements') or []),
            'latest_sync': state.get('last_sync'),
            'policy': state.get('policy'),
        }

    def configure(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        state = self._refresh()
        policy = self._policy(state)
        for key in [
            'base_currency', 'auto_sync_sources', 'require_approval', 'approval_threshold',
            'require_treasury_capacity', 'require_disclosure_acknowledgement', 'default_settlement_route',
            'retention_days'
        ]:
            if payload.get(key) is not None:
                policy[key] = payload[key]
        state['policy'] = policy
        save_state(state)
        append_audit('intercompany_policy_configured', {'policy': policy})
        if payload.get('sync_after_configure', True):
            self.sync_context({'source': 'configure'})
        return self.summary()

    def _find_case(self, state: Dict[str, Any], flow_case_id: str) -> Dict[str, Any]:
        for item in state.get('flow_cases', []):
            if item.get('flow_case_id') == flow_case_id:
                return item
        raise ValueError('flow_case_id not found')

    def register_flow(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        state = self._ensure_synced(self._refresh())
        policy = self._policy(state)
        operator = str(payload.get('operator') or '').strip()
        from_entity = str(payload.get('from_entity') or '').strip()
        to_entity = str(payload.get('to_entity') or '').strip()
        purpose = str(payload.get('purpose') or '').strip()
        amount = self._round(payload.get('amount'), 2)
        if not operator:
            raise ValueError('operator is required')
        if not from_entity or not to_entity:
            raise ValueError('from_entity and to_entity are required')
        if from_entity == to_entity:
            raise ValueError('from_entity and to_entity must be different')
        if amount <= 0:
            raise ValueError('amount must be positive')
        if not purpose:
            raise ValueError('purpose is required')
        if policy.get('require_treasury_capacity', True):
            available = self._round((state.get('last_sync') or {}).get('treasury_available_to_move', 0.0), 2)
            if available > 0 and amount > available:
                raise ValueError('amount exceeds treasury mobility capacity from QNT50008')
        if policy.get('require_disclosure_acknowledgement', False):
            count = int((state.get('last_sync') or {}).get('supervisory_acknowledgement_count') or 0)
            if count <= 0:
                raise ValueError('supervisory acknowledgement evidence is required by policy before intercompany flow registration')
        now = int(time.time())
        needs_approval = bool(policy.get('require_approval', True) or amount >= float(policy.get('approval_threshold') or 0.0))
        case = {
            'flow_case_id': f'icf_{uuid.uuid4().hex[:12]}',
            'created_at': now,
            'created_by': operator,
            'from_entity': from_entity,
            'to_entity': to_entity,
            'amount': amount,
            'currency': str(payload.get('currency') or policy.get('base_currency') or 'USD').upper(),
            'purpose': purpose,
            'flow_type': str(payload.get('flow_type') or 'capital_transfer'),
            'effective_date': str(payload.get('effective_date') or ''),
            'treasury_transfer_id': str(payload.get('treasury_transfer_id') or ''),
            'settlement_id': str(payload.get('settlement_id') or ''),
            'reference_id': str(payload.get('reference_id') or ''),
            'legal_entity_id': str(payload.get('legal_entity_id') or ''),
            'counterparty_entity_id': str(payload.get('counterparty_entity_id') or ''),
            'fund_id': str(payload.get('fund_id') or ''),
            'spv_id': str(payload.get('spv_id') or ''),
            'strategy_id': str(payload.get('strategy_id') or ''),
            'jurisdiction': str(payload.get('jurisdiction') or ''),
            'notes': str(payload.get('notes') or ''),
            'approval_required': needs_approval,
            'status': 'pending_approval' if needs_approval else 'approved',
            'retention_until': now + (int(policy.get('retention_days') or 2555) * 86400),
            'context_snapshot': dict(state.get('last_sync') or {}),
        }
        state.setdefault('flow_cases', []).insert(0, case)
        state['flow_cases'] = state['flow_cases'][:500]
        save_state(state)
        append_audit('intercompany_flow_registered', {
            'flow_case_id': case['flow_case_id'],
            'from_entity': from_entity,
            'to_entity': to_entity,
            'amount': amount,
        })
        return {'mission': 'QNT50018', 'status': case['status'], 'flow_case': case, 'summary': self.summary()}

    def approve_flow(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        state = self._ensure_synced(self._refresh())
        flow_case = self._find_case(state, str(payload.get('flow_case_id') or ''))
        approver = str(payload.get('approver') or '').strip()
        if not approver:
            raise ValueError('approver is required')
        flow_case['approved_by'] = approver
        flow_case['approved_at'] = int(time.time())
        flow_case['approval_memo'] = str(payload.get('approval_memo') or '')
        flow_case['status'] = 'approved'
        save_state(state)
        append_audit('intercompany_flow_approved', {'flow_case_id': flow_case['flow_case_id'], 'approver': approver})
        return {'mission': 'QNT50018', 'status': flow_case['status'], 'flow_case': flow_case}

    def post_flow(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        state = self._ensure_synced(self._refresh())
        flow_case = self._find_case(state, str(payload.get('flow_case_id') or ''))
        operator = str(payload.get('operator') or '').strip()
        if not operator:
            raise ValueError('operator is required')
        if flow_case.get('status') not in {'approved', 'posted'}:
            raise ValueError('flow must be approved before posting')
        if flow_case.get('journal_entry_id'):
            return {'mission': 'QNT50018', 'status': flow_case.get('status'), 'flow_case': flow_case, 'journal_entry': next((j for j in state.get('journal_entries', []) if j.get('journal_entry_id') == flow_case.get('journal_entry_id')), None)}
        debit_account = str(payload.get('debit_account') or 'due_from_affiliate')
        credit_account = str(payload.get('credit_account') or 'due_to_affiliate')
        entry = {
            'journal_entry_id': f'icj_{uuid.uuid4().hex[:12]}',
            'flow_case_id': flow_case['flow_case_id'],
            'posted_at': int(time.time()),
            'posted_by': operator,
            'currency': flow_case['currency'],
            'amount': flow_case['amount'],
            'debit': {
                'entity': flow_case['to_entity'],
                'account': debit_account,
                'amount': flow_case['amount'],
            },
            'credit': {
                'entity': flow_case['from_entity'],
                'account': credit_account,
                'amount': flow_case['amount'],
            },
            'memo': str(payload.get('posting_memo') or flow_case.get('purpose') or ''),
            'reference_id': flow_case.get('reference_id') or flow_case['flow_case_id'],
        }
        state.setdefault('journal_entries', []).insert(0, entry)
        state['journal_entries'] = state['journal_entries'][:1000]
        flow_case['journal_entry_id'] = entry['journal_entry_id']
        flow_case['posted_at'] = entry['posted_at']
        flow_case['status'] = 'posted'
        save_state(state)
        append_audit('intercompany_flow_posted', {'flow_case_id': flow_case['flow_case_id'], 'journal_entry_id': entry['journal_entry_id']})
        return {'mission': 'QNT50018', 'status': flow_case['status'], 'flow_case': flow_case, 'journal_entry': entry}

    def settle_flow(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        state = self._ensure_synced(self._refresh())
        flow_case = self._find_case(state, str(payload.get('flow_case_id') or ''))
        operator = str(payload.get('operator') or '').strip()
        if not operator:
            raise ValueError('operator is required')
        if flow_case.get('status') not in {'posted', 'settled'}:
            raise ValueError('flow must be posted before settlement')
        if flow_case.get('settlement_record_id'):
            return {'mission': 'QNT50018', 'status': flow_case.get('status'), 'flow_case': flow_case}
        settlement = {
            'settlement_record_id': f'ics_{uuid.uuid4().hex[:12]}',
            'flow_case_id': flow_case['flow_case_id'],
            'settled_at': int(time.time()),
            'settled_by': operator,
            'treasury_transfer_id': str(payload.get('treasury_transfer_id') or flow_case.get('treasury_transfer_id') or ''),
            'settlement_id': flow_case.get('settlement_id') or '',
            'settlement_route': str(payload.get('settlement_route') or self._policy(state).get('default_settlement_route') or 'internal_treasury_route'),
            'amount': flow_case['amount'],
            'currency': flow_case['currency'],
            'memo': str(payload.get('settlement_memo') or ''),
        }
        state.setdefault('settlements', []).insert(0, settlement)
        state['settlements'] = state['settlements'][:1000]
        flow_case['settlement_record_id'] = settlement['settlement_record_id']
        flow_case['settled_at'] = settlement['settled_at']
        flow_case['status'] = 'settled'
        save_state(state)
        append_audit('intercompany_flow_settled', {
            'flow_case_id': flow_case['flow_case_id'],
            'settlement_record_id': settlement['settlement_record_id'],
        })
        return {'mission': 'QNT50018', 'status': flow_case['status'], 'flow_case': flow_case, 'settlement': settlement, 'summary': self.summary()}

    def reset(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        operator = str(payload.get('operator') or '').strip()
        if not operator:
            raise ValueError('operator is required')
        current = load_state()
        save_state({
            'generated_by': 'QNT50018',
            'status': 'degraded',
            'policy': current.get('policy') or load_state().get('policy', {}),
            'last_sync': None,
            'sync_history': [],
            'flow_cases': [],
            'journal_entries': [],
            'settlements': [],
            'exceptions': [],
            'audit_log': [],
        })
        append_audit('intercompany_ledger_reset', {'operator': operator, 'reason': str(payload.get('reason') or 'manual reset')})
        return {'mission': 'QNT50018', 'status': 'reset', 'summary': self.summary()}
