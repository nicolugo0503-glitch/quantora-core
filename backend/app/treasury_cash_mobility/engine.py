from __future__ import annotations

import time
import uuid
from typing import Any, Dict, List, Optional

from backend.app.settlement_reconciliation.state_store import load_state as load_settlement_state
from backend.app.treasury_cash_mobility.state_store import append_audit, load_state, save_state


class TreasuryCashMobilityEngine:
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

    def _settlement_context(self) -> Dict[str, Any]:
        settlement = load_settlement_state()
        pending = settlement.get('pending_settlements') or []
        settled = settlement.get('settled_settlements') or []
        pending_buy = sum(float(t.get('gross_notional') or 0.0) for t in pending if str(t.get('side') or '').upper() == 'BUY')
        pending_sell = sum(float(t.get('gross_notional') or 0.0) for t in pending if str(t.get('side') or '').upper() == 'SELL')
        return {
            'cash_balance': self._round(settlement.get('cash_balance', 0.0), 2),
            'pending_outflows': self._round(pending_buy, 2),
            'pending_inflows': self._round(pending_sell, 2),
            'pending_count': len(pending),
            'settled_count': len(settled),
            'break_count': len(settlement.get('reconciliation_breaks') or []),
            'settlement_status': (settlement.get('last_reconciliation') or {}).get('status') or 'unreconciled',
        }

    def _total_account_balance(self, state: Dict[str, Any]) -> float:
        return self._round(sum(float((row or {}).get('balance') or 0.0) for row in (state.get('accounts') or {}).values()), 2)

    def _reserve_target(self, cash_balance: float, policy: Dict[str, Any]) -> float:
        floor = float(policy.get('reserve_floor') or 0.0)
        pct = float(policy.get('reserve_buffer_pct') or 0.0)
        return self._round(max(floor, cash_balance * pct), 2)

    def _operating_target(self, cash_balance: float, policy: Dict[str, Any]) -> float:
        return self._round(max(float(policy.get('min_operating_cash') or 0.0), cash_balance * 0.20), 2)

    def _sync_accounts_to_cash(self, state: Dict[str, Any], cash_balance: float) -> Dict[str, Any]:
        policy = self._policy(state)
        accounts = dict(state.get('accounts') or {})
        base_currency = str(policy.get('base_currency') or 'USD').upper()
        if not accounts:
            accounts = {
                'operating': {'currency': base_currency, 'balance': 0.0},
                'broker_buffer': {'currency': base_currency, 'balance': 0.0},
                'custody_reserve': {'currency': base_currency, 'balance': 0.0},
            }
        reserve_target = self._reserve_target(cash_balance, policy)
        operating_target = min(cash_balance, self._operating_target(cash_balance, policy))
        custody_target = min(max(cash_balance - operating_target, 0.0), reserve_target)
        broker_target = max(cash_balance - operating_target - custody_target, 0.0)
        total_existing = self._total_account_balance(state)
        if total_existing == 0.0:
            accounts['operating'] = {'currency': base_currency, 'balance': self._round(operating_target, 2)}
            accounts['custody_reserve'] = {'currency': base_currency, 'balance': self._round(custody_target, 2)}
            accounts['broker_buffer'] = {'currency': base_currency, 'balance': self._round(broker_target, 2)}
        else:
            delta = self._round(cash_balance - total_existing, 2)
            accounts.setdefault('broker_buffer', {'currency': base_currency, 'balance': 0.0})
            accounts['broker_buffer']['balance'] = self._round(float(accounts['broker_buffer'].get('balance') or 0.0) + delta, 2)
            for account_name in ['operating', 'custody_reserve', 'broker_buffer']:
                accounts.setdefault(account_name, {'currency': base_currency, 'balance': 0.0})
                accounts[account_name]['currency'] = base_currency
        state['accounts'] = accounts
        return state

    def sync_settlement_context(self, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        payload = payload or {}
        state = self._refresh()
        settlement = self._settlement_context()
        state = self._sync_accounts_to_cash(state, settlement['cash_balance'])
        policy = self._policy(state)
        total_cash = self._total_account_balance(state)
        reserve_target = self._reserve_target(total_cash, policy)
        pending_transfer_amount = sum(float(t.get('amount') or 0.0) for t in state.get('pending_transfers', []) if t.get('status') in {'staged', 'approved'})
        available_to_move = max(total_cash - reserve_target - settlement['pending_outflows'] - pending_transfer_amount, 0.0)
        snapshot = {
            'synced_at': int(time.time()),
            'source': str(payload.get('source') or 'manual'),
            'cash_balance': self._round(total_cash, 2),
            'reserve_target': self._round(reserve_target, 2),
            'pending_settlement_outflows': settlement['pending_outflows'],
            'pending_settlement_inflows': settlement['pending_inflows'],
            'pending_transfer_amount': self._round(pending_transfer_amount, 2),
            'available_to_move': self._round(available_to_move, 2),
            'break_count': settlement['break_count'],
            'settlement_status': settlement['settlement_status'],
        }
        state['last_sync'] = snapshot
        state.setdefault('liquidity_snapshots', []).insert(0, snapshot)
        state['liquidity_snapshots'] = state['liquidity_snapshots'][:500]
        save_state(state)
        append_audit('settlement_context_synced', snapshot)
        return {
            'mission': 'QNT50008',
            'status': 'synced',
            'snapshot': snapshot,
            'accounts': load_state().get('accounts', {}),
        }

    def _ensure_synced(self, state: Dict[str, Any]) -> Dict[str, Any]:
        if (self._policy(state).get('auto_sync_settlement', True)) and not state.get('last_sync'):
            self.sync_settlement_context({'source': 'auto'})
            state = self._refresh()
        return state

    def _mobility_status(self, summary: Dict[str, Any]) -> str:
        if summary['break_count'] > 0:
            return 'constrained'
        if summary['available_to_move'] <= 0:
            return 'locked'
        if summary['approved_transfer_count'] > 0:
            return 'active'
        return 'ready'

    def summary(self) -> Dict[str, Any]:
        state = self._ensure_synced(self._refresh())
        policy = self._policy(state)
        settlement = self._settlement_context()
        total_cash = self._total_account_balance(state)
        reserve_target = self._reserve_target(total_cash, policy)
        pending_transfers = state.get('pending_transfers', [])
        approved_amount = sum(float(t.get('amount') or 0.0) for t in pending_transfers if t.get('status') == 'approved')
        staged_amount = sum(float(t.get('amount') or 0.0) for t in pending_transfers if t.get('status') == 'staged')
        max_single_pct = float(policy.get('max_single_transfer_pct_of_available') or 0.0)
        available_to_move = max(total_cash - reserve_target - settlement['pending_outflows'] - approved_amount - staged_amount, 0.0)
        summary = {
            'mission': 'QNT50008',
            'status': 'ok',
            'treasury_status': self._mobility_status({
                'break_count': settlement['break_count'],
                'available_to_move': available_to_move,
                'approved_transfer_count': len([t for t in pending_transfers if t.get('status') == 'approved']),
            }),
            'base_currency': str(policy.get('base_currency') or 'USD').upper(),
            'cash_balance': self._round(total_cash, 2),
            'reserve_target': self._round(reserve_target, 2),
            'available_to_move': self._round(available_to_move, 2),
            'max_single_transfer_amount': self._round(available_to_move * max_single_pct, 2),
            'pending_settlement_outflows': settlement['pending_outflows'],
            'pending_settlement_inflows': settlement['pending_inflows'],
            'pending_transfer_count': len(pending_transfers),
            'approved_transfer_count': len([t for t in pending_transfers if t.get('status') == 'approved']),
            'completed_transfer_count': len(state.get('completed_transfers', [])),
            'break_count': settlement['break_count'],
            'settlement_status': settlement['settlement_status'],
            'accounts': state.get('accounts', {}),
            'last_sync': state.get('last_sync'),
            'last_rebalance': state.get('last_rebalance'),
        }
        return summary

    def configure(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        state = self._refresh()
        policy = self._policy(state)
        for key in [
            'base_currency', 'reserve_floor', 'reserve_buffer_pct', 'min_operating_cash',
            'max_single_transfer_pct_of_available', 'auto_sync_settlement',
            'settlement_haircut_pct', 'rebalance_tolerance_pct'
        ]:
            if payload.get(key) is not None:
                policy[key] = payload[key]
        state['policy'] = policy
        save_state(state)
        append_audit('treasury_policy_configured', {'policy': policy})
        if payload.get('sync_after_configure', True):
            self.sync_settlement_context({'source': 'configure'})
        return self.summary()

    def _find_transfer(self, state: Dict[str, Any], transfer_id: str) -> Dict[str, Any]:
        for item in state.get('pending_transfers', []):
            if item.get('transfer_id') == transfer_id:
                return item
        raise ValueError('transfer_id not found')

    def stage_transfer(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        state = self._ensure_synced(self._refresh())
        summary = self.summary()
        operator = str(payload.get('operator') or '').strip()
        if not operator:
            raise ValueError('operator is required')
        amount = self._round(payload.get('amount'), 2)
        if amount <= 0:
            raise ValueError('amount must be positive')
        from_account = str(payload.get('from_account') or 'broker_buffer').strip() or 'broker_buffer'
        to_account = str(payload.get('to_account') or '').strip()
        destination = str(payload.get('destination') or '').strip() or 'internal_treasury_route'
        policy = self._policy(state)
        max_single = self._round(summary['max_single_transfer_amount'], 2)
        review_reasons: List[str] = []
        if amount > summary['available_to_move']:
            raise ValueError('transfer amount exceeds available treasury mobility capacity')
        if max_single > 0 and amount > max_single:
            review_reasons.append('transfer exceeds single-move policy threshold')
        if summary['break_count'] > 0:
            review_reasons.append('reconciliation breaks require review before cash mobility')
        source_balance = float(((state.get('accounts') or {}).get(from_account) or {}).get('balance') or 0.0)
        if source_balance < amount:
            raise ValueError('source account balance is insufficient for requested transfer')
        transfer = {
            'transfer_id': f'trf_{uuid.uuid4().hex[:12]}',
            'created_at': int(time.time()),
            'operator': operator,
            'decision_id': str(payload.get('decision_id') or ''),
            'allocation_id': str(payload.get('allocation_id') or ''),
            'investor_id': str(payload.get('investor_id') or ''),
            'capital_activity_id': str(payload.get('capital_activity_id') or ''),
            'statement_cycle_id': str(payload.get('statement_cycle_id') or ''),
            'transfer_type': str(payload.get('transfer_type') or 'internal_rebalance'),
            'from_account': from_account,
            'to_account': to_account,
            'destination': destination,
            'amount': amount,
            'currency': str(payload.get('currency') or policy.get('base_currency') or 'USD').upper(),
            'priority': str(payload.get('priority') or 'normal').lower(),
            'purpose': str(payload.get('purpose') or 'treasury cash mobility request'),
            'settlement_dependency': str(payload.get('settlement_dependency') or ''),
            'status': 'review' if review_reasons else 'staged',
            'review_reasons': review_reasons,
            'executed_at': None,
            'approved_at': None,
            'approved_by': None,
        }
        state.setdefault('pending_transfers', []).insert(0, transfer)
        state['pending_transfers'] = state['pending_transfers'][:500]
        save_state(state)
        append_audit('transfer_staged', {
            'transfer_id': transfer['transfer_id'],
            'amount': amount,
            'status': transfer['status'],
            'operator': operator,
        })
        return {
            'mission': 'QNT50008',
            'status': transfer['status'],
            'transfer': transfer,
            'summary': self.summary(),
        }

    def approve_transfer(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        state = self._refresh()
        approver = str(payload.get('approver') or '').strip()
        if not approver:
            raise ValueError('approver is required')
        transfer = self._find_transfer(state, str(payload.get('transfer_id') or '').strip())
        if transfer.get('status') not in {'staged', 'review'}:
            raise ValueError('only staged or review transfers can be approved')
        transfer['status'] = 'approved'
        transfer['approved_at'] = int(time.time())
        transfer['approved_by'] = approver
        if payload.get('approval_notes'):
            transfer['approval_notes'] = str(payload.get('approval_notes'))
        save_state(state)
        append_audit('transfer_approved', {
            'transfer_id': transfer['transfer_id'],
            'approver': approver,
            'amount': transfer['amount'],
        })
        return {
            'mission': 'QNT50008',
            'status': 'approved',
            'transfer': transfer,
            'summary': self.summary(),
        }

    def execute_transfer(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        state = self._refresh()
        operator = str(payload.get('operator') or '').strip()
        if not operator:
            raise ValueError('operator is required')
        transfer = self._find_transfer(state, str(payload.get('transfer_id') or '').strip())
        if transfer.get('status') != 'approved':
            raise ValueError('only approved transfers can be executed')
        transfer_type = str(transfer.get('transfer_type') or '').lower()
        destination = str(transfer.get('destination') or '').lower()
        if transfer_type in {'investor_distribution', 'distribution_payable', 'income_distribution'} or destination in {'investor_distribution', 'investor_distribution_bank', 'investor distribution bank'}:
            from backend.app.investor_distribution_payables.state_store import distribution_release_status
            distribution_status = distribution_release_status(str(transfer.get('transfer_id') or ''))
            if not distribution_status.get('authorized'):
                raise ValueError(f"distribution payable release authority is required before execution: {distribution_status.get('reason')}")
            transfer['payable_release_id'] = distribution_status.get('payable_release_id')
        elif transfer_type in {'investor_redemption', 'capital_return'} or destination in {'investor_settlement', 'investor settlement bank', 'investor_settlement_bank'}:
            from backend.app.investor_cash_confirmation.state_store import transfer_release_status
            release_status = transfer_release_status(str(transfer.get('transfer_id') or ''))
            if not release_status.get('authorized'):
                raise ValueError(f"investor cash release authority is required before execution: {release_status.get('reason')}")
            transfer['release_authority_id'] = release_status.get('release_authority_id')
        accounts = state.get('accounts') or {}
        from_account = transfer.get('from_account')
        to_account = transfer.get('to_account')
        amount = self._round(transfer.get('amount'), 2)
        if float(((accounts.get(from_account) or {}).get('balance') or 0.0)) < amount:
            raise ValueError('source account balance is insufficient at execution time')
        accounts.setdefault(from_account, {'currency': transfer.get('currency') or 'USD', 'balance': 0.0})
        accounts[from_account]['balance'] = self._round(float(accounts[from_account].get('balance') or 0.0) - amount, 2)
        if to_account:
            accounts.setdefault(to_account, {'currency': transfer.get('currency') or 'USD', 'balance': 0.0})
            accounts[to_account]['balance'] = self._round(float(accounts[to_account].get('balance') or 0.0) + amount, 2)
        transfer['status'] = 'executed'
        transfer['executed_at'] = int(time.time())
        transfer['executed_by'] = operator
        state['pending_transfers'] = [t for t in state.get('pending_transfers', []) if t.get('transfer_id') != transfer.get('transfer_id')]
        state.setdefault('completed_transfers', []).insert(0, transfer)
        state['completed_transfers'] = state['completed_transfers'][:500]
        save_state(state)
        append_audit('transfer_executed', {
            'transfer_id': transfer['transfer_id'],
            'operator': operator,
            'amount': amount,
            'from_account': from_account,
            'to_account': to_account,
            'destination': transfer.get('destination'),
        })
        self.sync_settlement_context({'source': 'post_execute'})
        return {
            'mission': 'QNT50008',
            'status': 'executed',
            'transfer': transfer,
            'summary': self.summary(),
        }

    def rebalance(self, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        payload = payload or {}
        state = self._ensure_synced(self._refresh())
        summary = self.summary()
        policy = self._policy(state)
        total_cash = float(summary['cash_balance'] or 0.0)
        tolerance_pct = float(policy.get('rebalance_tolerance_pct') or 0.0)
        reserve_target = float(summary['reserve_target'] or 0.0)
        operating_target = min(total_cash, self._operating_target(total_cash, policy))
        broker_target = max(total_cash - reserve_target - operating_target, 0.0)
        targets = {
            'operating': self._round(operating_target, 2),
            'custody_reserve': self._round(min(max(total_cash - operating_target, 0.0), reserve_target), 2),
            'broker_buffer': self._round(broker_target, 2),
        }
        accounts = state.get('accounts') or {}
        actions: List[Dict[str, Any]] = []
        surpluses: List[Dict[str, Any]] = []
        deficits: List[Dict[str, Any]] = []
        for name, target in targets.items():
            actual = self._round(((accounts.get(name) or {}).get('balance') or 0.0), 2)
            delta = self._round(actual - target, 2)
            if total_cash > 0 and abs(delta) <= self._round(total_cash * tolerance_pct, 2):
                continue
            if delta > 0:
                surpluses.append({'account': name, 'amount': delta})
            elif delta < 0:
                deficits.append({'account': name, 'amount': abs(delta)})
        for surplus in surpluses:
            remaining = surplus['amount']
            for deficit in deficits:
                if remaining <= 0:
                    break
                if deficit['amount'] <= 0:
                    continue
                move = self._round(min(remaining, deficit['amount']), 2)
                if move <= 0:
                    continue
                actions.append({
                    'from_account': surplus['account'],
                    'to_account': deficit['account'],
                    'amount': move,
                    'currency': str(policy.get('base_currency') or 'USD').upper(),
                    'reason': 'treasury rebalance to policy targets',
                })
                remaining = self._round(remaining - move, 2)
                deficit['amount'] = self._round(deficit['amount'] - move, 2)
        result = {
            'mission': 'QNT50008',
            'status': 'planned' if actions else 'balanced',
            'targets': targets,
            'actions': actions,
            'action_count': len(actions),
        }
        if payload.get('stage_actions') and actions:
            staged = []
            for idx, action in enumerate(actions, start=1):
                staged.append(self.stage_transfer({
                    'operator': str(payload.get('operator') or 'treasury_rebalance_engine'),
                    'decision_id': str(payload.get('decision_id') or f'rebalance_{idx}'),
                    'transfer_type': 'internal_rebalance',
                    'from_account': action['from_account'],
                    'to_account': action['to_account'],
                    'destination': 'internal_treasury_route',
                    'amount': action['amount'],
                    'currency': action['currency'],
                    'purpose': action['reason'],
                    'priority': 'normal',
                })['transfer'])
            result['staged_transfers'] = staged
        state = self._refresh()
        state['last_rebalance'] = {
            'planned_at': int(time.time()),
            'targets': targets,
            'action_count': len(actions),
        }
        save_state(state)
        append_audit('treasury_rebalance_planned', state['last_rebalance'])
        return result

    def reset(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        operator = str(payload.get('operator') or '').strip()
        if not operator:
            raise ValueError('operator is required')
        clear_audit = bool(payload.get('clear_audit', False))
        fresh = load_state()
        fresh = {
            **fresh,
            'pending_transfers': [],
            'completed_transfers': [],
            'rejected_transfers': [],
            'liquidity_snapshots': [],
            'last_sync': None,
            'last_rebalance': None,
        }
        if clear_audit:
            fresh['audit_log'] = []
        save_state(fresh)
        append_audit('treasury_state_reset', {
            'operator': operator,
            'reason': str(payload.get('reason') or 'manual reset'),
            'clear_audit': clear_audit,
        })
        return self.sync_settlement_context({'source': 'reset'})
