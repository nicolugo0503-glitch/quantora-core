from __future__ import annotations

import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from backend.app.execution.fill_handler import load_state as load_execution_state
from backend.app.settlement_reconciliation.state_store import append_audit, load_state, save_state


class SettlementReconciliationEngine:
    def __init__(self):
        self.state = load_state()

    def _refresh(self) -> Dict[str, Any]:
        self.state = load_state()
        return self.state

    def _now_date(self) -> str:
        return datetime.now(timezone.utc).strftime('%Y-%m-%d')

    def _round(self, value: Any, digits: int = 6) -> float:
        return round(float(value or 0.0), digits)

    def _infer_currency(self, symbol: str) -> str:
        symbol = str(symbol or '').upper()
        for suffix in ['USDT', 'USDC', 'USD', 'EUR', 'GBP']:
            if symbol.endswith(suffix):
                return suffix
        return str((self.state.get('control') or {}).get('base_currency') or 'USD').upper()

    def _signed_qty(self, side: str, qty: float) -> float:
        return qty if str(side or '').upper() == 'BUY' else -qty

    def _signed_cash(self, side: str, notional: float) -> float:
        return -notional if str(side or '').upper() == 'BUY' else notional

    def _ticket_from_fill(self, fill: Dict[str, Any]) -> Dict[str, Any]:
        qty = self._round(fill.get('filled_qty'), 10)
        price = self._round(fill.get('fill_price'), 8)
        notional = self._round(qty * price, 2)
        return {
            'settlement_id': f'stl_{uuid.uuid4().hex[:12]}',
            'created_at': int(time.time()),
            'settlement_date': self._now_date(),
            'order_id': fill.get('order_id'),
            'decision_id': fill.get('decision_id'),
            'allocation_id': fill.get('allocation_id'),
            'strategy_id': fill.get('strategy_id'),
            'risk_tag': fill.get('risk_tag'),
            'broker': fill.get('broker') or 'unknown',
            'symbol': str(fill.get('symbol') or '').upper(),
            'side': str(fill.get('side') or '').upper(),
            'filled_qty': qty,
            'fill_price': price,
            'gross_notional': notional,
            'currency': self._infer_currency(fill.get('symbol')),
            'status': 'pending',
            'custody_status': 'awaiting_confirmation',
            'cash_status': 'awaiting_confirmation',
            'reconciliation_status': 'unreconciled',
            'notes': 'generated from execution fill',
        }

    def ingest_execution_fills(self, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        payload = payload or {}
        state = self._refresh()
        execution = load_execution_state()
        processed = set(state.get('processed_order_ids') or [])
        inserted: List[Dict[str, Any]] = []
        for fill in execution.get('fills', []):
            order_id = str(fill.get('order_id') or '')
            if not order_id or order_id in processed:
                continue
            ticket = self._ticket_from_fill(fill)
            state.setdefault('pending_settlements', []).insert(0, ticket)
            state.setdefault('processed_order_ids', []).append(order_id)
            inserted.append(ticket)
            processed.add(order_id)
        state['pending_settlements'] = state.get('pending_settlements', [])[:500]
        state['processed_order_ids'] = state.get('processed_order_ids', [])[-1000:]
        save_state(state)
        append_audit('execution_fills_ingested', {
            'inserted_count': len(inserted),
            'auto_process': bool(payload.get('auto_process', False)),
        })
        result = {
            'mission': 'QNT50007',
            'status': 'ingested',
            'inserted_count': len(inserted),
            'pending_count': len(load_state().get('pending_settlements', [])),
            'tickets': inserted[:25],
        }
        if payload.get('auto_process') and inserted:
            ids = [item['settlement_id'] for item in inserted]
            result['auto_process_result'] = self.confirm_settlement({
                'settlement_ids': ids,
                'operator': str(payload.get('operator') or 'auto_settlement_control'),
                'cash_confirmed': True,
                'custody_confirmed': True,
                'notes': str(payload.get('notes') or 'auto settlement confirmation'),
            })
        return result

    def configure(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        state = self._refresh()
        control = dict(state.get('control') or {})
        for key in ['auto_ingest_fills', 'auto_reconcile_after_confirm', 'position_tolerance_qty', 'cash_tolerance', 'notional_tolerance', 'base_currency']:
            if payload.get(key) is not None:
                control[key] = payload[key]
        state['control'] = control
        save_state(state)
        append_audit('settlement_control_configured', {'control': control})
        return self.summary()

    def confirm_settlement(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        state = self._refresh()
        control = state.get('control') or {}
        requested_ids = set(payload.get('settlement_ids') or [])
        if not requested_ids:
            requested_ids = {item.get('settlement_id') for item in state.get('pending_settlements', [])}
        operator = str(payload.get('operator') or '').strip()
        if not operator:
            raise ValueError('operator is required')
        cash_confirmed = bool(payload.get('cash_confirmed', True))
        custody_confirmed = bool(payload.get('custody_confirmed', True))
        notes = str(payload.get('notes') or 'settlement confirmation')
        remaining = []
        settled = []
        exceptions = []
        for ticket in state.get('pending_settlements', []):
            if ticket.get('settlement_id') not in requested_ids:
                remaining.append(ticket)
                continue
            updated = dict(ticket)
            updated['confirmed_at'] = int(time.time())
            updated['confirmed_by'] = operator
            updated['notes'] = notes
            updated['cash_status'] = 'confirmed' if cash_confirmed else 'exception'
            updated['custody_status'] = 'confirmed' if custody_confirmed else 'exception'
            if cash_confirmed and custody_confirmed:
                updated['status'] = 'settled'
                updated['reconciliation_status'] = 'ready'
                state['cash_balance'] = self._round(state.get('cash_balance', 0.0) + self._signed_cash(updated.get('side'), updated.get('gross_notional')), 2)
                symbol = str(updated.get('symbol') or '').upper()
                state.setdefault('positions', {})[symbol] = self._round((state.get('positions') or {}).get(symbol, 0.0) + self._signed_qty(updated.get('side'), updated.get('filled_qty')), 10)
                state.setdefault('cash_ledger', []).insert(0, {
                    'ledger_id': f'cash_{uuid.uuid4().hex[:12]}',
                    'settlement_id': updated.get('settlement_id'),
                    'order_id': updated.get('order_id'),
                    'timestamp': int(time.time()),
                    'currency': updated.get('currency'),
                    'amount': self._signed_cash(updated.get('side'), updated.get('gross_notional')),
                    'balance_after': state.get('cash_balance'),
                    'operator': operator,
                })
                state.setdefault('position_ledger', []).insert(0, {
                    'ledger_id': f'pos_{uuid.uuid4().hex[:12]}',
                    'settlement_id': updated.get('settlement_id'),
                    'order_id': updated.get('order_id'),
                    'timestamp': int(time.time()),
                    'symbol': symbol,
                    'qty_delta': self._signed_qty(updated.get('side'), updated.get('filled_qty')),
                    'position_after': (state.get('positions') or {}).get(symbol, 0.0),
                    'operator': operator,
                })
                state.setdefault('settled_settlements', []).insert(0, updated)
                settled.append(updated)
            else:
                updated['status'] = 'exception'
                updated['reconciliation_status'] = 'break'
                remaining.append(updated)
                exceptions.append(updated)
        state['pending_settlements'] = remaining[:500]
        state['settled_settlements'] = state.get('settled_settlements', [])[:500]
        state['cash_ledger'] = state.get('cash_ledger', [])[:1000]
        state['position_ledger'] = state.get('position_ledger', [])[:1000]
        save_state(state)
        append_audit('settlement_confirmed', {
            'operator': operator,
            'settled_count': len(settled),
            'exception_count': len(exceptions),
        })
        result = {
            'mission': 'QNT50007',
            'status': 'processed',
            'settled_count': len(settled),
            'exception_count': len(exceptions),
            'pending_count': len(remaining),
            'cash_balance': load_state().get('cash_balance', 0.0),
            'positions': load_state().get('positions', {}),
        }
        if control.get('auto_reconcile_after_confirm', True):
            result['reconciliation'] = self.reconcile({
                'operator': operator,
                'notes': 'auto reconcile after settlement confirm',
                'auto_ingest': False,
            })
        return result

    def reconcile(self, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        payload = payload or {}
        state = self._refresh()
        if payload.get('auto_ingest', True) and (state.get('control') or {}).get('auto_ingest_fills', True):
            self.ingest_execution_fills({'auto_process': False})
            state = self._refresh()
        tolerance_qty = float((state.get('control') or {}).get('position_tolerance_qty', 0.000001) or 0.000001)
        tolerance_cash = float((state.get('control') or {}).get('cash_tolerance', 1.0) or 1.0)
        broker_positions = {str(k).upper(): self._round(v, 10) for k, v in (payload.get('broker_positions') or (state.get('last_broker_snapshot') or {}).get('positions', {})).items()}
        broker_cash_balance = self._round(payload.get('broker_cash_balance', (state.get('last_broker_snapshot') or {}).get('cash_balance', state.get('cash_balance', 0.0))), 2)
        internal_positions = {str(k).upper(): self._round(v, 10) for k, v in (state.get('positions') or {}).items()}
        all_symbols = sorted(set(internal_positions) | set(broker_positions))
        breaks: List[Dict[str, Any]] = []
        for symbol in all_symbols:
            internal_qty = self._round(internal_positions.get(symbol, 0.0), 10)
            broker_qty = self._round(broker_positions.get(symbol, 0.0), 10)
            delta = self._round(internal_qty - broker_qty, 10)
            if abs(delta) > tolerance_qty:
                breaks.append({
                    'break_id': f'brk_{uuid.uuid4().hex[:12]}',
                    'break_type': 'position_mismatch',
                    'symbol': symbol,
                    'internal_qty': internal_qty,
                    'broker_qty': broker_qty,
                    'delta': delta,
                    'severity': 'high' if abs(delta) > max(tolerance_qty * 10, 0.01) else 'medium',
                })
        cash_delta = self._round(self._round(state.get('cash_balance', 0.0), 2) - broker_cash_balance, 2)
        if abs(cash_delta) > tolerance_cash:
            breaks.append({
                'break_id': f'brk_{uuid.uuid4().hex[:12]}',
                'break_type': 'cash_mismatch',
                'internal_cash_balance': self._round(state.get('cash_balance', 0.0), 2),
                'broker_cash_balance': broker_cash_balance,
                'delta': cash_delta,
                'severity': 'high' if abs(cash_delta) > max(tolerance_cash * 10, 10.0) else 'medium',
            })
        summary = {
            'run_at': int(time.time()),
            'operator': str(payload.get('operator') or 'settlement_control_layer'),
            'notes': str(payload.get('notes') or 'reconciliation run'),
            'status': 'matched' if not breaks else 'breaks_detected',
            'pending_count': len(state.get('pending_settlements', [])),
            'settled_count': len(state.get('settled_settlements', [])),
            'break_count': len(breaks),
            'cash_balance': self._round(state.get('cash_balance', 0.0), 2),
            'broker_cash_balance': broker_cash_balance,
            'positions': internal_positions,
            'broker_positions': broker_positions,
        }
        state['last_broker_snapshot'] = {
            'positions': broker_positions,
            'cash_balance': broker_cash_balance,
        }
        state['last_reconciliation'] = summary
        state['reconciliation_breaks'] = breaks[:250]
        for ticket in state.get('settled_settlements', []):
            ticket['reconciliation_status'] = 'matched' if not breaks else 'break'
        save_state(state)
        append_audit('reconciliation_completed', {
            'operator': summary['operator'],
            'break_count': len(breaks),
            'status': summary['status'],
        })
        return {'mission': 'QNT50007', **summary, 'breaks': breaks}

    def reset(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        operator = str(payload.get('operator') or '').strip()
        if not operator:
            raise ValueError('operator is required')
        reason = str(payload.get('reason') or 'manual reset')
        state = load_state()
        control = state.get('control') or {}
        next_state = {
            'generated_by': 'QNT50007',
            'status': 'degraded',
            'control': control,
            'processed_order_ids': [],
            'pending_settlements': [],
            'settled_settlements': [],
            'cash_ledger': [],
            'position_ledger': [],
            'positions': {},
            'cash_balance': 0.0,
            'last_broker_snapshot': {'positions': {}, 'cash_balance': 0.0},
            'last_reconciliation': None,
            'reconciliation_breaks': [],
            'audit_log': [] if payload.get('clear_audit', False) else state.get('audit_log', []),
        }
        save_state(next_state)
        append_audit('settlement_state_reset', {'operator': operator, 'reason': reason})
        return self.summary()

    def summary(self) -> Dict[str, Any]:
        state = self._refresh()
        last_recon = state.get('last_reconciliation') or {}
        return {
            'mission': 'QNT50007',
            'status': 'ok',
            'generated_by': state.get('generated_by'),
            'pending_count': len(state.get('pending_settlements', [])),
            'settled_count': len(state.get('settled_settlements', [])),
            'break_count': len(state.get('reconciliation_breaks', [])),
            'cash_balance': self._round(state.get('cash_balance', 0.0), 2),
            'positions': state.get('positions', {}),
            'last_reconciliation_status': last_recon.get('status'),
            'last_reconciliation_at': last_recon.get('run_at'),
            'control': state.get('control', {}),
            'recent_breaks': state.get('reconciliation_breaks', [])[:10],
            'recent_pending': state.get('pending_settlements', [])[:10],
        }
