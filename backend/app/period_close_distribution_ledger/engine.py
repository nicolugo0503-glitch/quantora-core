from __future__ import annotations

import time
import uuid
from typing import Any, Dict, List, Optional

from backend.app.investor_distribution_payables.state_store import load_state as load_distribution_state
from backend.app.investor_exit_finalization.state_store import load_state as load_exit_state
from backend.app.period_close_distribution_ledger.state_store import append_audit, load_state, save_state
from backend.app.performance_engine.state_store import load_state as load_performance_state
from backend.app.settlement_reconciliation.state_store import load_state as load_settlement_state


class PeriodCloseDistributionLedgerEngine:
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
        distributions = load_distribution_state()
        performance = load_performance_state()
        settlement = load_settlement_state()
        exits = load_exit_state()
        metrics = performance.get('metrics') or {}
        investor_metrics = performance.get('investor_metrics') or {}
        return {
            'executed_payable_count': len(distributions.get('executed_payables') or []),
            'authorized_payable_release_count': len(distributions.get('authorized_payable_releases') or []),
            'distribution_batch_count': len(distributions.get('distribution_batches') or []),
            'settlement_break_count': len(settlement.get('reconciliation_breaks') or []),
            'settlement_status': (settlement.get('last_reconciliation') or {}).get('status') or 'unreconciled',
            'latest_equity': self._round(investor_metrics.get('latest_equity'), 2),
            'nav_per_unit': self._round(investor_metrics.get('nav_per_unit'), 4),
            'performance_as_of_date': str(investor_metrics.get('as_of_date') or ''),
            'cumulative_return_pct': round(float(metrics.get('cumulative_return_pct') or 0.0), 6),
            'investor_exit_finalization_count': len(exits.get('finalized_cases') or []),
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
        append_audit('period_close_context_synced', snapshot)
        return {'mission': 'QNT50012', 'status': 'synced', 'snapshot': snapshot}

    def _ensure_synced(self, state: Dict[str, Any]) -> Dict[str, Any]:
        if self._policy(state).get('auto_sync_sources', True) and not state.get('last_sync'):
            self.sync_context({'source': 'auto'})
            state = self._refresh()
        return state

    def configure(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        state = self._refresh()
        policy = self._policy(state)
        for key in [
            'base_currency', 'require_executed_payables', 'require_notice_finalization',
            'require_zero_open_breaks', 'require_period_attestation', 'notice_delivery_channel',
            'notice_ttl_seconds', 'auto_sync_sources'
        ]:
            if payload.get(key) is not None:
                policy[key] = payload[key]
        state['policy'] = policy
        save_state(state)
        append_audit('period_close_policy_configured', {'policy': policy})
        if payload.get('sync_after_configure', True):
            self.sync_context({'source': 'configure'})
        return self.summary()

    def _find_period_close(self, state: Dict[str, Any], period_close_id: str) -> Dict[str, Any]:
        for item in state.get('period_closes', []):
            if item.get('period_close_id') == period_close_id:
                return item
        raise ValueError('period_close_id not found')

    def _executed_payables_for_period(self, period_id: str) -> List[Dict[str, Any]]:
        distributions = load_distribution_state()
        period_id = str(period_id or '').strip()
        matched: List[Dict[str, Any]] = []
        batches = {b.get('batch_id'): b for b in distributions.get('distribution_batches', [])}
        for item in distributions.get('executed_payables', []):
            batch = batches.get(item.get('batch_id')) or {}
            batch_period_id = str(batch.get('period_id') or '')
            if period_id and batch_period_id != period_id:
                continue
            matched.append({
                'batch_id': item.get('batch_id'),
                'investor_id': item.get('investor_id'),
                'investor_name': item.get('investor_name') or item.get('investor_id'),
                'amount': self._round(item.get('amount'), 2),
                'currency': item.get('currency') or batch.get('currency') or 'USD',
                'executed_at': item.get('executed_at'),
                'treasury_transfer_id': item.get('treasury_transfer_id'),
                'period_id': batch_period_id,
                'statement_cycle_id': batch.get('statement_cycle_id') or '',
                'distribution_type': batch.get('distribution_type') or 'profit_distribution',
                'source_nav_date': batch.get('source_nav_date') or '',
            })
        return matched

    def register_close(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        state = self._ensure_synced(self._refresh())
        operator = str(payload.get('operator') or '').strip()
        period_id = str(payload.get('period_id') or '').strip()
        if not operator:
            raise ValueError('operator is required')
        if not period_id:
            raise ValueError('period_id is required')
        lines = self._executed_payables_for_period(period_id)
        if self._policy(state).get('require_executed_payables', True) and not lines:
            raise ValueError('no executed payables found for period_id')
        ctx = self._source_context()
        totals_by_investor: Dict[str, float] = {}
        notices: List[Dict[str, Any]] = []
        ledger_lines: List[Dict[str, Any]] = []
        for item in lines:
            investor_id = str(item.get('investor_id') or '')
            totals_by_investor[investor_id] = self._round(totals_by_investor.get(investor_id, 0.0) + float(item.get('amount') or 0.0), 2)
            ledger_lines.append({
                'ledger_line_id': f'pcl_{uuid.uuid4().hex[:12]}',
                **item,
                'status': 'pending_ledger_finalization',
            })
        for investor_id, total_amount in totals_by_investor.items():
            sample = next((x for x in lines if x.get('investor_id') == investor_id), {})
            notices.append({
                'notice_id': f'ntc_{uuid.uuid4().hex[:12]}',
                'investor_id': investor_id,
                'investor_name': sample.get('investor_name') or investor_id,
                'period_id': period_id,
                'statement_cycle_id': sample.get('statement_cycle_id') or str(payload.get('statement_cycle_id') or ''),
                'currency': sample.get('currency') or 'USD',
                'total_distribution_amount': self._round(total_amount, 2),
                'delivery_channel': self._policy(state).get('notice_delivery_channel') or 'secure_inbox',
                'status': 'pending_notice_finalization',
                'finalized_at': None,
                'expires_at': None,
            })
        period_close = {
            'period_close_id': f'pcd_{uuid.uuid4().hex[:12]}',
            'created_at': int(time.time()),
            'created_by': operator,
            'period_id': period_id,
            'statement_cycle_id': str(payload.get('statement_cycle_id') or ''),
            'close_date': str(payload.get('close_date') or ''),
            'notes': str(payload.get('notes') or ''),
            'ledger_lines': ledger_lines,
            'investor_notices': notices,
            'distribution_total': self._round(sum(float(x.get('amount') or 0.0) for x in lines), 2),
            'investor_count': len(notices),
            'ops_attested': bool(payload.get('ops_attested', False)),
            'finance_attested': bool(payload.get('finance_attested', False)),
            'status': 'pending_ledger_finalization',
            'context_snapshot': ctx,
        }
        state.setdefault('period_closes', []).insert(0, period_close)
        state['period_closes'] = state['period_closes'][:250]
        save_state(state)
        append_audit('period_close_registered', {
            'period_close_id': period_close['period_close_id'],
            'period_id': period_id,
            'distribution_total': period_close['distribution_total'],
            'investor_count': period_close['investor_count'],
        })
        return {'mission': 'QNT50012', 'status': period_close['status'], 'period_close': period_close, 'summary': self.summary()}

    def finalize_ledger(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        state = self._ensure_synced(self._refresh())
        period_close = self._find_period_close(state, str(payload.get('period_close_id') or ''))
        approver = str(payload.get('approver') or '').strip()
        if not approver:
            raise ValueError('approver is required')
        if self._policy(state).get('require_zero_open_breaks', True):
            breaks = int((state.get('last_sync') or {}).get('settlement_break_count') or 0)
            if breaks > 0:
                raise ValueError('open settlement breaks block ledger finalization')
        if self._policy(state).get('require_period_attestation', True) and not (period_close.get('ops_attested') and period_close.get('finance_attested')):
            raise ValueError('ops_attested and finance_attested are required before ledger finalization')
        finalized_at = int(time.time())
        for line in period_close.get('ledger_lines', []):
            line['status'] = 'ledger_finalized'
            line['finalized_at'] = finalized_at
        period_close['status'] = 'pending_notice_finalization'
        record = {
            'ledger_finalization_id': f'lgf_{uuid.uuid4().hex[:12]}',
            'period_close_id': period_close.get('period_close_id'),
            'period_id': period_close.get('period_id'),
            'approved_by': approver,
            'finalized_at': finalized_at,
            'ledger_line_count': len(period_close.get('ledger_lines', [])),
            'distribution_total': period_close.get('distribution_total'),
        }
        state.setdefault('ledger_finalizations', []).insert(0, record)
        state['ledger_finalizations'] = state['ledger_finalizations'][:250]
        save_state(state)
        append_audit('distribution_ledger_finalized', record)
        return {'mission': 'QNT50012', 'status': period_close['status'], 'ledger_finalization': record, 'period_close': period_close}

    def finalize_notice(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        state = self._ensure_synced(self._refresh())
        period_close = self._find_period_close(state, str(payload.get('period_close_id') or ''))
        operator = str(payload.get('operator') or '').strip()
        investor_id = str(payload.get('investor_id') or '').strip()
        if not operator:
            raise ValueError('operator is required')
        if not investor_id:
            raise ValueError('investor_id is required')
        if period_close.get('status') == 'pending_ledger_finalization':
            raise ValueError('ledger must be finalized before investor notices can be finalized')
        notice = next((n for n in period_close.get('investor_notices', []) if n.get('investor_id') == investor_id), None)
        if not notice:
            raise ValueError('investor notice not found for period_close_id')
        finalized_at = int(time.time())
        ttl = int(self._policy(state).get('notice_ttl_seconds') or 604800)
        notice['status'] = 'notice_finalized'
        notice['finalized_at'] = finalized_at
        notice['expires_at'] = finalized_at + ttl
        notice['finalized_by'] = operator
        record = {
            'notice_finalization_id': f'nff_{uuid.uuid4().hex[:12]}',
            'period_close_id': period_close.get('period_close_id'),
            'period_id': period_close.get('period_id'),
            'investor_id': investor_id,
            'investor_name': notice.get('investor_name') or investor_id,
            'operator': operator,
            'finalized_at': finalized_at,
            'expires_at': finalized_at + ttl,
            'delivery_channel': notice.get('delivery_channel'),
            'amount': notice.get('total_distribution_amount'),
        }
        state.setdefault('notice_finalizations', []).insert(0, record)
        state['notice_finalizations'] = state['notice_finalizations'][:1000]
        if all(n.get('status') == 'notice_finalized' for n in period_close.get('investor_notices', [])):
            period_close['status'] = 'ready_for_period_close'
        save_state(state)
        append_audit('investor_notice_finalized', record)
        return {'mission': 'QNT50012', 'status': period_close['status'], 'notice_finalization': record, 'period_close': period_close}

    def close_period(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        state = self._ensure_synced(self._refresh())
        period_close = self._find_period_close(state, str(payload.get('period_close_id') or ''))
        approver = str(payload.get('approver') or '').strip()
        if not approver:
            raise ValueError('approver is required')
        if period_close.get('status') == 'pending_ledger_finalization':
            raise ValueError('ledger finalization is incomplete')
        if self._policy(state).get('require_notice_finalization', True):
            pending = [n for n in period_close.get('investor_notices', []) if n.get('status') != 'notice_finalized']
            if pending:
                raise ValueError('all investor notices must be finalized before period close')
        closed_at = int(time.time())
        period_close['status'] = 'closed'
        period_close['closed_at'] = closed_at
        period_close['closed_by'] = approver
        record = {
            'period_close_id': period_close.get('period_close_id'),
            'period_id': period_close.get('period_id'),
            'closed_by': approver,
            'closed_at': closed_at,
            'distribution_total': period_close.get('distribution_total'),
            'investor_count': period_close.get('investor_count'),
            'notice_count': len(period_close.get('investor_notices', [])),
        }
        state.setdefault('closed_periods', []).insert(0, record)
        state['closed_periods'] = state['closed_periods'][:250]
        save_state(state)
        append_audit('distribution_period_closed', record)
        return {'mission': 'QNT50012', 'status': 'closed', 'closed_period': record, 'summary': self.summary()}

    def reset(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        operator = str(payload.get('operator') or '').strip()
        if not operator:
            raise ValueError('operator is required')
        reason = str(payload.get('reason') or 'manual reset')
        from backend.app.period_close_distribution_ledger.state_store import default_state
        state = default_state()
        save_state(state)
        append_audit('period_close_reset', {'operator': operator, 'reason': reason})
        return {'mission': 'QNT50012', 'status': 'reset', 'summary': self.summary()}

    def summary(self) -> Dict[str, Any]:
        state = self._ensure_synced(self._refresh())
        open_periods = [p for p in state.get('period_closes', []) if p.get('status') != 'closed']
        notices = state.get('notice_finalizations', [])
        return {
            'mission': 'QNT50012',
            'posture': state.get('status') or 'degraded',
            'period_close_count': len(state.get('period_closes', [])),
            'open_period_close_count': len(open_periods),
            'ledger_finalization_count': len(state.get('ledger_finalizations', [])),
            'notice_finalization_count': len(notices),
            'closed_period_count': len(state.get('closed_periods', [])),
            'last_sync': state.get('last_sync'),
        }
