from __future__ import annotations

import time
import uuid
from typing import Any, Dict, List

from backend.app.autonomous_execution.state_store import append_audit, load_state, save_state
from backend.app.execution.fill_handler import append_audit as append_execution_audit
from backend.app.execution.fill_handler import load_state as load_execution_state
from backend.app.execution.order_router import OrderRouter
from backend.app.performance_engine.state_store import load_state as load_performance_state
from backend.app.risk_control.state_store import load_state as load_risk_state
from backend.app.strategy_deployment.state_store import load_state as load_deployment_state


class AutonomousExecutionEngine:
    ACTION_PRIORITY = {
        'activate': 5,
        'scale_up': 4,
        'hold': 3,
        'scale_down': 2,
        'retire': 1,
    }

    def __init__(self):
        self.state = load_state()

    def _refresh(self) -> Dict[str, Any]:
        self.state = load_state()
        return self.state

    @staticmethod
    def _round(value: float, digits: int = 6) -> float:
        return round(float(value or 0.0), digits)

    def _environment(self) -> Dict[str, Any]:
        risk = load_risk_state()
        execution = load_execution_state()
        performance = load_performance_state()
        deployment = load_deployment_state()
        metrics = performance.get('metrics') or {}
        investor_metrics = performance.get('investor_metrics') or {}
        return {
            'risk': risk,
            'execution': execution,
            'performance': performance,
            'deployment': deployment,
            'sharpe_ratio': float(metrics.get('sharpe_ratio') or 0.0),
            'current_drawdown_pct': float(metrics.get('current_drawdown_pct') or metrics.get('max_drawdown_pct') or 0.0),
            'latest_equity': float(investor_metrics.get('latest_equity') or 0.0),
            'current_regime': str((deployment.get('current_plan') or {}).get('regime') or deployment.get('current_regime') or 'neutral').lower(),
        }

    def _queue_summary(self, state: Dict[str, Any]) -> Dict[str, Any]:
        queue = state.get('decision_queue') or []
        return {
            'queued_count': len(queue),
            'ready_count': len([q for q in queue if q.get('status') == 'queued']),
            'planned_count': len([q for q in queue if q.get('status') == 'planned']),
            'executed_count': len([q for q in queue if q.get('status') == 'executed']),
            'manual_review_count': len([q for q in queue if q.get('status') == 'manual_review']),
            'failed_count': len([q for q in queue if q.get('status') == 'failed']),
        }

    def _gating(self, state: Dict[str, Any], env: Dict[str, Any]) -> Dict[str, Any]:
        policy = state.get('policy') or {}
        execution = env['execution']
        risk = env['risk']
        issues: List[str] = []
        target_mode = execution.get('mode', 'paper')
        if risk.get('kill_switch_triggered'):
            issues.append('risk kill switch is triggered')
        if env['sharpe_ratio'] < float(policy.get('minimum_sharpe_ratio', 0.0)):
            issues.append('performance threshold below autonomous minimum sharpe ratio')
        if env['current_drawdown_pct'] > float(policy.get('maximum_drawdown_pct', 1.0)):
            issues.append('drawdown exceeds autonomous threshold')
        if env['current_regime'] == 'stress' and not bool(policy.get('allow_regime_stress', False)):
            issues.append('stress regime blocks autonomous execution')
        if target_mode == 'paper' and not bool(policy.get('auto_execute_paper', True)):
            issues.append('paper autonomous execution disabled by policy')
        if target_mode == 'live':
            if execution.get('safe_mode', True):
                issues.append('safe mode blocks live autonomous execution')
            if execution.get('active_broker') == 'paper':
                issues.append('paper broker cannot be used for live autonomous execution')
            if not bool(policy.get('auto_execute_live', False)):
                issues.append('live autonomous execution disabled by policy')
        enabled = bool(policy.get('enabled', False))
        readiness = enabled and not issues and len(state.get('decision_queue') or []) > 0
        return {
            'enabled': enabled,
            'target_mode': target_mode,
            'issues': issues,
            'ready': readiness,
        }

    def configure(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        state = self._refresh()
        policy = dict(state.get('policy') or {})
        for key in [
            'enabled', 'auto_execute_paper', 'auto_execute_live', 'require_committee_ticket_for_live',
            'max_orders_per_cycle', 'max_cycle_notional', 'minimum_sharpe_ratio', 'maximum_drawdown_pct',
            'allow_regime_stress', 'default_order_type', 'participation_rate'
        ]:
            if payload.get(key) is not None:
                policy[key] = payload[key]
        if payload.get('price_map'):
            state.setdefault('price_map', {}).update({k.upper(): float(v) for k, v in payload['price_map'].items() if float(v) > 0})
        state['policy'] = policy
        save_state(state)
        append_audit('autonomous_policy_configured', {'enabled': policy.get('enabled', False)})
        return self.summary()

    def ingest_release_queue(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        state = self._refresh()
        deployment = load_deployment_state()
        queue_index = int(payload.get('queue_index', 0))
        release_queue = deployment.get('release_queue') or []
        if queue_index >= len(release_queue):
            raise ValueError('strategy deployment release queue index out of range')
        release = release_queue[queue_index]
        tickets = release.get('tickets') or []
        if payload.get('clear_existing'):
            state['decision_queue'] = []
        seen_keys = {
            (str(item.get('decision_id')), str(item.get('strategy_id')), str(item.get('routing_action')))
            for item in state.get('decision_queue', [])
            if item.get('status') in {'queued', 'planned'}
        }
        inserted = []
        for ticket in tickets:
            key = (str(ticket.get('decision_id')), str(ticket.get('strategy_id')), str(ticket.get('routing_action')))
            if key in seen_keys:
                continue
            item = {
                'queue_item_id': f'autoq_{uuid.uuid4().hex[:12]}',
                'deployment_id': ticket.get('deployment_id'),
                'decision_id': ticket.get('decision_id'),
                'source_allocation_id': ticket.get('source_allocation_id'),
                'source_decision_id': ticket.get('source_decision_id'),
                'strategy_id': ticket.get('strategy_id'),
                'symbol': str(ticket.get('symbol') or '').upper(),
                'target_capital': round(float(ticket.get('target_capital') or 0.0), 2),
                'target_weight': float(ticket.get('target_weight') or 0.0),
                'routing_action': ticket.get('routing_action') or 'hold',
                'broker': ticket.get('broker') or 'paper',
                'regime': ticket.get('regime') or 'neutral',
                'risk_tag': ticket.get('risk_tag') or 'AUTO_EXEC',
                'staged_at': ticket.get('staged_at') or int(time.time()),
                'status': 'queued',
                'queue_notes': 'ingested from QNT50003 release queue',
            }
            state.setdefault('decision_queue', []).append(item)
            inserted.append(item)
            seen_keys.add(key)
        state['release_queue_cache'] = release_queue[:10]
        save_state(state)
        append_audit('release_queue_ingested', {
            'queue_index': queue_index,
            'inserted_count': len(inserted),
            'deployment_id': release.get('deployment_id'),
        })
        return {
            'mission': 'QNT50006',
            'status': 'ingested',
            'queue_index': queue_index,
            'deployment_id': release.get('deployment_id'),
            'inserted_count': len(inserted),
            'queue_summary': self._queue_summary(load_state()),
        }

    def _sorted_candidates(self, queue: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return sorted(
            [q for q in queue if q.get('status') in {'queued', 'planned'}],
            key=lambda item: (self.ACTION_PRIORITY.get(str(item.get('routing_action') or 'hold'), 0), float(item.get('target_capital') or 0.0)),
            reverse=True,
        )

    def _resolve_price(self, state: Dict[str, Any], payload: Dict[str, Any], symbol: str) -> float:
        prices = {str(k).upper(): float(v) for k, v in (payload.get('market_prices') or {}).items() if float(v) > 0}
        if symbol.upper() in prices:
            return prices[symbol.upper()]
        return float((state.get('price_map') or {}).get(symbol.upper()) or 0.0)

    def _manual_escalation(self, item: Dict[str, Any], reason: str) -> Dict[str, Any]:
        return {
            'queue_item_id': item.get('queue_item_id'),
            'strategy_id': item.get('strategy_id'),
            'symbol': item.get('symbol'),
            'routing_action': item.get('routing_action'),
            'reason': reason,
            'created_at': int(time.time()),
        }

    def plan_cycle(self, payload: Dict[str, Any] | None = None) -> Dict[str, Any]:
        payload = payload or {}
        state = self._refresh()
        if not state.get('decision_queue') and payload.get('ingest_if_empty', True):
            deployment = load_deployment_state()
            if deployment.get('release_queue'):
                self.ingest_release_queue({'queue_index': 0, 'clear_existing': False})
                state = self._refresh()
        env = self._environment()
        gate = self._gating(state, env)
        policy = state.get('policy') or {}
        queue = self._sorted_candidates(state.get('decision_queue') or [])
        max_orders = int(payload.get('max_orders') or policy.get('max_orders_per_cycle') or 1)
        queue_item_limit = int(payload.get('queue_item_limit') or max_orders)
        cycle_notional_limit = float(payload.get('cycle_notional_limit') or policy.get('max_cycle_notional') or 0.0)
        participation_rate = float(payload.get('participation_rate') or policy.get('participation_rate') or 1.0)
        portfolio_value = env['latest_equity'] or 1000000.0
        plans: List[Dict[str, Any]] = []
        blocked: List[Dict[str, Any]] = []
        remaining = cycle_notional_limit
        for item in queue[:queue_item_limit]:
            action = str(item.get('routing_action') or 'hold')
            symbol = str(item.get('symbol') or '').upper()
            price = self._resolve_price(state, payload, symbol)
            if action in {'retire', 'scale_down'}:
                blocked.append(self._manual_escalation(item, 'position inventory and exit trajectory required for reduction path'))
                continue
            if price <= 0:
                blocked.append(self._manual_escalation(item, 'missing market price for symbol'))
                continue
            target_capital = max(float(item.get('target_capital') or 0.0), 0.0)
            desired_notional = round(target_capital * participation_rate, 2)
            if cycle_notional_limit > 0:
                planned_notional = round(min(desired_notional, remaining), 2)
                if planned_notional <= 0:
                    blocked.append(self._manual_escalation(item, 'cycle notional limit exhausted'))
                    continue
                remaining = max(0.0, round(remaining - planned_notional, 2))
            else:
                planned_notional = desired_notional
            qty = self._round(planned_notional / price, 8)
            if qty <= 0:
                blocked.append(self._manual_escalation(item, 'planned quantity rounded to zero'))
                continue
            envelope = {
                'symbol': symbol,
                'side': 'BUY',
                'qty': qty,
                'order_type': policy.get('default_order_type', 'MARKET'),
                'price': price,
                'strategy_id': item.get('strategy_id'),
                'allocation_id': item.get('source_allocation_id') or item.get('deployment_id') or f'alloc_{uuid.uuid4().hex[:8]}',
                'risk_tag': item.get('risk_tag') or 'AUTO_EXEC',
                'decision_id': f"{item.get('decision_id') or 'decision'}_auto_{uuid.uuid4().hex[:8]}",
                'venue_hint': item.get('broker'),
                'notional_estimate': planned_notional,
                'portfolio_value_snapshot': portfolio_value,
            }
            plans.append({
                'queue_item_id': item.get('queue_item_id'),
                'strategy_id': item.get('strategy_id'),
                'symbol': symbol,
                'routing_action': action,
                'price': price,
                'planned_notional': planned_notional,
                'planned_qty': qty,
                'broker_preference': item.get('broker'),
                'envelope': envelope,
            })
            if len(plans) >= max_orders:
                break
        plan = {
            'mission': 'QNT50006',
            'plan_id': f'auto_plan_{uuid.uuid4().hex[:12]}',
            'generated_at': int(time.time()),
            'status': 'ready' if gate.get('ready') and plans else ('blocked' if gate.get('issues') else 'empty'),
            'target_mode': gate.get('target_mode'),
            'gate': gate,
            'planned_orders': plans,
            'blocked_items': blocked,
            'queue_depth': len(queue),
            'cycle_notional_limit': cycle_notional_limit,
            'remaining_notional_capacity': remaining,
        }
        state['last_plan'] = plan
        plan_ids = {p.get('queue_item_id') for p in plans}
        block_ids = {b.get('queue_item_id') for b in blocked}
        for item in state.get('decision_queue', []):
            if item.get('queue_item_id') in plan_ids:
                item['status'] = 'planned'
                item['planned_at'] = plan['generated_at']
            elif item.get('queue_item_id') in block_ids:
                item['status'] = 'manual_review'
        save_state(state)
        append_audit('autonomous_cycle_planned', {
            'plan_id': plan['plan_id'],
            'planned_order_count': len(plans),
            'blocked_count': len(blocked),
            'status': plan['status'],
        })
        return plan

    def execute_cycle(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        state = self._refresh()
        plan = self.plan_cycle(payload)
        if plan.get('status') != 'ready':
            return {'mission': 'QNT50006', 'status': plan.get('status'), 'plan': plan, 'executions': []}
        if not state.get('policy', {}).get('enabled') and not payload.get('allow_when_disabled', False):
            return {'mission': 'QNT50006', 'status': 'blocked', 'reason': 'autonomous execution policy is disabled', 'plan': plan, 'executions': []}
        executions: List[Dict[str, Any]] = []
        escalations: List[Dict[str, Any]] = []
        state = self._refresh()
        queue_lookup = {item.get('queue_item_id'): item for item in state.get('decision_queue', [])}
        for planned in plan.get('planned_orders', []):
            queue_item = queue_lookup.get(planned.get('queue_item_id'))
            try:
                response = OrderRouter().route(planned['envelope'])
                executions.append({
                    'queue_item_id': planned.get('queue_item_id'),
                    'strategy_id': planned.get('strategy_id'),
                    'symbol': planned.get('symbol'),
                    'planned_notional': planned.get('planned_notional'),
                    'execution': response,
                })
                if queue_item is not None:
                    queue_item['status'] = 'executed'
                    queue_item['executed_at'] = int(time.time())
                    queue_item['execution_order_id'] = response.get('order_id')
            except Exception as exc:
                escalation = {
                    'queue_item_id': planned.get('queue_item_id'),
                    'strategy_id': planned.get('strategy_id'),
                    'symbol': planned.get('symbol'),
                    'reason': str(exc),
                    'created_at': int(time.time()),
                    'plan_id': plan.get('plan_id'),
                }
                escalations.append(escalation)
                if queue_item is not None:
                    queue_item['status'] = 'failed'
                    queue_item['failed_at'] = escalation['created_at']
                    queue_item['failure_reason'] = escalation['reason']
        state.setdefault('escalations', []).extend(plan.get('blocked_items', []))
        state.setdefault('escalations', []).extend(escalations)
        state['escalations'] = state['escalations'][-500:]
        cycle = {
            'cycle_id': f'auto_cycle_{uuid.uuid4().hex[:12]}',
            'executed_at': int(time.time()),
            'plan_id': plan.get('plan_id'),
            'approver': payload.get('approver') or 'autonomous_execution_layer',
            'notes': payload.get('notes') or 'controlled autonomous execution cycle',
            'target_mode': plan.get('target_mode'),
            'executions': executions,
            'blocked_items': plan.get('blocked_items', []),
            'escalations': escalations,
            'status': 'completed' if executions and not escalations else ('partial' if executions else 'escalated'),
        }
        state['last_cycle'] = cycle
        state.setdefault('cycle_history', []).insert(0, cycle)
        state['cycle_history'] = state['cycle_history'][:200]
        save_state(state)
        append_audit('autonomous_cycle_executed', {
            'cycle_id': cycle['cycle_id'],
            'execution_count': len(executions),
            'escalation_count': len(plan.get('blocked_items', [])) + len(escalations),
            'status': cycle['status'],
        })
        append_execution_audit('autonomous_execution_cycle_completed', {
            'cycle_id': cycle['cycle_id'],
            'execution_count': len(executions),
            'status': cycle['status'],
        })
        return {'mission': 'QNT50006', 'status': cycle['status'], 'cycle': cycle, 'queue_summary': self._queue_summary(load_state())}

    def reset(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        state = self._refresh()
        approver = payload.get('approver') or 'operator'
        reason = payload.get('reason') or 'manual reset'
        state['decision_queue'] = []
        state['last_plan'] = None
        state['last_cycle'] = None
        if payload.get('clear_escalations'):
            state['escalations'] = []
        save_state(state)
        append_audit('autonomous_execution_reset', {'approver': approver, 'reason': reason})
        return self.summary()

    def summary(self) -> Dict[str, Any]:
        state = self._refresh()
        env = self._environment()
        gate = self._gating(state, env)
        return {
            'mission': 'QNT50006',
            'status': 'ok',
            'policy': state.get('policy', {}),
            'gate': gate,
            'queue_summary': self._queue_summary(state),
            'current_regime': env.get('current_regime'),
            'sharpe_ratio': env.get('sharpe_ratio'),
            'current_drawdown_pct': env.get('current_drawdown_pct'),
            'latest_equity': env.get('latest_equity'),
            'execution_mode': env['execution'].get('mode', 'paper'),
            'safe_mode': bool(env['execution'].get('safe_mode', True)),
            'active_broker': env['execution'].get('active_broker', 'paper'),
            'kill_switch_triggered': bool(env['risk'].get('kill_switch_triggered', False)),
            'last_plan': state.get('last_plan'),
            'last_cycle': state.get('last_cycle'),
        }
