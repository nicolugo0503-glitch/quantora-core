from __future__ import annotations

import time
import uuid
from typing import Any, Dict, Optional

from backend.app.governance_binder_publication.state_store import append_audit, load_state, save_state
from backend.app.official_books_archive_certification.state_store import load_state as load_official_books_state
from backend.app.period_close_distribution_ledger.state_store import load_state as load_period_close_state


class GovernanceBinderPublicationEngine:
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
        books = load_official_books_state()
        periods = load_period_close_state()
        latest_release = (books.get('official_releases') or [{}])[0]
        latest_archive = (books.get('archive_certifications') or [{}])[0]
        latest_closed = (periods.get('closed_periods') or [{}])[0]
        return {
            'official_release_count': len(books.get('official_releases') or []),
            'books_release_count': len(books.get('books_releases') or []),
            'archive_certification_count': len(books.get('archive_certifications') or []),
            'latest_official_release_id': latest_release.get('official_release_id') or '',
            'latest_books_release_id': latest_release.get('books_release_id') or '',
            'latest_period_close_id': latest_release.get('period_close_id') or latest_closed.get('period_close_id') or '',
            'latest_period_id': latest_release.get('period_id') or latest_closed.get('period_id') or '',
            'latest_distribution_total': self._round(latest_release.get('distribution_total') or latest_closed.get('distribution_total'), 2),
            'latest_investor_count': int(latest_release.get('investor_count') or latest_closed.get('investor_count') or 0),
            'latest_archive_channel': latest_archive.get('archive_channel') or 'governance_binder',
            'latest_released_at': latest_release.get('released_at') or 0,
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
        append_audit('governance_binder_context_synced', snapshot)
        return {'mission': 'QNT50014', 'status': 'synced', 'snapshot': snapshot}

    def _ensure_synced(self, state: Dict[str, Any]) -> Dict[str, Any]:
        if self._policy(state).get('auto_sync_sources', True) and not state.get('last_sync'):
            self.sync_context({'source': 'auto'})
            state = self._refresh()
        return state

    def summary(self) -> Dict[str, Any]:
        state = self._ensure_synced(self._refresh())
        posture = 'clear' if state.get('published_binders') else ('ready' if state.get('retrieval_packets') else 'degraded')
        state['status'] = posture
        save_state(state)
        return {
            'mission': 'QNT50014',
            'posture': posture,
            'publication_case_count': len(state.get('publication_cases') or []),
            'retrieval_packet_count': len(state.get('retrieval_packets') or []),
            'published_binder_count': len(state.get('published_binders') or []),
            'latest_sync': state.get('last_sync'),
            'policy': state.get('policy'),
        }

    def configure(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        state = self._refresh()
        policy = self._policy(state)
        for key in [
            'base_currency', 'require_official_books_release', 'require_archive_certification',
            'require_retrieval_packet_assembly', 'require_regulator_channel',
            'require_operations_attestation', 'require_compliance_attestation',
            'retain_packet_days', 'binder_channel', 'regulator_channel', 'auto_sync_sources'
        ]:
            if payload.get(key) is not None:
                policy[key] = payload[key]
        state['policy'] = policy
        save_state(state)
        append_audit('governance_binder_policy_configured', {'policy': policy})
        if payload.get('sync_after_configure', True):
            self.sync_context({'source': 'configure'})
        return self.summary()

    def _find_publication_case(self, state: Dict[str, Any], publication_case_id: str) -> Dict[str, Any]:
        for item in state.get('publication_cases', []):
            if item.get('publication_case_id') == publication_case_id:
                return item
        raise ValueError('publication_case_id not found')

    def register_publication(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        state = self._ensure_synced(self._refresh())
        policy = self._policy(state)
        operator = str(payload.get('operator') or '').strip()
        official_release_id = str(payload.get('official_release_id') or '').strip()
        operations = str(payload.get('operations') or '').strip()
        compliance = str(payload.get('compliance') or '').strip()
        if not operator:
            raise ValueError('operator is required')
        if not official_release_id:
            raise ValueError('official_release_id is required')
        books = load_official_books_state()
        official_release = next((r for r in books.get('official_releases', []) if r.get('official_release_id') == official_release_id), None)
        if not official_release:
            raise ValueError('official_release_id not found in QNT50013 state')
        related_books_release = next((r for r in books.get('books_releases', []) if r.get('books_release_id') == official_release.get('books_release_id')), None)
        if policy.get('require_official_books_release', True) and official_release.get('status') != 'released':
            raise ValueError('official books release must be released before governance binder publication can be registered')
        if policy.get('require_archive_certification', True) and (not related_books_release or not related_books_release.get('archive_certified_at')):
            raise ValueError('archive certification is required before governance binder publication registration')
        if policy.get('require_operations_attestation', True) and not operations:
            raise ValueError('operations is required by policy')
        if policy.get('require_compliance_attestation', True) and not compliance:
            raise ValueError('compliance is required by policy')
        now = int(time.time())
        retain_days = int(policy.get('retain_packet_days') or 2555)
        case = {
            'publication_case_id': f'gbp_{uuid.uuid4().hex[:12]}',
            'created_at': now,
            'created_by': operator,
            'official_release_id': official_release_id,
            'books_release_id': official_release.get('books_release_id'),
            'period_close_id': official_release.get('period_close_id'),
            'period_id': official_release.get('period_id'),
            'operations': operations,
            'compliance': compliance,
            'distribution_total': self._round(official_release.get('distribution_total'), 2),
            'investor_count': int(official_release.get('investor_count') or 0),
            'binder_channel': policy.get('binder_channel') or 'governance_binder',
            'regulator_channel': policy.get('regulator_channel') or 'supervisory_retrieval_packet',
            'retention_until': now + (retain_days * 86400),
            'status': 'pending_retrieval_packet',
            'context_snapshot': dict(state.get('last_sync') or {}),
            'notes': str(payload.get('notes') or ''),
        }
        state.setdefault('publication_cases', []).insert(0, case)
        state['publication_cases'] = state['publication_cases'][:250]
        save_state(state)
        append_audit('governance_binder_publication_registered', {
            'publication_case_id': case['publication_case_id'],
            'official_release_id': official_release_id,
            'period_id': case['period_id'],
            'distribution_total': case['distribution_total'],
            'investor_count': case['investor_count'],
        })
        return {'mission': 'QNT50014', 'status': case['status'], 'publication_case': case, 'summary': self.summary()}

    def assemble_retrieval_packet(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        state = self._ensure_synced(self._refresh())
        policy = self._policy(state)
        publication_case = self._find_publication_case(state, str(payload.get('publication_case_id') or ''))
        assembler = str(payload.get('assembler') or '').strip()
        if not assembler:
            raise ValueError('assembler is required')
        regulator_channel = str(payload.get('regulator_channel') or publication_case.get('regulator_channel') or '').strip()
        if policy.get('require_regulator_channel', True) and not regulator_channel:
            raise ValueError('regulator_channel is required by policy')
        record = {
            'retrieval_packet_id': f'grp_{uuid.uuid4().hex[:12]}',
            'publication_case_id': publication_case.get('publication_case_id'),
            'official_release_id': publication_case.get('official_release_id'),
            'books_release_id': publication_case.get('books_release_id'),
            'period_close_id': publication_case.get('period_close_id'),
            'period_id': publication_case.get('period_id'),
            'assembler': assembler,
            'regulator_channel': regulator_channel,
            'assembled_at': int(time.time()),
            'artifact_count': int(payload.get('artifact_count') or max(4, publication_case.get('investor_count') or 1)),
            'packet_manifest_id': str(payload.get('packet_manifest_id') or f"pkt_{uuid.uuid4().hex[:10]}"),
            'status': 'assembled',
        }
        state.setdefault('retrieval_packets', []).insert(0, record)
        state['retrieval_packets'] = state['retrieval_packets'][:250]
        publication_case['status'] = 'ready_for_publication'
        publication_case['retrieval_packet_id'] = record['retrieval_packet_id']
        publication_case['packet_manifest_id'] = record['packet_manifest_id']
        publication_case['retrieval_packet_assembled_at'] = record['assembled_at']
        save_state(state)
        append_audit('regulator_retrieval_packet_assembled', record)
        return {'mission': 'QNT50014', 'status': publication_case['status'], 'retrieval_packet': record, 'publication_case': publication_case}

    def publish_binder(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        state = self._ensure_synced(self._refresh())
        policy = self._policy(state)
        publication_case = self._find_publication_case(state, str(payload.get('publication_case_id') or ''))
        approver = str(payload.get('approver') or '').strip()
        if not approver:
            raise ValueError('approver is required')
        if policy.get('require_retrieval_packet_assembly', True) and publication_case.get('status') != 'ready_for_publication':
            raise ValueError('retrieval packet assembly is required before binder publication')
        record = {
            'published_binder_id': f'gbd_{uuid.uuid4().hex[:12]}',
            'publication_case_id': publication_case.get('publication_case_id'),
            'official_release_id': publication_case.get('official_release_id'),
            'books_release_id': publication_case.get('books_release_id'),
            'period_close_id': publication_case.get('period_close_id'),
            'period_id': publication_case.get('period_id'),
            'approver': approver,
            'published_at': int(time.time()),
            'binder_channel': publication_case.get('binder_channel'),
            'regulator_channel': publication_case.get('regulator_channel'),
            'retention_until': publication_case.get('retention_until'),
            'status': 'published',
        }
        state.setdefault('published_binders', []).insert(0, record)
        state['published_binders'] = state['published_binders'][:250]
        publication_case['status'] = 'published'
        publication_case['published_at'] = record['published_at']
        publication_case['published_by'] = approver
        save_state(state)
        append_audit('governance_binder_published', record)
        return {'mission': 'QNT50014', 'status': 'published', 'published_binder': record, 'summary': self.summary()}

    def reset(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        operator = str(payload.get('operator') or '').strip()
        if not operator:
            raise ValueError('operator is required')
        current = load_state()
        save_state({
            'generated_by': 'QNT50014',
            'status': 'degraded',
            'policy': current.get('policy') or load_state().get('policy', {}),
            'last_sync': None,
            'sync_history': [],
            'publication_cases': [],
            'retrieval_packets': [],
            'published_binders': [],
            'exceptions': [],
            'audit_log': [],
        })
        append_audit('governance_binder_reset', {'operator': operator, 'reason': str(payload.get('reason') or 'manual reset')})
        return {'mission': 'QNT50014', 'status': 'reset', 'summary': self.summary()}
