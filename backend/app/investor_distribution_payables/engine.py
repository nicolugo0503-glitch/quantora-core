from __future__ import annotations

import time
import uuid
from typing import Any, Dict, List, Optional

from backend.app.investor_cash_confirmation.state_store import load_state as load_investor_confirmation_state
from backend.app.investor_distribution_payables.state_store import append_audit, default_state, load_state, save_state
from backend.app.performance_engine.state_store import load_state as load_performance_state
from backend.app.settlement_reconciliation.state_store import load_state as load_settlement_state
from backend.app.treasury_cash_mobility.engine import TreasuryCashMobilityEngine
from backend.app.treasury_cash_mobility.state_store import load_state as load_treasury_state


class InvestorDistributionPayablesEngine:
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

    def _investor_registry(self) -> Dict[str, Any]:
        return dict((load_investor_confirmation_state().get('investors') or {}))

    def _performance_context(self) -> Dict[str, Any]:
        perf = load_performance_state()
        investor_metrics = perf.get('investor_metrics') or {}
        metrics = perf.get('metrics') or {}
        return {
            'latest_equity': self._round(investor_metrics.get('latest_equity'), 2),
            'nav_per_unit': self._round(investor_metrics.get('nav_per_unit'), 4),
            'as_of_date': str(investor_metrics.get('as_of_date') or ''),
            'cumulative_return_pct': round(float(metrics.get('cumulative_return_pct') or 0.0), 6),
            'mtd_return_pct': round(float(investor_metrics.get('mtd_return_pct') or 0.0), 6),
        }

    def _source_context(self) -> Dict[str, Any]:
        treasury_summary = self.treasury.summary()
        settlement = load_settlement_state()
        perf = self._performance_context()
        investors = self._investor_registry()
        treasury_state = load_treasury_state()
        return {
            'treasury_available_to_move': self._round(treasury_summary.get('available_to_move'), 2),
            'treasury_cash_balance': self._round(treasury_summary.get('cash_balance'), 2),
            'treasury_break_count': int(treasury_summary.get('break_count') or 0),
            'settlement_break_count': len(settlement.get('reconciliation_breaks') or []),
            'settlement_status': (settlement.get('last_reconciliation') or {}).get('status') or 'unreconciled',
            'latest_equity': perf.get('latest_equity'),
            'nav_per_unit': perf.get('nav_per_unit'),
            'performance_as_of_date': perf.get('as_of_date'),
            'cumulative_return_pct': perf.get('cumulative_return_pct'),
            'mtd_return_pct': perf.get('mtd_return_pct'),
            'registered_investor_count': len(investors),
            'pending_distribution_transfer_count': len([
                t for t in treasury_state.get('pending_transfers', [])
                if self._is_distribution_transfer(t)
            ]),
            'completed_distribution_transfer_count': len([
                t for t in treasury_state.get('completed_transfers', [])
                if self._is_distribution_transfer(t)
            ]),
        }

    @staticmethod
    def _is_distribution_transfer(transfer: Optional[Dict[str, Any]]) -> bool:
        transfer = transfer or {}
        transfer_type = str(transfer.get('transfer_type') or '').lower()
        destination = str(transfer.get('destination') or '').lower()
        return transfer_type in {'investor_distribution', 'distribution_payable', 'income_distribution'} or destination in {
            'investor_distribution', 'investor_distribution_bank', 'investor distribution bank'
        }

    def sync_context(self, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        payload = payload or {}
        state = self._refresh()
        ctx = self._source_context()
        snapshot = {
            'synced_at': int(time.time()),
            'source': str(payload.get('source') or 'manual'),
            **ctx,
        }
        state['last_sync'] = snapshot
        state.setdefault('sync_history', []).insert(0, snapshot)
        state['sync_history'] = state['sync_history'][:500]
        save_state(state)
        append_audit('distribution_context_synced', snapshot)
        return {'mission': 'QNT50011', 'status': 'synced', 'snapshot': snapshot}

    def _ensure_synced(self, state: Dict[str, Any]) -> Dict[str, Any]:
        if self._policy(state).get('auto_sync_sources', True) and not state.get('last_sync'):
            self.sync_context({'source': 'auto'})
            state = self._refresh()
        return state

    def configure(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        state = self._refresh()
        policy = self._policy(state)
        for key in [
            'base_currency', 'require_registered_investor', 'require_statement_cycle', 'require_dual_attestation',
            'require_treasury_capacity', 'require_batch_authority', 'require_transfer_approved',
            'require_positive_distributable_return', 'max_unresolved_breaks', 'max_distribution_pct_of_equity',
            'distribution_amount_tolerance', 'release_authority_ttl_seconds', 'auto_sync_sources'
        ]:
            if payload.get(key) is not None:
                policy[key] = payload[key]
        state['policy'] = policy
        save_state(state)
        append_audit('distribution_policy_configured', {'policy': policy})
        if payload.get('sync_after_configure', True):
            self.sync_context({'source': 'configure'})
        return self.summary()

    def _normalize_allocations(self, allocations: List[Dict[str, Any]], total_amount: float, currency: str, state: Dict[str, Any]) -> List[Dict[str, Any]]:
        registry = self._investor_registry()
        policy = self._policy(state)
        if not allocations:
            if not registry:
                raise ValueError('allocations are required when no investor registry exists')
            allocations = [{'investor_id': investor_id, 'weight': 1.0} for investor_id in registry.keys()]
        normalized: List[Dict[str, Any]] = []
        explicit_total = 0.0
        weight_total = 0.0
        weighted_indexes: List[int] = []
        equal_indexes: List[int] = []
        for row in allocations:
            investor_id = str((row or {}).get('investor_id') or '').strip()
            if not investor_id:
                raise ValueError('each allocation requires investor_id')
            investor = registry.get(investor_id)
            if policy.get('require_registered_investor', True) and not investor:
                raise ValueError(f'investor_id is not registered: {investor_id}')
            amount = row.get('amount')
            weight = row.get('weight')
            bank_destination = str((row or {}).get('bank_destination') or 'investor_distribution_bank')
            normalized.append({
                'line_id': f'dln_{uuid.uuid4().hex[:12]}',
                'investor_id': investor_id,
                'investor_name': str((row or {}).get('investor_name') or (investor or {}).get('investor_name') or investor_id),
                'amount': self._round(amount, 2) if amount is not None else None,
                'weight': float(weight) if weight is not None else None,
                'currency': currency,
                'bank_destination': bank_destination,
                'notes': str((row or {}).get('notes') or ''),
                'status': 'pending_attestation',
                'treasury_transfer_id': None,
                'payable_release_id': None,
            })
        for idx, row in enumerate(normalized):
            if row['amount'] is not None:
                explicit_total += float(row['amount'])
            elif row['weight'] is not None:
                weight_total += float(row['weight'])
                weighted_indexes.append(idx)
            else:
                equal_indexes.append(idx)
        explicit_total = self._round(explicit_total, 2)
        if explicit_total > total_amount:
            raise ValueError('explicit allocation amounts exceed total_amount')
        remainder = self._round(total_amount - explicit_total, 2)
        if remainder < 0:
            raise ValueError('invalid allocation remainder')
        if weighted_indexes:
            if weight_total <= 0:
                raise ValueError('allocation weights must be positive')
            for idx in weighted_indexes:
                share = remainder * (float(normalized[idx]['weight']) / weight_total)
                normalized[idx]['amount'] = self._round(share, 2)
        elif equal_indexes:
            split = remainder / max(len(equal_indexes), 1)
            for idx in equal_indexes:
                normalized[idx]['amount'] = self._round(split, 2)
        current_total = self._round(sum(float(row.get('amount') or 0.0) for row in normalized), 2)
        diff = self._round(total_amount - current_total, 2)
        if normalized and abs(diff) > 0:
            normalized[-1]['amount'] = self._round(float(normalized[-1].get('amount') or 0.0) + diff, 2)
        final_total = self._round(sum(float(row.get('amount') or 0.0) for row in normalized), 2)
        if abs(final_total - total_amount) > 0.01:
            raise ValueError('normalized waterfall does not reconcile to total_amount')
        for row in normalized:
            row['weight_pct'] = round((float(row.get('amount') or 0.0) / total_amount), 6) if total_amount > 0 else 0.0
        return normalized

    def _find_batch(self, state: Dict[str, Any], batch_id: str) -> Dict[str, Any]:
        for batch in state.get('distribution_batches', []):
            if batch.get('batch_id') == batch_id:
                return batch
        raise ValueError('batch_id not found')

    def _find_line(self, batch: Dict[str, Any], investor_id: str = '', line_id: str = '') -> Dict[str, Any]:
        for line in batch.get('lines', []):
            if line_id and line.get('line_id') == line_id:
                return line
            if investor_id and line.get('investor_id') == investor_id and not line.get('treasury_transfer_id'):
                return line
        raise ValueError('distribution line not found')

    def _find_transfer(self, transfer_id: str) -> Dict[str, Any]:
        transfer_id = str(transfer_id or '').strip()
        treasury_state = load_treasury_state()
        for bucket in ['pending_transfers', 'completed_transfers']:
            for item in treasury_state.get(bucket, []):
                if item.get('transfer_id') == transfer_id:
                    return item
        raise ValueError('treasury transfer_id not found')

    def register_batch(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        state = self._ensure_synced(self._refresh())
        operator = str(payload.get('operator') or '').strip()
        if not operator:
            raise ValueError('operator is required')
        total_amount = self._round(payload.get('total_amount'), 2)
        if total_amount <= 0:
            raise ValueError('total_amount must be positive')
        currency = str(payload.get('currency') or self._policy(state).get('base_currency') or 'USD').upper()
        lines = self._normalize_allocations(list(payload.get('allocations') or []), total_amount, currency, state)
        ctx = self._source_context()
        batch = {
            'batch_id': f'idb_{uuid.uuid4().hex[:12]}',
            'created_at': int(time.time()),
            'created_by': operator,
            'batch_name': str(payload.get('batch_name') or '').strip(),
            'distribution_type': str(payload.get('distribution_type') or 'profit_distribution').strip().lower(),
            'total_amount': total_amount,
            'currency': currency,
            'period_id': str(payload.get('period_id') or ''),
            'statement_cycle_id': str(payload.get('statement_cycle_id') or ''),
            'source_nav_date': str(payload.get('source_nav_date') or ctx.get('performance_as_of_date') or ''),
            'payable_basis': str(payload.get('payable_basis') or 'pro_rata').strip().lower(),
            'latest_equity_at_registration': self._round(ctx.get('latest_equity'), 2),
            'cumulative_return_pct_at_registration': float(ctx.get('cumulative_return_pct') or 0.0),
            'treasury_available_to_move_at_registration': self._round(ctx.get('treasury_available_to_move'), 2),
            'status': 'pending_attestation',
            'ops_attested': False,
            'finance_attested': False,
            'reporting_attested': False,
            'notes': str(payload.get('notes') or ''),
            'lines': lines,
        }
        state.setdefault('distribution_batches', []).insert(0, batch)
        state['distribution_batches'] = state['distribution_batches'][:500]
        save_state(state)
        append_audit('distribution_batch_registered', {
            'batch_id': batch['batch_id'],
            'batch_name': batch['batch_name'],
            'distribution_type': batch['distribution_type'],
            'total_amount': total_amount,
            'investor_count': len(lines),
        })
        return {'mission': 'QNT50011', 'status': batch['status'], 'batch': batch, 'summary': self.summary()}

    def attest(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        state = self._refresh()
        actor = str(payload.get('actor') or '').strip()
        if not actor:
            raise ValueError('actor is required')
        batch = self._find_batch(state, str(payload.get('batch_id') or '').strip())
        attestation_type = str(payload.get('attestation_type') or 'ops').strip().lower()
        if attestation_type not in {'ops', 'finance', 'reporting'}:
            raise ValueError('attestation_type must be one of ops, finance, reporting')
        if attestation_type == 'ops':
            batch['ops_attested'] = True
        elif attestation_type == 'finance':
            batch['finance_attested'] = True
        elif attestation_type == 'reporting':
            batch['reporting_attested'] = True
        batch['status'] = 'ready_for_authority'
        attestation = {
            'attestation_id': f'dat_{uuid.uuid4().hex[:12]}',
            'batch_id': batch['batch_id'],
            'attestation_type': attestation_type,
            'actor': actor,
            'note': str(payload.get('note') or ''),
            'attested_at': int(time.time()),
        }
        state.setdefault('attestations', []).insert(0, attestation)
        state['attestations'] = state['attestations'][:500]
        save_state(state)
        append_audit('distribution_batch_attested', attestation)
        return {'mission': 'QNT50011', 'status': batch['status'], 'batch': batch, 'attestation': attestation, 'summary': self.summary()}

    def authorize_batch(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        state = self._ensure_synced(self._refresh())
        approver = str(payload.get('approver') or '').strip()
        if not approver:
            raise ValueError('approver is required')
        batch = self._find_batch(state, str(payload.get('batch_id') or '').strip())
        policy = self._policy(state)
        ctx = self._source_context()
        reasons: List[str] = []
        if policy.get('require_statement_cycle', True) and not str(batch.get('statement_cycle_id') or '').strip():
            reasons.append('statement_cycle_id is required for investor distributions')
        if policy.get('require_dual_attestation', True) and not (bool(batch.get('ops_attested')) and bool(batch.get('finance_attested'))):
            reasons.append('operations and finance attestation are required')
        if policy.get('require_treasury_capacity', True) and self._round(ctx.get('treasury_available_to_move'), 2) < self._round(batch.get('total_amount'), 2):
            reasons.append('treasury mobility capacity is insufficient for the distribution batch')
        if int(ctx.get('settlement_break_count') or 0) > int(policy.get('max_unresolved_breaks') or 0):
            reasons.append('unresolved settlement or reconciliation breaks block payable authority')
        latest_equity = self._round(ctx.get('latest_equity'), 2)
        max_pct = float(policy.get('max_distribution_pct_of_equity') or 0.0)
        if latest_equity > 0 and max_pct > 0 and self._round(batch.get('total_amount'), 2) > self._round(latest_equity * max_pct, 2):
            reasons.append('distribution batch exceeds equity-based payout threshold')
        if policy.get('require_positive_distributable_return', False) and float(ctx.get('cumulative_return_pct') or 0.0) <= 0:
            reasons.append('positive distributable return is required by policy')
        expires_at = int(time.time()) + int(policy.get('release_authority_ttl_seconds') or 86400)
        if reasons:
            batch['status'] = 'blocked'
            batch['blocked_reasons'] = reasons
            blocked = {
                'batch_id': batch['batch_id'],
                'blocked_at': int(time.time()),
                'blocked_by': approver,
                'reasons': reasons,
                'total_amount': batch['total_amount'],
                'currency': batch['currency'],
                'status': 'blocked',
            }
            state.setdefault('blocked_batches', []).insert(0, blocked)
            state['blocked_batches'] = state['blocked_batches'][:500]
            save_state(state)
            append_audit('distribution_batch_blocked', blocked)
            return {'mission': 'QNT50011', 'status': 'blocked', 'batch': batch, 'reasons': reasons, 'summary': self.summary()}
        authority = {
            'batch_authority_id': f'dba_{uuid.uuid4().hex[:12]}',
            'batch_id': batch['batch_id'],
            'batch_name': batch['batch_name'],
            'distribution_type': batch['distribution_type'],
            'total_amount': batch['total_amount'],
            'currency': batch['currency'],
            'authorized_at': int(time.time()),
            'authorized_by': approver,
            'expires_at': expires_at,
            'status': 'authorized',
            'statement_cycle_id': batch.get('statement_cycle_id'),
            'period_id': batch.get('period_id'),
        }
        batch['status'] = 'authorized_batch'
        batch['batch_authority_id'] = authority['batch_authority_id']
        state.setdefault('authorized_batches', []).insert(0, authority)
        state['authorized_batches'] = state['authorized_batches'][:500]
        save_state(state)
        append_audit('distribution_batch_authorized', authority)
        return {'mission': 'QNT50011', 'status': 'authorized_batch', 'authority': authority, 'batch': batch, 'summary': self.summary()}

    def bind_transfer(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        state = self._refresh()
        operator = str(payload.get('operator') or '').strip()
        if not operator:
            raise ValueError('operator is required')
        batch = self._find_batch(state, str(payload.get('batch_id') or '').strip())
        transfer = self._find_transfer(str(payload.get('transfer_id') or '').strip())
        if not self._is_distribution_transfer(transfer):
            raise ValueError('transfer is not an investor distribution transfer')
        line = self._find_line(batch, investor_id=str(payload.get('investor_id') or '').strip(), line_id=str(payload.get('line_id') or '').strip())
        tolerance = self._round(self._policy(state).get('distribution_amount_tolerance'), 2)
        transfer_amount = self._round(transfer.get('amount'), 2)
        line_amount = self._round(line.get('amount'), 2)
        if abs(transfer_amount - line_amount) > tolerance:
            raise ValueError('treasury transfer amount does not match payable line within tolerance')
        transfer_investor_id = str(transfer.get('investor_id') or '').strip()
        if transfer_investor_id and transfer_investor_id != line.get('investor_id'):
            raise ValueError('treasury transfer investor_id does not match payable line')
        link = {
            'link_id': f'dlk_{uuid.uuid4().hex[:12]}',
            'batch_id': batch['batch_id'],
            'line_id': line['line_id'],
            'treasury_transfer_id': transfer['transfer_id'],
            'investor_id': line['investor_id'],
            'investor_name': line['investor_name'],
            'amount': line_amount,
            'currency': line['currency'],
            'linked_at': int(time.time()),
            'linked_by': operator,
            'status': 'linked',
            'note': str(payload.get('note') or ''),
        }
        line['treasury_transfer_id'] = transfer['transfer_id']
        line['status'] = 'linked'
        state.setdefault('transfer_links', []).insert(0, link)
        state['transfer_links'] = state['transfer_links'][:1000]
        save_state(state)
        append_audit('distribution_transfer_linked', link)
        return {'mission': 'QNT50011', 'status': 'linked', 'link': link, 'batch': batch, 'summary': self.summary()}

    def _find_link(self, state: Dict[str, Any], transfer_id: str) -> Dict[str, Any]:
        for item in state.get('transfer_links', []):
            if item.get('treasury_transfer_id') == transfer_id:
                return item
        raise ValueError('transfer link not found')

    def authorize_payable(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        state = self._ensure_synced(self._refresh())
        approver = str(payload.get('approver') or '').strip()
        if not approver:
            raise ValueError('approver is required')
        transfer_id = str(payload.get('transfer_id') or '').strip()
        link = self._find_link(state, transfer_id)
        batch = self._find_batch(state, link.get('batch_id'))
        line = self._find_line(batch, line_id=link.get('line_id'))
        transfer = self._find_transfer(transfer_id)
        policy = self._policy(state)
        reasons: List[str] = []
        if policy.get('require_batch_authority', True) and str(batch.get('status') or '') != 'authorized_batch':
            reasons.append('distribution batch authority is not active')
        if policy.get('require_transfer_approved', True) and str(transfer.get('status') or '').lower() != 'approved':
            reasons.append('treasury transfer is not approved')
        if self._round(transfer.get('amount'), 2) != self._round(line.get('amount'), 2):
            reasons.append('treasury transfer amount does not equal linked payable amount')
        if reasons:
            line['status'] = 'blocked'
            link['status'] = 'blocked'
            save_state(state)
            append_audit('distribution_payable_blocked', {
                'batch_id': batch['batch_id'],
                'treasury_transfer_id': transfer_id,
                'reasons': reasons,
                'blocked_by': approver,
            })
            return {'mission': 'QNT50011', 'status': 'blocked', 'reasons': reasons, 'batch': batch, 'summary': self.summary()}
        expires_at = int(time.time()) + int(policy.get('release_authority_ttl_seconds') or 86400)
        release = {
            'payable_release_id': f'dpr_{uuid.uuid4().hex[:12]}',
            'batch_id': batch['batch_id'],
            'line_id': line['line_id'],
            'treasury_transfer_id': transfer_id,
            'investor_id': line['investor_id'],
            'investor_name': line['investor_name'],
            'amount': line['amount'],
            'currency': line['currency'],
            'authorized_at': int(time.time()),
            'authorized_by': approver,
            'expires_at': expires_at,
            'status': 'authorized',
            'statement_cycle_id': batch.get('statement_cycle_id'),
            'period_id': batch.get('period_id'),
        }
        line['status'] = 'authorized'
        line['payable_release_id'] = release['payable_release_id']
        link['status'] = 'authorized'
        link['payable_release_id'] = release['payable_release_id']
        state.setdefault('authorized_payable_releases', []).insert(0, release)
        state['authorized_payable_releases'] = state['authorized_payable_releases'][:1000]
        save_state(state)
        append_audit('distribution_payable_authorized', release)
        return {'mission': 'QNT50011', 'status': 'authorized', 'payable_release': release, 'batch': batch, 'summary': self.summary()}

    def record_execution(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        state = self._refresh()
        operator = str(payload.get('operator') or '').strip()
        if not operator:
            raise ValueError('operator is required')
        transfer_id = str(payload.get('transfer_id') or '').strip()
        transfer = self._find_transfer(transfer_id)
        if str(transfer.get('status') or '').lower() != 'executed':
            raise ValueError('treasury transfer is not executed')
        link = self._find_link(state, transfer_id)
        batch = self._find_batch(state, link.get('batch_id'))
        line = self._find_line(batch, line_id=link.get('line_id'))
        execution = {
            'execution_record_id': f'dex_{uuid.uuid4().hex[:12]}',
            'batch_id': batch['batch_id'],
            'line_id': line['line_id'],
            'treasury_transfer_id': transfer_id,
            'investor_id': line['investor_id'],
            'amount': self._round(transfer.get('amount'), 2),
            'currency': str(transfer.get('currency') or line.get('currency') or 'USD').upper(),
            'executed_at': int(transfer.get('executed_at') or time.time()),
            'recorded_at': int(time.time()),
            'recorded_by': operator,
            'note': str(payload.get('note') or ''),
            'status': 'executed',
        }
        line['status'] = 'executed'
        link['status'] = 'executed'
        state.setdefault('executed_payables', []).insert(0, execution)
        state['executed_payables'] = state['executed_payables'][:1000]
        save_state(state)
        append_audit('distribution_payable_executed', execution)
        return {'mission': 'QNT50011', 'status': 'executed', 'execution_record': execution, 'batch': batch, 'summary': self.summary()}

    def summary(self) -> Dict[str, Any]:
        state = self._ensure_synced(self._refresh())
        ctx = self._source_context()
        batches = state.get('distribution_batches', [])
        linked = state.get('transfer_links', [])
        releases = [r for r in state.get('authorized_payable_releases', []) if r.get('status') == 'authorized']
        blocked = [b for b in state.get('blocked_batches', []) if b.get('status') == 'blocked']
        posture = 'ready'
        if blocked:
            posture = 'constrained'
        if int(ctx.get('settlement_break_count') or 0) > int(self._policy(state).get('max_unresolved_breaks') or 0):
            posture = 'blocked'
        elif batches and not releases:
            posture = 'awaiting_release'
        return {
            'mission': 'QNT50011',
            'status': 'ok',
            'posture': posture,
            'distribution_batch_count': len(batches),
            'authorized_batch_count': len([b for b in batches if str(b.get('status') or '') == 'authorized_batch']),
            'transfer_link_count': len(linked),
            'authorized_payable_release_count': len(releases),
            'executed_payable_count': len(state.get('executed_payables', [])),
            'blocked_batch_count': len(blocked),
            'treasury_available_to_move': self._round(ctx.get('treasury_available_to_move'), 2),
            'latest_equity': self._round(ctx.get('latest_equity'), 2),
            'settlement_break_count': int(ctx.get('settlement_break_count') or 0),
            'registered_investor_count': int(ctx.get('registered_investor_count') or 0),
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
            'status': 'degraded',
        }
        if clear_audit:
            fresh['audit_log'] = []
        else:
            fresh.setdefault('audit_log', [])
        save_state(fresh)
        append_audit('distribution_payables_reset', {
            'operator': operator,
            'reason': str(payload.get('reason') or 'manual reset'),
            'clear_audit': clear_audit,
        })
        return self.summary()
