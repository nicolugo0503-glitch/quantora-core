from __future__ import annotations

import time
import uuid
from typing import Any, Dict

from backend.app.live_strategy_scale_up.state_store import append_audit, default_state, load_state, save_state
from backend.app.live_capital_reactivation.state_store import load_state as load_reentry_state
from backend.app.performance_engine.state_store import load_state as load_performance_state
from backend.app.risk_control.state_store import load_state as load_risk_state
from backend.app.strategy_deployment.state_store import load_state as load_strategy_state
from backend.app.treasury_cash_mobility.state_store import load_state as load_treasury_state


class LiveStrategyScaleUpEngine:
    def __init__(self):
        self.state = load_state()

    def _refresh(self):
        self.state = load_state()
        return self.state

    def _policy(self, state: Dict[str, Any]) -> Dict[str, Any]:
        return dict(default_state().get('policy', {}), **(state.get('policy') or {}))

    def _trim(self, state: Dict[str, Any]):
        policy = self._policy(state)
        state['scale_cases'] = (state.get('scale_cases') or [])[: int(policy.get('max_scale_cases', 250))]
        state['ramp_events'] = (state.get('ramp_events') or [])[: int(policy.get('max_ramp_events', 500))]
        state['audit_log'] = (state.get('audit_log') or [])[: int(policy.get('max_audit_events', 500))]

    def _source_snapshot(self) -> Dict[str, Any]:
        reentry = load_reentry_state()
        risk = load_risk_state()
        strategy = load_strategy_state()
        treasury = load_treasury_state()
        performance = load_performance_state()
        reentries = reentry.get('reentry_events') or []
        accounts = treasury.get('accounts') or {}
        total_treasury_balance = round(sum(float((v or {}).get('balance') or 0.0) for v in accounts.values()), 4)
        perf_returns = performance.get('return_series') or performance.get('returns') or []
        latest_return = 0.0
        if perf_returns:
            last = perf_returns[0] if isinstance(perf_returns[0], dict) else perf_returns[-1]
            if isinstance(last, dict):
                latest_return = float(last.get('net_return') or last.get('return') or 0.0)
            else:
                latest_return = float(last or 0.0)
        return {
            'synced_at': int(time.time()),
            'source': 'manual',
            'latest_reentry_event_id': (reentries[0] or {}).get('event_id') if reentries else '',
            'latest_reentry_status': (reentries[0] or {}).get('status') if reentries else '',
            'risk_triggered': bool(risk.get('kill_switch_triggered')),
            'risk_level': risk.get('kill_switch_level', 'normal'),
            'safe_mode': bool(strategy.get('safe_mode', True)),
            'execution_mode': str(strategy.get('execution_mode') or 'paper'),
            'current_regime': str(strategy.get('current_regime') or 'neutral'),
            'deployment_profiles': strategy.get('deployment_profiles') or [],
            'treasury_total_balance': total_treasury_balance,
            'broker_buffer_balance': float((accounts.get('broker_buffer') or {}).get('balance') or 0.0),
            'operating_balance': float((accounts.get('operating') or {}).get('balance') or 0.0),
            'latest_return': round(latest_return, 6),
        }

    def sync_context(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        state = self._refresh()
        snapshot = self._source_snapshot()
        snapshot['source'] = str(payload.get('source') or 'manual')
        state['last_sync'] = snapshot
        state.setdefault('sync_history', []).insert(0, snapshot)
        state['sync_history'] = state['sync_history'][:100]
        save_state(state)
        append_audit('live_strategy_scale_up_context_synced', snapshot)
        return {'mission': 'QNT50030', 'status': 'synced', 'snapshot': snapshot}

    def _ensure_sync(self, state: Dict[str, Any], source: str = 'auto') -> Dict[str, Any]:
        if not state.get('last_sync') and self._policy(state).get('auto_sync_sources', True):
            self.sync_context({'source': source})
            return self._refresh()
        return state

    def configure(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        state = self._refresh()
        policy = self._policy(state)
        for key, value in payload.items():
            if key in policy and value is not None:
                policy[key] = value
        state['policy'] = policy
        self._trim(state)
        save_state(state)
        append_audit('live_strategy_scale_up_configured', {'policy': policy})
        result = {'mission': 'QNT50030', 'status': 'configured', 'policy': policy}
        if payload.get('sync_after_configure', True):
            result['sync'] = self.sync_context({'source': 'configure'})
        return result

    def summary(self) -> Dict[str, Any]:
        state = self._ensure_sync(self._refresh())
        snapshot = state.get('last_sync') or {}
        active = [x for x in (state.get('scale_cases') or []) if str(x.get('status') or '').lower() not in {'closed', 'rejected'}]
        return {
            'mission': 'QNT50030',
            'posture': 'guarded' if snapshot.get('safe_mode') else 'controlled',
            'risk_triggered': bool(snapshot.get('risk_triggered')),
            'safe_mode': bool(snapshot.get('safe_mode')),
            'scale_case_count': len(state.get('scale_cases') or []),
            'open_scale_case_count': len(active),
            'ramp_event_count': len(state.get('ramp_events') or []),
            'current_regime': snapshot.get('current_regime'),
            'execution_mode': snapshot.get('execution_mode'),
            'latest_return': snapshot.get('latest_return'),
            'treasury_total_balance': snapshot.get('treasury_total_balance'),
        }

    def register_scale_case(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        state = self._ensure_sync(self._refresh())
        snapshot = state.get('last_sync') or {}
        policy = self._policy(state)
        reentry_event_id = str(payload.get('reentry_event_id') or '').strip()
        strategy_id = str(payload.get('strategy_id') or '').strip()
        if not reentry_event_id or not strategy_id:
            raise ValueError('reentry_event_id and strategy_id are required')
        reentry_state = load_reentry_state()
        reentry_event = next((x for x in (reentry_state.get('reentry_events') or []) if x.get('event_id') == reentry_event_id), None)
        if not reentry_event:
            raise ValueError('reentry_event_id not found')
        if policy.get('require_reentry_execution', True) and str(reentry_event.get('status') or '').lower() != 'executed':
            raise ValueError('re-entry event must be executed before scale-up registration')
        if policy.get('require_positive_performance_signal', False) and float(snapshot.get('latest_return') or 0.0) <= 0:
            raise ValueError('positive performance signal required for scale-up registration')
        profile = next((x for x in (snapshot.get('deployment_profiles') or []) if x.get('strategy_id') == strategy_id), None)
        requested_ramp_capital = round(float(payload.get('requested_ramp_capital') or 0.0), 4)
        if requested_ramp_capital <= 0:
            raise ValueError('requested_ramp_capital must be greater than zero')
        if policy.get('require_treasury_capacity', True) and requested_ramp_capital > float(snapshot.get('treasury_total_balance') or 0.0):
            raise ValueError('requested ramp capital exceeds treasury capacity')
        case = {
            'scale_case_id': f'scale_case_{uuid.uuid4().hex[:12]}',
            'created_at': int(time.time()),
            'operator': str(payload.get('operator') or '').strip(),
            'title': str(payload.get('title') or '').strip(),
            'reentry_event_id': reentry_event_id,
            'strategy_id': strategy_id,
            'symbol': str(payload.get('symbol') or reentry_event.get('symbol') or (profile or {}).get('symbol') or '').strip(),
            'broker': str(payload.get('broker') or reentry_event.get('broker') or ((profile or {}).get('allowed_brokers') or ['paper'])[0]).strip(),
            'current_capital': round(float(payload.get('current_capital') or reentry_event.get('capital_activated') or 0.0), 4),
            'requested_ramp_capital': requested_ramp_capital,
            'requested_target_weight': round(float(payload.get('requested_target_weight') or 0.0), 4),
            'ramp_steps': int(payload.get('ramp_steps') or policy.get('default_max_ramp_steps', 5)),
            'max_ramp_pct': round(float(payload.get('max_ramp_pct') or policy.get('default_max_ramp_pct', 0.25)), 4),
            'ramp_reason': str(payload.get('ramp_reason') or '').strip(),
            'notes': str(payload.get('notes') or '').strip(),
            'regime': snapshot.get('current_regime', 'neutral'),
            'status': 'registered',
        }
        if not case['operator'] or not case['title']:
            raise ValueError('operator and title are required')
        state.setdefault('scale_cases', []).insert(0, case)
        self._trim(state)
        save_state(state)
        append_audit('live_strategy_scale_case_registered', case)
        return {'mission': 'QNT50030', 'status': 'registered', 'scale_case': case}

    def approve_ramp(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        state = self._ensure_sync(self._refresh())
        snapshot = state.get('last_sync') or {}
        policy = self._policy(state)
        scale_case_id = str(payload.get('scale_case_id') or '').strip()
        case = next((x for x in (state.get('scale_cases') or []) if x.get('scale_case_id') == scale_case_id), None)
        if not case:
            raise ValueError('scale_case_id not found')
        if policy.get('require_risk_clearance', True) and snapshot.get('risk_triggered'):
            raise ValueError('cannot approve ramp while risk kill-switch is active')
        approved_ramp_capital = round(float(payload.get('approved_ramp_capital') or case.get('requested_ramp_capital') or 0.0), 4)
        if approved_ramp_capital <= 0:
            raise ValueError('approved_ramp_capital must be greater than zero')
        mode = str(payload.get('mode') or 'paper').strip().lower()
        if mode == 'live' and (snapshot.get('safe_mode') or not policy.get('allow_live_scale_up', False)):
            raise ValueError('live scale-up approval is blocked while safe mode is enabled or live scale-up policy is disabled')
        case['status'] = 'approved'
        case['approved_at'] = int(time.time())
        case['approved_by'] = str(payload.get('operator') or '').strip()
        case['approved_ramp_capital'] = approved_ramp_capital
        case['approved_target_weight'] = round(float(payload.get('approved_target_weight') or case.get('requested_target_weight') or 0.0), 4)
        case['approved_mode'] = mode
        case['approval_notes'] = str(payload.get('approval_notes') or '').strip()
        save_state(state)
        append_audit('live_strategy_ramp_approved', {'scale_case_id': scale_case_id, 'approved_ramp_capital': approved_ramp_capital, 'mode': mode})
        return {'mission': 'QNT50030', 'status': 'approved', 'scale_case': case}

    def execute_ramp(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        state = self._ensure_sync(self._refresh())
        snapshot = state.get('last_sync') or {}
        scale_case_id = str(payload.get('scale_case_id') or '').strip()
        case = next((x for x in (state.get('scale_cases') or []) if x.get('scale_case_id') == scale_case_id), None)
        if not case:
            raise ValueError('scale_case_id not found')
        if str(case.get('status') or '').lower() != 'approved':
            raise ValueError('scale case must be approved before ramp execution')
        mode = str(payload.get('execution_mode') or case.get('approved_mode') or 'paper').strip().lower()
        if mode == 'live' and (snapshot.get('risk_triggered') or snapshot.get('safe_mode')):
            raise ValueError('live ramp execution blocked by risk or safe mode posture')
        ramp_capital_deployed = round(float(payload.get('ramp_capital_deployed') or case.get('approved_ramp_capital') or 0.0), 4)
        if ramp_capital_deployed <= 0:
            raise ValueError('ramp_capital_deployed must be greater than zero')
        event = {
            'ramp_event_id': f'ramp_event_{uuid.uuid4().hex[:12]}',
            'executed_at': int(time.time()),
            'operator': str(payload.get('operator') or '').strip(),
            'scale_case_id': scale_case_id,
            'reentry_event_id': case.get('reentry_event_id'),
            'strategy_id': case.get('strategy_id'),
            'symbol': case.get('symbol'),
            'broker': case.get('broker'),
            'execution_mode': mode,
            'ramp_capital_deployed': ramp_capital_deployed,
            'target_weight': round(float(payload.get('target_weight') or case.get('approved_target_weight') or 0.0), 4),
            'release_to': str(payload.get('release_to') or 'allocation_engine').strip(),
            'result_summary': str(payload.get('result_summary') or '').strip(),
            'status': 'executed',
        }
        case['status'] = 'executed'
        case['executed_at'] = event['executed_at']
        case['last_ramp_event_id'] = event['ramp_event_id']
        state.setdefault('ramp_events', []).insert(0, event)
        self._trim(state)
        save_state(state)
        append_audit('live_strategy_ramp_executed', event)
        return {'mission': 'QNT50030', 'status': 'executed', 'scale_case': case, 'ramp_event': event}

    def close_scale_case(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        state = self._ensure_sync(self._refresh())
        scale_case_id = str(payload.get('scale_case_id') or '').strip()
        case = next((x for x in (state.get('scale_cases') or []) if x.get('scale_case_id') == scale_case_id), None)
        if not case:
            raise ValueError('scale_case_id not found')
        if str(case.get('status') or '').lower() not in {'executed', 'approved', 'registered'}:
            raise ValueError('scale case is not eligible for closure')
        case['status'] = 'closed'
        case['closed_at'] = int(time.time())
        case['closed_by'] = str(payload.get('operator') or '').strip()
        case['closure_notes'] = str(payload.get('closure_notes') or '').strip()
        save_state(state)
        append_audit('live_strategy_scale_case_closed', {'scale_case_id': scale_case_id, 'closed_by': case['closed_by']})
        return {'mission': 'QNT50030', 'status': 'closed', 'scale_case': case}

    def reset(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        operator = str(payload.get('operator') or '').strip()
        if not operator:
            raise ValueError('operator is required')
        state = default_state()
        save_state(state)
        append_audit('live_strategy_scale_up_reset', {'operator': operator, 'reason': str(payload.get('reason') or 'manual reset')})
        return {'mission': 'QNT50030', 'status': 'reset', 'state': state}
