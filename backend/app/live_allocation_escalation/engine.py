from __future__ import annotations

import time
import uuid
from typing import Any, Dict

from backend.app.live_allocation_escalation.state_store import append_audit, default_state, load_state, save_state
from backend.app.live_strategy_scale_up.state_store import load_state as load_scale_state
from backend.app.risk_control.state_store import load_state as load_risk_state
from backend.app.treasury_cash_mobility.state_store import load_state as load_treasury_state
from backend.app.performance_engine.state_store import load_state as load_performance_state
from backend.app.institutional_allocation_execution_charter.state_store import load_state as load_charter_state


class LiveAllocationEscalationEngine:
    def __init__(self) -> None:
        self.state = load_state()

    def _refresh(self) -> Dict[str, Any]:
        self.state = load_state()
        return self.state

    def _policy(self, state: Dict[str, Any]) -> Dict[str, Any]:
        return dict(default_state().get('policy', {}), **(state.get('policy') or {}))

    def _trim(self, state: Dict[str, Any]) -> None:
        policy = self._policy(state)
        state['escalation_cases'] = (state.get('escalation_cases') or [])[: int(policy.get('max_escalation_cases', 250))]
        state['escalation_events'] = (state.get('escalation_events') or [])[: int(policy.get('max_escalation_events', 500))]
        state['audit_log'] = (state.get('audit_log') or [])[: int(policy.get('max_audit_events', 500))]

    def _source_snapshot(self) -> Dict[str, Any]:
        scale = load_scale_state()
        risk = load_risk_state()
        treasury = load_treasury_state()
        performance = load_performance_state()
        charter = load_charter_state()

        latest_scale_event = (scale.get('ramp_events') or [None])[0] or {}
        risk_summary = risk.get('summary') if isinstance(risk.get('summary'), dict) else {}
        treasury_balances = treasury.get('balances') or treasury.get('cash_balances') or {}
        total_balance = 0.0
        if isinstance(treasury_balances, dict):
            total_balance = round(sum(float(v or 0.0) for v in treasury_balances.values()), 4)
        last_return = 0.0
        returns = performance.get('returns') or performance.get('return_series') or []
        if isinstance(returns, list) and returns:
            last = returns[0] if isinstance(returns[0], dict) else None
            if isinstance(last, dict):
                last_return = float(last.get('net_return') or last.get('return') or 0.0)
        active_directive = ((charter.get('directives') or [None])[0] or {}) if isinstance(charter, dict) else {}
        return {
            'synced_at': int(time.time()),
            'source': 'manual',
            'latest_scale_event_id': latest_scale_event.get('ramp_event_id') or latest_scale_event.get('event_id'),
            'latest_scale_status': latest_scale_event.get('status', ''),
            'risk_triggered': bool(risk_summary.get('kill_switch_triggered') or risk.get('kill_switch_armed') or False),
            'risk_level': risk_summary.get('kill_switch_level') or risk.get('risk_level') or 'normal',
            'safe_mode': bool(risk.get('safe_mode', True)),
            'execution_mode': risk.get('execution_mode', 'paper'),
            'current_regime': scale.get('last_sync', {}).get('current_regime', 'neutral'),
            'treasury_total_balance': total_balance,
            'latest_return': round(last_return, 6),
            'active_directive_id': active_directive.get('directive_id', ''),
            'directive_status': active_directive.get('status', ''),
        }

    def sync_context(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        state = self._refresh()
        snapshot = self._source_snapshot()
        snapshot['source'] = str(payload.get('source') or 'manual')
        state['last_sync'] = snapshot
        state.setdefault('sync_history', []).insert(0, snapshot)
        state['sync_history'] = state['sync_history'][:100]
        save_state(state)
        append_audit('live_allocation_escalation_context_synced', snapshot)
        return {'mission': 'QNT50031', 'status': 'synced', 'snapshot': snapshot}

    def _ensure_sync(self, state: Dict[str, Any], source: str = 'auto') -> Dict[str, Any]:
        if not state.get('last_sync') and self._policy(state).get('auto_sync_sources', True):
            return self.sync_context({'source': source}).get('snapshot') and load_state()
        return state

    def configure(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        state = self._refresh()
        policy = state.setdefault('policy', {})
        for key, value in payload.items():
            if key in policy and value is not None:
                policy[key] = value
        save_state(state)
        append_audit('live_allocation_escalation_configured', {'policy': policy})
        if payload.get('sync_after_configure', True):
            self.sync_context({'source': 'configure'})
        return {'mission': 'QNT50031', 'status': 'configured', 'policy': policy}

    def summary(self) -> Dict[str, Any]:
        state = self._ensure_sync(self._refresh())
        snapshot = state.get('last_sync') or {}
        return {
            'mission': 'QNT50031',
            'posture': state.get('status', 'degraded'),
            'escalation_case_count': len(state.get('escalation_cases') or []),
            'escalation_event_count': len(state.get('escalation_events') or []),
            'latest_scale_event_id': snapshot.get('latest_scale_event_id'),
            'risk_triggered': snapshot.get('risk_triggered'),
            'safe_mode': snapshot.get('safe_mode'),
            'execution_mode': snapshot.get('execution_mode'),
            'latest_return': snapshot.get('latest_return'),
            'treasury_total_balance': snapshot.get('treasury_total_balance'),
        }

    def register_escalation_case(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        state = self._ensure_sync(self._refresh())
        snapshot = state.get('last_sync') or {}
        policy = self._policy(state)
        scale_event_id = str(payload.get('scale_event_id') or '').strip()
        strategy_id = str(payload.get('strategy_id') or '').strip()
        if not scale_event_id or not strategy_id:
            raise ValueError('scale_event_id and strategy_id are required')
        scale_state = load_scale_state()
        scale_event = next((x for x in (scale_state.get('ramp_events') or []) if (x.get('ramp_event_id') or x.get('event_id')) == scale_event_id), None)
        if not scale_event:
            raise ValueError('scale_event_id not found')
        if policy.get('require_scale_execution', True) and str(scale_event.get('status') or '').lower() != 'executed':
            raise ValueError('scale event must be executed before escalation registration')
        requested_total_weight = round(float(payload.get('requested_total_weight') or 0.0), 4)
        capacity_ceiling_pct = round(float(payload.get('capacity_ceiling_pct') or policy.get('default_capacity_ceiling_pct', 0.4)), 4)
        if requested_total_weight <= 0:
            raise ValueError('requested_total_weight must be greater than zero')
        if policy.get('require_capacity_headroom', True) and requested_total_weight > capacity_ceiling_pct:
            raise ValueError('requested_total_weight exceeds capacity ceiling')
        requested_incremental_capital = round(float(payload.get('requested_incremental_capital') or 0.0), 4)
        if requested_incremental_capital <= 0:
            raise ValueError('requested_incremental_capital must be greater than zero')
        if requested_incremental_capital > float(snapshot.get('treasury_total_balance') or 0.0):
            raise ValueError('requested incremental capital exceeds treasury capacity')
        case = {
            'escalation_case_id': f'escalation_case_{uuid.uuid4().hex[:12]}',
            'created_at': int(time.time()),
            'operator': str(payload.get('operator') or '').strip(),
            'title': str(payload.get('title') or '').strip(),
            'scale_event_id': scale_event_id,
            'strategy_id': strategy_id,
            'symbol': str(payload.get('symbol') or scale_event.get('symbol') or '').strip(),
            'broker': str(payload.get('broker') or scale_event.get('broker') or 'paper').strip(),
            'current_weight': round(float(payload.get('current_weight') or scale_event.get('target_weight') or 0.0), 4),
            'requested_total_weight': requested_total_weight,
            'requested_incremental_capital': requested_incremental_capital,
            'capacity_ceiling_pct': capacity_ceiling_pct,
            'escalation_step_pct': round(float(payload.get('escalation_step_pct') or policy.get('default_escalation_step_pct', 0.05)), 4),
            'allocation_reason': str(payload.get('allocation_reason') or '').strip(),
            'directive_id': str(payload.get('directive_id') or snapshot.get('active_directive_id') or '').strip(),
            'notes': str(payload.get('notes') or '').strip(),
            'status': 'registered',
        }
        if not case['operator'] or not case['title']:
            raise ValueError('operator and title are required')
        state.setdefault('escalation_cases', []).insert(0, case)
        self._trim(state)
        save_state(state)
        append_audit('live_allocation_escalation_registered', case)
        return {'mission': 'QNT50031', 'status': 'registered', 'escalation_case': case}

    def approve_escalation(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        state = self._ensure_sync(self._refresh())
        snapshot = state.get('last_sync') or {}
        policy = self._policy(state)
        case_id = str(payload.get('escalation_case_id') or '').strip()
        case = next((x for x in (state.get('escalation_cases') or []) if x.get('escalation_case_id') == case_id), None)
        if not case:
            raise ValueError('escalation_case_id not found')
        if policy.get('require_risk_clearance', True) and snapshot.get('risk_triggered'):
            raise ValueError('cannot approve escalation while risk kill-switch is active')
        mode = str(payload.get('mode') or 'paper').strip().lower()
        if mode == 'live' and (snapshot.get('safe_mode') or not policy.get('allow_live_escalation', False)):
            raise ValueError('live escalation approval is blocked while safe mode is enabled or live escalation policy is disabled')
        approved_total_weight = round(float(payload.get('approved_total_weight') or case.get('requested_total_weight') or 0.0), 4)
        capacity_ceiling_pct = round(float(case.get('capacity_ceiling_pct') or 0.0), 4)
        if approved_total_weight > capacity_ceiling_pct:
            raise ValueError('approved_total_weight exceeds capacity ceiling')
        case['status'] = 'approved'
        case['approved_at'] = int(time.time())
        case['approved_by'] = str(payload.get('operator') or '').strip()
        case['approved_total_weight'] = approved_total_weight
        case['approved_incremental_capital'] = round(float(payload.get('approved_incremental_capital') or case.get('requested_incremental_capital') or 0.0), 4)
        case['approved_mode'] = mode
        case['approval_notes'] = str(payload.get('approval_notes') or '').strip()
        save_state(state)
        append_audit('live_allocation_escalation_approved', {'escalation_case_id': case_id, 'approved_total_weight': approved_total_weight, 'mode': mode})
        return {'mission': 'QNT50031', 'status': 'approved', 'escalation_case': case}

    def execute_escalation(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        state = self._ensure_sync(self._refresh())
        snapshot = state.get('last_sync') or {}
        case_id = str(payload.get('escalation_case_id') or '').strip()
        case = next((x for x in (state.get('escalation_cases') or []) if x.get('escalation_case_id') == case_id), None)
        if not case:
            raise ValueError('escalation_case_id not found')
        if str(case.get('status') or '').lower() != 'approved':
            raise ValueError('escalation case must be approved before execution')
        mode = str(payload.get('execution_mode') or case.get('approved_mode') or 'paper').strip().lower()
        if mode == 'live' and snapshot.get('safe_mode'):
            raise ValueError('cannot execute live escalation while safe mode is enabled')
        event = {
            'escalation_event_id': f'escalation_event_{uuid.uuid4().hex[:12]}',
            'executed_at': int(time.time()),
            'operator': str(payload.get('operator') or '').strip(),
            'escalation_case_id': case_id,
            'scale_event_id': case.get('scale_event_id'),
            'strategy_id': case.get('strategy_id'),
            'symbol': case.get('symbol'),
            'broker': case.get('broker'),
            'execution_mode': mode,
            'incremental_capital_deployed': round(float(payload.get('incremental_capital_deployed') or case.get('approved_incremental_capital') or 0.0), 4),
            'total_weight': round(float(payload.get('total_weight') or case.get('approved_total_weight') or 0.0), 4),
            'release_to': str(payload.get('release_to') or 'allocation_engine').strip(),
            'result_summary': str(payload.get('result_summary') or '').strip(),
            'status': 'executed',
        }
        case['status'] = 'executed'
        case['executed_at'] = event['executed_at']
        case['last_escalation_event_id'] = event['escalation_event_id']
        state.setdefault('escalation_events', []).insert(0, event)
        self._trim(state)
        save_state(state)
        append_audit('live_allocation_escalation_executed', event)
        return {'mission': 'QNT50031', 'status': 'executed', 'escalation_event': event, 'escalation_case': case}

    def close_escalation_case(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        state = self._ensure_sync(self._refresh())
        case_id = str(payload.get('escalation_case_id') or '').strip()
        case = next((x for x in (state.get('escalation_cases') or []) if x.get('escalation_case_id') == case_id), None)
        if not case:
            raise ValueError('escalation_case_id not found')
        if str(case.get('status') or '').lower() not in {'executed', 'approved'}:
            raise ValueError('escalation case must be approved or executed before closure')
        case['status'] = 'closed'
        case['closed_at'] = int(time.time())
        case['closed_by'] = str(payload.get('operator') or '').strip()
        case['closure_notes'] = str(payload.get('closure_notes') or '').strip()
        save_state(state)
        append_audit('live_allocation_escalation_closed', {'escalation_case_id': case_id, 'closed_by': case.get('closed_by')})
        return {'mission': 'QNT50031', 'status': 'closed', 'escalation_case': case}

    def reset(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        operator = str(payload.get('operator') or '').strip()
        if not operator:
            raise ValueError('operator is required')
        state = default_state()
        save_state(state)
        append_audit('live_allocation_escalation_reset', {'operator': operator, 'reason': str(payload.get('reason') or 'manual reset')})
        return {'mission': 'QNT50031', 'status': 'reset'}
