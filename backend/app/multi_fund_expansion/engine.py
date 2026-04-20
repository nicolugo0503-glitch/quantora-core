from __future__ import annotations

import time
import uuid
from typing import Any, Dict

from backend.app.live_allocation_escalation.state_store import load_state as load_allocation_state
from backend.app.risk_control.state_store import load_state as load_risk_state
from backend.app.treasury_cash_mobility.state_store import load_state as load_treasury_state
from backend.app.institutional_allocation_execution_charter.state_store import load_state as load_charter_state
from .state_store import append_audit, default_state, load_state, save_state


class MultiFundExpansionEngine:
    def __init__(self) -> None:
        self.state = load_state()

    def _refresh(self) -> Dict[str, Any]:
        self.state = load_state()
        return self.state

    def _policy(self, state: Dict[str, Any]) -> Dict[str, Any]:
        return dict(default_state().get('policy', {}), **(state.get('policy') or {}))

    def _trim(self, state: Dict[str, Any]) -> None:
        policy = self._policy(state)
        state['launch_cases'] = (state.get('launch_cases') or [])[: int(policy.get('max_launch_cases', 250))]
        state['launch_events'] = (state.get('launch_events') or [])[: int(policy.get('max_launch_events', 500))]
        state['audit_log'] = (state.get('audit_log') or [])[: int(policy.get('max_audit_events', 500))]

    def _source_snapshot(self) -> Dict[str, Any]:
        allocation = load_allocation_state()
        risk = load_risk_state()
        treasury = load_treasury_state()
        charter = load_charter_state()
        latest_escalation_event = next(iter(allocation.get('escalation_events') or []), None)
        risk_summary = risk.get('summary') or {}
        balances = treasury.get('cash_balances') or treasury.get('balances') or {}
        total_balance = round(sum(float(v) for v in balances.values() if isinstance(v, (int, float))), 2) if balances else 0.0
        active_directive = next((x for x in (charter.get('directives') or []) if str(x.get('status') or '').lower() in {'approved','executed','active'}), None)
        return {
            'synced_at': int(time.time()),
            'latest_escalation_event_id': (latest_escalation_event or {}).get('escalation_event_id', ''),
            'latest_escalation_status': (latest_escalation_event or {}).get('status', ''),
            'risk_triggered': bool(risk_summary.get('kill_switch_triggered') or risk_summary.get('kill_switch_armed')),
            'risk_level': risk_summary.get('kill_switch_level', 'normal'),
            'safe_mode': bool(risk_summary.get('safe_mode', True)),
            'execution_mode': risk_summary.get('execution_mode', 'paper'),
            'treasury_total_balance': total_balance,
            'active_directive_id': (active_directive or {}).get('directive_id', ''),
            'directive_status': (active_directive or {}).get('status', ''),
        }

    def sync_context(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        state = self._refresh()
        snapshot = self._source_snapshot()
        state['last_sync'] = snapshot
        state.setdefault('sync_history', []).insert(0, {
            'mission': 'QNT50033',
            'timestamp': snapshot['synced_at'],
            'source': str(payload.get('source') or 'manual'),
            'snapshot': snapshot,
        })
        state['sync_history'] = state['sync_history'][:100]
        save_state(state)
        append_audit('multi_fund_expansion_context_synced', {'mission': 'QNT50033', 'snapshot': snapshot})
        return {'mission': 'QNT50033', 'status': 'synced', 'snapshot': snapshot}

    def _ensure_sync(self, state: Dict[str, Any], source: str = 'manual') -> Dict[str, Any]:
        policy = self._policy(state)
        if policy.get('auto_sync_sources', True) and not state.get('last_sync'):
            return self.sync_context({'source': source}) and self._refresh()
        return state

    def configure(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        state = self._refresh()
        policy = state.setdefault('policy', {})
        for key, value in payload.items():
            if key in default_state()['policy'] and value is not None:
                policy[key] = value
        save_state(state)
        if payload.get('sync_after_configure', True):
            self.sync_context({'source': 'configure'})
        append_audit('multi_fund_expansion_configured', {'mission': 'QNT50033', 'policy': policy})
        return {'mission': 'QNT50033', 'status': 'configured', 'policy': policy}

    def register_launch_case(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        state = self._ensure_sync(self._refresh(), 'register')
        snapshot = state.get('last_sync') or {}
        policy = self._policy(state)
        if policy.get('require_escalation_execution', True) and not snapshot.get('latest_escalation_event_id'):
            raise ValueError('executed QNT50031 escalation evidence is required before vehicle launch registration')
        if policy.get('require_risk_clearance', True) and snapshot.get('risk_triggered'):
            raise ValueError('cannot register launch case while risk kill-switch is active')
        if policy.get('require_charter_alignment', True) and not snapshot.get('active_directive_id'):
            raise ValueError('active institutional directive is required for vehicle launch registration')
        operator = str(payload.get('operator') or '').strip()
        vehicle_name = str(payload.get('vehicle_name') or '').strip()
        if not operator or not vehicle_name:
            raise ValueError('operator and vehicle_name are required')
        seed_capital = round(float(payload.get('seed_capital_required') or 0.0), 2)
        seed_floor = round(float(payload.get('seed_capital_floor') or policy.get('default_seed_capital_floor', 250000.0)), 2)
        if seed_capital < seed_floor:
            raise ValueError('seed_capital_required is below configured seed capital floor')
        if policy.get('require_treasury_capacity', True) and seed_capital > float(snapshot.get('treasury_total_balance') or 0.0):
            raise ValueError('seed capital requirement exceeds treasury capacity')
        target_capacity = round(float(payload.get('target_capacity_pct') or policy.get('default_capacity_target', 0.2)), 4)
        case = {
            'launch_case_id': f'launch_case_{uuid.uuid4().hex[:12]}',
            'created_at': int(time.time()),
            'operator': operator,
            'vehicle_name': vehicle_name,
            'vehicle_type': str(payload.get('vehicle_type') or 'fund').strip(),
            'jurisdiction': str(payload.get('jurisdiction') or '').strip(),
            'launch_reason': str(payload.get('launch_reason') or '').strip(),
            'strategy_scope': str(payload.get('strategy_scope') or '').strip(),
            'seed_capital_required': seed_capital,
            'seed_capital_floor': seed_floor,
            'target_capacity_pct': target_capacity,
            'escalation_event_id': str(payload.get('escalation_event_id') or snapshot.get('latest_escalation_event_id') or '').strip(),
            'directive_id': str(payload.get('directive_id') or snapshot.get('active_directive_id') or '').strip(),
            'launch_mode': str(payload.get('launch_mode') or 'paper').strip().lower(),
            'notes': str(payload.get('notes') or '').strip(),
            'status': 'registered',
        }
        state.setdefault('launch_cases', []).insert(0, case)
        self._trim(state)
        save_state(state)
        append_audit('multi_fund_expansion_registered', case)
        return {'mission': 'QNT50033', 'status': 'registered', 'launch_case': case}

    def approve_launch(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        state = self._ensure_sync(self._refresh(), 'approve')
        snapshot = state.get('last_sync') or {}
        case_id = str(payload.get('launch_case_id') or '').strip()
        case = next((x for x in (state.get('launch_cases') or []) if x.get('launch_case_id') == case_id), None)
        if not case:
            raise ValueError('launch_case_id not found')
        if snapshot.get('risk_triggered'):
            raise ValueError('cannot approve launch while risk kill-switch is active')
        mode = str(payload.get('approval_mode') or case.get('launch_mode') or 'paper').strip().lower()
        if mode == 'live' and snapshot.get('safe_mode'):
            raise ValueError('live vehicle launch approval is blocked while safe mode is enabled')
        case['status'] = 'approved'
        case['approved_at'] = int(time.time())
        case['approved_by'] = str(payload.get('operator') or '').strip()
        case['approved_seed_capital'] = round(float(payload.get('approved_seed_capital') or case.get('seed_capital_required') or 0.0), 2)
        case['approved_vehicle_code'] = str(payload.get('approved_vehicle_code') or '').strip()
        case['approval_mode'] = mode
        case['approval_notes'] = str(payload.get('approval_notes') or '').strip()
        save_state(state)
        append_audit('multi_fund_expansion_approved', {'launch_case_id': case_id, 'approval_mode': mode})
        return {'mission': 'QNT50033', 'status': 'approved', 'launch_case': case}

    def execute_launch(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        state = self._ensure_sync(self._refresh(), 'execute')
        snapshot = state.get('last_sync') or {}
        case_id = str(payload.get('launch_case_id') or '').strip()
        case = next((x for x in (state.get('launch_cases') or []) if x.get('launch_case_id') == case_id), None)
        if not case:
            raise ValueError('launch_case_id not found')
        if str(case.get('status') or '').lower() != 'approved':
            raise ValueError('launch case must be approved before execution')
        mode = str(payload.get('execution_mode') or case.get('approval_mode') or 'paper').strip().lower()
        if mode == 'live' and snapshot.get('safe_mode'):
            raise ValueError('cannot execute live vehicle launch while safe mode is enabled')
        event = {
            'launch_event_id': f'launch_event_{uuid.uuid4().hex[:12]}',
            'executed_at': int(time.time()),
            'operator': str(payload.get('operator') or '').strip(),
            'launch_case_id': case_id,
            'vehicle_name': case.get('vehicle_name'),
            'vehicle_type': case.get('vehicle_type'),
            'jurisdiction': case.get('jurisdiction'),
            'execution_mode': mode,
            'vehicle_code': str(payload.get('vehicle_code') or case.get('approved_vehicle_code') or '').strip(),
            'seed_capital_deployed': round(float(payload.get('seed_capital_deployed') or case.get('approved_seed_capital') or 0.0), 2),
            'launch_destination': str(payload.get('launch_destination') or 'vehicle_registry').strip(),
            'result_summary': str(payload.get('result_summary') or '').strip(),
            'status': 'executed',
        }
        case['status'] = 'executed'
        case['executed_at'] = event['executed_at']
        case['last_launch_event_id'] = event['launch_event_id']
        state.setdefault('launch_events', []).insert(0, event)
        self._trim(state)
        save_state(state)
        append_audit('multi_fund_expansion_executed', event)
        return {'mission': 'QNT50033', 'status': 'executed', 'launch_event': event, 'launch_case': case}

    def close_launch_case(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        state = self._ensure_sync(self._refresh(), 'close')
        case_id = str(payload.get('launch_case_id') or '').strip()
        case = next((x for x in (state.get('launch_cases') or []) if x.get('launch_case_id') == case_id), None)
        if not case:
            raise ValueError('launch_case_id not found')
        if str(case.get('status') or '').lower() not in {'approved', 'executed'}:
            raise ValueError('launch case must be approved or executed before closure')
        case['status'] = 'closed'
        case['closed_at'] = int(time.time())
        case['closed_by'] = str(payload.get('operator') or '').strip()
        case['closure_notes'] = str(payload.get('closure_notes') or '').strip()
        save_state(state)
        append_audit('multi_fund_expansion_closed', {'launch_case_id': case_id, 'closed_by': case.get('closed_by')})
        return {'mission': 'QNT50033', 'status': 'closed', 'launch_case': case}

    def reset(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        operator = str(payload.get('operator') or '').strip()
        if not operator:
            raise ValueError('operator is required')
        save_state(default_state())
        append_audit('multi_fund_expansion_reset', {'operator': operator, 'reason': str(payload.get('reason') or 'manual reset')})
        return {'mission': 'QNT50033', 'status': 'reset'}

    def summary(self) -> Dict[str, Any]:
        state = self._refresh()
        snapshot = state.get('last_sync') or {}
        return {
            'mission': 'QNT50033',
            'posture': state.get('status', 'degraded'),
            'launch_case_count': len(state.get('launch_cases') or []),
            'launch_event_count': len(state.get('launch_events') or []),
            'safe_mode': snapshot.get('safe_mode', True),
            'execution_mode': snapshot.get('execution_mode', 'paper'),
            'latest_escalation_event_id': snapshot.get('latest_escalation_event_id', ''),
            'treasury_total_balance': snapshot.get('treasury_total_balance', 0.0),
            'active_directive_id': snapshot.get('active_directive_id', ''),
        }
