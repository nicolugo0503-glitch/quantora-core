from __future__ import annotations

import os
from typing import Any, Dict

from backend.app.execution.execution_service import ExecutionService
from backend.app.execution.fill_handler import append_audit, load_state, record_order, save_state
from backend.app.risk_control.engine import RiskKillSwitchEngine


class OrderRouter:
    def __init__(self):
        self.state = load_state()

    def risk_check(self, envelope: Dict[str, Any]) -> None:
        mode = self.state.get('mode', 'paper')
        safe_mode = bool(self.state.get('safe_mode', True))
        active_broker = self.state.get('active_broker', 'paper')
        if mode == 'live' and safe_mode:
            raise PermissionError('safe_mode blocks live execution')
        if mode == 'live' and active_broker == 'paper':
            raise PermissionError('live mode requires a live broker')
        if mode == 'live' and active_broker == 'binance':
            if not os.getenv('BINANCE_API_KEY') or not os.getenv('BINANCE_SECRET'):
                raise PermissionError('binance credentials missing')
        if float(envelope.get('qty') or 0.0) <= 0.0:
            raise PermissionError('qty must be positive')
        RiskKillSwitchEngine().pre_trade_check(envelope)
        append_audit('pre_execution_check_passed', {
            'mode': mode,
            'broker': active_broker,
            'decision_id': envelope.get('decision_id'),
            'strategy_id': envelope.get('strategy_id'),
        })

    def route(self, envelope: Dict[str, Any]) -> Dict[str, Any]:
        self.state = load_state()
        self.risk_check(envelope)
        broker_name = self.state.get('active_broker', 'paper') if self.state.get('mode') == 'live' else 'paper'
        execution = ExecutionService(broker_name)
        response = execution.execute_trade(envelope)
        latest = load_state()
        latest['active_broker'] = broker_name
        save_state(latest)
        record_order(envelope, response)
        append_audit('order_routed', {
            'broker': broker_name,
            'order_id': response.get('order_id'),
            'status': response.get('status'),
            'decision_id': envelope.get('decision_id'),
            'allocation_id': envelope.get('allocation_id'),
        })
        return response
