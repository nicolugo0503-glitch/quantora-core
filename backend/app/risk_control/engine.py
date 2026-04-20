from __future__ import annotations

import time
from typing import Any, Dict, List

from backend.app.allocation.state_store import load_state as load_allocation_state, save_state as save_allocation_state
from backend.app.execution.fill_handler import append_audit as append_execution_audit
from backend.app.execution.fill_handler import load_state as load_execution_state, save_state as save_execution_state
from backend.app.risk_control.state_store import append_audit, load_state, save_state
from backend.app.strategy_deployment.state_store import load_state as load_deployment_state, save_state as save_deployment_state


class RiskKillSwitchEngine:
    def __init__(self):
        self.state = load_state()

    def _refresh(self) -> Dict[str, Any]:
        self.state = load_state()
        return self.state

    def _sync_safe_mode(self, reason: str) -> None:
        execution_state = load_execution_state()
        execution_state['safe_mode'] = True
        execution_state['mode'] = 'paper'
        execution_state['active_broker'] = 'paper'
        execution_state['locked'] = True
        save_execution_state(execution_state)
        append_execution_audit('risk_kill_switch_enforced', {
            'reason': reason,
            'kill_switch': True,
        })

        allocation_state = load_allocation_state()
        allocation_state['safe_mode'] = True
        allocation_state['execution_mode'] = 'paper'
        save_allocation_state(allocation_state)

        deployment_state = load_deployment_state()
        deployment_state['safe_mode'] = True
        deployment_state['execution_mode'] = 'paper'
        save_deployment_state(deployment_state)

    def _normalize_metrics(self, incoming: Dict[str, Any], state: Dict[str, Any]) -> Dict[str, Any]:
        metrics = dict(state.get('metrics') or {})
        metrics.update({k: v for k, v in incoming.items() if v is not None})
        equity = float(metrics.get('equity') or 0.0)
        peak = float(metrics.get('peak_equity') or 0.0)
        if equity > peak:
            peak = equity
        metrics['peak_equity'] = peak
        if peak > 0:
            metrics['portfolio_drawdown_pct'] = max(float(metrics.get('portfolio_drawdown_pct') or 0.0), max((peak - equity) / peak, 0.0))
        for key in ['strategy_drawdown_pct', 'daily_loss_pct', 'open_notional', 'largest_position_pct', 'margin_usage_pct']:
            metrics[key] = max(float(metrics.get(key) or 0.0), 0.0)
        metrics['latency_ms'] = max(float(metrics.get('latency_ms') or 0.0), 0.0)
        metrics['venue_connectivity_ok'] = bool(metrics.get('venue_connectivity_ok', True))
        return metrics

    def _detect_breaches(self, metrics: Dict[str, Any], thresholds: Dict[str, Any], order_notional: float | None = None) -> List[Dict[str, Any]]:
        breaches: List[Dict[str, Any]] = []
        def flag(code: str, value: float | bool, limit: float | bool, severity: str, message: str) -> None:
            breaches.append({
                'code': code,
                'value': value,
                'limit': limit,
                'severity': severity,
                'message': message,
            })

        if float(metrics.get('portfolio_drawdown_pct') or 0.0) >= float(thresholds.get('portfolio_drawdown_limit_pct') or 0.0):
            flag('portfolio_drawdown_limit', metrics.get('portfolio_drawdown_pct'), thresholds.get('portfolio_drawdown_limit_pct'), 'critical', 'portfolio drawdown breached')
        if float(metrics.get('strategy_drawdown_pct') or 0.0) >= float(thresholds.get('strategy_drawdown_limit_pct') or 0.0):
            flag('strategy_drawdown_limit', metrics.get('strategy_drawdown_pct'), thresholds.get('strategy_drawdown_limit_pct'), 'critical', 'strategy drawdown breached')
        if float(metrics.get('daily_loss_pct') or 0.0) >= float(thresholds.get('daily_loss_limit_pct') or 0.0):
            flag('daily_loss_limit', metrics.get('daily_loss_pct'), thresholds.get('daily_loss_limit_pct'), 'critical', 'daily loss breached')
        if float(metrics.get('open_notional') or 0.0) >= float(thresholds.get('max_live_notional') or 0.0):
            flag('live_notional_limit', metrics.get('open_notional'), thresholds.get('max_live_notional'), 'critical', 'live notional breached')
        if float(metrics.get('largest_position_pct') or 0.0) >= float(thresholds.get('max_position_concentration_pct') or 0.0):
            flag('position_concentration_limit', metrics.get('largest_position_pct'), thresholds.get('max_position_concentration_pct'), 'critical', 'position concentration breached')
        if float(metrics.get('margin_usage_pct') or 0.0) >= float(thresholds.get('max_margin_usage_pct') or 0.0):
            flag('margin_usage_limit', metrics.get('margin_usage_pct'), thresholds.get('max_margin_usage_pct'), 'critical', 'margin usage breached')
        if not bool(metrics.get('venue_connectivity_ok', True)):
            flag('venue_connectivity_down', metrics.get('venue_connectivity_ok'), True, 'critical', 'venue connectivity failed')
        if float(metrics.get('latency_ms') or 0.0) >= float(thresholds.get('max_latency_ms') or 0.0):
            flag('latency_limit', metrics.get('latency_ms'), thresholds.get('max_latency_ms'), 'warning', 'execution latency elevated')
        if order_notional is not None and float(order_notional) >= float(thresholds.get('max_single_order_notional') or 0.0):
            flag('single_order_notional_limit', order_notional, thresholds.get('max_single_order_notional'), 'critical', 'single order notional breached')
        return breaches

    def _engage(self, state: Dict[str, Any], breaches: List[Dict[str, Any]], source: str, reason: str, context: Dict[str, Any] | None = None) -> Dict[str, Any]:
        state['kill_switch_triggered'] = True
        state['kill_switch_level'] = 'hard_stop'
        state['trigger_reason'] = reason
        state['triggered_at'] = int(time.time())
        state['active_breaches'] = breaches
        state.setdefault('trigger_log', []).insert(0, {
            'triggered_at': state['triggered_at'],
            'source': source,
            'reason': reason,
            'breaches': breaches,
            'context': context or {},
        })
        state['trigger_log'] = state['trigger_log'][:200]
        save_state(state)
        self._sync_safe_mode(reason)
        append_audit('kill_switch_triggered', {
            'source': source,
            'reason': reason,
            'breach_count': len(breaches),
        })
        return {
            'mission': 'QNT50004',
            'status': 'triggered',
            'kill_switch_triggered': True,
            'reason': reason,
            'breaches': breaches,
        }

    def summary(self) -> Dict[str, Any]:
        state = self._refresh()
        return {
            'mission': 'QNT50004',
            'status': 'ok',
            'armed': bool(state.get('armed', True)),
            'kill_switch_triggered': bool(state.get('kill_switch_triggered', False)),
            'kill_switch_level': state.get('kill_switch_level', 'normal'),
            'trigger_reason': state.get('trigger_reason'),
            'active_breach_count': len(state.get('active_breaches', [])),
            'blocked_order_count': len(state.get('blocked_orders', [])),
            'safe_mode_on_trigger': bool(state.get('safe_mode_on_trigger', True)),
            'metrics': state.get('metrics', {}),
            'thresholds': state.get('thresholds', {}),
        }

    def configure(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        state = self._refresh()
        thresholds = dict(state.get('thresholds') or {})
        thresholds.update({k: v for k, v in (payload.get('thresholds') or {}).items() if v is not None})
        state['thresholds'] = thresholds
        if 'armed' in payload and payload.get('armed') is not None:
            state['armed'] = bool(payload.get('armed'))
        if 'safe_mode_on_trigger' in payload and payload.get('safe_mode_on_trigger') is not None:
            state['safe_mode_on_trigger'] = bool(payload.get('safe_mode_on_trigger'))
        save_state(state)
        append_audit('risk_thresholds_configured', {
            'armed': state.get('armed', True),
            'safe_mode_on_trigger': state.get('safe_mode_on_trigger', True),
        })
        return self.summary()

    def arm(self, payload: Dict[str, Any] | None = None) -> Dict[str, Any]:
        state = self._refresh()
        state['armed'] = True
        if payload and payload.get('safe_mode_on_trigger') is not None:
            state['safe_mode_on_trigger'] = bool(payload.get('safe_mode_on_trigger'))
        save_state(state)
        append_audit('kill_switch_armed', {'safe_mode_on_trigger': state.get('safe_mode_on_trigger', True)})
        return self.summary()

    def disarm(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        state = self._refresh()
        approver = payload.get('approver') or 'operator'
        reason = payload.get('reason') or 'manual disarm'
        state['armed'] = False
        state.setdefault('override_log', []).insert(0, {
            'action': 'disarm',
            'approver': approver,
            'reason': reason,
            'timestamp': int(time.time()),
        })
        state['override_log'] = state['override_log'][:200]
        save_state(state)
        append_audit('kill_switch_disarmed', {'approver': approver, 'reason': reason})
        return self.summary()

    def update_metrics(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        state = self._refresh()
        state['metrics'] = self._normalize_metrics(payload, state)
        save_state(state)
        return self.evaluate({'metrics': state['metrics'], 'source': 'metrics_update'})

    def evaluate(self, payload: Dict[str, Any] | None = None) -> Dict[str, Any]:
        state = self._refresh()
        payload = payload or {}
        state['metrics'] = self._normalize_metrics(payload.get('metrics') or state.get('metrics') or {}, state)
        thresholds = dict(state.get('thresholds') or {})
        breaches = self._detect_breaches(state['metrics'], thresholds)
        state['metrics']['breach_count'] = len(breaches)
        state['active_breaches'] = breaches
        state.setdefault('evaluation_log', []).insert(0, {
            'evaluated_at': int(time.time()),
            'source': payload.get('source', 'manual'),
            'breaches': breaches,
            'metrics': state['metrics'],
        })
        state['evaluation_log'] = state['evaluation_log'][:200]
        save_state(state)
        if state.get('armed', True) and breaches and any(b.get('severity') == 'critical' for b in breaches):
            return self._engage(state, breaches, payload.get('source', 'manual'), breaches[0]['message'], payload.get('context'))
        append_audit('risk_evaluated', {
            'source': payload.get('source', 'manual'),
            'breach_count': len(breaches),
        })
        return {
            'mission': 'QNT50004',
            'status': 'ok' if not breaches else 'warning',
            'armed': bool(state.get('armed', True)),
            'kill_switch_triggered': bool(state.get('kill_switch_triggered', False)),
            'breaches': breaches,
            'metrics': state['metrics'],
        }

    def reset(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        state = self._refresh()
        approver = payload.get('approver') or 'operator'
        reason = payload.get('reason') or 'manual reset'
        preserve_armed = bool(payload.get('preserve_armed', True))
        state['kill_switch_triggered'] = False
        state['kill_switch_level'] = 'normal'
        state['trigger_reason'] = None
        state['triggered_at'] = None
        state['reset_at'] = int(time.time())
        state['active_breaches'] = []
        state['metrics']['breach_count'] = 0
        state['armed'] = preserve_armed
        state.setdefault('override_log', []).insert(0, {
            'action': 'reset',
            'approver': approver,
            'reason': reason,
            'timestamp': state['reset_at'],
            'preserve_armed': preserve_armed,
        })
        state['override_log'] = state['override_log'][:200]
        save_state(state)
        append_audit('kill_switch_reset', {'approver': approver, 'reason': reason})
        return self.summary()

    def override(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        state = self._refresh()
        approver = payload.get('approver') or 'operator'
        ticket_id = payload.get('ticket_id') or 'override_required'
        reason = payload.get('reason') or 'controlled override'
        keep_armed = bool(payload.get('keep_armed', True))
        state['kill_switch_triggered'] = False
        state['kill_switch_level'] = 'override'
        state['trigger_reason'] = None
        state['triggered_at'] = None
        state['armed'] = keep_armed
        state['active_breaches'] = []
        state['metrics']['breach_count'] = 0
        state.setdefault('override_log', []).insert(0, {
            'action': 'override',
            'approver': approver,
            'ticket_id': ticket_id,
            'reason': reason,
            'timestamp': int(time.time()),
            'keep_armed': keep_armed,
        })
        state['override_log'] = state['override_log'][:200]
        save_state(state)
        append_audit('kill_switch_override_applied', {
            'approver': approver,
            'ticket_id': ticket_id,
            'reason': reason,
        })
        return self.summary()

    def triggers(self, limit: int = 25) -> Dict[str, Any]:
        state = self._refresh()
        use_limit = max(1, min(int(limit), 100))
        return {
            'mission': 'QNT50004',
            'trigger_log': state.get('trigger_log', [])[:use_limit],
            'override_log': state.get('override_log', [])[:use_limit],
            'blocked_orders': state.get('blocked_orders', [])[:use_limit],
            'audit_log': state.get('audit_log', [])[:use_limit],
        }

    def pre_trade_check(self, envelope: Dict[str, Any]) -> Dict[str, Any]:
        state = self._refresh()
        if state.get('kill_switch_triggered', False):
            state.setdefault('blocked_orders', []).insert(0, {
                'blocked_at': int(time.time()),
                'decision_id': envelope.get('decision_id'),
                'strategy_id': envelope.get('strategy_id'),
                'symbol': envelope.get('symbol'),
                'reason': state.get('trigger_reason') or 'kill switch active',
            })
            state['blocked_orders'] = state['blocked_orders'][:200]
            save_state(state)
            append_audit('trade_blocked_by_kill_switch', {
                'decision_id': envelope.get('decision_id'),
                'strategy_id': envelope.get('strategy_id'),
                'symbol': envelope.get('symbol'),
            })
            raise PermissionError(state.get('trigger_reason') or 'risk kill-switch active')

        price = float(envelope.get('price') or 0.0)
        qty = float(envelope.get('qty') or 0.0)
        order_notional = float(envelope.get('notional_estimate') or (qty * price if price > 0 else qty))
        evaluation = self.evaluate({
            'source': 'pre_trade_check',
            'context': {
                'decision_id': envelope.get('decision_id'),
                'strategy_id': envelope.get('strategy_id'),
                'symbol': envelope.get('symbol'),
            },
            'metrics': state.get('metrics') or {},
        })
        state = self._refresh()
        breaches = self._detect_breaches(state.get('metrics') or {}, state.get('thresholds') or {}, order_notional=order_notional)
        if state.get('armed', True) and breaches and any(b.get('severity') == 'critical' for b in breaches):
            self._engage(state, breaches, 'pre_trade_check', breaches[0]['message'], {
                'decision_id': envelope.get('decision_id'),
                'strategy_id': envelope.get('strategy_id'),
                'symbol': envelope.get('symbol'),
                'order_notional': order_notional,
            })
            raise PermissionError(breaches[0]['message'])
        return evaluation
