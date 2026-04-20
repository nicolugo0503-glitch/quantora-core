
from __future__ import annotations

import time
import uuid
from typing import Any, Dict, List, Optional

from backend.app.autonomous_control_loop.state_store import append_audit, load_state, save_state
from backend.app.autonomous_execution.engine import AutonomousExecutionEngine
from backend.app.autonomous_execution.state_store import load_state as load_autonomous_execution_state
from backend.app.intercompany_ledger.state_store import load_state as load_intercompany_state
from backend.app.performance_engine.state_store import load_state as load_performance_state
from backend.app.risk_control.state_store import load_state as load_risk_state
from backend.app.strategy_deployment.state_store import load_state as load_deployment_state
from backend.app.treasury_cash_mobility.state_store import load_state as load_treasury_state


class AutonomousControlLoopEngine:
    def __init__(self):
        self.state = load_state()
        self.auto_exec = AutonomousExecutionEngine()

    def _refresh(self) -> Dict[str, Any]:
        self.state = load_state()
        return self.state

    @staticmethod
    def _round(value: Any, digits: int = 4) -> float:
        return round(float(value or 0.0), digits)

    def _policy(self, state: Dict[str, Any]) -> Dict[str, Any]:
        return dict(state.get('policy') or {})

    def _system_snapshot(self, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        payload = payload or {}
        risk = load_risk_state()
        perf = load_performance_state()
        treasury = load_treasury_state()
        deploy = load_deployment_state()
        auto_exec_state = load_autonomous_execution_state()
        intercompany = load_intercompany_state()
        metrics = perf.get('metrics') or {}
        investor_metrics = perf.get('investor_metrics') or {}
        treasury_sync = treasury.get('last_sync') or {}
        release_queue = deploy.get('release_queue') or []
        decision_queue = auto_exec_state.get('decision_queue') or []
        open_intercompany = [x for x in intercompany.get('flow_cases') or [] if x.get('status') not in {'settled', 'rejected'}]
        return {
            'synced_at': int(time.time()),
            'source': str(payload.get('source') or 'manual'),
            'risk_triggered': bool(risk.get('kill_switch_triggered')),
            'risk_level': str(risk.get('kill_switch_level') or 'normal'),
            'safe_mode': bool(deploy.get('safe_mode', True)),
            'execution_mode': str(deploy.get('execution_mode') or 'paper'),
            'cumulative_return_pct': self._round(metrics.get('cumulative_return_pct'), 6),
            'latest_equity': self._round(investor_metrics.get('latest_equity') or 0.0, 2),
            'available_to_move': self._round(treasury_sync.get('available_to_move') or 0.0, 2),
            'cash_balance': self._round(treasury_sync.get('cash_balance') or 0.0, 2),
            'settlement_status': str(treasury_sync.get('settlement_status') or ''),
            'release_queue_count': len(release_queue),
            'autonomous_decision_queue_count': len(decision_queue),
            'open_intercompany_flow_count': len(open_intercompany),
            'latest_release_id': str((release_queue[0] if release_queue else {}).get('deployment_id') or ''),
            'current_regime': str((deploy.get('current_plan') or {}).get('regime') or deploy.get('current_regime') or 'neutral'),
        }

    def sync_context(self, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        payload = payload or {}
        state = self._refresh()
        snapshot = self._system_snapshot(payload)
        state['last_sync'] = snapshot
        state.setdefault('sync_history', []).insert(0, snapshot)
        state['sync_history'] = state['sync_history'][:500]
        save_state(state)
        append_audit('autonomous_control_context_synced', snapshot)
        return {'mission': 'QNT50022', 'status': 'synced', 'snapshot': snapshot}

    def _ensure_sync(self, state: Dict[str, Any], source: str = 'auto') -> Dict[str, Any]:
        if self._policy(state).get('auto_sync_sources', True) and not state.get('last_sync'):
            self.sync_context({'source': source})
            state = self._refresh()
        return state

    def _gate(self, state: Dict[str, Any]) -> Dict[str, Any]:
        policy = self._policy(state)
        snap = state.get('last_sync') or self._system_snapshot({'source': 'direct'})
        issues: List[str] = []
        if not bool(policy.get('enabled', True)):
            issues.append('autonomous control loop disabled by policy')
        if policy.get('require_risk_clearance', True) and snap.get('risk_triggered'):
            issues.append('risk kill switch is active')
        if policy.get('require_liquidity_capacity', True) and float(snap.get('available_to_move') or 0.0) < float(policy.get('minimum_available_liquidity') or 0.0):
            issues.append('available liquidity below policy minimum')
        if policy.get('require_intercompany_clear', False) and int(snap.get('open_intercompany_flow_count') or 0) > 0:
            issues.append('open intercompany ledger items block autonomous control loop')
        if policy.get('require_positive_performance_bias', False) and float(snap.get('cumulative_return_pct') or 0.0) < float(policy.get('minimum_cumulative_return_pct') or 0.0):
            issues.append('performance posture below autonomous policy minimum')
        if int(snap.get('release_queue_count') or 0) <= 0 and int(snap.get('autonomous_decision_queue_count') or 0) <= 0:
            issues.append('no deployable strategy tickets available')
        return {
            'ready': len(issues) == 0,
            'issues': issues,
            'snapshot': snap,
        }

    def summary(self) -> Dict[str, Any]:
        state = self._ensure_sync(self._refresh())
        gate = self._gate(state)
        posture = 'ready' if gate.get('ready') else 'guarded'
        if any('risk' in issue for issue in gate.get('issues') or []):
            posture = 'blocked'
        state['status'] = posture
        save_state(state)
        return {
            'mission': 'QNT50022',
            'posture': posture,
            'policy': state.get('policy'),
            'latest_sync': state.get('last_sync'),
            'plan_count': len(state.get('control_plans') or []),
            'cycle_count': len(state.get('control_cycles') or []),
            'escalation_count': len(state.get('escalations') or []),
            'gate': gate,
        }

    def configure(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        state = self._refresh()
        policy = self._policy(state)
        for key in [
            'enabled', 'auto_sync_sources', 'auto_ingest_release_queue', 'require_risk_clearance',
            'require_liquidity_capacity', 'require_intercompany_clear', 'require_positive_performance_bias',
            'minimum_available_liquidity', 'minimum_cumulative_return_pct', 'max_cycles_to_keep'
        ]:
            if payload.get(key) is not None:
                policy[key] = payload[key]
        state['policy'] = policy
        save_state(state)
        append_audit('autonomous_control_policy_configured', {'policy': policy})
        if payload.get('sync_after_configure', True):
            self.sync_context({'source': 'configure'})
        return self.summary()

    def plan_loop(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        state = self._ensure_sync(self._refresh(), source=str(payload.get('source') or 'plan'))
        if self._policy(state).get('auto_sync_sources', True):
            self.sync_context({'source': str(payload.get('source') or 'plan')})
            state = self._refresh()
        gate = self._gate(state)
        plan = {
            'plan_id': f'ctl_plan_{uuid.uuid4().hex[:12]}',
            'created_at': int(time.time()),
            'created_by': str(payload.get('operator') or 'system'),
            'source': str(payload.get('source') or 'manual'),
            'snapshot': state.get('last_sync'),
            'gate': gate,
            'status': 'ready' if gate.get('ready') else 'escalated',
            'autonomous_plan': None,
            'autonomous_execution_plan_id': '',
            'actions': [],
        }
        if gate.get('ready'):
            if self._policy(state).get('auto_ingest_release_queue', True):
                try:
                    self.auto_exec.ingest_release_queue({
                        'queue_index': int(payload.get('queue_index', 0)),
                        'clear_existing': False,
                    })
                except Exception:
                    pass
            auto_plan = self.auto_exec.plan_cycle({
                'ingest_if_empty': bool(payload.get('ingest_if_empty', True)),
                'max_orders': int(payload.get('max_orders', 3)),
                'cycle_notional_limit': float(payload.get('cycle_notional_limit', 250000.0)),
                'market_prices': payload.get('market_prices') or {},
            })
            plan['autonomous_plan'] = auto_plan
            plan['autonomous_execution_plan_id'] = str(auto_plan.get('plan_id') or '')
            plan['actions'] = [
                'sync_context',
                'ingest_release_queue_if_needed',
                'plan_autonomous_execution_cycle',
                'escalate_if_reductions_or_limits_block_execution',
            ]
            if auto_plan.get('status') not in {'ready', 'planned'}:
                plan['status'] = 'escalated'
                state.setdefault('escalations', []).insert(0, {
                    'escalation_id': f'ctl_esc_{uuid.uuid4().hex[:12]}',
                    'created_at': int(time.time()),
                    'reason': 'autonomous execution plan did not return ready/planned status',
                    'plan_id': plan['plan_id'],
                    'autonomous_plan_status': auto_plan.get('status'),
                })
        else:
            state.setdefault('escalations', []).insert(0, {
                'escalation_id': f'ctl_esc_{uuid.uuid4().hex[:12]}',
                'created_at': int(time.time()),
                'reason': '; '.join(gate.get('issues') or ['control loop blocked']),
                'plan_id': plan['plan_id'],
            })
        state.setdefault('control_plans', []).insert(0, plan)
        state['control_plans'] = state['control_plans'][:200]
        state['escalations'] = state.get('escalations', [])[:200]
        save_state(state)
        append_audit('autonomous_control_plan_created', {
            'plan_id': plan['plan_id'],
            'status': plan['status'],
            'issue_count': len(gate.get('issues') or []),
        })
        return {'mission': 'QNT50022', 'status': plan['status'], 'plan': plan, 'summary': self.summary()}

    def _find_plan(self, state: Dict[str, Any], plan_id: str) -> Dict[str, Any]:
        for item in state.get('control_plans', []):
            if item.get('plan_id') == plan_id:
                return item
        raise ValueError('plan_id not found')

    def execute_loop(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        state = self._ensure_sync(self._refresh(), source=str(payload.get('source') or 'execute'))
        plan = None
        if payload.get('use_latest_plan', True):
            plan = (state.get('control_plans') or [None])[0]
        elif payload.get('plan_id'):
            plan = self._find_plan(state, str(payload.get('plan_id')))
        if not plan:
            raise ValueError('no control plan available for execution')
        cycle = {
            'cycle_id': f'ctl_cycle_{uuid.uuid4().hex[:12]}',
            'created_at': int(time.time()),
            'created_by': str(payload.get('operator') or 'system'),
            'source': str(payload.get('source') or 'manual'),
            'plan_id': plan.get('plan_id'),
            'status': 'blocked',
            'gate': plan.get('gate'),
            'execution_result': None,
        }
        if not (plan.get('gate') or {}).get('ready'):
            cycle['status'] = 'escalated'
            state.setdefault('escalations', []).insert(0, {
                'escalation_id': f'ctl_esc_{uuid.uuid4().hex[:12]}',
                'created_at': int(time.time()),
                'reason': 'control loop execution blocked by gate',
                'plan_id': plan.get('plan_id'),
                'cycle_id': cycle['cycle_id'],
            })
        else:
            auto_plan_id = str(plan.get('autonomous_execution_plan_id') or '')
            if not auto_plan_id and plan.get('autonomous_plan'):
                auto_plan_id = str(plan['autonomous_plan'].get('plan_id') or '')
            if not auto_plan_id:
                raise ValueError('autonomous execution plan reference missing')
            result = self.auto_exec.execute_cycle({
                'plan_id': auto_plan_id,
                'market_prices': payload.get('market_prices') or {},
            })
            cycle['execution_result'] = result
            cycle['status'] = str(result.get('status') or 'executed')
        state.setdefault('control_cycles', []).insert(0, cycle)
        keep = int(self._policy(state).get('max_cycles_to_keep', 200) or 200)
        state['control_cycles'] = state['control_cycles'][:keep]
        state['escalations'] = state.get('escalations', [])[:200]
        save_state(state)
        append_audit('autonomous_control_cycle_executed', {
            'cycle_id': cycle['cycle_id'],
            'plan_id': plan.get('plan_id'),
            'status': cycle['status'],
        })
        return {'mission': 'QNT50022', 'status': cycle['status'], 'cycle': cycle, 'summary': self.summary()}

    def reset(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        operator = str(payload.get('operator') or '').strip()
        if not operator:
            raise ValueError('operator is required')
        current = self._refresh()
        state = {
            'generated_by': 'QNT50022',
            'status': 'degraded',
            'policy': current.get('policy') or load_state().get('policy'),
            'last_sync': None,
            'sync_history': [],
            'control_plans': [],
            'control_cycles': [],
            'escalations': [],
            'audit_log': [],
        }
        save_state(state)
        append_audit('autonomous_control_reset', {
            'operator': operator,
            'reason': str(payload.get('reason') or 'manual reset'),
        })
        return self.summary()
