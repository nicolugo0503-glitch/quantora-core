from __future__ import annotations

import time
import uuid
from typing import Any, Dict, Optional

from backend.app.official_books_archive_certification.state_store import append_audit, load_state, save_state
from backend.app.period_close_distribution_ledger.state_store import load_state as load_period_close_state
from backend.app.settlement_reconciliation.state_store import load_state as load_settlement_state
from backend.app.investor_distribution_payables.state_store import load_state as load_distribution_state


class OfficialBooksArchiveCertificationEngine:
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
        period_close = load_period_close_state()
        settlement = load_settlement_state()
        distributions = load_distribution_state()
        closed_periods = period_close.get('closed_periods') or []
        latest_closed = closed_periods[0] if closed_periods else {}
        return {
            'closed_period_count': len(closed_periods),
            'latest_closed_period_id': latest_closed.get('period_close_id') or '',
            'latest_period_id': latest_closed.get('period_id') or '',
            'latest_closed_at': latest_closed.get('closed_at'),
            'latest_distribution_total': self._round(latest_closed.get('distribution_total'), 2),
            'latest_notice_count': int(latest_closed.get('notice_count') or 0),
            'open_settlement_break_count': len(settlement.get('reconciliation_breaks') or []),
            'settlement_status': (settlement.get('last_reconciliation') or {}).get('status') or 'unreconciled',
            'executed_payable_count': len(distributions.get('executed_payables') or []),
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
        append_audit('official_books_context_synced', snapshot)
        return {'mission': 'QNT50013', 'status': 'synced', 'snapshot': snapshot}

    def _ensure_synced(self, state: Dict[str, Any]) -> Dict[str, Any]:
        if self._policy(state).get('auto_sync_sources', True) and not state.get('last_sync'):
            self.sync_context({'source': 'auto'})
            state = self._refresh()
        return state

    def summary(self) -> Dict[str, Any]:
        state = self._ensure_synced(self._refresh())
        releases = state.get('books_releases', [])
        archives = state.get('archive_certifications', [])
        official = state.get('official_releases', [])
        posture = 'clear' if official else ('ready' if archives else 'degraded')
        state['status'] = posture
        save_state(state)
        return {
            'mission': 'QNT50013',
            'posture': posture,
            'books_release_count': len(releases),
            'archive_certification_count': len(archives),
            'official_release_count': len(official),
            'latest_sync': state.get('last_sync'),
            'policy': state.get('policy'),
        }

    def configure(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        state = self._refresh()
        policy = self._policy(state)
        for key in [
            'base_currency', 'require_closed_period', 'require_notice_finalization',
            'require_archive_certification', 'require_zero_open_breaks',
            'require_controller_signoff', 'require_operations_signoff',
            'retain_release_payload_days', 'archive_channel', 'auto_sync_sources'
        ]:
            if payload.get(key) is not None:
                policy[key] = payload[key]
        state['policy'] = policy
        save_state(state)
        append_audit('official_books_policy_configured', {'policy': policy})
        if payload.get('sync_after_configure', True):
            self.sync_context({'source': 'configure'})
        return self.summary()

    def _find_release(self, state: Dict[str, Any], books_release_id: str) -> Dict[str, Any]:
        for item in state.get('books_releases', []):
            if item.get('books_release_id') == books_release_id:
                return item
        raise ValueError('books_release_id not found')

    def register_release(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        state = self._ensure_synced(self._refresh())
        operator = str(payload.get('operator') or '').strip()
        period_close_id = str(payload.get('period_close_id') or '').strip()
        controller = str(payload.get('controller') or '').strip()
        operations = str(payload.get('operations') or '').strip()
        if not operator:
            raise ValueError('operator is required')
        if not period_close_id:
            raise ValueError('period_close_id is required')
        period_state = load_period_close_state()
        period_close = next((p for p in period_state.get('period_closes', []) if p.get('period_close_id') == period_close_id), None)
        if not period_close:
            raise ValueError('period_close_id not found in QNT50012 state')
        policy = self._policy(state)
        if policy.get('require_closed_period', True) and period_close.get('status') != 'closed':
            raise ValueError('period must be closed before official books release can be registered')
        if policy.get('require_notice_finalization', True):
            notices = period_close.get('investor_notices', [])
            if any(n.get('status') != 'notice_finalized' for n in notices):
                raise ValueError('all investor notices must be finalized before official books release can be registered')
        if policy.get('require_zero_open_breaks', True):
            open_breaks = int((state.get('last_sync') or {}).get('open_settlement_break_count') or 0)
            if open_breaks > 0:
                raise ValueError('open settlement breaks block official books release registration')
        if policy.get('require_controller_signoff', True) and not controller:
            raise ValueError('controller is required by policy')
        if policy.get('require_operations_signoff', True) and not operations:
            raise ValueError('operations is required by policy')
        ttl_days = int(policy.get('retain_release_payload_days') or 2555)
        now = int(time.time())
        record = {
            'books_release_id': f'obr_{uuid.uuid4().hex[:12]}',
            'created_at': now,
            'created_by': operator,
            'period_close_id': period_close_id,
            'period_id': period_close.get('period_id') or '',
            'statement_cycle_id': period_close.get('statement_cycle_id') or '',
            'controller': controller,
            'operations': operations,
            'distribution_total': self._round(period_close.get('distribution_total'), 2),
            'investor_count': int(period_close.get('investor_count') or 0),
            'notice_count': len(period_close.get('investor_notices') or []),
            'archive_channel': policy.get('archive_channel') or 'governance_binder',
            'retention_until': now + (ttl_days * 86400),
            'status': 'pending_archive_certification',
            'context_snapshot': dict(state.get('last_sync') or {}),
            'notes': str(payload.get('notes') or ''),
        }
        state.setdefault('books_releases', []).insert(0, record)
        state['books_releases'] = state['books_releases'][:250]
        save_state(state)
        append_audit('official_books_release_registered', {
            'books_release_id': record['books_release_id'],
            'period_close_id': period_close_id,
            'period_id': record['period_id'],
            'distribution_total': record['distribution_total'],
            'investor_count': record['investor_count'],
        })
        return {'mission': 'QNT50013', 'status': record['status'], 'books_release': record, 'summary': self.summary()}

    def certify_archive(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        state = self._ensure_synced(self._refresh())
        books_release = self._find_release(state, str(payload.get('books_release_id') or ''))
        certifier = str(payload.get('certifier') or '').strip()
        if not certifier:
            raise ValueError('certifier is required')
        finalized_at = int(time.time())
        record = {
            'archive_certification_id': f'arc_{uuid.uuid4().hex[:12]}',
            'books_release_id': books_release.get('books_release_id'),
            'period_close_id': books_release.get('period_close_id'),
            'period_id': books_release.get('period_id'),
            'certifier': certifier,
            'archive_channel': books_release.get('archive_channel'),
            'finalized_at': finalized_at,
            'artifact_count': int(payload.get('artifact_count') or books_release.get('notice_count') or 0),
            'checksum_manifest_id': str(payload.get('checksum_manifest_id') or f"chk_{uuid.uuid4().hex[:10]}"),
            'status': 'certified',
        }
        state.setdefault('archive_certifications', []).insert(0, record)
        state['archive_certifications'] = state['archive_certifications'][:250]
        books_release['status'] = 'ready_for_official_release'
        books_release['archive_certified_at'] = finalized_at
        books_release['archive_certified_by'] = certifier
        save_state(state)
        append_audit('distribution_archive_certified', record)
        return {'mission': 'QNT50013', 'status': books_release['status'], 'archive_certification': record, 'books_release': books_release}

    def release_official_books(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        state = self._ensure_synced(self._refresh())
        books_release = self._find_release(state, str(payload.get('books_release_id') or ''))
        approver = str(payload.get('approver') or '').strip()
        if not approver:
            raise ValueError('approver is required')
        if self._policy(state).get('require_archive_certification', True) and books_release.get('status') != 'ready_for_official_release':
            raise ValueError('archive certification is required before official books release')
        finalized_at = int(time.time())
        record = {
            'official_release_id': f'ofr_{uuid.uuid4().hex[:12]}',
            'books_release_id': books_release.get('books_release_id'),
            'period_close_id': books_release.get('period_close_id'),
            'period_id': books_release.get('period_id'),
            'approver': approver,
            'released_at': finalized_at,
            'distribution_total': books_release.get('distribution_total'),
            'investor_count': books_release.get('investor_count'),
            'archive_channel': books_release.get('archive_channel'),
            'retention_until': books_release.get('retention_until'),
            'status': 'released',
        }
        state.setdefault('official_releases', []).insert(0, record)
        state['official_releases'] = state['official_releases'][:250]
        books_release['status'] = 'released'
        books_release['released_at'] = finalized_at
        books_release['released_by'] = approver
        save_state(state)
        append_audit('official_books_released', record)
        return {'mission': 'QNT50013', 'status': 'released', 'official_release': record, 'summary': self.summary()}

    def reset(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        operator = str(payload.get('operator') or '').strip()
        if not operator:
            raise ValueError('operator is required')
        save_state(load_state() | {
            'generated_by': 'QNT50013',
            'status': 'degraded',
            'policy': load_state().get('policy') or load_state().get('policy', {}),
            'last_sync': None,
            'sync_history': [],
            'books_releases': [],
            'archive_certifications': [],
            'official_releases': [],
            'exceptions': [],
            'audit_log': [],
        })
        append_audit('official_books_reset', {'operator': operator, 'reason': str(payload.get('reason') or 'manual reset')})
        return {'mission': 'QNT50013', 'status': 'reset', 'summary': self.summary()}
