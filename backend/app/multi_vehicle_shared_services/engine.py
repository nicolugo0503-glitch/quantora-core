from __future__ import annotations

import time
import uuid
from typing import Any, Dict

from backend.app.multi_vehicle_shared_services.state_store import append_audit, default_state, load_state, save_state


class MultiVehicleSharedServicesEngine:
    def __init__(self) -> None:
        self.state = load_state()

    def _refresh(self) -> Dict[str, Any]:
        self.state = load_state()
        return self.state

    def _policy(self, state: Dict[str, Any]) -> Dict[str, Any]:
        return dict((state or {}).get('policy') or {})

    def _trim(self, state: Dict[str, Any]) -> None:
        policy = self._policy(state)
        state['service_models'] = (state.get('service_models') or [])[: int(policy.get('max_service_models', 250))]
        state['service_events'] = (state.get('service_events') or [])[: int(policy.get('max_service_events', 500))]
        state['audit_log'] = (state.get('audit_log') or [])[: int(policy.get('max_audit_events', 500))]

    def _source_snapshot(self) -> Dict[str, Any]:
        snapshot: Dict[str, Any] = {
            'synced_at': int(time.time()),
            'safe_mode': True,
            'risk_triggered': False,
            'execution_mode': 'paper',
            'latest_launch_case_id': '',
            'latest_launch_status': '',
            'latest_launch_event_id': '',
            'treasury_total_balance': 0.0,
            'active_directive_id': '',
            'directive_status': '',
        }
        try:
            from backend.app.multi_fund_expansion.state_store import load_state as load_launch_state
            launch = load_launch_state()
            cases = launch.get('launch_cases') or []
            events = launch.get('launch_events') or []
            latest_case = cases[0] if cases else {}
            latest_event = events[0] if events else {}
            snapshot['latest_launch_case_id'] = str(latest_case.get('launch_case_id') or '')
            snapshot['latest_launch_status'] = str(latest_case.get('status') or '')
            snapshot['latest_launch_event_id'] = str(latest_event.get('launch_event_id') or '')
        except Exception:
            pass
        try:
            from backend.app.treasury_cash_mobility.state_store import load_state as load_treasury_state
            treasury = load_treasury_state()
            balances = treasury.get('balances') or treasury.get('cash_balances') or {}
            if isinstance(balances, dict):
                snapshot['treasury_total_balance'] = round(sum(v for v in balances.values() if isinstance(v, (int, float))), 2)
            summary = treasury.get('summary') or {}
            snapshot['safe_mode'] = bool(summary.get('safe_mode', snapshot['safe_mode']))
            snapshot['execution_mode'] = str(summary.get('execution_mode') or snapshot['execution_mode'])
        except Exception:
            pass
        try:
            from backend.app.risk_control.state_store import load_state as load_risk_state
            risk = load_risk_state()
            summary = risk.get('summary') or risk.get('last_summary') or {}
            snapshot['risk_triggered'] = bool(summary.get('kill_switch_triggered') or summary.get('triggered') or risk.get('kill_switch_triggered') or False)
        except Exception:
            pass
        try:
            from backend.app.institutional_allocation_execution_charter.state_store import load_state as load_charter_state
            charter = load_charter_state()
            directives = charter.get('directives') or []
            active = next((d for d in directives if str(d.get('status') or '').lower() in {'active','approved','executed'}), {})
            snapshot['active_directive_id'] = str(active.get('directive_id') or '')
            snapshot['directive_status'] = str(active.get('status') or '')
        except Exception:
            pass
        return snapshot

    def sync_context(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        state = self._refresh()
        snap = self._source_snapshot()
        state['last_sync'] = {
            'mission': 'QNT50034',
            'timestamp': int(time.time()),
            'source': str(payload.get('source') or 'manual'),
            'snapshot': snap,
        }
        state.setdefault('sync_history', []).insert(0, state['last_sync'])
        state['sync_history'] = state['sync_history'][:100]
        save_state(state)
        append_audit('multi_vehicle_shared_services_context_synced', {'source': state['last_sync']['source'], 'snapshot': snap})
        return {'mission': 'QNT50034', 'status': 'synced', 'snapshot': snap}

    def _ensure_sync(self, state: Dict[str, Any], action: str) -> Dict[str, Any]:
        policy = self._policy(state)
        if not state.get('last_sync') and policy.get('auto_sync_sources', True):
            self.sync_context({'source': action})
            return self._refresh()
        return state

    def configure(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        state = self._refresh()
        policy = state.setdefault('policy', {})
        for k, v in payload.items():
            if k in {'sync_after_configure'}:
                continue
            if v is not None:
                policy[k] = v
        save_state(state)
        if payload.get('sync_after_configure', True):
            self.sync_context({'source': 'configure'})
        append_audit('multi_vehicle_shared_services_configured', {'policy': policy})
        return {'mission': 'QNT50034', 'status': 'configured', 'policy': policy}

    def register_service_model(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        state = self._ensure_sync(self._refresh(), 'register')
        snap = ((state.get('last_sync') or {}).get('snapshot') or {})
        policy = self._policy(state)
        if policy.get('require_vehicle_launch_execution', True) and not snap.get('latest_launch_event_id'):
            raise ValueError('executed QNT50033 vehicle launch evidence is required before shared-services registration')
        if policy.get('require_charter_alignment', True) and not snap.get('active_directive_id'):
            raise ValueError('active institutional directive is required for shared-services registration')
        if snap.get('risk_triggered'):
            raise ValueError('cannot register shared-services model while risk kill-switch is active')
        operator = str(payload.get('operator') or '').strip()
        service_name = str(payload.get('service_name') or '').strip()
        if not operator or not service_name:
            raise ValueError('operator and service_name are required')
        annual_budget = round(float(payload.get('annual_budget') or 0.0), 2)
        minimum_vehicles = int(payload.get('minimum_supported_vehicles') or policy.get('default_minimum_supported_vehicles', 2))
        model = {
            'service_model_id': f'service_model_{uuid.uuid4().hex[:12]}',
            'created_at': int(time.time()),
            'operator': operator,
            'service_name': service_name,
            'service_type': str(payload.get('service_type') or 'shared-services').strip(),
            'operating_region': str(payload.get('operating_region') or 'global').strip(),
            'supported_vehicle_types': list(payload.get('supported_vehicle_types') or []),
            'minimum_supported_vehicles': minimum_vehicles,
            'annual_budget': annual_budget,
            'budget_source': str(payload.get('budget_source') or 'opex').strip(),
            'service_scope': str(payload.get('service_scope') or '').strip(),
            'launch_event_id': str(payload.get('launch_event_id') or snap.get('latest_launch_event_id') or '').strip(),
            'directive_id': str(payload.get('directive_id') or snap.get('active_directive_id') or '').strip(),
            'operating_mode': str(payload.get('operating_mode') or 'paper').strip().lower(),
            'notes': str(payload.get('notes') or '').strip(),
            'status': 'registered',
        }
        state.setdefault('service_models', []).insert(0, model)
        self._trim(state)
        save_state(state)
        append_audit('multi_vehicle_shared_services_registered', model)
        return {'mission': 'QNT50034', 'status': 'registered', 'service_model': model}

    def approve_service_model(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        state = self._ensure_sync(self._refresh(), 'approve')
        snap = ((state.get('last_sync') or {}).get('snapshot') or {})
        service_model_id = str(payload.get('service_model_id') or '').strip()
        model = next((x for x in (state.get('service_models') or []) if x.get('service_model_id') == service_model_id), None)
        if not model:
            raise ValueError('service_model_id not found')
        mode = str(payload.get('approval_mode') or model.get('operating_mode') or 'paper').strip().lower()
        if mode == 'live' and snap.get('safe_mode'):
            raise ValueError('live shared-services approval is blocked while safe mode is enabled')
        if snap.get('risk_triggered'):
            raise ValueError('cannot approve shared-services model while risk kill-switch is active')
        model['status'] = 'approved'
        model['approved_at'] = int(time.time())
        model['approved_by'] = str(payload.get('operator') or '').strip()
        model['approval_mode'] = mode
        model['approved_budget'] = round(float(payload.get('approved_budget') or model.get('annual_budget') or 0.0), 2)
        model['approval_notes'] = str(payload.get('approval_notes') or '').strip()
        save_state(state)
        append_audit('multi_vehicle_shared_services_approved', {'service_model_id': service_model_id, 'approval_mode': mode})
        return {'mission': 'QNT50034', 'status': 'approved', 'service_model': model}

    def execute_service_model(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        state = self._ensure_sync(self._refresh(), 'execute')
        snap = ((state.get('last_sync') or {}).get('snapshot') or {})
        service_model_id = str(payload.get('service_model_id') or '').strip()
        model = next((x for x in (state.get('service_models') or []) if x.get('service_model_id') == service_model_id), None)
        if not model:
            raise ValueError('service_model_id not found')
        if str(model.get('status') or '').lower() != 'approved':
            raise ValueError('service model must be approved before execution')
        mode = str(payload.get('execution_mode') or model.get('approval_mode') or 'paper').strip().lower()
        if mode == 'live' and snap.get('safe_mode'):
            raise ValueError('cannot execute live shared-services model while safe mode is enabled')
        event = {
            'service_event_id': f'service_event_{uuid.uuid4().hex[:12]}',
            'executed_at': int(time.time()),
            'operator': str(payload.get('operator') or '').strip(),
            'service_model_id': service_model_id,
            'service_name': model.get('service_name'),
            'execution_mode': mode,
            'service_destination': str(payload.get('service_destination') or 'shared_services_registry').strip(),
            'vehicle_count': int(payload.get('vehicle_count') or model.get('minimum_supported_vehicles') or 0),
            'result_summary': str(payload.get('result_summary') or '').strip(),
            'status': 'executed',
        }
        model['status'] = 'executed'
        model['executed_at'] = event['executed_at']
        model['last_service_event_id'] = event['service_event_id']
        state.setdefault('service_events', []).insert(0, event)
        self._trim(state)
        save_state(state)
        append_audit('multi_vehicle_shared_services_executed', event)
        return {'mission': 'QNT50034', 'status': 'executed', 'service_event': event, 'service_model': model}

    def close_service_model(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        state = self._ensure_sync(self._refresh(), 'close')
        service_model_id = str(payload.get('service_model_id') or '').strip()
        model = next((x for x in (state.get('service_models') or []) if x.get('service_model_id') == service_model_id), None)
        if not model:
            raise ValueError('service_model_id not found')
        if str(model.get('status') or '').lower() not in {'approved', 'executed'}:
            raise ValueError('service model must be approved or executed before closure')
        model['status'] = 'closed'
        model['closed_at'] = int(time.time())
        model['closed_by'] = str(payload.get('operator') or '').strip()
        model['closure_notes'] = str(payload.get('closure_notes') or '').strip()
        save_state(state)
        append_audit('multi_vehicle_shared_services_closed', {'service_model_id': service_model_id, 'closed_by': model.get('closed_by')})
        return {'mission': 'QNT50034', 'status': 'closed', 'service_model': model}

    def reset(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        operator = str(payload.get('operator') or '').strip()
        if not operator:
            raise ValueError('operator is required')
        save_state(default_state())
        append_audit('multi_vehicle_shared_services_reset', {'operator': operator, 'reason': str(payload.get('reason') or 'manual reset')})
        return {'mission': 'QNT50034', 'status': 'reset'}

    def summary(self) -> Dict[str, Any]:
        state = self._refresh()
        snap = ((state.get('last_sync') or {}).get('snapshot') or {})
        return {
            'mission': 'QNT50034',
            'posture': state.get('status', 'degraded'),
            'safe_mode': bool(snap.get('safe_mode', True)),
            'risk_triggered': bool(snap.get('risk_triggered', False)),
            'latest_launch_event_id': snap.get('latest_launch_event_id'),
            'active_directive_id': snap.get('active_directive_id'),
            'service_model_count': len(state.get('service_models') or []),
            'service_event_count': len(state.get('service_events') or []),
        }
