from __future__ import annotations

import time
import uuid
from typing import Any, Dict, Optional

from backend.app.governance_binder_publication.state_store import load_state as load_governance_state
from backend.app.regulatory_disclosure_delivery.state_store import append_audit, load_state, save_state


class RegulatoryDisclosureDeliveryEngine:
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
        governance = load_governance_state()
        latest_publication = (governance.get('publication_cases') or [{}])[0]
        latest_binder = (governance.get('published_binders') or [{}])[0]
        latest_packet = (governance.get('retrieval_packets') or [{}])[0]
        return {
            'published_binder_count': len(governance.get('published_binders') or []),
            'publication_case_count': len(governance.get('publication_cases') or []),
            'retrieval_packet_count': len(governance.get('retrieval_packets') or []),
            'latest_published_binder_id': latest_binder.get('published_binder_id') or '',
            'latest_publication_case_id': latest_binder.get('publication_case_id') or latest_publication.get('publication_case_id') or '',
            'latest_official_release_id': latest_binder.get('official_release_id') or latest_publication.get('official_release_id') or '',
            'latest_books_release_id': latest_binder.get('books_release_id') or latest_publication.get('books_release_id') or '',
            'latest_period_close_id': latest_binder.get('period_close_id') or latest_publication.get('period_close_id') or '',
            'latest_period_id': latest_binder.get('period_id') or latest_publication.get('period_id') or '',
            'latest_retrieval_packet_id': latest_publication.get('retrieval_packet_id') or latest_packet.get('retrieval_packet_id') or '',
            'latest_distribution_total': self._round(latest_publication.get('distribution_total'), 2),
            'latest_investor_count': int(latest_publication.get('investor_count') or 0),
            'latest_binder_channel': latest_binder.get('binder_channel') or latest_publication.get('binder_channel') or 'governance_binder',
            'latest_regulator_channel': latest_binder.get('regulator_channel') or latest_packet.get('regulator_channel') or latest_publication.get('regulator_channel') or 'supervisory_retrieval_packet',
            'latest_published_at': latest_binder.get('published_at') or 0,
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
        append_audit('regulatory_disclosure_context_synced', snapshot)
        return {'mission': 'QNT50015', 'status': 'synced', 'snapshot': snapshot}

    def _ensure_synced(self, state: Dict[str, Any]) -> Dict[str, Any]:
        if self._policy(state).get('auto_sync_sources', True) and not state.get('last_sync'):
            self.sync_context({'source': 'auto'})
            state = self._refresh()
        return state

    def summary(self) -> Dict[str, Any]:
        state = self._ensure_synced(self._refresh())
        posture = 'clear' if state.get('supervisory_acknowledgements') else ('ready' if state.get('delivery_receipts') else 'degraded')
        state['status'] = posture
        save_state(state)
        return {
            'mission': 'QNT50015',
            'posture': posture,
            'delivery_case_count': len(state.get('delivery_cases') or []),
            'delivery_receipt_count': len(state.get('delivery_receipts') or []),
            'supervisory_acknowledgement_count': len(state.get('supervisory_acknowledgements') or []),
            'latest_sync': state.get('last_sync'),
            'policy': state.get('policy'),
        }

    def configure(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        state = self._refresh()
        policy = self._policy(state)
        for key in [
            'base_currency', 'require_published_binder', 'require_retrieval_packet',
            'require_supervisory_channel', 'require_delivery_receipt',
            'require_primary_acknowledgement_before_close', 'auto_sync_sources',
            'primary_supervisor', 'default_delivery_channel', 'retention_days'
        ]:
            if payload.get(key) is not None:
                policy[key] = payload[key]
        state['policy'] = policy
        save_state(state)
        append_audit('regulatory_disclosure_policy_configured', {'policy': policy})
        if payload.get('sync_after_configure', True):
            self.sync_context({'source': 'configure'})
        return self.summary()

    def _find_delivery_case(self, state: Dict[str, Any], delivery_case_id: str) -> Dict[str, Any]:
        for item in state.get('delivery_cases', []):
            if item.get('delivery_case_id') == delivery_case_id:
                return item
        raise ValueError('delivery_case_id not found')

    def register_delivery(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        state = self._ensure_synced(self._refresh())
        policy = self._policy(state)
        operator = str(payload.get('operator') or '').strip()
        published_binder_id = str(payload.get('published_binder_id') or '').strip()
        operations = str(payload.get('operations') or '').strip()
        compliance = str(payload.get('compliance') or '').strip()
        supervisor = str(payload.get('supervisor') or policy.get('primary_supervisor') or '').strip()
        if not operator:
            raise ValueError('operator is required')
        if not published_binder_id:
            raise ValueError('published_binder_id is required')
        if policy.get('require_supervisory_channel', True) and not supervisor:
            raise ValueError('supervisor is required by policy')

        governance = load_governance_state()
        published_binder = next((r for r in governance.get('published_binders', []) if r.get('published_binder_id') == published_binder_id), None)
        if not published_binder:
            raise ValueError('published_binder_id not found in QNT50014 state')
        publication_case = next((r for r in governance.get('publication_cases', []) if r.get('publication_case_id') == published_binder.get('publication_case_id')), None)
        if policy.get('require_published_binder', True) and published_binder.get('status') != 'published':
            raise ValueError('published governance binder is required before regulatory disclosure delivery registration')
        if policy.get('require_retrieval_packet', True) and not (publication_case or {}).get('retrieval_packet_id'):
            raise ValueError('retrieval packet evidence is required before regulatory disclosure delivery registration')
        if not operations:
            raise ValueError('operations is required')
        if not compliance:
            raise ValueError('compliance is required')

        now = int(time.time())
        retention_days = int(policy.get('retention_days') or 2555)
        case = {
            'delivery_case_id': f'rdd_{uuid.uuid4().hex[:12]}',
            'created_at': now,
            'created_by': operator,
            'published_binder_id': published_binder_id,
            'publication_case_id': published_binder.get('publication_case_id'),
            'official_release_id': published_binder.get('official_release_id'),
            'books_release_id': published_binder.get('books_release_id'),
            'period_close_id': published_binder.get('period_close_id'),
            'period_id': published_binder.get('period_id'),
            'retrieval_packet_id': (publication_case or {}).get('retrieval_packet_id', ''),
            'operations': operations,
            'compliance': compliance,
            'supervisor': supervisor,
            'delivery_channel': str(payload.get('delivery_channel') or policy.get('default_delivery_channel') or 'regulatory_disclosure_delivery'),
            'distribution_total': self._round((publication_case or {}).get('distribution_total'), 2),
            'investor_count': int((publication_case or {}).get('investor_count') or 0),
            'retention_until': now + (retention_days * 86400),
            'status': 'pending_delivery_receipt',
            'context_snapshot': dict(state.get('last_sync') or {}),
            'notes': str(payload.get('notes') or ''),
        }
        state.setdefault('delivery_cases', []).insert(0, case)
        state['delivery_cases'] = state['delivery_cases'][:250]
        save_state(state)
        append_audit('regulatory_disclosure_delivery_registered', {
            'delivery_case_id': case['delivery_case_id'],
            'published_binder_id': published_binder_id,
            'official_release_id': case['official_release_id'],
            'period_id': case['period_id'],
            'supervisor': supervisor,
        })
        return {'mission': 'QNT50015', 'status': case['status'], 'delivery_case': case, 'summary': self.summary()}

    def record_delivery_receipt(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        state = self._ensure_synced(self._refresh())
        delivery_case = self._find_delivery_case(state, str(payload.get('delivery_case_id') or ''))
        receiver = str(payload.get('receiver') or '').strip()
        if not receiver:
            raise ValueError('receiver is required')
        receipt = {
            'delivery_receipt_id': f'rdr_{uuid.uuid4().hex[:12]}',
            'delivery_case_id': delivery_case.get('delivery_case_id'),
            'published_binder_id': delivery_case.get('published_binder_id'),
            'retrieval_packet_id': delivery_case.get('retrieval_packet_id'),
            'receiver': receiver,
            'recorded_at': int(time.time()),
            'receipt_reference': str(payload.get('receipt_reference') or f"rcpt_{uuid.uuid4().hex[:10]}"),
            'delivery_channel': str(payload.get('delivery_channel') or delivery_case.get('delivery_channel') or ''),
            'status': 'delivered',
        }
        state.setdefault('delivery_receipts', []).insert(0, receipt)
        state['delivery_receipts'] = state['delivery_receipts'][:250]
        delivery_case['status'] = 'delivered_pending_acknowledgement'
        delivery_case['delivery_receipt_id'] = receipt['delivery_receipt_id']
        delivery_case['delivery_receipt_recorded_at'] = receipt['recorded_at']
        save_state(state)
        append_audit('regulatory_disclosure_delivery_receipt_recorded', receipt)
        return {'mission': 'QNT50015', 'status': delivery_case['status'], 'delivery_receipt': receipt, 'delivery_case': delivery_case}

    def record_acknowledgement(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        state = self._ensure_synced(self._refresh())
        policy = self._policy(state)
        delivery_case = self._find_delivery_case(state, str(payload.get('delivery_case_id') or ''))
        acknowledger = str(payload.get('acknowledger') or '').strip()
        outcome = str(payload.get('outcome') or 'accepted').strip()
        if not acknowledger:
            raise ValueError('acknowledger is required')
        if policy.get('require_delivery_receipt', True) and not delivery_case.get('delivery_receipt_id'):
            raise ValueError('delivery receipt is required before supervisory acknowledgement')
        record = {
            'acknowledgement_id': f'rsa_{uuid.uuid4().hex[:12]}',
            'delivery_case_id': delivery_case.get('delivery_case_id'),
            'published_binder_id': delivery_case.get('published_binder_id'),
            'delivery_receipt_id': delivery_case.get('delivery_receipt_id', ''),
            'acknowledger': acknowledger,
            'supervisor': delivery_case.get('supervisor'),
            'acknowledged_at': int(time.time()),
            'outcome': outcome,
            'reference': str(payload.get('reference') or f"ack_{uuid.uuid4().hex[:10]}"),
            'notes': str(payload.get('notes') or ''),
            'status': 'acknowledged' if outcome in {'accepted', 'acknowledged', 'received'} else 'exception',
        }
        state.setdefault('supervisory_acknowledgements', []).insert(0, record)
        state['supervisory_acknowledgements'] = state['supervisory_acknowledgements'][:250]
        delivery_case['status'] = 'acknowledged' if record['status'] == 'acknowledged' else 'exception'
        delivery_case['acknowledgement_id'] = record['acknowledgement_id']
        delivery_case['acknowledged_at'] = record['acknowledged_at']
        delivery_case['acknowledgement_outcome'] = outcome
        if record['status'] == 'exception':
            state.setdefault('exceptions', []).insert(0, {
                'delivery_case_id': delivery_case.get('delivery_case_id'),
                'acknowledgement_id': record['acknowledgement_id'],
                'outcome': outcome,
                'noted_at': record['acknowledged_at'],
            })
            state['exceptions'] = state['exceptions'][:250]
        save_state(state)
        append_audit('supervisory_acknowledgement_recorded', record)
        return {'mission': 'QNT50015', 'status': delivery_case['status'], 'acknowledgement': record, 'summary': self.summary()}

    def reset(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        operator = str(payload.get('operator') or '').strip()
        if not operator:
            raise ValueError('operator is required')
        current = load_state()
        save_state({
            'generated_by': 'QNT50015',
            'status': 'degraded',
            'policy': current.get('policy') or load_state().get('policy', {}),
            'last_sync': None,
            'sync_history': [],
            'delivery_cases': [],
            'delivery_receipts': [],
            'supervisory_acknowledgements': [],
            'exceptions': [],
            'audit_log': [],
        })
        append_audit('regulatory_disclosure_delivery_reset', {'operator': operator, 'reason': str(payload.get('reason') or 'manual reset')})
        return {'mission': 'QNT50015', 'status': 'reset', 'summary': self.summary()}
